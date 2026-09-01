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

import uuid
from dataclasses import dataclass
from typing import Any

import httpx

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


def _json(resposta: httpx.Response, rota: str) -> dict[str, Any]:
    if resposta.status_code >= 400:
        raise EvolutionIndisponivelError(f"{rota} respondeu {resposta.status_code}")
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
        escolhido = token or str(uuid.uuid4())
        dados = _json(
            self._client.post(
                "/instance/create",
                headers={"apikey": self._api_key, "X-Tenant-ID": self._tenant_id},
                json={"name": nome, "token": escolhido},
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
            self._client.post(
                "/instance/connect",
                headers=self._headers,
                json={"webhookUrl": webhook_url, "subscribe": list(EVENTOS_ASSINADOS)},
            ),
            "/instance/connect",
        )

    def qrcode(self) -> str:
        """Devolve o QR como data URI PNG.

        O campo é `Qrcode`, com Q maiúsculo. Não é detalhe estético: buscar
        `qrcode` devolve `None` e a tela mostraria um quadrado vazio.
        """
        dados = _json(self._client.get("/instance/qr", headers=self._headers), "/instance/qr")
        imagem = dados.get("Qrcode")
        if not isinstance(imagem, str) or "base64," not in imagem:
            raise EvolutionIndisponivelError("/instance/qr nao devolveu imagem utilizavel")
        return imagem

    def estado(self) -> EstadoInstancia:
        dados = _json(
            self._client.get("/instance/status", headers=self._headers), "/instance/status"
        )
        nome = dados.get("Name")
        return EstadoInstancia(
            conectado=bool(dados.get("Connected")),
            pareado=bool(dados.get("LoggedIn")),
            nome_exibicao=nome if isinstance(nome, str) and nome else None,
        )

    def desconectar(self) -> None:
        """Desvincula o número. A instância permanece."""
        resposta = self._client.delete("/instance/logout", headers=self._headers)
        if resposta.status_code >= 400:
            raise EvolutionIndisponivelError(f"/instance/logout respondeu {resposta.status_code}")
