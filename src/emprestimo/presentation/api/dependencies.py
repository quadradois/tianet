"""Dependências da API — montagem do caso de uso (IMP-017/018/025/026/027).

A Presentation apenas compõe as peças da camada de Aplicação/Infrastructure
e expõe os serviços. A sessão de leitura é criada por requisição e fechada ao final.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from emprestimo.application.atualizacao import TenantAtualizacaoService
from emprestimo.application.atualizacao_devedor import DevedorAtualizacaoService
from emprestimo.application.cadastro_devedor import DevedorCadastroService
from emprestimo.application.consulta import (
    TenantConsultaPorIdService,
    TenantConsultaService,
    TenantListagemService,
)
from emprestimo.application.consulta_devedor import (
    DevedorConsultaPorDocumentoService,
    DevedorConsultaService,
    DevedorListagemService,
)
from emprestimo.application.estado import TenantEstadoService
from emprestimo.application.estado_devedor import DevedorEstadoService
from emprestimo.application.historico_devedor import DevedorHistoricoService
from emprestimo.application.provisioning import TenantProvisioningService
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.unicidade_devedor import UnicidadeDevedorService
from emprestimo.domain.platform.ports import TenantRepository
from emprestimo.domain.platform.unicidade import UnicidadeTenantService
from emprestimo.infrastructure.auditoria import (
    SqlAlchemyAuditoriaConsulta,
    SqlAlchemyAuditoriaRegistro,
)
from emprestimo.infrastructure.db.session import create_session, get_session_factory
from emprestimo.infrastructure.repositories import (
    SqlAlchemyDevedorRepository,
    SqlAlchemyTenantRepository,
)
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


# --- Credit Context — Devedor (IMP-056) ---


def get_devedor_cadastro_service(
    session: Session = Depends(_get_session),
) -> DevedorCadastroService:
    """Serviço de cadastro de Devedor (IMP-051)."""
    session_factory = get_session_factory()
    return DevedorCadastroService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        unicidade=UnicidadeDevedorService(SqlAlchemyDevedorRepository(session)),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_devedor_consulta_service(
    session: Session = Depends(_get_session),
) -> DevedorConsultaService:
    """Serviço de consulta de Devedor por ID (IMP-052)."""
    session_factory = get_session_factory()
    return DevedorConsultaService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_devedor_consulta_por_documento_service(
    session: Session = Depends(_get_session),
) -> DevedorConsultaPorDocumentoService:
    """Serviço de consulta de Devedor por documento na Carteira (IMP-052)."""
    session_factory = get_session_factory()
    return DevedorConsultaPorDocumentoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_devedor_listagem_service(
    session: Session = Depends(_get_session),
) -> DevedorListagemService:
    """Serviço de listagem paginada de Devedores (IMP-053)."""
    session_factory = get_session_factory()
    return DevedorListagemService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_devedor_atualizacao_service(
    session: Session = Depends(_get_session),
) -> DevedorAtualizacaoService:
    """Serviço de atualização cadastral de Devedor (IMP-054)."""
    session_factory = get_session_factory()
    return DevedorAtualizacaoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        unicidade=UnicidadeDevedorService(SqlAlchemyDevedorRepository(session)),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_devedor_estado_service(
    session: Session = Depends(_get_session),
) -> DevedorEstadoService:
    """Serviço de transições de estado de Devedor (IMP-055)."""
    session_factory = get_session_factory()
    return DevedorEstadoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_devedor_da_carteira(
    carteira_id: uuid.UUID,
    devedor_id: uuid.UUID,
    service: DevedorConsultaService = Depends(get_devedor_consulta_service),
) -> Devedor:
    """Resolve o Devedor validando a pertinência à Carteira da rota (ADR-018).

    Ponto único de validação de pertinência: toda rota aninhada por ID a declara
    como dependência, em vez de repetir a checagem no handler.

    Devedor inexistente e Devedor de outra Carteira respondem o mesmo
    ``404 devedor_nao_encontrado``. A indistinguibilidade é intencional (ADR-018):
    um código distinto confirmaria a existência do identificador em outra
    Carteira, vazando informação através da fronteira de isolamento.
    """
    devedor = service.consultar_por_id(devedor_id)
    if devedor is None or devedor.carteira_id != carteira_id:
        raise HTTPException(
            status_code=404,
            detail={
                "codigo": "devedor_nao_encontrado",
                "mensagem": "Devedor inexistente",
            },
        )
    return devedor


def get_devedor_historico_service(
    session: Session = Depends(_get_session),
) -> DevedorHistoricoService:
    """Serviço de consulta do histórico cadastral do Devedor (US-027)."""
    session_factory = get_session_factory()
    return DevedorHistoricoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria_consulta=SqlAlchemyAuditoriaConsulta(session),
    )
