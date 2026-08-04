"""Dependências da API — montagem do caso de uso (IMP-017/018/025/026/027).

A Presentation apenas compõe as peças da camada de Aplicação/Infrastructure
e expõe os serviços. A sessão de leitura é criada por requisição e fechada ao final.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from emprestimo.application.atualizacao import TenantAtualizacaoService
from emprestimo.application.consulta import (
    TenantConsultaPorIdService,
    TenantConsultaService,
    TenantListagemService,
)
from emprestimo.application.estado import TenantEstadoService
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
    """Repositório de consulta de Tenant (IMP-018/024/025/026)."""
    return SqlAlchemyTenantRepository(session)


def get_tenant_consulta_service(
    session: Session = Depends(_get_session),
) -> TenantConsultaService:
    """Serviço de consulta por identificador institucional (IMP-025)."""
    session_factory = get_session_factory()
    return TenantConsultaService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_tenant_consulta_por_id_service(
    session: Session = Depends(_get_session),
) -> TenantConsultaPorIdService:
    """Serviço de consulta por ID (IMP-026)."""
    session_factory = get_session_factory()
    return TenantConsultaPorIdService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_tenant_listagem_service(
    session: Session = Depends(_get_session),
) -> TenantListagemService:
    """Serviço de listagem paginada de Tenants (IMP-027)."""
    session_factory = get_session_factory()
    return TenantListagemService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_tenant_atualizacao_service(
    session: Session = Depends(_get_session),
) -> TenantAtualizacaoService:
    """Serviço de atualização cadastral de Tenants (IMP-030/031/032)."""
    session_factory = get_session_factory()
    return TenantAtualizacaoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_tenant_estado_service(
    session: Session = Depends(_get_session),
) -> TenantEstadoService:
    """Serviço de transições de estado de Tenants (IMP-034/035/036)."""
    session_factory = get_session_factory()
    return TenantEstadoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )
