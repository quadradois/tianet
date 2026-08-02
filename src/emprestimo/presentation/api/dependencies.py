"""Dependências da API — montagem do caso de uso (IMP-017/018).

A Presentation apenas compõe as peças da camada de Aplicação/Infrastructure
e expõe o TenantProvisioningService e o repositório de consulta. A sessão
de leitura da unicidade é criada por requisição e fechada ao final.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from emprestimo.application.provisioning import TenantProvisioningService
from emprestimo.domain.platform.ports import TenantRepository
from emprestimo.domain.platform.unicidade import UnicidadeTenantService
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.session import create_session, get_session_factory
from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def _get_session() -> Iterator[Session]:
    """Sessão de leitura por requisição (fechada ao final)."""
    session = create_session()
    try:
        yield session
    finally:
        session.close()


def get_tenant_provisioning_service(
    session: Session = Depends(_get_session),
) -> TenantProvisioningService:
    """Monta o serviço de provisionamento (IMP-013..016)."""
    session_factory = get_session_factory()
    return TenantProvisioningService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        unicidade=UnicidadeTenantService(SqlAlchemyTenantRepository(session)),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_tenant_repository(session: Session = Depends(_get_session)) -> TenantRepository:
    """Repositório de consulta de Tenant (IMP-018)."""
    return SqlAlchemyTenantRepository(session)
