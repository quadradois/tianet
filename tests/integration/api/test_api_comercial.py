"""Testes de integracao da API Comercial (IMP-118..IMP-122)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.autorizacao import Principal
from emprestimo.application.errors import AcessoNegadoError
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

CPF = "52998224725"
PRINCIPAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000101")
TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000202")
PRINCIPAL_TESTE = Principal(
    usuario_id=PRINCIPAL_ID,
    tenant_id=TENANT_ID,
    perfil_acesso="Comercial",
    access_token_expira_em=datetime.now(UTC) + timedelta(minutes=15),
)


@pytest.fixture
def contexto(session: Session) -> tuple[str, str]:
    tenant = TenantFactory.build(id=TENANT_ID)
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    usuario = UsuarioFactory.build(id=PRINCIPAL_ID, tenant_id=tenant.id)
    SqlAlchemyUsuarioRepository(session).save(usuario)
    devedor = Devedor.criar(
        carteira_id=carteira.id,
        documento=Documento.from_str(CPF),
        nome="Devedor Comercial",
        contatos=(
            Contato(
                devedor_id=uuid.uuid4(),
                tipo=TipoContato.EMAIL,
                valor="comercial@example.com",
                preferencial=True,
            ),
        ),
    )
    SqlAlchemyDevedorRepository(session).save(devedor)
    session.commit()
    return str(carteira.id), str(devedor.id)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL_TESTE
    autorizacao = Mock()
    autorizacao.exigir_permissao.return_value = None
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    with TestClient(app) as c:
        yield c


def test_api_comercial_cria_decide_e_gera_contrato_logico(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, devedor_id = contexto
    simulacao = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais",
        json={"parametros": {"valor": 2500, "parcelas": 10}},
    )
    assert simulacao.status_code == 201

    proposta = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
        json={"simulacao_id": simulacao.json()["id"]},
    )
    assert proposta.status_code == 201
    proposta_id = proposta.json()["id"]

    enviada = client.post(f"/credit/propostas-comerciais/{proposta_id}/enviar-para-analise")
    aprovada = client.post(f"/credit/propostas-comerciais/{proposta_id}/aprovar")
    contrato = client.get(f"/credit/propostas-comerciais/{proposta_id}/contrato-logico")

    assert enviada.status_code == 200
    assert enviada.json()["estado"] == "em_analise"
    assert aprovada.status_code == 200
    assert aprovada.json()["estado"] == "aprovada"
    assert aprovada.json()["total_decisoes"] == 2
    assert contrato.status_code == 200
    assert contrato.json()["proposta_id"] == proposta_id
    assert contrato.json()["parametros_aprovados"]["valor"] == 2500


def test_api_comercial_consulta_simulacao_por_id(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, devedor_id = contexto
    criada = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais",
        json={"parametros": {"valor": 1800, "parcelas": 6}},
    )
    assert criada.status_code == 201

    consulta = client.get(f"/credit/simulacoes-comerciais/{criada.json()['id']}")

    assert consulta.status_code == 200
    assert consulta.json()["id"] == criada.json()["id"]
    assert consulta.json()["parametros"]["valor"] == 1800


def test_api_comercial_lista_e_consulta_propostas(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, devedor_id = contexto
    criada = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
        json={"parametros": {"valor": 900}},
    )
    assert criada.status_code == 201

    listagem = client.get(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais"
    )
    consulta = client.get(f"/credit/propostas-comerciais/{criada.json()['id']}")

    assert listagem.status_code == 200
    assert listagem.json()["total"] == 1
    assert listagem.json()["items"][0]["id"] == criada.json()["id"]
    assert consulta.status_code == 200
    assert consulta.json()["parametros"]["valor"] == 900


def test_api_comercial_rejeita_devedor_inativo(
    client: TestClient,
    contexto: tuple[str, str],
    session: Session,
) -> None:
    carteira_id, devedor_id = contexto
    _inativar_devedor(session, uuid.UUID(devedor_id))

    simulacao = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais",
        json={"parametros": {"valor": 1000}},
    )
    proposta = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
        json={"parametros": {"valor": 1000}},
    )

    assert simulacao.status_code == 422
    assert simulacao.json()["codigo"] == "regra_violada"
    assert proposta.status_code == 422
    assert proposta.json()["codigo"] == "regra_violada"


def test_api_comercial_transicao_invalida_retorna_409(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, devedor_id = contexto
    proposta = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
        json={"parametros": {"valor": 1000}},
    )
    assert proposta.status_code == 201

    aprovar = client.post(f"/credit/propostas-comerciais/{proposta.json()['id']}/aprovar")

    assert aprovar.status_code == 409
    assert aprovar.json()["codigo"] == "conflito_estado"


def test_api_comercial_openapi_publica_respostas_protegidas(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    post_simulacao = schema["paths"][
        "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais"
    ]["post"]
    get_simulacao = schema["paths"]["/credit/simulacoes-comerciais/{simulacao_id}"]["get"]
    aprovar = schema["paths"]["/credit/propostas-comerciais/{proposta_id}/aprovar"]["post"]

    assert post_simulacao["responses"]["201"]
    assert {"401", "403", "404"} <= set(post_simulacao["responses"])
    assert {"401", "403", "404"} <= set(get_simulacao["responses"])
    assert {"401", "403", "404", "409"} <= set(aprovar["responses"])


def test_api_comercial_exige_permissao(contexto: tuple[str, str]) -> None:
    carteira_id, devedor_id = contexto
    app = create_app()
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL_TESTE
    autorizacao = Mock()
    autorizacao.exigir_permissao.side_effect = AcessoNegadoError("comercial.simulacao.criar")
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais",
            json={"parametros": {"valor": 100}},
        )

    assert resp.status_code == 403
    autorizacao.exigir_permissao.assert_called_once_with(
        PRINCIPAL_TESTE, "comercial.simulacao.criar"
    )


def _inativar_devedor(session: Session, devedor_id: uuid.UUID) -> None:
    repo = SqlAlchemyDevedorRepository(session)
    devedor = repo.find_by_id(devedor_id)
    assert devedor is not None
    devedor.inativar()
    repo.save(devedor)
    session.commit()
