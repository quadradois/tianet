from __future__ import annotations

import httpx
import pytest

from emprestimo.domain.credit.notifications import ResultadoCanal
from emprestimo.infrastructure.notifications import ResendNotificationChannel


@pytest.mark.parametrize(
    ("status", "body", "esperado"),
    [
        (200, {"id": "msg-1"}, ResultadoCanal.ACEITA),
        (200, {}, ResultadoCanal.DESCONHECIDO),
        (429, {}, ResultadoCanal.FALHA_TEMPORARIA),
        (400, {}, ResultadoCanal.FALHA_PERMANENTE),
        (500, {}, ResultadoCanal.DESCONHECIDO),
    ],
)
def test_resend_classifica_respostas_sem_retry_interno(
    status: int,
    body: dict[str, str],
    esperado: ResultadoCanal,
) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=body))
    client = httpx.Client(base_url="https://api.resend.com", transport=transport)
    channel = ResendNotificationChannel(
        api_key="secret-for-test",
        remetente="noreply@example.test",
        client=client,
    )
    resultado = channel.enviar(
        destinatario="destino@example.test",
        assunto="Assunto",
        corpo="Corpo",
        chave_idempotente="key-1",
    )
    assert resultado.resultado is esperado


def test_timeout_e_resultado_desconhecido() -> None:
    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    client = httpx.Client(
        base_url="https://api.resend.com",
        transport=httpx.MockTransport(timeout),
    )
    channel = ResendNotificationChannel(
        api_key="secret-for-test",
        remetente="noreply@example.test",
        client=client,
    )
    resultado = channel.enviar(
        destinatario="destino@example.test",
        assunto="Assunto",
        corpo="Corpo",
        chave_idempotente="key-2",
    )
    assert resultado.resultado is ResultadoCanal.DESCONHECIDO


def test_consulta_status_exige_chave_idempotente_na_evidencia() -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/emails/msg-1"
        return httpx.Response(
            200,
            json={
                "id": "msg-1",
                "last_event": "delivered",
                "headers": {"X-Entity-Ref-ID": "notification/key-1"},
            },
        )

    client = httpx.Client(
        base_url="https://api.resend.com",
        transport=httpx.MockTransport(responder),
    )
    channel = ResendNotificationChannel(
        api_key="secret-for-test",
        remetente="noreply@example.test",
        client=client,
    )

    resultado = channel.consultar_status("msg-1")

    assert resultado.resultado is ResultadoCanal.ACEITA
    assert resultado.chave_idempotente == "notification/key-1"
