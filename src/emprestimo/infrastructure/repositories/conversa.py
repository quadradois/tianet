"""Repositórios SQLAlchemy da conversa do agente (IMP-356-A, 356-F slice 1)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from emprestimo.agent.conversa import (
    ClasseContexto,
    EntradaConversa,
    InboxConversaRepository,
    MensagemConversa,
    MensagemConversaRepository,
    PapelMensagem,
    ReferenciaSessao,
    ReferenciaSessaoRepository,
    SessaoConversa,
    SessaoConversaRepository,
    ToolCallExec,
    ToolCallExecRepository,
)
from emprestimo.infrastructure.db.orm import (
    InboxConversaORM,
    MensagemConversaORM,
    ReferenciaSessaoORM,
    SessaoConversaORM,
    ToolCallExecORM,
)


def _to_entrada(row: InboxConversaORM) -> EntradaConversa:
    return EntradaConversa(
        id=row.id,
        tenant_id=row.tenant_id,
        instancia_ref=row.instancia_ref,
        envelope_instance_id=row.envelope_instance_id,
        provider_input_id=row.provider_input_id,
        remetente_normalizado=row.remetente_normalizado,
        classe=ClasseContexto(row.classe),
        texto=row.texto,
        estado=row.estado,
        recebido_em=row.recebido_em,
    )


def _to_sessao(row: SessaoConversaORM) -> SessaoConversa:
    return SessaoConversa(
        id=row.id,
        tenant_id=row.tenant_id,
        instancia_ref=row.instancia_ref,
        classe=ClasseContexto(row.classe),
        remetente_normalizado=row.remetente_normalizado,
        referencia_pendente=row.referencia_pendente,
        expira_em=row.expira_em,
    )


def _to_mensagem(row: MensagemConversaORM) -> MensagemConversa:
    return MensagemConversa(
        id=row.id,
        sessao_id=row.sessao_id,
        inbox_id=row.inbox_id,
        indice=row.indice,
        papel=PapelMensagem(row.papel),
        texto=row.texto,
        criado_em=row.criado_em,
    )


def _to_tool_call(row: ToolCallExecORM) -> ToolCallExec:
    parametros = dict(row.parametros)
    resultado = dict(row.resultado)
    return ToolCallExec(
        id=row.id,
        sessao_id=row.sessao_id,
        inbox_id=row.inbox_id,
        call_id=row.call_id,
        ferramenta=row.ferramenta,
        schema_versao=row.schema_versao,
        parametros={str(k): str(v) for k, v in parametros.items()},
        resultado={str(k): str(v) for k, v in resultado.items()},
        latencia_ms=row.latencia_ms,
        completa=row.completa,
        criado_em=row.criado_em,
        correlation_id=row.correlation_id,
    )


def _to_referencia(row: ReferenciaSessaoORM) -> ReferenciaSessao:
    return ReferenciaSessao(
        id=row.id,
        sessao_id=row.sessao_id,
        ref=row.ref,
        devedor_id=row.devedor_id,
        expira_em=row.expira_em,
        revogada_em=row.revogada_em,
        criado_em=row.criado_em,
    )


class SqlAlchemyInboxConversaRepository(InboxConversaRepository):
    """Inbox durável: o INSERT em savepoint decide replay sem desfazer nada."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def salvar(self, entrada: EntradaConversa) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(
                    InboxConversaORM(
                        id=entrada.id,
                        tenant_id=entrada.tenant_id,
                        instancia_ref=entrada.instancia_ref,
                        envelope_instance_id=entrada.envelope_instance_id,
                        provider_input_id=entrada.provider_input_id,
                        remetente_normalizado=entrada.remetente_normalizado,
                        classe=entrada.classe.value,
                        texto=entrada.texto,
                        estado=entrada.estado,
                        motivo_descarte=None,
                    )
                )
                self._session.flush()
        except IntegrityError:
            # Chave (tenant, instancia, provider-ID) já existe: replay.
            # O savepoint desfaz só este INSERT; a transação externa segue.
            return False
        return True

    def buscar_por_chave(
        self,
        tenant_id: uuid.UUID,
        instancia_ref: str,
        provider_input_id: str,
    ) -> EntradaConversa | None:
        row = self._session.scalars(
            select(InboxConversaORM)
            .where(InboxConversaORM.tenant_id == tenant_id)
            .where(InboxConversaORM.instancia_ref == instancia_ref)
            .where(InboxConversaORM.provider_input_id == provider_input_id)
        ).one_or_none()
        return _to_entrada(row) if row is not None else None

    def contar(self, tenant_id: uuid.UUID) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(InboxConversaORM)
                .where(InboxConversaORM.tenant_id == tenant_id)
            )
            or 0
        )

    def contar_por_classe(self, tenant_id: uuid.UUID) -> dict[ClasseContexto, int]:
        rows = self._session.execute(
            select(InboxConversaORM.classe, func.count())
            .where(InboxConversaORM.tenant_id == tenant_id)
            .group_by(InboxConversaORM.classe)
        ).all()
        return {ClasseContexto(classe): int(total) for classe, total in rows}

    def listar_recentes(self, tenant_id: uuid.UUID, limite: int) -> list[EntradaConversa]:
        rows = self._session.scalars(
            select(InboxConversaORM)
            .where(InboxConversaORM.tenant_id == tenant_id)
            .order_by(InboxConversaORM.recebido_em.desc(), InboxConversaORM.provider_input_id)
            .limit(max(limite, 0))
        ).all()
        return [_to_entrada(row) for row in rows]


class SqlAlchemySessaoConversaRepository(SessaoConversaRepository):
    """Sessões isoladas por (tenant, instancia, classe, remetente)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def garantir(
        self,
        tenant_id: uuid.UUID,
        instancia_ref: str,
        classe: ClasseContexto,
        remetente_normalizado: str,
    ) -> SessaoConversa:
        existente = self.buscar(tenant_id, instancia_ref, classe, remetente_normalizado)
        if existente is not None:
            return existente
        row = SessaoConversaORM(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            instancia_ref=instancia_ref,
            classe=classe.value,
            remetente_normalizado=remetente_normalizado,
            referencia_pendente=None,
            expira_em=None,
        )
        try:
            with self._session.begin_nested():
                self._session.add(row)
                self._session.flush()
        except IntegrityError:
            # Corrida: outro executor criou primeiro; lê o vencedor.
            existente = self.buscar(tenant_id, instancia_ref, classe, remetente_normalizado)
            assert existente is not None
            return existente
        return _to_sessao(row)

    def buscar(
        self,
        tenant_id: uuid.UUID,
        instancia_ref: str,
        classe: ClasseContexto,
        remetente_normalizado: str,
    ) -> SessaoConversa | None:
        row = self._session.scalars(
            select(SessaoConversaORM)
            .where(SessaoConversaORM.tenant_id == tenant_id)
            .where(SessaoConversaORM.instancia_ref == instancia_ref)
            .where(SessaoConversaORM.classe == classe.value)
            .where(SessaoConversaORM.remetente_normalizado == remetente_normalizado)
        ).one_or_none()
        return _to_sessao(row) if row is not None else None

    def definir_referencia(self, sessao_id: uuid.UUID, ref: str, expira_em: datetime) -> None:
        self._session.execute(
            update(SessaoConversaORM)
            .where(SessaoConversaORM.id == sessao_id)
            .values(referencia_pendente=ref, expira_em=expira_em)
        )

    def limpar_referencia(self, sessao_id: uuid.UUID) -> None:
        self._session.execute(
            update(SessaoConversaORM)
            .where(SessaoConversaORM.id == sessao_id)
            .values(referencia_pendente=None, expira_em=None)
        )


class SqlAlchemyMensagemConversaRepository(MensagemConversaRepository):
    """Memória da sessão em ordem de índice único."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def adicionar(self, mensagem: MensagemConversa) -> None:
        self._session.add(
            MensagemConversaORM(
                id=mensagem.id,
                sessao_id=mensagem.sessao_id,
                inbox_id=mensagem.inbox_id,
                indice=mensagem.indice,
                papel=mensagem.papel.value,
                texto=mensagem.texto,
            )
        )
        self._session.flush()

    def listar_por_sessao(self, sessao_id: uuid.UUID) -> list[MensagemConversa]:
        rows = self._session.scalars(
            select(MensagemConversaORM)
            .where(MensagemConversaORM.sessao_id == sessao_id)
            .order_by(MensagemConversaORM.indice)
        ).all()
        return [_to_mensagem(row) for row in rows]


class SqlAlchemyToolCallExecRepository(ToolCallExecRepository):
    """Registro operacional: um (sessao_id, call_id) não se repete."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def registrar(self, execucao: ToolCallExec) -> None:
        self._session.add(
            ToolCallExecORM(
                id=execucao.id,
                sessao_id=execucao.sessao_id,
                inbox_id=execucao.inbox_id,
                call_id=execucao.call_id,
                ferramenta=execucao.ferramenta,
                schema_versao=execucao.schema_versao,
                parametros=dict(execucao.parametros),
                resultado=dict(execucao.resultado),
                latencia_ms=execucao.latencia_ms,
                completa=execucao.completa,
                correlation_id=execucao.correlation_id,
            )
        )
        self._session.flush()

    def listar_por_sessao(self, sessao_id: uuid.UUID) -> list[ToolCallExec]:
        rows = self._session.scalars(
            select(ToolCallExecORM)
            .where(ToolCallExecORM.sessao_id == sessao_id)
            .order_by(ToolCallExecORM.criado_em, ToolCallExecORM.call_id)
        ).all()
        return [_to_tool_call(row) for row in rows]


class SqlAlchemyReferenciaSessaoRepository(ReferenciaSessaoRepository):
    """Mapeamento opaco por sessão com invalidação sem apagar."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def salvar(self, referencia: ReferenciaSessao) -> None:
        self._session.add(
            ReferenciaSessaoORM(
                id=referencia.id,
                sessao_id=referencia.sessao_id,
                ref=referencia.ref,
                devedor_id=referencia.devedor_id,
                expira_em=referencia.expira_em,
            )
        )
        self._session.flush()

    def listar_por_sessao(self, sessao_id: uuid.UUID) -> list[ReferenciaSessao]:
        rows = self._session.scalars(
            select(ReferenciaSessaoORM).where(ReferenciaSessaoORM.sessao_id == sessao_id)
        ).all()
        return [_to_referencia(row) for row in rows]

    def invalidar_por_sessao(self, sessao_id: uuid.UUID, agora: datetime) -> None:
        self._session.execute(
            update(ReferenciaSessaoORM)
            .where(ReferenciaSessaoORM.sessao_id == sessao_id)
            .where(ReferenciaSessaoORM.revogada_em.is_(None))
            .values(revogada_em=agora)
        )
