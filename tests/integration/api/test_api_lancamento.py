"""Testes de integracao da API de lancamento composto (IMP-306, PLAN-027)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.autorizacao import Principal
from emprestimo.application.errors import AcessoNegadoError
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

PRINCIPAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000901")
TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000902")
PRINCIPAL_TESTE = Principal(
    usuario_id=PRINCIPAL_ID,
    tenant_id=TENANT_ID,
    perfil_acesso="Credor",
    access_token_expira_em=datetime.now(UTC) + timedelta(minutes=15),
)


def _cpf() -> str:
    digitos = [int(d) for d in f"{uuid.uuid4().int % 10**9:09d}"]
    for _ in range(2):
        peso = len(digitos) + 1
        soma = sum(d * (peso - i) for i, d in enumerate(digitos))
        resto = (soma * 10) % 11
        digitos.append(0 if resto == 10 else resto)
    return "".join(str(d) for d in digitos)


def _payload(**overrides: object) -> dict[str, object]:
    corpo: dict[str, object] = {
        "condicoes": {
            "valor_contratado": "6000.00",
            "taxa_juros_mensal": "0.0300",
            "quantidade_parcelas": 3,
            "primeiro_vencimento": "2026-09-20",
            "moeda": "BRL",
        },
        "data_referencia": "2026-08-16",
        "devedor_novo": {
            "documento": _cpf(),
            "nome": "Cliente do Wizard",
            "contato_whatsapp": "(11) 98888-7766",
        },
    }
    corpo.update(overrides)
    return corpo


@pytest.fixture
def carteira_id(session: Session) -> str:
    tenant = TenantFactory.build(id=TENANT_ID)
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    usuario = UsuarioFactory.build(id=PRINCIPAL_ID, tenant_id=tenant.id)
    SqlAlchemyUsuarioRepository(session).save(usuario)
    session.commit()
    return str(carteira.id)


@pytest.fixture
def autorizacao() -> Mock:
    mock = Mock()
    mock.exigir_permissao.return_value = None
    return mock


@pytest.fixture
def client(session_factory: sessionmaker[Session], autorizacao: Mock) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL_TESTE
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    with TestClient(app) as c:
        yield c


def test_lancamento_cria_a_cadeia_completa_em_uma_chamada(
    client: TestClient, carteira_id: str
) -> None:
    resposta = client.post(
        f"/credit/carteiras/{carteira_id}/lancamentos",
        json=_payload(),
        headers={"Idempotency-Key": "api-lancamento-1"},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["quantidade_parcelas"] == 3
    for chave in ("devedor_id", "proposta_id", "contrato_id", "emprestimo_id"):
        assert uuid.UUID(corpo[chave])


def test_replay_com_a_mesma_chave_devolve_o_resultado_original(
    client: TestClient, carteira_id: str
) -> None:
    corpo = _payload()
    primeira = client.post(
        f"/credit/carteiras/{carteira_id}/lancamentos",
        json=corpo,
        headers={"Idempotency-Key": "api-lancamento-replay"},
    )
    segunda = client.post(
        f"/credit/carteiras/{carteira_id}/lancamentos",
        json=corpo,
        headers={"Idempotency-Key": "api-lancamento-replay"},
    )

    assert primeira.status_code == 201
    assert segunda.status_code == 201
    assert segunda.json() == primeira.json()


def test_mesma_chave_com_payload_divergente_e_conflito(
    client: TestClient, carteira_id: str
) -> None:
    client.post(
        f"/credit/carteiras/{carteira_id}/lancamentos",
        json=_payload(),
        headers={"Idempotency-Key": "api-lancamento-divergente"},
    )
    divergente = client.post(
        f"/credit/carteiras/{carteira_id}/lancamentos",
        json=_payload(),
        headers={"Idempotency-Key": "api-lancamento-divergente"},
    )

    assert divergente.status_code == 409


def test_idempotency_key_ausente_e_rejeitada(client: TestClient, carteira_id: str) -> None:
    resposta = client.post(f"/credit/carteiras/{carteira_id}/lancamentos", json=_payload())

    # Convencao do projeto: header ausente e 400, nao 422 (CLAUDE.md, e o mesmo
    # contrato ja exercido em test_api_motor_financeiro).
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_payload_sem_devedor_nem_devedor_novo_e_invalido(
    client: TestClient, carteira_id: str
) -> None:
    corpo = _payload()
    corpo.pop("devedor_novo")

    resposta = client.post(
        f"/credit/carteiras/{carteira_id}/lancamentos",
        json=corpo,
        headers={"Idempotency-Key": "api-lancamento-sem-devedor"},
    )

    assert resposta.status_code in (400, 422)


def test_sem_permissao_nao_lanca(client: TestClient, carteira_id: str, autorizacao: Mock) -> None:
    autorizacao.exigir_permissao.side_effect = AcessoNegadoError("motor.emprestimo.criar")

    resposta = client.post(
        f"/credit/carteiras/{carteira_id}/lancamentos",
        json=_payload(),
        headers={"Idempotency-Key": "api-lancamento-sem-permissao"},
    )

    assert resposta.status_code == 403
