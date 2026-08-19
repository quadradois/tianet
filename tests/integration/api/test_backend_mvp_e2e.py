"""Fluxos E2E transversais do Backend MVP (PLAN-020/P1)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.iam_catalogo import CATALOGO_PERMISSOES
from emprestimo.application.notifications import FakeNotificationChannel, NotificationService
from emprestimo.application.scheduler import SchedulerService
from emprestimo.domain.credit.operacao_diaria import CobrancaCaso
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.db.orm import (
    AuditoriaLogORM,
    JobAgendadoORM,
    LembreteORM,
    RegistroComunicacaoORM,
    SolicitacaoNotificacaoORM,
)
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyCredencialRepository,
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.repositories.operacao_diaria import (
    SqlAlchemyCobrancaCasoRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "segredo-plan-020-e2e"


@dataclass(frozen=True)
class AmbienteMVP:
    client: TestClient
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    usuario: Usuario
    headers: dict[str, str]


@pytest.fixture
def ambiente_mvp(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[AmbienteMVP]:
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, JWT_SECRET)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_FROM", raising=False)
    monkeypatch.setenv("APP_ENV", "test")

    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id, nome="Carteira MVP")
    SqlAlchemyCarteiraRepository(session).save(carteira)
    usuario = UsuarioFactory.build(
        tenant_id=tenant.id,
        email="operador.mvp@example.com",
        estado=UsuarioState.ATIVO,
        perfil_acesso="Administrador MVP",
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=usuario.id, segredo="senha-mvp-segura")
    )
    perfil = PerfilAcesso(tenant_id=tenant.id, nome="Administrador MVP")
    for permissao in CATALOGO_PERMISSOES:
        perfil.adicionar_permissao(permissao)
    perfil_repo = SqlAlchemyPerfilAcessoRepository(session)
    perfil_repo.save(perfil)
    perfil_repo.atribuir_usuario(usuario.id, perfil.id)
    session.commit()

    with TestClient(create_app()) as client:
        login = client.post(
            "/auth/login",
            json={
                "identificador_institucional": tenant.identificador_institucional,
                "email": usuario.email,
                "segredo": "senha-mvp-segura",
            },
            headers={"X-Correlation-ID": "plan-020-login"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        yield AmbienteMVP(
            client=client,
            tenant_id=tenant.id,
            carteira_id=carteira.id,
            usuario=usuario,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Correlation-ID": "plan-020-e2e",
            },
        )


def test_imp_257_e2e_tenant_iam_cadastro(
    ambiente_mvp: AmbienteMVP,
    session: Session,
) -> None:
    devedor = _criar_devedor(ambiente_mvp)

    consulta = ambiente_mvp.client.get(
        f"/credit/carteiras/{ambiente_mvp.carteira_id}/devedores/{devedor['id']}",
        headers=ambiente_mvp.headers,
    )

    assert consulta.status_code == 200
    assert consulta.headers["X-Correlation-ID"] == "plan-020-e2e"
    assert consulta.json()["id"] == devedor["id"]
    assert _contar(session, AuditoriaLogORM) >= 3

    sem_token = ambiente_mvp.client.get(
        f"/credit/carteiras/{ambiente_mvp.carteira_id}/devedores/{devedor['id']}"
    )
    assert sem_token.status_code == 401

    outro_tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(outro_tenant)
    outra_carteira = CarteiraFactory.build(tenant_id=outro_tenant.id)
    SqlAlchemyCarteiraRepository(session).save(outra_carteira)
    session.commit()

    fora_do_escopo = ambiente_mvp.client.get(
        f"/credit/carteiras/{outra_carteira.id}/devedores/{devedor['id']}",
        headers=ambiente_mvp.headers,
    )
    assert fora_do_escopo.status_code == 404


def test_imp_258_e2e_cadastro_comercial_contratos(
    ambiente_mvp: AmbienteMVP,
) -> None:
    devedor = _criar_devedor(ambiente_mvp)
    proposta = _proposta_aprovada(ambiente_mvp, devedor["id"])

    contrato_logico = ambiente_mvp.client.get(
        f"/credit/propostas-comerciais/{proposta['id']}/contrato-logico",
        headers=ambiente_mvp.headers,
    )
    assert contrato_logico.status_code == 200
    assert contrato_logico.json()["proposta_id"] == proposta["id"]

    contrato = _contrato_liberado(ambiente_mvp, proposta["id"])

    assert contrato["estado"] == "liberado_para_motor"
    assert contrato["proposta_comercial_id"] == proposta["id"]


def test_imp_259_e2e_contratos_motor_financeiro(
    ambiente_mvp: AmbienteMVP,
) -> None:
    contexto = _emprestimo_com_pagamento(ambiente_mvp)

    saldo = ambiente_mvp.client.get(
        f"/credit/emprestimos/{contexto['emprestimo_id']}/saldo",
        params={"data_referencia": "2026-10-10"},
        headers=ambiente_mvp.headers,
    )
    memoria = ambiente_mvp.client.get(
        f"/credit/emprestimos/{contexto['emprestimo_id']}/memoria-calculo",
        headers=ambiente_mvp.headers,
    )

    assert saldo.status_code == 200
    assert Decimal(saldo.json()["total"]) >= Decimal("0.00")
    assert memoria.status_code == 200
    assert memoria.json()

    replay = ambiente_mvp.client.post(
        f"/credit/emprestimos/{contexto['emprestimo_id']}/pagamentos",
        json={"valor": contexto["pagamento_valor"], "recebido_em": "2026-09-10T12:00:00Z"},
        headers={**ambiente_mvp.headers, "Idempotency-Key": contexto["pagamento_key"]},
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == contexto["pagamento_id"]


def test_imp_260_e2e_motor_operacao_diaria(
    ambiente_mvp: AmbienteMVP,
    session: Session,
) -> None:
    contexto = _emprestimo_com_pagamento(ambiente_mvp)
    caso = CobrancaCaso(
        tenant_id=ambiente_mvp.tenant_id,
        carteira_id=ambiente_mvp.carteira_id,
        devedor_id=uuid.UUID(contexto["devedor_id"]),
        emprestimo_id=uuid.UUID(contexto["emprestimo_id"]),
        titulo="Cobranca MVP",
        origem="motor_financeiro",
        total_pendente=Decimal("100.00"),
    )
    SqlAlchemyCobrancaCasoRepository(session).save(caso)
    session.commit()

    fila = ambiente_mvp.client.get("/credit/cobrancas/casos", headers=ambiente_mvp.headers)
    assert fila.status_code == 200
    assert fila.json()["total"] == 1

    acao = ambiente_mvp.client.post(
        f"/credit/cobrancas/casos/{caso.id}/acoes",
        json={"tipo": "telefone", "resultado": "cliente contatado"},
        headers={**ambiente_mvp.headers, "Idempotency-Key": "plan020-acao"},
    )
    assert acao.status_code == 200

    promessa = ambiente_mvp.client.post(
        f"/credit/cobrancas/casos/{caso.id}/promessas",
        json={"valor_declarado": "100.00", "data_promessa": "2026-09-20"},
        headers={**ambiente_mvp.headers, "Idempotency-Key": "plan020-promessa"},
    )
    assert promessa.status_code == 200

    comunicacao = ambiente_mvp.client.post(
        f"/credit/carteiras/{ambiente_mvp.carteira_id}/devedores/{contexto['devedor_id']}"
        "/comunicacoes",
        json={
            "canal": "telefone",
            "ocorrido_em": "2026-09-10T12:00:00Z",
            "resumo": "Acompanhamento operacional",
            "resultado": "registrado",
            "emprestimo_id": contexto["emprestimo_id"],
        },
        headers={**ambiente_mvp.headers, "Idempotency-Key": "plan020-comunicacao"},
    )
    assert comunicacao.status_code == 200

    periodo_invalido = ambiente_mvp.client.get(
        f"/credit/carteiras/{ambiente_mvp.carteira_id}/relatorios/pagamentos",
        params={"inicio": "2026-10-10", "fim": "2026-09-10"},
        headers=ambiente_mvp.headers,
    )
    assert periodo_invalido.status_code == 400

    resumo = ambiente_mvp.client.get(
        f"/credit/carteiras/{ambiente_mvp.carteira_id}/relatorios/resumo",
        params={"data_referencia": "2026-09-10"},
        headers=ambiente_mvp.headers,
    )
    assert resumo.status_code == 200
    assert resumo.json()["total_operacoes"] >= 1


def test_imp_261_e2e_agenda_scheduler_notification(
    ambiente_mvp: AmbienteMVP,
    session_factory: sessionmaker[Session],
) -> None:
    contexto = _emprestimo_com_pagamento(ambiente_mvp)
    template = _criar_template_ativo(ambiente_mvp)

    compromisso = ambiente_mvp.client.post(
        f"/credit/carteiras/{ambiente_mvp.carteira_id}/devedores/{contexto['devedor_id']}"
        "/agenda/compromissos",
        json={
            "titulo": "Contato preventivo",
            "previsto_para": "2026-09-10T12:00:00Z",
            "emprestimo_id": contexto["emprestimo_id"],
        },
        headers={**ambiente_mvp.headers, "Idempotency-Key": "plan020-compromisso"},
    )
    assert compromisso.status_code == 200

    lembrete = ambiente_mvp.client.post(
        f"/credit/agenda/compromissos/{compromisso.json()['agenda_item_id']}/lembretes",
        json={"horario": "2026-09-10T11:00:00Z", "mensagem": "Ligar para cliente"},
        headers={**ambiente_mvp.headers, "Idempotency-Key": "plan020-lembrete"},
    )
    assert lembrete.status_code == 200
    assert lembrete.json()["estado"] == "programa"

    jobs = ambiente_mvp.client.get(
        "/credit/automacao/jobs",
        params={"carteira_id": ambiente_mvp.carteira_id},
        headers=ambiente_mvp.headers,
    )
    assert jobs.status_code == 200
    assert jobs.json()["total"] == 1
    assert jobs.json()["items"][0]["origem_id"] == lembrete.json()["lembrete_id"]

    scheduler = SchedulerService(lambda: SqlAlchemyUnitOfWork(session_factory))
    claims = scheduler.reivindicar(
        slots_livres=1,
        batch_size=1,
        agora=datetime(2026, 9, 10, 11, 1, tzinfo=UTC),
    )
    assert len(claims) == 1

    notification = NotificationService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        FakeNotificationChannel(),
    )
    resultado = notification.processar_lembrete(claims[0])
    assert resultado == "finalizado"

    with session_factory() as session:
        assert _contar(session, JobAgendadoORM) == 1
        assert _contar(session, SolicitacaoNotificacaoORM) == 1
        assert _contar(session, RegistroComunicacaoORM) == 1
        lembrete_row = session.get(LembreteORM, uuid.UUID(lembrete.json()["lembrete_id"]))
        assert lembrete_row is not None
        assert lembrete_row.estado == "enviado"
        notificacao = session.scalar(select(SolicitacaoNotificacaoORM))
        assert notificacao is not None
        assert notificacao.template_id == uuid.UUID(template["id"])
        assert notificacao.estado == "aceita"


def _criar_devedor(ambiente: AmbienteMVP) -> dict[str, Any]:
    resposta = ambiente.client.post(
        f"/credit/carteiras/{ambiente.carteira_id}/devedores",
        json={
            "documento": "52998224725",
            "nome": "Cliente MVP",
            "contatos": [
                {
                    "tipo": "email",
                    "valor": f"cliente-{uuid.uuid4().hex[:8]}@example.com",
                    "preferencial": True,
                    "notificacao_estado": "permitido",
                    "notificacao_evidencia": "consentimento registrado no E2E",
                    "notificacao_origem": "teste-plan-020",
                }
            ],
        },
        headers={**ambiente.headers, "Idempotency-Key": f"plan020-devedor-{uuid.uuid4()}"},
    )
    assert resposta.status_code == 201
    return dict(resposta.json())


def _proposta_aprovada(ambiente: AmbienteMVP, devedor_id: str) -> dict[str, Any]:
    simulacao = ambiente.client.post(
        f"/credit/carteiras/{ambiente.carteira_id}/devedores/{devedor_id}" "/simulacoes-comerciais",
        json={"parametros": _parametros_financeiros()},
        headers=ambiente.headers,
    )
    assert simulacao.status_code == 201

    proposta = ambiente.client.post(
        f"/credit/carteiras/{ambiente.carteira_id}/devedores/{devedor_id}" "/propostas-comerciais",
        json={"simulacao_id": simulacao.json()["id"], "parametros": _parametros_financeiros()},
        headers=ambiente.headers,
    )
    assert proposta.status_code == 201

    enviada = ambiente.client.post(
        f"/credit/propostas-comerciais/{proposta.json()['id']}/enviar-para-analise",
        headers=ambiente.headers,
    )
    assert enviada.status_code == 200

    aprovada = ambiente.client.post(
        f"/credit/propostas-comerciais/{proposta.json()['id']}/aprovar",
        headers=ambiente.headers,
    )
    assert aprovada.status_code == 200
    assert aprovada.json()["estado"] == "aprovada"
    return dict(aprovada.json())


def _contrato_liberado(ambiente: AmbienteMVP, proposta_id: str) -> dict[str, Any]:
    contrato = ambiente.client.post(
        f"/credit/carteiras/{ambiente.carteira_id}/contratos",
        json={"proposta_comercial_id": proposta_id},
        headers=ambiente.headers,
    )
    assert contrato.status_code == 201

    assinado = ambiente.client.post(
        f"/credit/contratos/{contrato.json()['id']}/assinar",
        headers=ambiente.headers,
    )
    assert assinado.status_code == 200

    liberado = ambiente.client.post(
        f"/credit/contratos/{contrato.json()['id']}/liberar-para-motor",
        headers=ambiente.headers,
    )
    assert liberado.status_code == 200
    consulta = ambiente.client.get(
        f"/credit/contratos/{contrato.json()['id']}",
        headers=ambiente.headers,
    )
    assert consulta.status_code == 200
    return dict(consulta.json())


def _emprestimo_com_pagamento(ambiente: AmbienteMVP) -> dict[str, str]:
    devedor = _criar_devedor(ambiente)
    proposta = _proposta_aprovada(ambiente, devedor["id"])
    contrato = _contrato_liberado(ambiente, proposta["id"])

    emprestimo = ambiente.client.post(
        f"/credit/contratos/{contrato['id']}/emprestimos",
        headers={**ambiente.headers, "Idempotency-Key": f"plan020-emprestimo-{uuid.uuid4()}"},
    )
    assert emprestimo.status_code == 201

    # Sem plano de parcelas (DR-004): o pagamento e o proprio evento que move a
    # divida, e o valor devido vem do saldo no dia do acerto.
    valor_pago = "1000.00"
    pagamento_key = f"plan020-pagamento-{uuid.uuid4()}"
    pagamento = ambiente.client.post(
        f"/credit/emprestimos/{emprestimo.json()['id']}/pagamentos",
        json={"valor": valor_pago, "recebido_em": "2026-09-10T12:00:00Z"},
        headers={**ambiente.headers, "Idempotency-Key": pagamento_key},
    )
    assert pagamento.status_code == 200
    return {
        "devedor_id": devedor["id"],
        "contrato_id": contrato["id"],
        "emprestimo_id": emprestimo.json()["id"],
        "pagamento_id": pagamento.json()["id"],
        "pagamento_valor": valor_pago,
        "pagamento_key": pagamento_key,
    }


def _criar_template_ativo(ambiente: AmbienteMVP) -> dict[str, Any]:
    template = ambiente.client.post(
        "/credit/notificacoes/templates",
        json={
            "codigo": "lembrete_operacional_v1",
            "versao": 1,
            "assunto": "Lembrete {data_hora}",
            "corpo": "Atendimento via {canal_atendimento} em {data_hora}",
            "parametros_permitidos": ["data_hora", "canal_atendimento"],
        },
        headers=ambiente.headers,
    )
    assert template.status_code == 201

    aprovado = ambiente.client.post(
        f"/credit/notificacoes/templates/{template.json()['id']}/aprovar",
        json={"motivo": "template padrao do E2E MVP"},
        headers=ambiente.headers,
    )
    assert aprovado.status_code == 200

    ativo = ambiente.client.post(
        f"/credit/notificacoes/templates/{template.json()['id']}/ativar",
        headers=ambiente.headers,
    )
    assert ativo.status_code == 200
    return dict(ativo.json())


def _parametros_financeiros() -> dict[str, str | int]:
    return {
        "valor_contratado": "10000.00",
        "dia_de_acerto": 10,
        "taxa_juros_mensal": "0.0200",
        "moeda": "BRL",
    }


def _contar(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0
