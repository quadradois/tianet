from __future__ import annotations

import httpx
import pytest

from emprestimo.domain.credit.notifications import ResultadoCanal
from emprestimo.infrastructure.notifications import EvolutionWhatsAppNotificationChannel


def _canal(handler: httpx.MockTransport) -> EvolutionWhatsAppNotificationChannel:
    client = httpx.Client(base_url="https://evolution.example.test", transport=handler)
    return EvolutionWhatsAppNotificationChannel(
        host="https://evolution.example.test",
        instance_token="instance-secret",
        client=client,
    )


def test_whatsapp_envia_texto_com_token_da_instancia_sem_tenant_header() -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/send/text"
        assert request.headers["apikey"] == "instance-secret"
        assert "x-tenant-id" not in request.headers
        assert request.read()
        assert request.content == (
            b'{"number":"5511999999999","text":"Corpo","id":"notification/key-1"}'
        )
        return httpx.Response(
            200,
            json={"message": "success", "data": {"Info": {"ID": "message-1"}}},
        )

    channel = _canal(httpx.MockTransport(responder))

    resultado = channel.enviar(
        destinatario="5511999999999",
        assunto="Assunto ignorado pelo WhatsApp",
        corpo="Corpo",
        chave_idempotente="notification/key-1",
    )

    assert resultado.resultado is ResultadoCanal.ACEITA
    assert resultado.provider_message_id == "message-1"
    assert resultado.chave_idempotente == "notification/key-1"


@pytest.mark.parametrize(
    ("status", "body", "codigo"),
    [
        (401, {"error": "not authorized"}, "auth_invalid"),
        (401, {"error": "X-Tenant-ID header is required"}, "auth_invalid"),
        (403, {"error": "tenant is inactive"}, "tenant_inactive"),
        (401, {"error": "tenant is inactive"}, "tenant_inactive"),
        (400, {"error": "phone number is required"}, "provider_4xx"),
    ],
)
def test_whatsapp_erros_de_auth_e_payload_sao_permanentes(
    status: int,
    body: dict[str, object],
    codigo: str,
) -> None:
    channel = _canal(
        httpx.MockTransport(lambda request: httpx.Response(status, json=body, request=request))
    )

    resultado = channel.enviar(
        destinatario="5511999999999",
        assunto="Assunto",
        corpo="Corpo",
        chave_idempotente="notification/key-2",
    )

    assert resultado.resultado is ResultadoCanal.FALHA_PERMANENTE
    assert resultado.codigo == codigo


def test_whatsapp_429_permite_retry() -> None:
    """429 e o unico status que a ADR-009 declara temporario."""

    channel = _canal(
        httpx.MockTransport(lambda request: httpx.Response(429, json={}, request=request))
    )

    resultado = channel.enviar(
        destinatario="5511999999999",
        assunto="Assunto",
        corpo="Corpo",
        chave_idempotente="notification/key-3",
    )

    assert resultado.resultado is ResultadoCanal.FALHA_TEMPORARIA
    assert resultado.codigo == "rate_limited"


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_whatsapp_5xx_bloqueia_retry(status: int) -> None:
    """Nenhum 5xx prova recusa: a ADR-009 manda conciliar, nao reenviar."""

    channel = _canal(
        httpx.MockTransport(lambda request: httpx.Response(status, json={}, request=request))
    )

    resultado = channel.enviar(
        destinatario="5511999999999",
        assunto="Assunto",
        corpo="Corpo",
        chave_idempotente="notification/key-3",
    )

    assert resultado.resultado is ResultadoCanal.DESCONHECIDO
    assert resultado.codigo == "provider_5xx"


@pytest.mark.parametrize(
    "erro",
    [
        httpx.ConnectTimeout("sem conexao"),
        httpx.ConnectError("recusada"),
        httpx.PoolTimeout("pool cheio"),
    ],
)
def test_whatsapp_falha_antes_da_rede_permite_retry(erro: Exception) -> None:
    """A requisicao nao chegou a existir na rede — nao ha efeito a duplicar."""

    def falhar(_: httpx.Request) -> httpx.Response:
        raise erro

    channel = _canal(httpx.MockTransport(falhar))

    resultado = channel.enviar(
        destinatario="5511999999999",
        assunto="Assunto",
        corpo="Corpo",
        chave_idempotente="notification/key-4",
    )

    assert resultado.resultado is ResultadoCanal.FALHA_TEMPORARIA
    assert resultado.codigo == "transport_temporary"


@pytest.mark.parametrize(
    "erro",
    [
        httpx.ReadTimeout("timeout"),
        httpx.WriteTimeout("timeout"),
        httpx.ReadError("reset"),
        httpx.WriteError("reset"),
        httpx.CloseError("close"),
        httpx.RemoteProtocolError("protocolo"),
        httpx.DecodingError("encoding invalido"),
    ],
)
def test_whatsapp_falha_sem_prova_bloqueia_retry(erro: Exception) -> None:
    """Sem prova de nao aceite, reenviar pode entregar a mensagem duas vezes.

    Cobre tambem `DecodingError`, que nao e `TransportError` e antes escapava do
    adapter — o `SchedulerWorker` converte qualquer excecao em falha temporaria.
    """

    def falhar(_: httpx.Request) -> httpx.Response:
        raise erro

    channel = _canal(httpx.MockTransport(falhar))

    resultado = channel.enviar(
        destinatario="5511999999999",
        assunto="Assunto",
        corpo="Corpo",
        chave_idempotente="notification/key-4",
    )

    assert resultado.resultado is ResultadoCanal.DESCONHECIDO
    assert resultado.codigo == "transport_unknown"


@pytest.mark.parametrize(
    ("status", "body", "codigo"),
    [
        (200, {"message": "success", "data": {"Info": {}}}, "success_malformed"),
        (302, {}, "provider_unexpected_status"),
    ],
)
def test_whatsapp_resposta_sem_identificador_utilizavel_e_desconhecida(
    status: int,
    body: dict[str, object],
    codigo: str,
) -> None:
    channel = _canal(
        httpx.MockTransport(lambda request: httpx.Response(status, json=body, request=request))
    )

    resultado = channel.enviar(
        destinatario="5511999999999",
        assunto="Assunto",
        corpo="Corpo",
        chave_idempotente="notification/key-5",
    )

    assert resultado.resultado is ResultadoCanal.DESCONHECIDO
    assert resultado.codigo == codigo


def test_whatsapp_consultar_status_declara_receipt_sem_fazer_requisicao() -> None:
    def requisicao_indevida(_: httpx.Request) -> httpx.Response:
        raise AssertionError("consultar_status nao deve chamar o Evolution Go")

    channel = _canal(httpx.MockTransport(requisicao_indevida))

    resultado = channel.consultar_status("message-1")

    assert resultado.resultado is ResultadoCanal.DESCONHECIDO
    assert resultado.codigo == "status_available_by_receipt_only"
    assert resultado.provider_message_id is None
