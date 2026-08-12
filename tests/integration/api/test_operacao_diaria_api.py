"""Testes de integracao da API Operacao Diaria (IMP-181..IMP-184)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from emprestimo.application.autorizacao import Principal
from emprestimo.application.errors import AcessoNegadoError, TransicaoEstadoInvalidaError
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.operacao_diaria import (
    CanalComunicacao,
    EstadoCobranca,
    EstadoCompromisso,
    EstadoLembrete,
    TipoAcaoCobranca,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

TENANT_ID = uuid.UUID("78000000-0000-0000-0000-000000000001")
USUARIO_ID = uuid.UUID("78000000-0000-0000-0000-000000000002")
CARTEIRA_ID = uuid.UUID("78000000-0000-0000-0000-000000000003")
DEVEDOR_ID = uuid.UUID("78000000-0000-0000-0000-000000000004")
EMPRESTIMO_ID = uuid.UUID("78000000-0000-0000-0000-000000000005")
CASO_ID = uuid.UUID("78000000-0000-0000-0000-000000000006")
PAGAMENTO_ID = uuid.UUID("78000000-0000-0000-0000-000000000007")
AGENDA_ID = uuid.UUID("78000000-0000-0000-0000-000000000008")

PRINCIPAL = Principal(
    usuario_id=USUARIO_ID,
    tenant_id=TENANT_ID,
    perfil_acesso="Operacao",
    access_token_expira_em=datetime.now(UTC) + timedelta(minutes=15),
)


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    autorizacao = Mock()
    autorizacao.exigir_permissao.return_value = None
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    app.dependency_overrides[dependencies.get_carteira_do_principal] = lambda: Carteira(
        id=CARTEIRA_ID,
        tenant_id=TENANT_ID,
        nome="Carteira",
    )
    app.dependency_overrides[dependencies.get_consultar_fila_cobranca_service] = (
        lambda: _fila_service()
    )
    app.dependency_overrides[dependencies.get_registrar_acao_cobranca_service] = (
        lambda: _acao_service()
    )
    app.dependency_overrides[dependencies.get_consultar_agenda_operacional_service] = (
        lambda: _agenda_service()
    )
    app.dependency_overrides[dependencies.get_registrar_comunicacao_manual_service] = (
        lambda: _comunicacao_service()
    )
    app.dependency_overrides[dependencies.get_relatorios_operacionais_service] = (
        lambda: _relatorios_service()
    )
    return TestClient(app)


def test_api_operacao_diaria_expõe_fila_cobranca(client: TestClient) -> None:
    resposta = client.get("/credit/cobrancas/casos")

    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1
    assert resposta.json()["items"][0]["estado"] == "pendente"


def test_api_operacao_diaria_registra_acao_com_idempotency_key(client: TestClient) -> None:
    resposta = client.post(
        f"/credit/cobrancas/casos/{CASO_ID}/acoes",
        json={"tipo": "telefone", "resultado": "cliente contatado"},
        headers={"Idempotency-Key": "api-operacao-acao"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["tipo"] == "telefone"


def test_api_operacao_diaria_exige_idempotency_key(client: TestClient) -> None:
    resposta = client.post(
        f"/credit/cobrancas/casos/{CASO_ID}/acoes",
        json={"tipo": "telefone", "resultado": "cliente contatado"},
    )

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_api_operacao_diaria_expõe_agenda_e_comunicacao(client: TestClient) -> None:
    agenda = client.get("/credit/agenda")
    comunicacao = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}/comunicacoes",
        json={
            "canal": "telefone",
            "ocorrido_em": "2026-09-10T12:00:00Z",
            "resumo": "Contato",
            "resultado": "sem resposta",
        },
        headers={"Idempotency-Key": "api-operacao-comunicacao"},
    )

    assert agenda.status_code == 200
    assert agenda.json()["total"] == 1
    assert comunicacao.status_code == 200
    assert comunicacao.json()["canal"] == "telefone"


def test_api_operacao_diaria_expõe_relatorios_operacionais(client: TestClient) -> None:
    resumo = client.get(
        f"/credit/carteiras/{CARTEIRA_ID}/relatorios/resumo?data_referencia=2026-09-10"
    )
    fluxo = client.get(
        f"/credit/carteiras/{CARTEIRA_ID}/relatorios/fluxo?inicio=2026-09-01&fim=2026-09-30"
    )

    assert resumo.status_code == 200
    assert resumo.json()["total_previsto"] == "100.00"
    assert fluxo.status_code == 200
    assert fluxo.json()["itens"][0]["realizado"] == "50.00"


def test_api_operacao_diaria_rejeita_periodo_de_relatorio_invertido(
    client: TestClient,
) -> None:
    resposta = client.get(
        f"/credit/carteiras/{CARTEIRA_ID}/relatorios/pagamentos" "?inicio=2026-09-30&fim=2026-09-01"
    )

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "payload_invalido"


def test_api_operacao_diaria_exige_evidencia_na_conciliacao_legada_e_mapeia_cancelamento(
    client: TestClient,
) -> None:
    def _falhar(**_: object) -> None:
        raise TransicaoEstadoInvalidaError(AGENDA_ID, "enviar_lembrete_agenda", "estado invalido")

    app = cast(FastAPI, client.app)
    app.dependency_overrides[dependencies.get_manter_lembrete_agenda_service] = (
        lambda: SimpleNamespace(enviar=_falhar, cancelar=_falhar)
    )

    enviar = client.post(
        f"/credit/agenda/lembretes/{AGENDA_ID}/enviar",
        headers={"Idempotency-Key": "api-lembrete-enviar-invalido"},
    )
    cancelar = client.post(
        f"/credit/agenda/lembretes/{AGENDA_ID}/cancelar",
        headers={"Idempotency-Key": "api-lembrete-cancelar-invalido"},
    )

    assert enviar.status_code == 400
    assert enviar.json()["codigo"] == "payload_invalido"
    assert cancelar.status_code == 409
    assert cancelar.json()["codigo"] == "conflito_estado"


def test_api_operacao_diaria_aplica_rbac() -> None:
    app = create_app()
    autorizacao = Mock()
    autorizacao.exigir_permissao.side_effect = AcessoNegadoError("sem permissao")
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao

    resposta = TestClient(app).get("/credit/cobrancas/casos")

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "acesso_negado"


def _fila_service() -> SimpleNamespace:
    return SimpleNamespace(
        listar=lambda **_: SimpleNamespace(
            items=(
                SimpleNamespace(
                    caso_id=CASO_ID,
                    tenant_id=TENANT_ID,
                    carteira_id=CARTEIRA_ID,
                    devedor_id=DEVEDOR_ID,
                    emprestimo_id=EMPRESTIMO_ID,
                    titulo="Cobranca",
                    origem="motor",
                    estado=EstadoCobranca.PENDENTE,
                    total_pendente=Decimal("100.00"),
                    criado_em=datetime(2026, 9, 10, tzinfo=UTC),
                ),
            ),
            total=1,
        )
    )


def _acao_service() -> SimpleNamespace:
    return SimpleNamespace(
        registrar=lambda **_: SimpleNamespace(
            acao_id=uuid.uuid4(),
            caso_id=CASO_ID,
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
            emprestimo_id=EMPRESTIMO_ID,
            usuario_id=USUARIO_ID,
            tipo=TipoAcaoCobranca.TELEFONE,
            resultado="cliente contatado",
            registrada_em=datetime(2026, 9, 10, tzinfo=UTC),
        )
    )


def _agenda_service() -> SimpleNamespace:
    agenda = SimpleNamespace(
        agenda_item_id=AGENDA_ID,
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_solicitante_id=USUARIO_ID,
        titulo="Contato",
        previsto_para=datetime(2026, 9, 10, tzinfo=UTC),
        emprestimo_id=EMPRESTIMO_ID,
        estado=EstadoCompromisso.ABERTO,
        atualizado_em=None,
    )
    lembrete = SimpleNamespace(
        lembrete_id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        agenda_item_id=AGENDA_ID,
        horario=datetime(2026, 9, 10, tzinfo=UTC),
        enviado_por_usuario_id=USUARIO_ID,
        mensagem="Ligar",
        estado=EstadoLembrete.PROGRAMA,
    )
    return SimpleNamespace(
        listar=lambda **_: SimpleNamespace(compromissos=(agenda,), lembretes=(lembrete,), total=1)
    )


def _comunicacao_service() -> SimpleNamespace:
    return SimpleNamespace(registrar=lambda **_: _registro_comunicacao())


def _relatorios_service() -> SimpleNamespace:
    return SimpleNamespace(
        resumo_carteira=lambda **_: SimpleNamespace(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            data_referencia=date(2026, 9, 10),
            total_operacoes=1,
            operacoes_ativas=1,
            operacoes_quitadas=0,
            parcelas_previstas=1,
            parcelas_vencidas=0,
            total_previsto=Decimal("100.00"),
            total_realizado=Decimal("50.00"),
        ),
        fluxo_previsto_realizado=lambda **_: SimpleNamespace(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            inicio=date(2026, 9, 1),
            fim=date(2026, 9, 30),
            itens=(
                SimpleNamespace(
                    data=date(2026, 9, 10),
                    previsto=Decimal("100.00"),
                    realizado=Decimal("50.00"),
                    parcela_ids=(uuid.uuid4(),),
                    pagamento_ids=(PAGAMENTO_ID,),
                ),
            ),
        ),
    )


def _registro_comunicacao() -> SimpleNamespace:
    return SimpleNamespace(
        registro_id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        responsavel_id=USUARIO_ID,
        canal=CanalComunicacao.TELEFONE,
        ocorrido_em=datetime(2026, 9, 10, tzinfo=UTC),
        resumo="Contato",
        resultado="sem resposta",
        devedor_id=DEVEDOR_ID,
        emprestimo_id=EMPRESTIMO_ID,
        parcela_id=None,
        cobranca_acao_id=None,
        agenda_item_id=None,
    )


def test_api_operacao_diaria_documenta_respostas_de_relatorios() -> None:
    schema = create_app().openapi()
    responses = schema["paths"]["/credit/carteiras/{carteira_id}/relatorios/resumo"]["get"][
        "responses"
    ]

    assert {"401", "403", "404"} <= set(responses)
    assert "ResumoCarteiraResponse" in str(responses["200"])


def test_schemas_openapi_incluem_estados_operacionais() -> None:
    schema = create_app().openapi()

    assert "EstadoCobranca" in schema["components"]["schemas"]
    assert "EstadoCompromisso" in schema["components"]["schemas"]
    assert "EstadoLembrete" in schema["components"]["schemas"]
    assert "PromessaPagamentoState" in schema["components"]["schemas"]
    assert "PagamentoState" in schema["components"]["schemas"]
    assert "ParcelaState" in schema["components"]["schemas"]
