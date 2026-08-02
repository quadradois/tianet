"""Implementação SQLAlchemy da auditoria append-only (IMP-016).

Cada evento persiste em sessão própria (``session_factory``) com commit
imediato: os registros de início/falha/rollback sobrevivem ao rollback da
transação de negócio (AD-001). A trilha é imutável — somente INSERT.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

from emprestimo.application.ports import AuditoriaRegistro
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
