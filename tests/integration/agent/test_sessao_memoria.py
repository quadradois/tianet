"""Memória da sessão e refs em PostgreSQL real (IMP-356-F slice 1).

Round-trip dos três repositórios novos, unicidades que protegem a
invariante (ordem da conversa, call único, ref única por sessão) e o
ciclo definir → resolver → invalidar da referência opaca.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.factories import TenantFactory

from emprestimo.agent.conversa import (
    ClasseContexto,
    MensagemConversa,
    PapelMensagem,
    ReferenciaSessao,
    SessaoConversa,
    ToolCallExec,
    resolver_referencia,
)
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.infrastructure.repositories import (
    SqlAlchemyMensagemConversaRepository,
    SqlAlchemyReferenciaSessaoRepository,
    SqlAlchemySessaoConversaRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyToolCallExecRepository,
)

T0 = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
INSTANCIA = "tianet_teste"
REMETENTE = "5511999999999"


@pytest.fixture
def tenant_id(session: Session) -> uuid.UUID:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    session.commit()
    return tenant.id


@pytest.fixture
def sessao(session: Session, tenant_id: uuid.UUID) -> SessaoConversa:
    repo = SqlAlchemySessaoConversaRepository(session)
    sessao = repo.garantir(tenant_id, INSTANCIA, ClasseContexto.OPERADORA, REMETENTE)
    session.commit()
    return sessao


def test_referencia_pendente_round_trip(session: Session, sessao: SessaoConversa) -> None:
    repo = SqlAlchemySessaoConversaRepository(session)
    expira = T0 + timedelta(minutes=5)
    repo.definir_referencia(sessao.id, "ref-1", expira)
    session.commit()
    lida = repo.buscar(sessao.tenant_id, INSTANCIA, ClasseContexto.OPERADORA, REMETENTE)
    assert lida is not None
    assert lida.referencia_pendente == "ref-1"
    assert lida.expira_em == expira
    repo.limpar_referencia(sessao.id)
    session.commit()
    limpa = repo.buscar(sessao.tenant_id, INSTANCIA, ClasseContexto.OPERADORA, REMETENTE)
    assert limpa is not None and limpa.referencia_pendente is None


def test_mensagens_em_ordem_de_indice(session: Session, sessao: SessaoConversa) -> None:
    repo = SqlAlchemyMensagemConversaRepository(session)
    for indice, texto in [(1, "segunda"), (0, "primeira")]:
        repo.adicionar(
            MensagemConversa(
                id=uuid.uuid4(),
                sessao_id=sessao.id,
                inbox_id=None,
                indice=indice,
                papel=PapelMensagem.USUARIO,
                texto=texto,
                criado_em=T0,
            )
        )
    session.commit()
    mensagens = repo.listar_por_sessao(sessao.id)
    assert [m.texto for m in mensagens] == ["primeira", "segunda"]
    with pytest.raises(IntegrityError):
        repo.adicionar(
            MensagemConversa(
                id=uuid.uuid4(),
                sessao_id=sessao.id,
                inbox_id=None,
                indice=0,
                papel=PapelMensagem.USUARIO,
                texto="duplicada",
                criado_em=T0,
            )
        )


def test_tool_call_registra_e_nao_repete_call_id(session: Session, sessao: SessaoConversa) -> None:
    repo = SqlAlchemyToolCallExecRepository(session)
    inbox_id = uuid.uuid4()
    repo.registrar(
        ToolCallExec(
            id=uuid.uuid4(),
            sessao_id=sessao.id,
            inbox_id=inbox_id,
            call_id="call_1",
            ferramenta="consultar_acertos",
            schema_versao="consulta_operadora_v1",
            parametros={},
            resultado={"status": "ok"},
            latencia_ms=100,
            completa=True,
            criado_em=T0,
        )
    )
    session.commit()
    assert len(repo.listar_por_sessao(sessao.id)) == 1
    with pytest.raises(IntegrityError):
        repo.registrar(
            ToolCallExec(
                id=uuid.uuid4(),
                sessao_id=sessao.id,
                inbox_id=inbox_id,
                call_id="call_1",
                ferramenta="consultar_acertos",
                schema_versao="consulta_operadora_v1",
                parametros={},
                resultado={"status": "ok"},
                latencia_ms=100,
                completa=True,
                criado_em=T0,
            )
        )


def test_ref_resolve_e_invalida_sem_apagar(session: Session, sessao: SessaoConversa) -> None:
    repo = SqlAlchemyReferenciaSessaoRepository(session)
    devedor_id = uuid.uuid4()
    repo.salvar(
        ReferenciaSessao(
            id=uuid.uuid4(),
            sessao_id=sessao.id,
            ref="ref-1",
            devedor_id=devedor_id,
            expira_em=T0 + timedelta(minutes=5),
            criado_em=T0,
        )
    )
    session.commit()
    refs = repo.listar_por_sessao(sessao.id)
    assert resolver_referencia(refs, sessao.id, "ref-1", T0) == devedor_id
    repo.invalidar_por_sessao(sessao.id, T0)
    session.commit()
    refs = repo.listar_por_sessao(sessao.id)
    assert len(refs) == 1
    assert refs[0].revogada_em == T0
    assert resolver_referencia(refs, sessao.id, "ref-1", T0) is None
    with pytest.raises(IntegrityError):
        repo.salvar(
            ReferenciaSessao(
                id=uuid.uuid4(),
                sessao_id=sessao.id,
                ref="ref-1",
                devedor_id=uuid.uuid4(),
                expira_em=T0 + timedelta(minutes=5),
                criado_em=T0,
            )
        )
