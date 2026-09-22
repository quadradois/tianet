"""Verificacao de credencial do Mercado Pago (IMP-388)."""

from __future__ import annotations

import httpx
import pytest

from emprestimo.infrastructure.mercadopago import verificar_credencial

TOKEN = "APP_USR-token-de-teste"


def _client(handler: object) -> httpx.Client:
    return httpx.Client(
        base_url="https://api.mercadopago.com",
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )


def test_credencial_valida_devolve_ok_e_envia_bearer() -> None:
    enviados: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        enviados.append(request.headers["Authorization"])
        return httpx.Response(200, json={"id": 1})

    resultado = verificar_credencial(TOKEN, client=_client(handler))

    assert resultado.valido is True
    assert enviados == [f"Bearer {TOKEN}"]


@pytest.mark.parametrize("status", [401, 403])
def test_credencial_recusada_nao_e_transporte(status: int) -> None:
    resultado = verificar_credencial(
        TOKEN, client=_client(lambda _r: httpx.Response(status, json={}))
    )

    assert resultado.valido is False
    assert resultado.detalhe == "credencial_recusada"


def test_falha_de_transporte_nao_liga_a_integracao() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("sem rede")

    resultado = verificar_credencial(TOKEN, client=_client(handler))

    assert resultado.valido is False
    assert resultado.detalhe == "falha_de_transporte"


def test_resposta_inesperada_carrega_o_status_e_nao_o_corpo() -> None:
    resultado = verificar_credencial(
        TOKEN,
        client=_client(lambda _r: httpx.Response(500, json={"erro": "segredo-do-provedor"})),
    )

    assert resultado.valido is False
    assert resultado.detalhe == "resposta_inesperada:500"
    assert "segredo" not in resultado.detalhe


def test_token_nunca_aparece_no_resultado() -> None:
    resultado = verificar_credencial(TOKEN, client=_client(lambda _r: httpx.Response(401, json={})))

    assert TOKEN not in repr(resultado)
