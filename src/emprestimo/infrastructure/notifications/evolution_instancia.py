"""Cliente de gestão de instância do Evolution Go (IMP-366, PLAN-034).

Separado de `EvolutionWhatsAppNotificationChannel` **de propósito**, e não por
organização de arquivos: são dois níveis de autenticação diferentes.

- criar instância usa a chave do **Tenant**, com header `X-Tenant-ID`;
- todo o resto usa o token da **instância**, sozinho.

O contrato §0 registra um incidente real causado por confundir as duas. Aqui a
confusão é impossível por construção — as credenciais entram por construtores
distintos, e nenhum método alcança a chave que não é a sua.

Tudo o que este módulo declara foi observado contra o servidor real em
2026-08-31, ao fechar o IMP-352. Onde a documentação pública e a resposta real
divergiam, vale a resposta.
"""

from __future__ import annotations

import base64
import binascii
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from emprestimo.domain.platform.conexao_whatsapp import EstadoPareamento
from emprestimo.domain.platform.ports import ProvedorWhatsApp

PREFIXO_QR = "data:image/png;base64,"
"""Prefixo que o contrato promete no campo `Qrcode`."""

ASSINATURA_PNG = bytes.fromhex("89504e470d0a1a0a")
FIM_PNG = bytes.fromhex("0000000049454e44ae426082")
"""Assinatura inicial e chunk IEND final. Juntos, pegam conteudo que nao e
PNG e payload truncado — os dois casos em que a tela receberia uma imagem que
nao renderiza."""

EVENTOS_ASSINADOS = ("MESSAGE", "CONNECTION", "QRCODE")
"""Únicos valores aceitos pelo `subscribe`.

O contrato §4 avisa que qualquer outro valor é **descartado em silêncio** — sem
erro, só um log no servidor que ninguém vê. Fixar a tupla aqui evita descobrir
isso pela ausência de eventos.
"""


class EvolutionIndisponivelError(RuntimeError):
    """O provedor não respondeu, ou respondeu o que não se esperava.

    Distinta de erro de negócio: aqui não há decisão a tomar, há um serviço
    externo fora do ar ou mudando contrato sem avisar.
    """


class QrCodeAindaGerandoError(EvolutionIndisponivelError):
    """O QR ainda nao existe — estado NORMAL logo apos `/instance/connect`.

    O contrato (Evento 4.2) descreve a corrida: o servidor responde "no QR code
    available. Please wait a moment and try again", e o CRM deve aguardar 3s e
    repetir, ate 5 vezes.

    Escolhemos **sinalizar em vez de dormir**: a tela ja faz polling, e bloquear
    o handler HTTP por ate 15 segundos trocaria uma espera visivel do usuario
    por uma requisicao pendurada. Quem chama distingue "gerando" de "provedor
    fora" — que era exatamente o que colapsar os dois impedia.
    """


@dataclass(frozen=True)
class InstanciaCriada:
    instancia_id: str
    nome: str
    token: str


@dataclass(frozen=True)
class EstadoInstancia:
    """Estado do pareamento, como o provedor o reporta.

    `conectado` é o socket de pé; `pareado` é o número vinculado. São coisas
    diferentes, e só a segunda significa WhatsApp funcionando — verificado em
    2026-08-31, quando a instância recém-criada respondeu `Connected: true` com
    `LoggedIn: false`.
    """

    conectado: bool
    pareado: bool
    nome_exibicao: str | None


def _base(host: str) -> str:
    normalizado = host.strip().rstrip("/")
    if not normalizado:
        raise ValueError("EVOLUTION_HOST vazio")
    return normalizado


def _exigir_png(base64_puro: str) -> None:
    """Confere que o payload decodifica e e mesmo um PNG.

    O prefixo sozinho nao garante nada: `data:image/png;base64,` seguido de
    vazio, ou de base64 quebrado, passaria por `startswith` e chegaria a tela
    como um QR que nao aparece — sem erro em lugar nenhum.
    """
    if not base64_puro:
        raise EvolutionIndisponivelError("/instance/qr devolveu data URI sem conteudo")
    try:
        bruto = base64.b64decode(base64_puro, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EvolutionIndisponivelError("/instance/qr devolveu base64 invalido") from exc
    if not bruto.startswith(ASSINATURA_PNG):
        raise EvolutionIndisponivelError("/instance/qr devolveu conteudo que nao e PNG")
    # O chunk IEND fecha todo PNG e e sempre estes doze bytes. Exigi-lo pega
    # payload truncado — que a assinatura sozinha nao pega — sem parser de
    # imagem nem dependencia nova. Validar a estrutura inteira de chunks seria
    # desproporcional: um PNG corrompido aparece na hora como imagem quebrada,
    # ao lado do botao de gerar outro, e nao corrompe estado nenhum.
    if not bruto.endswith(FIM_PNG):
        raise EvolutionIndisponivelError("/instance/qr devolveu PNG truncado")


def _executar(chamada: Callable[[], httpx.Response], rota: str) -> httpx.Response:
    """Traduz falha de transporte para o erro declarado deste modulo.

    Sem isto, DNS quebrado, conexao recusada ou timeout escapam como excecao
    `httpx` crua — e o chamador, que trata `EvolutionIndisponivelError`, nao a
    veria. O adapter de envio ja fazia essa traducao; este cliente precisa fazer
    igual, senao a mesma indisponibilidade se comporta de dois jeitos conforme a
    rota.
    """
    try:
        return chamada()
    # `RequestError` e a base de tudo que o httpx levanta do lado da requisicao:
    # timeout, transporte E `DecodingError` — esta ultima nao deriva de
    # `TransportError`, entao um `Content-Encoding: gzip` com corpo truncado
    # escaparia crua para o handler HTTP, que so trata o erro deste modulo.
    except httpx.RequestError as exc:
        raise EvolutionIndisponivelError(f"{rota} inacessivel: {type(exc).__name__}") from exc


def _booleano(dados: dict[str, Any], campo: str, rota: str) -> bool:
    """Exige booleano de verdade, nao qualquer coisa que `bool()` aceite.

    `bool("false")` e `True`: um provedor devolvendo a string "false" faria o
    sistema reportar PAREADO quando ele disse o contrario. E campo ausente
    viraria `False` silenciosamente, que e indistinguivel de "nao pareado" —
    quando na verdade significa que a resposta mudou de forma.
    """
    valor = dados.get(campo)
    if not isinstance(valor, bool):
        raise EvolutionIndisponivelError(
            f"{rota} devolveu {campo}={valor!r}, que nao e booleano: "
            "a resposta do provedor mudou de forma"
        )
    return valor


def _mensagem_do_provedor(resposta: httpx.Response) -> str:
    """Extrai o texto de erro que o provedor mandou, sem deixar vazar HTML."""
    try:
        corpo = resposta.json()
    except ValueError:
        return ""
    if not isinstance(corpo, dict):
        return ""
    for chave in ("error", "message"):
        valor = corpo.get(chave)
        if isinstance(valor, str) and valor:
            return valor
    return ""


def _json(resposta: httpx.Response, rota: str) -> dict[str, Any]:
    # 2xx exigido, e nao apenas "menor que 400": um 301 ou 307 de proxy nao e
    # sucesso, e trata-lo como tal faria o sistema acreditar numa operacao que
    # o provedor nunca executou. `httpx` nao segue redirect por padrao.
    if not resposta.is_success:
        detalhe = _mensagem_do_provedor(resposta)
        sufixo = f": {detalhe}" if detalhe else ""
        raise EvolutionIndisponivelError(f"{rota} respondeu {resposta.status_code}{sufixo}")
    try:
        corpo = resposta.json()
    except ValueError as exc:
        raise EvolutionIndisponivelError(f"{rota} respondeu corpo nao-JSON") from exc
    if not isinstance(corpo, dict):
        raise EvolutionIndisponivelError(f"{rota} respondeu JSON que nao e objeto")
    dados = corpo.get("data", corpo)
    return dados if isinstance(dados, dict) else corpo


class EvolutionTenantClient:
    """Cria instâncias dentro de um tenant. Único uso da chave de Tenant."""

    def __init__(
        self,
        *,
        host: str,
        tenant_id: str,
        api_key: str,
        client: httpx.Client | None = None,
    ) -> None:
        if not tenant_id.strip() or not api_key.strip():
            raise ValueError("credenciais de tenant do Evolution incompletas")
        self._tenant_id = tenant_id.strip()
        self._api_key = api_key.strip()
        self._client = client or httpx.Client(base_url=_base(host), timeout=15.0, trust_env=False)

    def criar_instancia(self, nome: str, *, token: str | None = None) -> InstanciaCriada:
        """Cria a instância. **Quem gera o token somos nós.**

        O Evolution ecoa de volta o valor enviado — não emite identificador
        próprio. Confundir isso é o que faz alguém procurar por um token que o
        servidor nunca vai gerar.
        """
        # `None` significa "gere um"; string vazia significa que o chamador
        # errou. Usar `or` colapsaria os dois e criaria a instancia com um UUID
        # que o chamador nao pediu nem conhece.
        if token is None:
            escolhido = str(uuid.uuid4())
        else:
            escolhido = token.strip()
            if not escolhido:
                raise ValueError("token de instancia vazio")
        # Normalizar e obrigatorio, nao cosmetico: `EvolutionInstanciaClient` faz
        # `.strip()` ao autenticar. Enviar " abc " na criacao faria o provedor
        # guardar com espacos e toda requisicao seguinte usar "abc" — criacao
        # bem-sucedida, e 401 em tudo depois, para sempre.
        dados = _json(
            _executar(
                lambda: self._client.post(
                    "/instance/create",
                    headers={"apikey": self._api_key, "X-Tenant-ID": self._tenant_id},
                    json={"name": nome, "token": escolhido},
                ),
                "/instance/create",
            ),
            "/instance/create",
        )
        instancia_id = dados.get("id")
        if not isinstance(instancia_id, str) or not instancia_id:
            raise EvolutionIndisponivelError("/instance/create nao devolveu id da instancia")
        devolvido = dados.get("token")
        if devolvido != escolhido:
            raise EvolutionIndisponivelError(
                "/instance/create devolveu token diferente do enviado: "
                "o provedor mudou de comportamento e o contrato §8.1 precisa ser revisto"
            )
        return InstanciaCriada(
            instancia_id=instancia_id, nome=str(dados.get("name", nome)), token=escolhido
        )


class EvolutionInstanciaClient:
    """Opera uma instância já criada. Usa o token dela, sozinho."""

    def __init__(
        self,
        *,
        host: str,
        instancia_token: str,
        client: httpx.Client | None = None,
    ) -> None:
        if not instancia_token.strip():
            raise ValueError("token de instancia do Evolution ausente")
        self._token = instancia_token.strip()
        self._client = client or httpx.Client(base_url=_base(host), timeout=15.0, trust_env=False)

    @property
    def _headers(self) -> dict[str, str]:
        return {"apikey": self._token}

    def conectar(self, webhook_url: str = "") -> None:
        """Inicia o pareamento e registra o webhook.

        `webhook_url` vazia é **aceita** — verificado em 2026-08-31, resposta
        `200` com `"webhookUrl": ""`. É o estado de hoje: a DR-006 decidiu
        apontar para o agente, que ainda não existe.
        """
        _json(
            _executar(
                lambda: self._client.post(
                    "/instance/connect",
                    headers=self._headers,
                    json={"webhookUrl": webhook_url, "subscribe": list(EVENTOS_ASSINADOS)},
                ),
                "/instance/connect",
            ),
            "/instance/connect",
        )

    def qrcode(self) -> str:
        """Devolve o QR como data URI PNG.

        O campo é `Qrcode`, com Q maiúsculo. Não é detalhe estético: buscar
        `qrcode` devolve `None` e a tela mostraria um quadrado vazio.
        """
        resposta = _executar(
            lambda: self._client.get("/instance/qr", headers=self._headers), "/instance/qr"
        )
        if not resposta.is_success:
            detalhe = _mensagem_do_provedor(resposta)
            if "no qr code available" in detalhe.lower():
                raise QrCodeAindaGerandoError(f"/instance/qr: {detalhe}")
        dados = _json(resposta, "/instance/qr")
        imagem = dados.get("Qrcode")
        # Prefixo completo, e nao so "base64,": o metodo promete um data URI PNG,
        # e aceitar qualquer coisa que contenha "base64," entregaria a tela um QR
        # que nao renderiza, em vez do erro nomeado do contrato.
        if not isinstance(imagem, str) or not imagem.startswith(PREFIXO_QR):
            raise EvolutionIndisponivelError(
                f"/instance/qr nao devolveu data URI PNG (esperado prefixo {PREFIXO_QR!r})"
            )
        _exigir_png(imagem[len(PREFIXO_QR) :])
        return imagem

    def estado(self) -> EstadoInstancia:
        dados = _json(
            _executar(
                lambda: self._client.get("/instance/status", headers=self._headers),
                "/instance/status",
            ),
            "/instance/status",
        )
        nome = dados.get("Name")
        return EstadoInstancia(
            conectado=_booleano(dados, "Connected", "/instance/status"),
            pareado=_booleano(dados, "LoggedIn", "/instance/status"),
            nome_exibicao=nome if isinstance(nome, str) and nome else None,
        )

    def desconectar(self) -> None:
        """Desvincula o número. A instância permanece."""
        resposta = _executar(
            lambda: self._client.delete("/instance/logout", headers=self._headers),
            "/instance/logout",
        )
        # 2xx exigido: um redirect aceito como sucesso marcaria a conexao como
        # desfeita enquanto a instancia continua pareada no provedor.
        if not resposta.is_success:
            detalhe = _mensagem_do_provedor(resposta)
            sufixo = f": {detalhe}" if detalhe else ""
            raise EvolutionIndisponivelError(
                f"/instance/logout respondeu {resposta.status_code}{sufixo}"
            )


class EvolutionProvedorWhatsApp(ProvedorWhatsApp):
    """Compõe os dois clientes por trás de uma porta só (IMP-367).

    A Application pede "crie", "conecte", "qual o estado" — e não precisa saber
    que criar usa a chave de Tenant e o resto usa o token da instância. Essa
    separação existe no provedor e continua existindo aqui, mas para dentro:
    confundir as duas chaves é o erro que o `EvolutionTenantClient` e o
    `EvolutionInstanciaClient` tornam impossível por construção.

    O token entra por parâmetro em vez de virar estado: quem o guarda é o
    repositório, e ele só o entrega a quem pedir explicitamente.
    """

    def __init__(
        self,
        *,
        host: str,
        tenant_id: str,
        api_key: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._host = host
        # Um cliente para o adapter inteiro. Sem isto, cada chamada de
        # `_instancia()` abriria um pool novo que ninguem fecha — e a tela faz
        # polling de estado e de QR, entao seriam sockets acumulando por
        # segundo, nao por sessao.
        self._client = client or httpx.Client(base_url=_base(host), timeout=15.0, trust_env=False)
        self._tenant = EvolutionTenantClient(
            host=host,
            tenant_id=tenant_id,
            api_key=api_key,
            client=self._client,
        )

    def _instancia(self, token: str) -> EvolutionInstanciaClient:
        return EvolutionInstanciaClient(
            host=self._host,
            instancia_token=token,
            client=self._client,
        )

    def criar_instancia(self, nome: str) -> tuple[str, str]:
        criada = self._tenant.criar_instancia(nome)
        return criada.instancia_id, criada.token

    def conectar(self, token: str) -> None:
        # Webhook vazio de propósito: a DR-006 apontou o webhook para o agente,
        # não para a TiaNet. Mandar a nossa URL aqui roubaria os eventos dele.
        self._instancia(token).conectar()

    def qrcode(self, token: str) -> str:
        return self._instancia(token).qrcode()

    def estado(self, token: str) -> EstadoPareamento:
        bruto = self._instancia(token).estado()
        return EstadoPareamento(
            conectado=bruto.conectado,
            pareado=bruto.pareado,
            # `Name` e o push name do WhatsApp — "Barbosa" na resposta real de
            # 2026-08-31 —, NAO o telefone. Chama-lo de numero faria a tela
            # exibir um nome onde promete um numero.
            nome_exibicao=bruto.nome_exibicao if bruto.pareado else None,
        )

    def desconectar(self, token: str) -> None:
        self._instancia(token).desconectar()
