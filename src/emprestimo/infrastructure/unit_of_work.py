"""Unit of Work SQLAlchemy — transação única (AD-001, IMP-014).

O UnitOfWork abre uma sessão própria, expõe os repositórios de domínio e o
registro de idempotência compartilhando a mesma transação, e só executa
commit no fim. Nenhum repositório executa commit; qualquer exceção dispara
rollback automático no ``__exit__``.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from emprestimo.application.ports import UnitOfWork
from emprestimo.infrastructure.idempotencia import SqlAlchemyIdempotenciaRegistro
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyConfiguracaoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Implementação SQLAlchemy do Unit of Work (AD-001)."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session = session_factory()
        self.tenant = SqlAlchemyTenantRepository(self._session)
        self.usuario = SqlAlchemyUsuarioRepository(self._session)
        self.configuracao = SqlAlchemyConfiguracaoRepository(self._session)
        self.carteira = SqlAlchemyCarteiraRepository(self._session)
        self.idempotencia = SqlAlchemyIdempotenciaRegistro(self._session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()
