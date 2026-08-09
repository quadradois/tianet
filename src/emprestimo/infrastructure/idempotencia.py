"""Implementação SQLAlchemy do registro de Idempotency-Key (AD-002, IMP-015).

Compartilha a sessão do Unit of Work: o INSERT da chave ocorre na mesma
transação do provisionamento; a corrida é traduzida para
``IdempotenciaConflitoError`` (sem exceção genérica de persistência).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import IdempotenciaRegistro
from emprestimo.infrastructure.db.orm import IdempotencyKeyORM

ESTADO_RUNNING = "running"
ESTADO_FINISHED = "finished"


class SqlAlchemyIdempotenciaRegistro(IdempotenciaRegistro):
    """Registro de Idempotency-Keys na tabela `idempotency_key`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def registrar(self, chave: str, escopo: str, solicitacao_hash: str) -> None:
        try:
            self._session.add(
                IdempotencyKeyORM(
                    id=uuid.uuid4(),
                    chave=chave,
                    escopo=escopo,
                    solicitacao_hash=solicitacao_hash,
                    estado=ESTADO_RUNNING,
                )
            )
            self._session.flush()
        except IntegrityError as exc:
            if "uq_idempotency_key_chave_escopo" in str(exc.orig):
                raise IdempotenciaConflitoError(
                    chave, f"chave já em uso no escopo {escopo!r}"
                ) from exc
            raise

    def _buscar(self, chave: str, escopo: str) -> IdempotencyKeyORM | None:
        """Localiza o registro por ``(chave, escopo)`` — a identidade real (AD-002).

        Filtrar apenas por ``chave`` fazia casos de uso distintos disputarem o
        mesmo registro: o escopo era gravado e nunca lido (TASK-100).
        """
        return self._session.scalar(
            select(IdempotencyKeyORM).where(
                IdempotencyKeyORM.chave == chave,
                IdempotencyKeyORM.escopo == escopo,
            )
        )

    def find_by_chave(self, chave: str, escopo: str) -> dict[str, Any] | None:
        row = self._buscar(chave, escopo)
        if row is None:
            return None
        return {
            "chave": row.chave,
            "escopo": row.escopo,
            "solicitacao_hash": row.solicitacao_hash,
            "estado": row.estado,
            "resultado": row.resultado,
        }

    def concluir(self, chave: str, escopo: str, resultado: str) -> None:
        row = self._buscar(chave, escopo)
        if row is None:
            raise IdempotenciaConflitoError(chave, "registro inexistente")
        row.estado = ESTADO_FINISHED
        row.resultado = resultado
        row.concluido_em = datetime.now(UTC)
