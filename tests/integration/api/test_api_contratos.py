"""Testes de integracao da API Contratos (IMP-138..IMP-142)."""

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
PRINCIPAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000301")
TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000302")
PRINCIPAL_TESTE = Principal(
    usuario_id=PRINCIPAL_ID,
    tenant_id=TENANT_ID,
    perfil_acesso="Contratos",
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
        nome="Devedor Contratos",
        contatos=(
            Contato(
                devedor_id=uuid.uuid4(),
                tipo=TipoContato.EMAIL,
                valor="contratos@example.com",
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


def test_api_contratos_cria_assina_libera_e_consulta(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, devedor_id = contexto
    proposta_id = _proposta_aprovada(client, carteira_id, devedor_id)

    contrato = client.post(
        f"/credit/carteiras/{carteira_id}/contratos",
        json={"proposta_comercial_id": proposta_id},
    )
    assert contrato.status_code == 201
    contrato_id = contrato.json()["id"]

    assinado = client.post(f"/credit/contratos/{contrato_id}/assinar")
    liberado = client.post(f"/credit/contratos/{contrato_id}/liberar-para-motor")
    consulta = client.get(f"/credit/contratos/{contrato_id}")
    historico = client.get(f"/credit/contratos/{contrato_id}/historico")

    assert assinado.status_code == 200
    assert assinado.json()["estado"] == "assinado"
    assert assinado.json()["total_eventos"] == 3
    assert liberado.status_code == 200
    assert liberado.json()["contrato_id"] == contrato_id
    assert liberado.json()["parametros_contratados"]["valor"] == 2500
    assert consulta.status_code == 200
    assert consulta.json()["estado"] == "liberado_para_motor"
    assert historico.status_code == 200
    assert [evento["estado_posterior"] for evento in historico.json()] == [
        "rascunho",
        "formalizado",
        "assinado",
        "liberado_para_motor",
    ]
    assert [evento["tipo"] for evento in historico.json()] == [
        "criado",
        "formalizado",
        "assinado",
        "liberado_para_motor",
    ]


def test_api_contratos_lista_contratos(client: TestClient, contexto: tuple[str, str]) -> None:
    carteira_id, devedor_id = contexto
    proposta_id = _proposta_aprovada(client, carteira_id, devedor_id)
    contrato = client.post(
        f"/credit/carteiras/{carteira_id}/contratos",
        json={"proposta_comercial_id": proposta_id},
    )
    assert contrato.status_code == 201

    listagem = client.get(f"/credit/carteiras/{carteira_id}/contratos")

    assert listagem.status_code == 200
    assert listagem.json()["total"] == 1
    assert listagem.json()["items"][0]["id"] == contrato.json()["id"]


def test_api_contratos_rejeita_proposta_nao_aprovada(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, devedor_id = contexto
    proposta = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
        json={"parametros": {"valor": 1000}},
    )
    assert proposta.status_code == 201

    contrato = client.post(
        f"/credit/carteiras/{carteira_id}/contratos",
        json={"proposta_comercial_id": proposta.json()["id"]},
    )

    assert contrato.status_code == 409
    assert contrato.json()["codigo"] == "conflito_estado"


def test_api_contratos_liberacao_sem_assinatura_retorna_409(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, devedor_id = contexto
    proposta_id = _proposta_aprovada(client, carteira_id, devedor_id)
    contrato = client.post(
        f"/credit/carteiras/{carteira_id}/contratos",
        json={"proposta_comercial_id": proposta_id},
    )
    assert contrato.status_code == 201

    liberacao = client.post(f"/credit/contratos/{contrato.json()['id']}/liberar-para-motor")

    assert liberacao.status_code == 409
    assert liberacao.json()["codigo"] == "conflito_estado"


def test_api_contratos_exige_permissao(contexto: tuple[str, str]) -> None:
    carteira_id, _ = contexto
    app = create_app()
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL_TESTE
    autorizacao = Mock()
    autorizacao.exigir_permissao.side_effect = AcessoNegadoError("contratos.contrato.criar")
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            f"/credit/carteiras/{carteira_id}/contratos",
            json={"proposta_comercial_id": str(uuid.uuid4())},
        )

    assert resp.status_code == 403
    autorizacao.exigir_permissao.assert_called_once_with(
        PRINCIPAL_TESTE, "contratos.contrato.criar"
    )


def test_api_contratos_retorna_400_para_payload_invalido(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, _ = contexto

    resp = client.post(
        f"/credit/carteiras/{carteira_id}/contratos",
        json={"proposta_comercial_id": "nao-e-uuid"},
    )

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_api_contratos_retorna_400_para_query_invalida(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, _ = contexto

    resp = client.get(f"/credit/carteiras/{carteira_id}/contratos?page=0")

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_api_contratos_openapi_publica_respostas_protegidas(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    criar = schema["paths"]["/credit/carteiras/{carteira_id}/contratos"]["post"]
    consultar = schema["paths"]["/credit/contratos/{contrato_id}"]["get"]
    liberar = schema["paths"]["/credit/contratos/{contrato_id}/liberar-para-motor"]["post"]

    assert criar["responses"]["201"]
    assert {"401", "403", "404", "409"} <= set(criar["responses"])
    assert {"401", "403", "404"} <= set(consultar["responses"])
    assert {"401", "403", "404", "409"} <= set(liberar["responses"])


def _proposta_aprovada(client: TestClient, carteira_id: str, devedor_id: str) -> str:
    proposta = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
        json={"parametros": {"valor": 2500, "prazo_meses": 10}},
    )
    assert proposta.status_code == 201
    proposta_id = proposta.json()["id"]
    enviada = client.post(f"/credit/propostas-comerciais/{proposta_id}/enviar-para-analise")
    aprovada = client.post(f"/credit/propostas-comerciais/{proposta_id}/aprovar")
    assert enviada.status_code == 200
    assert aprovada.status_code == 200
    return str(proposta_id)
