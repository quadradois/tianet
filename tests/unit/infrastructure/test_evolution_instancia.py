"""Cliente de gestão de instância do Evolution (IMP-366, PLAN-034).

As respostas usadas aqui **não são inventadas**: foram capturadas contra o
servidor real em 2026-08-31, ao fechar o IMP-352. Onde a documentação pública e
a resposta real divergiam, vale a resposta — e é por isso que estes testes
existem em vez de uma leitura atenta do contrato.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from emprestimo.infrastructure.notifications.evolution_instancia import (
    EvolutionIndisponivelError,
    EvolutionInstanciaClient,
    EvolutionTenantClient,
    QrCodeAindaGerandoError,
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

QR = {"data": {"Qrcode": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==", "Code": "2@abc"}}

# Estado logo apos criar: socket de pe, ninguem pareado.
SO_CONECTADA = {"data": {"Connected": True, "LoggedIn": False, "Name": ""}, "message": "success"}

# Estado depois do scan.
PAREADA = {"data": {"Connected": True, "LoggedIn": True, "Name": "Barbosa"}, "message": "success"}


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
            return httpx.Response(200, json=QR)

        assert self._cli(handler).qrcode().startswith("data:image/png;base64,")

    def test_qr_sem_imagem_e_recusado(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"Code": "2@abc"}})

        with pytest.raises(EvolutionIndisponivelError, match="imagem"):
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
