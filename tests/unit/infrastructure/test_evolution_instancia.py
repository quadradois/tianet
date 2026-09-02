"""Cliente de gestão de instância do Evolution (IMP-366, PLAN-034).

As respostas usadas aqui **não são inventadas**: foram capturadas contra o
servidor real em 2026-08-31, ao fechar o IMP-352. Onde a documentação pública e
a resposta real divergiam, vale a resposta — e é por isso que estes testes
existem em vez de uma leitura atenta do contrato.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
import pytest

from emprestimo.infrastructure.notifications.evolution_instancia import (
    PREFIXO_QR,
    EvolutionIndisponivelError,
    EvolutionInstanciaClient,
    EvolutionTenantClient,
    QrCodeAindaGerandoError,
    numero_do_jid,
)

HOST = "https://diamondgreen.com.br"
TOKEN = "5f29f723-7f3c-4ffa-9cbc-1df51d5eb9e5"
INSTANCIA_ID = "8a8c901f-16f9-4431-b19d-ed69cccc46c0"

# Resposta real do POST /instance/create, 2026-08-31.
CRIADA = {
    "message": "success",
    "data": {
        "id": INSTANCIA_ID,
        "name": "adm_tianet",
        "token": TOKEN,
        "webhook": "",
        "connected": False,
    },
}

# Resposta real do POST /instance/connect com webhookUrl vazia.
CONECTADA = {
    "data": {"eventString": "MESSAGE,CONNECTION,QRCODE", "jid": "", "webhookUrl": ""},
    "message": "success",
}

QR = {"data": {"Code": "2@abc"}}  # `Qrcode` injetado em cada teste com PNG real

# Estado logo apos criar: socket de pe, ninguem pareado.
SO_CONECTADA = {"data": {"Connected": True, "LoggedIn": False, "Name": ""}, "message": "success"}

# Estado depois do scan.
PAREADA = {"data": {"Connected": True, "LoggedIn": True, "Name": "Barbosa"}, "message": "success"}


def _png_minimo() -> str:
    """Um PNG 1x1 real, montado com a stdlib.

    A fixture anterior era assinatura + texto arbitrario — ou seja, o teste de
    caminho feliz afirmava que um nao-PNG era aceito. Achado do quinto review.
    """
    import struct
    import zlib

    def chunk(tipo: bytes, dados: bytes) -> bytes:
        corpo = tipo + dados
        return struct.pack(">I", len(dados)) + corpo + struct.pack(">I", zlib.crc32(corpo))

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(bytes(4)))
    iend = chunk(b"IEND", b"")
    return base64.b64encode(bytes.fromhex("89504e470d0a1a0a") + ihdr + idat + iend).decode()


def _cliente(handler: Any) -> httpx.Client:
    return httpx.Client(base_url=HOST, transport=httpx.MockTransport(handler))


class TestEvolutionTenantClient:
    def test_cria_instancia_com_o_token_que_nos_geramos(self) -> None:
        """O Evolution ECOA o token enviado — nao emite identificador proprio."""
        vistos: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            vistos["url"] = str(request.url)
            vistos["apikey"] = request.headers.get("apikey")
            vistos["tenant"] = request.headers.get("X-Tenant-ID")
            vistos["corpo"] = request.read().decode()
            return httpx.Response(200, json=CRIADA)

        criada = EvolutionTenantClient(
            host=HOST, tenant_id="tid", api_key="chave-do-tenant", client=_cliente(handler)
        ).criar_instancia("adm_tianet", token=TOKEN)

        assert criada.instancia_id == INSTANCIA_ID
        assert criada.token == TOKEN
        assert vistos["url"].endswith("/instance/create")
        assert vistos["apikey"] == "chave-do-tenant"
        assert vistos["tenant"] == "tid"
        assert TOKEN in vistos["corpo"]

    def test_gera_o_token_quando_nenhum_e_informado(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            enviado = request.read().decode()
            eco = dict(CRIADA)
            dados = dict(CRIADA["data"])  # type: ignore[arg-type]
            dados["token"] = enviado.split('"token":"')[1].split('"')[0]
            eco["data"] = dados
            return httpx.Response(200, json=eco)

        criada = EvolutionTenantClient(
            host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
        ).criar_instancia("adm_tianet")
        assert len(criada.token) == 36

    def test_token_devolvido_diferente_e_tratado_como_mudanca_de_contrato(self) -> None:
        """Se o eco parar de ecoar, o contrato §8.1 deixou de valer.

        Aceitar em silencio faria o sistema guardar um token que nao e o da
        instancia — e descobrir isso so no primeiro envio que falhasse.
        """
        divergente = {"data": {**CRIADA["data"], "token": "outro-token"}}  # type: ignore[dict-item]

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=divergente)

        with pytest.raises(EvolutionIndisponivelError, match="diferente do enviado"):
            EvolutionTenantClient(
                host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
            ).criar_instancia("adm_tianet", token=TOKEN)

    def test_401_vira_erro_nomeado(self) -> None:
        """Sem credencial, /instance/* responde 401 — observado em 2026-08-31."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "not authorized"})

        with pytest.raises(EvolutionIndisponivelError, match="401"):
            EvolutionTenantClient(
                host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
            ).criar_instancia("adm_tianet")

    def test_credenciais_incompletas_recusam_na_construcao(self) -> None:
        with pytest.raises(ValueError, match="incompletas"):
            EvolutionTenantClient(host=HOST, tenant_id="  ", api_key="k")


class TestEvolutionInstanciaClient:
    def _cli(self, handler: Any) -> EvolutionInstanciaClient:
        return EvolutionInstanciaClient(host=HOST, instancia_token=TOKEN, client=_cliente(handler))

    def test_conectar_aceita_webhook_vazio(self) -> None:
        """Verificado contra o servidor real: 200 com "webhookUrl": ""."""
        vistos: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            vistos["corpo"] = request.read().decode()
            vistos["apikey"] = request.headers.get("apikey")
            vistos["tenant"] = request.headers.get("X-Tenant-ID")
            return httpx.Response(200, json=CONECTADA)

        self._cli(handler).conectar()
        assert '"webhookUrl": ""' in vistos["corpo"] or '"webhookUrl":""' in vistos["corpo"]
        assert vistos["apikey"] == TOKEN
        # A chave de tenant nao alcanca esta rota: o header nao deve existir.
        assert vistos["tenant"] is None

    def test_conectar_assina_apenas_eventos_validos(self) -> None:
        """Valor invalido em `subscribe` e descartado em SILENCIO pelo servidor."""
        vistos: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            vistos["corpo"] = request.read().decode()
            return httpx.Response(200, json=CONECTADA)

        self._cli(handler).conectar()
        for evento in ("MESSAGE", "CONNECTION", "QRCODE"):
            assert evento in vistos["corpo"]

    def test_qrcode_le_o_campo_com_q_maiusculo(self) -> None:
        """`Qrcode`, nao `qrcode`. Buscar minusculo devolveria quadrado vazio."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"data": {**QR["data"], "Qrcode": PREFIXO_QR + _png_minimo()}}
            )

        assert self._cli(handler).qrcode().startswith("data:image/png;base64,")

    def test_qr_sem_imagem_e_recusado(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"Code": "2@abc"}})

        with pytest.raises(EvolutionIndisponivelError, match="data URI PNG"):
            self._cli(handler).qrcode()

    def test_conectado_sem_pareado_nao_e_conexao(self) -> None:
        """O estado logo apos criar. So `LoggedIn` significa WhatsApp ligado."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SO_CONECTADA)

        estado = self._cli(handler).estado()
        assert estado.conectado is True
        assert estado.pareado is False
        assert estado.nome_exibicao is None

    def test_pareado_traz_o_nome_do_numero(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=PAREADA)

        estado = self._cli(handler).estado()
        assert estado.pareado is True
        assert estado.nome_exibicao == "Barbosa"

    def test_desconectar_usa_delete(self) -> None:
        vistos: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            vistos["metodo"] = request.method
            return httpx.Response(200, json={"message": "success"})

        self._cli(handler).desconectar()
        assert vistos["metodo"] == "DELETE"

    def test_corpo_nao_json_vira_erro_nomeado(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html>gateway</html>")

        with pytest.raises(EvolutionIndisponivelError, match="nao-JSON"):
            self._cli(handler).estado()

    def test_token_ausente_recusa_na_construcao(self) -> None:
        with pytest.raises(ValueError, match="token de instancia"):
            EvolutionInstanciaClient(host=HOST, instancia_token="   ")


class TestFalhasDoProvedor:
    """Achados do review do Codex em 2026-09-01 (IMP-366)."""

    def _handler_que_explode(self, exc: Exception) -> Any:
        def handler(_: httpx.Request) -> httpx.Response:
            raise exc

        return handler

    @pytest.mark.parametrize(
        "exc",
        [
            httpx.ConnectError("dns"),
            httpx.ConnectTimeout("timeout"),
            httpx.ReadTimeout("leitura"),
        ],
    )
    def test_falha_de_transporte_vira_erro_declarado(self, exc: Exception) -> None:
        """Sem isto, o chamador recebe excecao httpx crua.

        Ele trata `EvolutionIndisponivelError`, entao a indisponibilidade
        escaparia sem tratamento — e o adapter de envio, ao lado, ja traduzia.
        """
        cli = EvolutionInstanciaClient(
            host=HOST, instancia_token=TOKEN, client=_cliente(self._handler_que_explode(exc))
        )
        with pytest.raises(EvolutionIndisponivelError, match="inacessivel"):
            cli.estado()

    def test_falha_de_transporte_no_logout_tambem_e_traduzida(self) -> None:
        """`desconectar` nao passa por `_json` — precisa da traducao explicita."""
        cli = EvolutionInstanciaClient(
            host=HOST,
            instancia_token=TOKEN,
            client=_cliente(self._handler_que_explode(httpx.ConnectError("dns"))),
        )
        with pytest.raises(EvolutionIndisponivelError, match="inacessivel"):
            cli.desconectar()

    def test_falha_de_transporte_ao_criar_instancia(self) -> None:
        cli = EvolutionTenantClient(
            host=HOST,
            tenant_id="tid",
            api_key="k",
            client=_cliente(self._handler_que_explode(httpx.ConnectError("dns"))),
        )
        with pytest.raises(EvolutionIndisponivelError, match="inacessivel"):
            cli.criar_instancia("adm_tianet")

    def test_logged_in_como_string_nao_vira_pareado(self) -> None:
        """O achado mais grave: `bool("false")` e True.

        Um provedor devolvendo a string "false" faria o sistema reportar
        PAREADO quando ele disse o contrario — anunciar WhatsApp conectado sem
        nenhum do outro lado.
        """

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"data": {"Connected": True, "LoggedIn": "false", "Name": ""}}
            )

        cli = EvolutionInstanciaClient(host=HOST, instancia_token=TOKEN, client=_cliente(handler))
        with pytest.raises(EvolutionIndisponivelError, match="LoggedIn"):
            cli.estado()

    def test_campo_ausente_no_status_e_erro_e_nao_falso(self) -> None:
        """Ausente nao e "nao pareado": e resposta que mudou de forma."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"Connected": True}})

        cli = EvolutionInstanciaClient(host=HOST, instancia_token=TOKEN, client=_cliente(handler))
        with pytest.raises(EvolutionIndisponivelError, match="LoggedIn"):
            cli.estado()


class TestSegundaRodadaDeReview:
    """Achados do segundo review do Codex em 2026-09-01 (IMP-366)."""

    def _cli(self, handler: Any) -> EvolutionInstanciaClient:
        return EvolutionInstanciaClient(host=HOST, instancia_token=TOKEN, client=_cliente(handler))

    def test_qr_ainda_gerando_e_estado_distinto_de_indisponibilidade(self) -> None:
        """O contrato (Evento 4.2) descreve isso como corrida NORMAL.

        Colapsar em `EvolutionIndisponivelError` impediria a tela de distinguir
        "aguarde, estou gerando" de "provedor fora do ar" — e a diferenca decide
        se o usuario espera ou se alguem e chamado.
        """

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400, json={"error": "no QR code available. Please wait a moment and try again"}
            )

        with pytest.raises(QrCodeAindaGerandoError):
            self._cli(handler).qrcode()

    def test_qr_ainda_gerando_e_subtipo_de_indisponivel(self) -> None:
        """Quem so quer saber "deu errado" continua pegando com o tipo base."""
        assert issubclass(QrCodeAindaGerandoError, EvolutionIndisponivelError)

    def test_outro_erro_no_qr_nao_vira_ainda_gerando(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "internal"})

        with pytest.raises(EvolutionIndisponivelError) as exc:
            self._cli(handler).qrcode()
        assert not isinstance(exc.value, QrCodeAindaGerandoError)

    def test_a_mensagem_do_provedor_chega_ao_erro(self) -> None:
        """Descartar o texto do provedor apaga a unica pista util do incidente."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"error": "tenant is inactive"})

        with pytest.raises(EvolutionIndisponivelError, match="tenant is inactive"):
            self._cli(handler).estado()

    @pytest.mark.parametrize("status", [301, 302, 307, 308])
    def test_redirect_no_logout_nao_e_sucesso(self, status: int) -> None:
        """`httpx` nao segue redirect por padrao.

        Aceitar 3xx marcaria a conexao como desfeita enquanto a instancia
        continua pareada no provedor — estado divergente e silencioso.
        """

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(status, headers={"location": "https://outro/instance/logout"})

        with pytest.raises(EvolutionIndisponivelError, match=str(status)):
            self._cli(handler).desconectar()

    @pytest.mark.parametrize("status", [301, 307])
    def test_redirect_tambem_nao_e_sucesso_nas_demais_rotas(self, status: int) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(status, headers={"location": "https://outro/instance/status"})

        with pytest.raises(EvolutionIndisponivelError, match=str(status)):
            self._cli(handler).estado()


class TestTerceiraRodadaDeReview:
    """Achados do terceiro review do Codex (IMP-366). Ambos de assimetria."""

    def test_token_com_espacos_e_normalizado_antes_de_criar(self) -> None:
        """Criar com " abc " e autenticar com "abc" e 401 para sempre.

        `EvolutionInstanciaClient` faz strip ao autenticar. Se a criacao enviar
        o valor com espacos, o provedor guarda um token e o sistema usa outro —
        criacao bem-sucedida, e falha em tudo que vier depois.
        """
        vistos: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            vistos["corpo"] = request.read().decode()
            enviado = vistos["corpo"].split('"token":')[1].split('"')[1]
            return httpx.Response(
                200, json={"data": {**CRIADA["data"], "token": enviado}}  # type: ignore[dict-item]
            )

        criada = EvolutionTenantClient(
            host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
        ).criar_instancia("adm_tianet", token=f"  {TOKEN}  ")

        assert criada.token == TOKEN
        assert f'"{TOKEN}"' in vistos["corpo"]

    def test_token_so_de_espacos_e_recusado(self) -> None:
        with pytest.raises(ValueError, match="vazio"):
            EvolutionTenantClient(
                host=HOST, tenant_id="tid", api_key="k", client=_cliente(lambda r: None)
            ).criar_instancia("adm_tianet", token="   ")

    @pytest.mark.parametrize(
        "imagem",
        [
            "not-a-data-uri;base64,iVBORw0KGgo=",
            "data:image/jpeg;base64,iVBORw0KGgo=",
            "iVBORw0KGgo=",
        ],
    )
    def test_qr_fora_do_formato_prometido_e_recusado(self, imagem: str) -> None:
        """O metodo promete data URI PNG. Entregar outra coisa daria um QR que
        nao renderiza, em vez do erro nomeado do contrato."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"Qrcode": imagem}})

        cli = EvolutionInstanciaClient(host=HOST, instancia_token=TOKEN, client=_cliente(handler))
        with pytest.raises(EvolutionIndisponivelError, match="data URI PNG"):
            cli.qrcode()


class TestQuartaRodadaDeReview:
    """Achados do quarto review do Codex (IMP-366)."""

    def _cli(self, handler: Any) -> EvolutionInstanciaClient:
        return EvolutionInstanciaClient(host=HOST, instancia_token=TOKEN, client=_cliente(handler))

    def test_token_string_vazia_e_recusado_e_nao_gera_outro(self) -> None:
        """`None` pede um token novo; string vazia e erro do chamador.

        Colapsar os dois com `or` criaria a instancia com um UUID que o chamador
        nao pediu nem conhece — e ele so descobriria ao tentar autenticar.
        """
        with pytest.raises(ValueError, match="vazio"):
            EvolutionTenantClient(
                host=HOST, tenant_id="tid", api_key="k", client=_cliente(lambda r: None)
            ).criar_instancia("adm_tianet", token="")

    @pytest.mark.parametrize(
        "conteudo",
        ["", "!!!nao-e-base64!!!", base64.b64encode(b"isto nao e png").decode()],
    )
    def test_qr_com_prefixo_certo_e_conteudo_invalido_e_recusado(self, conteudo: str) -> None:
        """Prefixo correto nao garante imagem: vazio, base64 quebrado ou
        conteudo que nao e PNG chegariam a tela como QR que nao aparece."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"Qrcode": PREFIXO_QR + conteudo}})

        with pytest.raises(EvolutionIndisponivelError):
            self._cli(handler).qrcode()

    def test_png_valido_e_aceito(self) -> None:
        """O caminho feliz continua passando — a validacao nao virou paranoia."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"Qrcode": PREFIXO_QR + _png_minimo()}})

        assert self._cli(handler).qrcode().startswith(PREFIXO_QR)


def test_png_truncado_e_recusado() -> None:
    """Assinatura correta nao basta: truncar apos o cabecalho passava antes.

    Nao validamos a estrutura inteira de chunks — seria desproporcional para um
    payload que apenas repassamos, e a falha aparece na hora como imagem
    quebrada. Exigir o IEND final pega truncamento sem parser nem dependencia.
    """
    completo = base64.b64decode(_png_minimo())
    truncado = base64.b64encode(completo[: len(completo) // 2]).decode()

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"Qrcode": PREFIXO_QR + truncado}})

    cli = EvolutionInstanciaClient(host=HOST, instancia_token=TOKEN, client=_cliente(handler))
    with pytest.raises(EvolutionIndisponivelError, match="truncado"):
        cli.qrcode()


def test_erro_de_decodificacao_tambem_vira_erro_declarado() -> None:
    """`DecodingError` deriva de `RequestError`, nao de `TransportError`.

    Um `Content-Encoding: gzip` com corpo truncado escaparia cru para o handler
    HTTP, que so trata `EvolutionIndisponivelError`. Achado do sexto review.
    """

    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.DecodingError("corpo gzip truncado")

    cli = EvolutionInstanciaClient(host=HOST, instancia_token=TOKEN, client=_cliente(handler))
    with pytest.raises(EvolutionIndisponivelError, match="inacessivel"):
        cli.estado()


class TestNumeroDaContaPareada:
    """O telefone existe, e mora atras da autenticacao de Tenant (2026-09-02).

    Ate esta data o codigo assumia que `/instance/status` era a unica fonte de
    estado — e ele nao traz telefone nenhum, so o push name. O fundador apontou
    que o CRM exibe o numero conectado; a leitura ao vivo confirmou o campo
    `jid` em `/instance/info/:id`, que responde a chave de Tenant.
    """

    @pytest.mark.parametrize(
        ("jid", "esperado"),
        [
            ("556299999999:74@s.whatsapp.net", "556299999999"),
            ("556299999999@s.whatsapp.net", "556299999999"),
            ("556299999999:74", "556299999999"),
            # Privacidade total: o WhatsApp entrega `@lid` e nenhum telefone.
            ("204327894327894@lid", None),
            ("", None),
            (None, None),
        ],
    )
    def test_extrai_o_telefone_do_jid(self, jid: str | None, esperado: str | None) -> None:
        assert numero_do_jid(jid) == esperado

    def test_le_o_jid_com_credencial_de_tenant(self) -> None:
        """A chave da instancia nao alcanca esta rota — e por isso ela existe aqui."""
        vistos: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            vistos["url"] = str(request.url)
            vistos["apikey"] = request.headers.get("apikey")
            vistos["tenant"] = request.headers.get("X-Tenant-ID")
            return httpx.Response(
                200,
                json={"data": {"id": INSTANCIA_ID, "jid": "556299999999:74@s.whatsapp.net"}},
            )

        jid = EvolutionTenantClient(
            host=HOST, tenant_id="tid", api_key="chave-do-tenant", client=_cliente(handler)
        ).jid_da_instancia(INSTANCIA_ID)

        assert numero_do_jid(jid) == "556299999999"
        assert vistos["url"].endswith(f"/instance/info/{INSTANCIA_ID}")
        assert vistos["apikey"] == "chave-do-tenant"
        assert vistos["tenant"] == "tid"

    def test_info_sem_jid_recusa_em_vez_de_devolver_none(self) -> None:
        """`None` significa "pareada sem numero", e preserva o numero antigo.

        Um payload que mudou de forma manteria dado velho na tela para sempre.
        """

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"id": INSTANCIA_ID}})

        with pytest.raises(EvolutionIndisponivelError, match="sem `jid`"):
            EvolutionTenantClient(
                host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
            ).jid_da_instancia(INSTANCIA_ID)

    def test_token_so_com_espacos_nao_e_adotado(self) -> None:
        """O cliente normaliza ao autenticar: adotar isso e conexao inutil."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"data": [{"id": INSTANCIA_ID, "name": "adm_tianet", "token": "   "}]}
            )

        with pytest.raises(EvolutionIndisponivelError, match="sem token utilizavel"):
            EvolutionTenantClient(
                host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
            ).buscar_instancia("adm_tianet")

    def test_instancia_sem_jid_nao_inventa_numero(self) -> None:
        """Instancia criada e nao pareada nao tem `jid` — e isso nao e erro."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"id": INSTANCIA_ID, "jid": ""}})

        jid = EvolutionTenantClient(
            host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
        ).jid_da_instancia(INSTANCIA_ID)

        assert numero_do_jid(jid) is None


class TestAdocaoDeInstanciaExistente:
    """`/instance/all` devolve o token — e o que permite adotar em vez de criar.

    A instancia do TiaNet nasceu a mao, antes da tela. Sem esta leitura, o
    primeiro `conectar` criaria uma segunda instancia e a plataforma passaria a
    apontar para ela, nao pareada, enquanto o WhatsApp do operador continua na
    primeira.
    """

    def test_encontra_pelo_nome_e_devolve_id_e_token(self) -> None:
        vistos: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            vistos["url"] = str(request.url)
            vistos["tenant"] = request.headers.get("X-Tenant-ID")
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "outra", "name": "outro_nome", "token": "tok-outro"},
                        {"id": INSTANCIA_ID, "name": "adm_tianet", "token": TOKEN},
                    ]
                },
            )

        achada = EvolutionTenantClient(
            host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
        ).buscar_instancia("adm_tianet")

        assert achada is not None
        assert achada.instancia_id == INSTANCIA_ID
        assert achada.token == TOKEN
        assert vistos["url"].endswith("/instance/all")
        assert vistos["tenant"] == "tid"

    def test_nome_ausente_devolve_none(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": [{"id": "x", "name": "z", "token": "t"}]})

        assert (
            EvolutionTenantClient(
                host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
            ).buscar_instancia("adm_tianet")
            is None
        )

    def test_instancia_sem_token_recusa_em_vez_de_devolver_none(self) -> None:
        """`None` aqui viraria `create`, e criaria uma segunda sobre a existente."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"data": [{"id": INSTANCIA_ID, "name": "adm_tianet", "token": ""}]}
            )

        with pytest.raises(EvolutionIndisponivelError, match="sem token utilizavel"):
            EvolutionTenantClient(
                host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
            ).buscar_instancia("adm_tianet")

    def test_listagem_fora_do_formato_nao_e_lida_como_ausencia(self) -> None:
        """2xx com `data` invalido nao autoriza concluir que nao ha instancia."""

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"message": "success"})

        with pytest.raises(EvolutionIndisponivelError, match="fora do formato"):
            EvolutionTenantClient(
                host=HOST, tenant_id="tid", api_key="k", client=_cliente(handler)
            ).buscar_instancia("adm_tianet")
