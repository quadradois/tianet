"""Trilha própria, zero-writes, máscara e expurgo em PG real (356-F slice 4).

Provas de operação: o turno persiste tool-calls com correlação sem
encostar em `audit_log`; logs carregam correlation sem PII/segredo; o
expurgo remove em lotes só o envelhecido e nunca a auditoria.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import TenantFactory

from emprestimo.agent.conversa import ClasseContexto, SessaoConversa
from emprestimo.agent.executor import EntradaExecucao, Executor
from emprestimo.agent.expurgo import executar_expurgo
from emprestimo.agent.llm_client import RespostaChat, Uso
from emprestimo.agent.metricas import MetricasIngress, MetricasLlm
from emprestimo.agent.trilha import criar_observador
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.infrastructure.db.orm import (
    AuditoriaLogORM,
    CredencialCopilotORM,
    InboxConversaORM,
    MensagemConversaORM,
    ReferenciaSessaoORM,
    SessaoConversaORM,
    SlotExecucaoORM,
    ToolCallExecORM,
)
from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

T0 = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
CPF = "52998224725"
TOKEN = "tok-secreto-distinto"
CARTEIRA = uuid.uuid4()


class LlmFalso:
    def __init__(self, resposta: Any) -> None:
        self._resposta = resposta

    async def chat(self, pedido: Any, timeout_segundos: Any = None) -> Any:
        del pedido, timeout_segundos
        return self._resposta


class ApiFalsa:
    def __init__(self, dto: Any) -> None:
        self._dto = dto

    async def get(self, caminho: str, params: Any = None, timeout_segundos: Any = None) -> Any:
        del caminho, params, timeout_segundos
        return self._dto

    async def close(self) -> None:
        return None


class AuthFalsa:
    def consultar_contexto(self, principal: Any) -> Any:
        del principal
        return SimpleNamespace(carteira_id=CARTEIRA)

    def exigir_permissao(self, principal: Any, operacao: str) -> None:
        del principal, operacao
        return None


class CredencialFalsa:
    def token(self) -> str:
        return TOKEN

    def renovar(self) -> None:
        return None


def _executor(
    session_factory: sessionmaker[Session],
    resposta: Any,
    dto: Any,
    observador: Any = None,
) -> Executor:
    def _criar_api() -> Any:
        return ApiFalsa(dto)

    return Executor(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        credencial=CredencialFalsa(),  # type: ignore[arg-type]
        llm=LlmFalso(resposta),  # type: ignore[arg-type]
        criar_api=_criar_api,
        autorizacao=AuthFalsa(),
        principal=SimpleNamespace(),
        modelo="gpt-4o-mini",
        medidor_tokens=len,
        relogio=lambda: T0,
        observador_tool=observador,
        metricas_llm=MetricasLlm(),
        metricas=MetricasIngress(),
    )


def _sessao() -> SessaoConversa:
    return SessaoConversa(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        instancia_ref="inst",
        classe=ClasseContexto.OPERADORA,
        remetente_normalizado="5511999999999",
    )


ACERTOS_DTO = {
    "tenant_id": "t",
    "carteira_id": "c",
    "data_referencia": "2026-09-16",
    "itens": [],
    "total": 0,
}


def _resposta_vazia() -> RespostaChat:
    return RespostaChat(texto=None, chamadas=(), uso=Uso(10, 5, 15))


def _semear_slots(session: Session) -> None:
    session.add_all(
        [
            SlotExecucaoORM(id=1, reservado_operadora=False, dono_sessao=None, expira_em=None),
            SlotExecucaoORM(id=2, reservado_operadora=True, dono_sessao=None, expira_em=None),
        ]
    )
    session.commit()


def _persistir_sessao(session: Session, sessao: SessaoConversa, tenant_id: uuid.UUID) -> None:
    session.add(
        SessaoConversaORM(
            id=sessao.id,
            tenant_id=tenant_id,
            instancia_ref=sessao.instancia_ref,
            classe=sessao.classe.value,
            remetente_normalizado=sessao.remetente_normalizado,
        )
    )
    session.commit()


def test_turno_persiste_trilha_sem_audit_log(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    from emprestimo.agent.llm_client import ChamadaFerramenta

    _semear_slots(session)
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    session.commit()

    observador = criar_observador(lambda: SqlAlchemyUnitOfWork(session_factory))
    executor = _executor(
        session_factory,
        RespostaChat(
            texto=None,
            chamadas=(ChamadaFerramenta(id="c1", nome="consultar_acertos", argumentos="{}"),),
            uso=Uso(10, 5, 15),
        ),
        ACERTOS_DTO,
        observador,
    )
    sessao = _sessao()
    _persistir_sessao(session, sessao, tenant.id)
    resultado = asyncio.run(
        executor.executar(
            EntradaExecucao(
                inbox_id=uuid.uuid4(),
                sessao=sessao,
                texto=f"acertos? meu doc {CPF}",
                recebido_em=T0,
                correlation_id="corr-teste-1",
            )
        )
    )
    assert resultado.estado == "concluida"
    with session_factory() as leitura:
        linhas = leitura.scalars(select(ToolCallExecORM)).all()
        assert len(linhas) == 1
        assert linhas[0].correlation_id == "corr-teste-1"
        assert linhas[0].ferramenta == "consultar_acertos"
        assert linhas[0].latencia_ms >= 0
        auditoria = leitura.scalar(select(func.count()).select_from(AuditoriaLogORM))
        assert auditoria == 0


def test_logs_levam_correlation_sem_pii_nem_segredo(
    session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    executor = _executor(session_factory, _resposta_vazia(), ACERTOS_DTO)
    with caplog.at_level(logging.INFO, logger="emprestimo.agent.executor"):
        asyncio.run(
            executor.executar(
                EntradaExecucao(
                    inbox_id=uuid.uuid4(),
                    sessao=_sessao(),
                    texto=f"oi, doc {CPF}",
                    recebido_em=T0,
                    correlation_id="corr-teste-2",
                )
            )
        )
    texto = caplog.text
    assert "corr-teste-2" in texto
    assert CPF not in texto and TOKEN not in texto


def _semeiar_antigo(session: Session, tenant_id: uuid.UUID, velho: datetime, sufixo: str) -> None:
    inbox = InboxConversaORM(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        instancia_ref="inst",
        envelope_instance_id="env",
        provider_input_id=f"pid-antigo-{sufixo}",
        remetente_normalizado="5511999999999",
        classe="operadora",
        texto="oi",
        estado="recebida",
        recebido_em=velho,
    )
    sessao = SessaoConversaORM(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        instancia_ref="inst",
        classe="operadora",
        remetente_normalizado=f"5511999999{sufixo}",
        criado_em=velho,
    )
    session.add_all([inbox, sessao])
    session.flush()
    session.add_all(
        [
            MensagemConversaORM(
                id=uuid.uuid4(),
                sessao_id=sessao.id,
                inbox_id=inbox.id,
                indice=0,
                papel="usuario",
                texto="oi",
                criado_em=velho,
            ),
            ToolCallExecORM(
                id=uuid.uuid4(),
                sessao_id=sessao.id,
                inbox_id=inbox.id,
                call_id="c-antiga",
                ferramenta="consultar_acertos",
                schema_versao="consulta_operadora_v1",
                parametros={},
                resultado={"estado": "ok"},
                latencia_ms=1,
                completa=True,
                correlation_id="corr-antiga",
                criado_em=velho,
            ),
            ReferenciaSessaoORM(
                id=uuid.uuid4(),
                sessao_id=sessao.id,
                ref="ref-antiga",
                devedor_id=uuid.uuid4(),
                expira_em=velho,
                criado_em=velho,
            ),
            CredencialCopilotORM(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                instancia_ref=f"inst-{sufixo}",
                refresh_cifrado=b"xx",
                chave_id="v1",
                criado_em=velho,
                atualizado_em=velho,
            ),
            AuditoriaLogORM(
                id=uuid.uuid4(),
                entidade="autenticacao",
                entidade_id=uuid.uuid4(),
                acao="login.sucesso",
                status="ok",
                criado_em=velho,
            ),
        ]
    )
    session.commit()


def test_expurgo_remove_em_lotes_e_poup_audit_log(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    session.commit()
    velho = datetime.now(UTC) - timedelta(days=100)
    _semeiar_antigo(session, tenant.id, velho, "a")
    _semeiar_antigo(session, tenant.id, velho, "b")
    with session_factory() as leitura:
        antes_inbox = leitura.scalar(select(func.count()).select_from(InboxConversaORM))
    assert antes_inbox == 2
    resultado = executar_expurgo(
        lambda: SqlAlchemyUnitOfWork(session_factory), datetime.now(UTC), lote=3
    )
    assert resultado.total == 12
    with session_factory() as leitura:
        assert leitura.scalar(select(func.count()).select_from(InboxConversaORM)) == 0
        assert leitura.scalar(select(func.count()).select_from(SessaoConversaORM)) == 0
        assert leitura.scalar(select(func.count()).select_from(MensagemConversaORM)) == 0
        assert leitura.scalar(select(func.count()).select_from(ToolCallExecORM)) == 0
        assert leitura.scalar(select(func.count()).select_from(ReferenciaSessaoORM)) == 0
        assert leitura.scalar(select(func.count()).select_from(CredencialCopilotORM)) == 0
        assert leitura.scalar(select(func.count()).select_from(AuditoriaLogORM)) == 2
