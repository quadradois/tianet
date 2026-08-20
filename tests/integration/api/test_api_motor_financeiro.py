"""Testes de integracao da API Motor Financeiro (IMP-165..IMP-168)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.autorizacao import Principal, RecursoDeOutroTenantError
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
PRINCIPAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000501")
TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000502")
PRINCIPAL_TESTE = Principal(
    usuario_id=PRINCIPAL_ID,
    tenant_id=TENANT_ID,
    perfil_acesso="Motor",
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
        nome="Devedor Motor",
        contatos=(
            Contato(
                devedor_id=uuid.uuid4(),
                tipo=TipoContato.EMAIL,
                valor="motor@example.com",
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


def test_api_motor_fluxo_financeiro_completo(client: TestClient, contexto: tuple[str, str]) -> None:
    carteira_id, devedor_id = contexto
    contrato_id = _contrato_liberado(client, carteira_id, devedor_id)

    emprestimo = client.post(
        f"/credit/contratos/{contrato_id}/emprestimos",
        headers={"Idempotency-Key": "api-motor-emprestimo-1"},
    )
    assert emprestimo.status_code == 201
    emprestimo_id = emprestimo.json()["id"]
    assert emprestimo.json()["estado"] == "ativo"
    assert emprestimo.json()["parametros_financeiros"]["valor_contratado"] == "10000.00"

    consulta = client.get(f"/credit/emprestimos/{emprestimo_id}")
    listagem = client.get(f"/credit/carteiras/{carteira_id}/emprestimos")

    assert consulta.status_code == 200
    assert consulta.json()["id"] == emprestimo_id
    assert listagem.status_code == 200
    assert listagem.json()["total"] == 1
    assert listagem.json()["items"][0]["id"] == emprestimo_id

    # Sem plano de parcelas (DR-004): o pagamento move a divida diretamente, e o
    # que o devedor deve em cada acerto vem do saldo daquele dia.
    pagamento = client.post(
        f"/credit/emprestimos/{emprestimo_id}/pagamentos",
        json={"valor": "1000.00", "recebido_em": "2026-09-10T12:00:00Z"},
        headers={"Idempotency-Key": "api-motor-pagamento-1"},
    )
    saldo = client.get(f"/credit/emprestimos/{emprestimo_id}/saldo?data_referencia=2026-10-10")
    memorias = client.get(f"/credit/emprestimos/{emprestimo_id}/memoria-calculo")
    consulta_quitacao = client.get(
        f"/credit/emprestimos/{emprestimo_id}/quitacao?data_referencia=2026-10-10"
    )
    renegociacao = client.post(
        f"/credit/emprestimos/{emprestimo_id}/renegociacoes",
        json={
            "novos_parametros": {"taxa_juros_mensal": "0.0150"},
            "renegociado_em": "2026-10-10T12:00:00Z",
        },
        headers={"Idempotency-Key": "api-motor-renegociacao-1"},
    )

    assert pagamento.status_code == 200
    assert pagamento.json()["memoria"]["tipo"] == "pagamento"
    assert saldo.status_code == 200
    assert saldo.json()["memoria"]["tipo"] == "saldo"
    assert memorias.status_code == 200
    assert {"pagamento"} <= {item["tipo"] for item in memorias.json()}
    assert consulta_quitacao.status_code == 200
    assert Decimal(consulta_quitacao.json()["valor_quitacao"]["valor_total"]) > Decimal("0.00")
    assert renegociacao.status_code == 200
    assert renegociacao.json()["memoria"]["tipo"] == "renegociacao"


def test_api_motor_quitacao_executa_e_replay(client: TestClient, contexto: tuple[str, str]) -> None:
    carteira_id, devedor_id = contexto
    emprestimo_id = _emprestimo_ativo(client, carteira_id, devedor_id)

    quitacao = client.post(
        f"/credit/emprestimos/{emprestimo_id}/quitacao",
        json={"recebido_em": "2026-10-10T12:00:00Z"},
        headers={"Idempotency-Key": "api-motor-quitacao-1"},
    )
    replay = client.post(
        f"/credit/emprestimos/{emprestimo_id}/quitacao",
        json={"recebido_em": "2026-10-10T12:00:00Z"},
        headers={"Idempotency-Key": "api-motor-quitacao-1"},
    )

    assert quitacao.status_code == 200
    assert quitacao.json()["estado"] == "quitado"
    assert replay.status_code == 200
    assert replay.json()["pagamento"]["id"] == quitacao.json()["pagamento"]["id"]


def test_api_motor_rejeita_payload_financeiro_arbitrario(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, devedor_id = contexto
    emprestimo_id = _emprestimo_ativo(client, carteira_id, devedor_id)

    resposta = client.post(
        f"/credit/emprestimos/{emprestimo_id}/renegociacoes",
        json={
            "novos_parametros": {
                "taxa_juros_mensal": "0.0150",
                "regra_calculo": {"tipo": "livre"},
            },
            "renegociado_em": "2026-10-10T12:00:00Z",
        },
        headers={"Idempotency-Key": "api-motor-renegociacao-invalida"},
    )

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "payload_invalido"


def test_api_motor_exige_idempotency_key(client: TestClient, contexto: tuple[str, str]) -> None:
    carteira_id, devedor_id = contexto
    contrato_id = _contrato_liberado(client, carteira_id, devedor_id)

    resposta = client.post(f"/credit/contratos/{contrato_id}/emprestimos")

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_api_motor_conflito_idempotencia_payload_divergente(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, devedor_id = contexto
    emprestimo_id = _emprestimo_ativo(client, carteira_id, devedor_id)

    primeiro = client.post(
        f"/credit/emprestimos/{emprestimo_id}/pagamentos",
        json={"valor": "100.00", "recebido_em": "2026-09-10T12:00:00Z"},
        headers={"Idempotency-Key": "api-motor-pagamento-divergente"},
    )
    divergente = client.post(
        f"/credit/emprestimos/{emprestimo_id}/pagamentos",
        json={"valor": "999.00", "recebido_em": "2026-09-11T12:00:00Z"},
        headers={"Idempotency-Key": "api-motor-pagamento-divergente"},
    )

    assert primeiro.status_code == 200
    assert divergente.status_code == 409
    assert divergente.json()["codigo"] == "conflito_idempotencia"


def test_api_motor_renegociacao_idempotente_e_exige_chave(
    client: TestClient, contexto: tuple[str, str]
) -> None:
    carteira_id, devedor_id = contexto
    emprestimo_id = _emprestimo_ativo(client, carteira_id, devedor_id)
    payload = {
        "novos_parametros": {"taxa_juros_mensal": "0.0150"},
        "renegociado_em": "2026-10-10T12:00:00Z",
    }

    sem_chave = client.post(f"/credit/emprestimos/{emprestimo_id}/renegociacoes", json=payload)
    primeira = client.post(
        f"/credit/emprestimos/{emprestimo_id}/renegociacoes",
        json=payload,
        headers={"Idempotency-Key": "api-motor-renegociacao-replay"},
    )
    replay = client.post(
        f"/credit/emprestimos/{emprestimo_id}/renegociacoes",
        json=payload,
        headers={"Idempotency-Key": "api-motor-renegociacao-replay"},
    )
    divergente = client.post(
        f"/credit/emprestimos/{emprestimo_id}/renegociacoes",
        json={
            "novos_parametros": {"taxa_juros_mensal": "0.0200"},
            "renegociado_em": "2026-10-10T12:00:00Z",
        },
        headers={"Idempotency-Key": "api-motor-renegociacao-replay"},
    )

    assert sem_chave.status_code == 400
    assert sem_chave.json()["codigo"] == "idempotency_key_ausente"
    assert primeira.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["memoria"]["id"] == primeira.json()["memoria"]["id"]
    assert divergente.status_code == 409
    assert divergente.json()["codigo"] == "conflito_idempotencia"


def test_api_motor_exige_permissao(client: TestClient, contexto: tuple[str, str]) -> None:
    carteira_id, devedor_id = contexto
    contrato_id = _contrato_liberado(client, carteira_id, devedor_id)
    app = create_app()
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL_TESTE
    autorizacao = Mock()
    autorizacao.exigir_permissao.side_effect = AcessoNegadoError("motor.emprestimo.criar")
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            f"/credit/contratos/{contrato_id}/emprestimos",
            headers={"Idempotency-Key": "api-motor-sem-permissao"},
        )

    assert resp.status_code == 403
    autorizacao.exigir_permissao.assert_any_call(PRINCIPAL_TESTE, "motor.emprestimo.criar")


def test_api_motor_listagem_cross_tenant_retorna_404(session: Session) -> None:
    tenant = TenantFactory.build(id=TENANT_ID)
    outro_tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    SqlAlchemyTenantRepository(session).save(outro_tenant)
    carteira_outro_tenant = CarteiraFactory.build(tenant_id=outro_tenant.id)
    SqlAlchemyCarteiraRepository(session).save(carteira_outro_tenant)
    usuario = UsuarioFactory.build(id=PRINCIPAL_ID, tenant_id=tenant.id)
    SqlAlchemyUsuarioRepository(session).save(usuario)
    session.commit()

    app = create_app()
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL_TESTE
    autorizacao = Mock()
    autorizacao.exigir_permissao.return_value = None
    autorizacao.exigir_tenant_do_recurso.side_effect = RecursoDeOutroTenantError()
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    with TestClient(app) as client:
        resp = client.get(f"/credit/carteiras/{carteira_outro_tenant.id}/emprestimos")

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "carteira_nao_encontrada"


def test_api_motor_openapi_publica_respostas_protegidas(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    criar = schema["paths"]["/credit/contratos/{contrato_id}/emprestimos"]["post"]
    consultar = schema["paths"]["/credit/emprestimos/{emprestimo_id}"]["get"]
    pagamento = schema["paths"]["/credit/emprestimos/{emprestimo_id}/pagamentos"]["post"]
    quitacao = schema["paths"]["/credit/emprestimos/{emprestimo_id}/quitacao"]["post"]

    assert {"400", "401", "403", "404", "409"} <= set(criar["responses"])
    assert {"400", "401", "403", "404"} <= set(consultar["responses"])
    assert {"400", "401", "403", "404", "409"} <= set(pagamento["responses"])
    assert {"400", "401", "403", "404", "409"} <= set(quitacao["responses"])


def _emprestimo_ativo(client: TestClient, carteira_id: str, devedor_id: str) -> str:
    contrato_id = _contrato_liberado(client, carteira_id, devedor_id)
    emprestimo = client.post(
        f"/credit/contratos/{contrato_id}/emprestimos",
        headers={"Idempotency-Key": f"api-motor-emp-{uuid.uuid4()}"},
    )
    assert emprestimo.status_code == 201
    return str(emprestimo.json()["id"])


def _contrato_liberado(client: TestClient, carteira_id: str, devedor_id: str) -> str:
    proposta = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
        json={
            "parametros": {
                "valor_contratado": "10000.00",
                "dia_de_acerto": 10,
                "primeiro_vencimento": "2026-09-10",
                "taxa_juros_mensal": "0.0200",
                "moeda": "BRL",
            }
        },
    )
    assert proposta.status_code == 201
    proposta_id = proposta.json()["id"]
    enviada = client.post(f"/credit/propostas-comerciais/{proposta_id}/enviar-para-analise")
    aprovada = client.post(f"/credit/propostas-comerciais/{proposta_id}/aprovar")
    contrato = client.post(
        f"/credit/carteiras/{carteira_id}/contratos",
        json={"proposta_comercial_id": proposta_id},
    )
    assert enviada.status_code == 200
    assert aprovada.status_code == 200
    assert contrato.status_code == 201
    assinado = client.post(f"/credit/contratos/{contrato.json()['id']}/assinar")
    liberado = client.post(f"/credit/contratos/{contrato.json()['id']}/liberar-para-motor")
    assert assinado.status_code == 200
    assert liberado.status_code == 200
    return str(contrato.json()["id"])
