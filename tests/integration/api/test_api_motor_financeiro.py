"""Testes de integracao da API Motor Financeiro (IMP-165..IMP-168)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.autorizacao import Principal, RecursoDeOutroTenantError
from emprestimo.application.errors import AcessoNegadoError
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.infrastructure.db.orm import AuditoriaLogORM, JobAgendadoORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyConfiguracaoRepository,
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


def test_pagamento_excedente_enfileira_aviso_e_estorno_reconcilia(
    client: TestClient,
    contexto: tuple[str, str],
    session: Session,
) -> None:
    carteira_id, devedor_id = contexto
    SqlAlchemyConfiguracaoRepository(session).save(
        Configuracao(
            tenant_id=TENANT_ID,
            chave="credor_whatsapp",
            valor="5511999999999",
        )
    )
    session.commit()
    emprestimo_id = _emprestimo_ativo(client, carteira_id, devedor_id)

    pagamento = client.post(
        f"/credit/emprestimos/{emprestimo_id}/pagamentos",
        json={"valor": "12000.00", "recebido_em": "2026-09-10T12:00:00Z"},
        headers={"Idempotency-Key": "api-motor-pagamento-excedente"},
    )

    assert pagamento.status_code == 200
    corpo = pagamento.json()
    sobra = Decimal(corpo["valor_devolvido"])
    distribuido = (
        Decimal(corpo["valor_juros"])
        + Decimal(corpo["valor_amortizacao"])
        + Decimal(corpo["valor_encargos"])
    )
    assert sobra > Decimal("0.00")
    assert Decimal(corpo["valor_recebido"]) - sobra == distribuido
    assert Decimal(corpo["valor_estornado"]) == Decimal("0.00")
    assert Decimal(corpo["valor_sobra"]) == sobra
    assert corpo["reconciliado"] is False
    session.expire_all()
    job = session.scalar(
        select(JobAgendadoORM).where(
            JobAgendadoORM.origem_tipo == "sobra_pagamento",
            JobAgendadoORM.origem_id == uuid.UUID(corpo["id"]),
        )
    )
    assert job is not None
    assert job.tipo == "avisar_sobra_pagamento_whatsapp"
    assert job.payload["destinatario"] == "5511999999999"

    acima_da_sobra = client.post(
        f"/credit/pagamentos/{corpo['id']}/estornos",
        json={"valor": str(sobra + Decimal("0.01"))},
        headers={"Idempotency-Key": "api-motor-estorno-acima"},
    )
    estorno = client.post(
        f"/credit/pagamentos/{corpo['id']}/estornos",
        json={"valor": str(sobra)},
        headers={"Idempotency-Key": "api-motor-estorno-total"},
    )

    assert acima_da_sobra.status_code == 409
    assert estorno.status_code == 200
    assert Decimal(estorno.json()["valor_estornado"]) == sobra
    assert Decimal(estorno.json()["valor_sobra"]) == Decimal("0.00")
    assert estorno.json()["reconciliado"] is True
    session.expire_all()
    acoes = set(
        session.scalars(
            select(AuditoriaLogORM.acao).where(
                AuditoriaLogORM.entidade == "pagamento",
                AuditoriaLogORM.entidade_id == uuid.UUID(corpo["id"]),
            )
        ).all()
    )
    assert {"estornar.inicio", "estornar.sucesso", "estornar.falha"} <= acoes


def test_pagamento_excedente_sem_whatsapp_nao_enfileira_e_audita_motivo(
    client: TestClient,
    contexto: tuple[str, str],
    session: Session,
) -> None:
    carteira_id, devedor_id = contexto
    emprestimo_id = _emprestimo_ativo(client, carteira_id, devedor_id)

    pagamento = client.post(
        f"/credit/emprestimos/{emprestimo_id}/pagamentos",
        json={"valor": "12000.00", "recebido_em": "2026-09-10T12:00:00Z"},
        headers={"Idempotency-Key": "api-motor-sem-whatsapp-credor"},
    )

    assert pagamento.status_code == 200
    pagamento_id = uuid.UUID(pagamento.json()["id"])
    session.expire_all()
    assert (
        session.scalar(
            select(JobAgendadoORM).where(
                JobAgendadoORM.origem_tipo == "sobra_pagamento",
                JobAgendadoORM.origem_id == pagamento_id,
            )
        )
        is None
    )
    auditoria = session.scalar(
        select(AuditoriaLogORM).where(
            AuditoriaLogORM.entidade == "sobra_pagamento_aviso",
            AuditoriaLogORM.entidade_id == pagamento_id,
            AuditoriaLogORM.acao == "enfileirar.ignorado",
        )
    )
    assert auditoria is not None
    assert auditoria.status == "nao_configurado"
    assert auditoria.detalhes is not None
    assert "credor_whatsapp_nao_configurado" in auditoria.detalhes


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
        headers={"Idempotency-Key": f"api-motor-proposta-{uuid.uuid4()}"},
    )
    assert proposta.status_code == 201
    proposta_id = proposta.json()["id"]
    enviada = client.post(
        f"/credit/propostas-comerciais/{proposta_id}/enviar-para-analise",
        headers={"Idempotency-Key": f"api-motor-enviar-{uuid.uuid4()}"},
    )
    aprovada = client.post(
        f"/credit/propostas-comerciais/{proposta_id}/aprovar",
        headers={"Idempotency-Key": f"api-motor-aprovar-{uuid.uuid4()}"},
    )
    contrato = client.post(
        f"/credit/carteiras/{carteira_id}/contratos",
        json={"proposta_comercial_id": proposta_id},
        headers={"Idempotency-Key": f"api-motor-contrato-{uuid.uuid4()}"},
    )
    assert enviada.status_code == 200
    assert aprovada.status_code == 200
    assert contrato.status_code == 201
    assinado = client.post(
        f"/credit/contratos/{contrato.json()['id']}/assinar",
        headers={"Idempotency-Key": f"api-motor-assinar-{uuid.uuid4()}"},
    )
    liberado = client.post(
        f"/credit/contratos/{contrato.json()['id']}/liberar-para-motor",
        headers={"Idempotency-Key": f"api-motor-liberar-{uuid.uuid4()}"},
    )
    assert assinado.status_code == 200
    assert liberado.status_code == 200
    return str(contrato.json()["id"])


def test_imp_362_saldo_por_devedor_soma_no_motor_e_bate_com_as_consultas_individuais(
    client: TestClient,
    contexto: tuple[str, str],
) -> None:
    """O total agregado tem que ser identico a soma das consultas individuais.

    E o ponto do IMP-362: sem este endpoint, responder "quanto o Devedor deve?"
    obrigaria o consumidor — frontend ou LLM — a somar saldos, violando a regra
    de que o Motor e a autoridade sobre dinheiro. O teste usa **dois**
    emprestimos porque com um so a soma seria indistinguivel da consulta unica.
    """
    carteira_id, devedor_id = contexto
    primeiro = _emprestimo_ativo(client, carteira_id, devedor_id)
    segundo = _emprestimo_ativo(client, carteira_id, devedor_id)
    data = "2026-09-10"

    agregado = client.get(f"/credit/devedores/{devedor_id}/saldo?data_referencia={data}")
    individuais = [
        client.get(f"/credit/emprestimos/{emprestimo_id}/saldo?data_referencia={data}")
        for emprestimo_id in (primeiro, segundo)
    ]

    assert agregado.status_code == 200
    corpo = agregado.json()
    assert corpo["emprestimos_considerados"] == 2
    assert {item["emprestimo_id"] for item in corpo["itens"]} == {primeiro, segundo}

    esperado = sum(Decimal(r.json()["total"]) for r in individuais)
    assert Decimal(corpo["total"]) == esperado, "o total agregado diverge das consultas"
    assert Decimal(corpo["principal"]) == sum(Decimal(r.json()["principal"]) for r in individuais)
    assert Decimal(corpo["juros"]) == sum(Decimal(r.json()["juros"]) for r in individuais)


def test_imp_362_devedor_sem_emprestimo_responde_zero_explicito(
    client: TestClient,
    contexto: tuple[str, str],
) -> None:
    """Zero explicito, nao 404: o Devedor existe e nao deve nada."""
    _, devedor_id = contexto

    resp = client.get(f"/credit/devedores/{devedor_id}/saldo?data_referencia=2026-09-10")

    assert resp.status_code == 200
    corpo = resp.json()
    assert Decimal(corpo["total"]) == Decimal("0.00")
    assert corpo["emprestimos_considerados"] == 0
    assert corpo["itens"] == []


def test_imp_362_devedor_inexistente_responde_404_e_nao_zero(
    client: TestClient,
    contexto: tuple[str, str],
) -> None:
    """Zero diria "nao deve nada" sobre quem nem esta cadastrado."""
    del contexto

    resp = client.get(f"/credit/devedores/{uuid.uuid4()}/saldo?data_referencia=2026-09-10")

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "devedor_nao_encontrado"
