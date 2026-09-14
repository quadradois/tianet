"""Repositórios SQLAlchemy da conversa do agente (IMP-356-A)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from emprestimo.agent.conversa import (
    ClasseContexto,
    EntradaConversa,
    InboxConversaRepository,
    SessaoConversa,
    SessaoConversaRepository,
)
from emprestimo.infrastructure.db.orm import InboxConversaORM, SessaoConversaORM


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
