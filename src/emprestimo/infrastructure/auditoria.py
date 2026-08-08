"""Implementação SQLAlchemy da auditoria append-only (IMP-016).

Cada evento persiste em sessão própria (``session_factory``) com commit
imediato: os registros de início/falha/rollback sobrevivem ao rollback da
transação de negócio (AD-001). A trilha é imutável — somente INSERT.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from emprestimo.application.ports import (
    AuditoriaConsulta,
    AuditoriaRegistro,
    EventoAuditoria,
)
from emprestimo.infrastructure.db.orm import AuditoriaLogORM


class SqlAlchemyAuditoriaRegistro(AuditoriaRegistro):
    """Grava eventos de auditoria na tabela `audit_log` (append-only)."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def registrar(
        self,
        entidade: str,
        entidade_id: uuid.UUID | None,
        acao: str,
        status: str,
        detalhes: str | None = None,
    ) -> None:
        with self._session_factory() as session:
            session.add(
                AuditoriaLogORM(
                    id=uuid.uuid4(),
                    entidade=entidade,
                    entidade_id=entidade_id,
                    acao=acao,
                    status=status,
                    detalhes=detalhes,
                )
            )
            session.commit()


class SqlAlchemyAuditoriaConsulta(AuditoriaConsulta):
    """Lê a trilha `audit_log` (US-027) — somente SELECT.

    Usa a sessão de leitura da requisição, não a sessão independente da
    escrita: a consulta não participa da trilha nem a modifica.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_por_entidade(self, entidade: str, entidade_id: uuid.UUID) -> list[EventoAuditoria]:
        """Eventos de uma entidade em ordem cronológica (mais antigo primeiro)."""
        rows = self._session.scalars(
            select(AuditoriaLogORM)
            .where(
                AuditoriaLogORM.entidade == entidade,
                AuditoriaLogORM.entidade_id == entidade_id,
            )
            .order_by(AuditoriaLogORM.criado_em, AuditoriaLogORM.id)
        ).all()
        return [
            EventoAuditoria(
                id=row.id,
                entidade=row.entidade,
                entidade_id=row.entidade_id,
                acao=row.acao,
                status=row.status,
                detalhes=row.detalhes,
                criado_em=row.criado_em,
            )
            for row in rows
        ]
