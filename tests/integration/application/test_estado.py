"""Testes de integração das transições de estado de Tenant (IMP-034/035/038).

PostgreSQL real: persistência correta do estado, trilha de auditoria
append-only e sobrevivência dos eventos de falha ao rollback (ADR-002).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.application.errors import TransicaoEstadoInvalidaError
from emprestimo.application.estado import TenantEstadoService
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import AuditoriaLogORM
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@dataclass
class _Ambiente:
    service: TenantEstadoService
    session_factory: sessionmaker[Session]


@pytest.fixture
def ambiente(session_factory: sessionmaker[Session], session: Session) -> _Ambiente:
    # `session` é solicitado apenas para disparar o TRUNCATE por teste (conftest)
    del session
    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    service = TenantEstadoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=auditoria,
    )
    return _Ambiente(service, session_factory)


def _criar_tenant(
    session_factory: sessionmaker[Session],
    identificador: str = "IDENT-INTEG",
    nome: str = "Financeira ABC",
    estado: TenantState = TenantState.ATIVO,
) -> Tenant:
    """Persiste um Tenant diretamente via UoW."""
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        tenant = Tenant(
            identificador_institucional=identificador,
            nome=nome,
            estado=estado,
        )
        uow.tenant.save(tenant)
        uow.commit()
        return tenant


def _acoes_auditoria(session_factory: sessionmaker[Session]) -> set[str]:
    with session_factory() as session:
        return set(session.scalars(select(AuditoriaLogORM.acao)).all())


def test_inativar_persiste_e_audita_sucesso(ambiente: _Ambiente) -> None:
    tenant = _criar_tenant(ambiente.session_factory, identificador="IDENT-INAT-OK")

    resultado = ambiente.service.inativar(tenant.id)

    assert resultado is not None
    assert resultado.estado == TenantState.INATIVO
    assert resultado.identificador_institucional == "IDENT-INAT-OK"
    assert resultado.nome == "Financeira ABC"

    from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository

    with ambiente.session_factory() as session:
        carregado = SqlAlchemyTenantRepository(session).find_by_id(tenant.id)
    assert carregado is not None
    assert carregado.estado == TenantState.INATIVO
    assert carregado.nome == "Financeira ABC"

    acoes = _acoes_auditoria(ambiente.session_factory)
    assert "inativar.inicio" in acoes
    assert "inativar.sucesso" in acoes
    assert "inativar.falha" not in acoes


def test_reativar_persiste_e_audita_sucesso(ambiente: _Ambiente) -> None:
    tenant = _criar_tenant(
        ambiente.session_factory,
        identificador="IDENT-REAT-OK",
        estado=TenantState.INATIVO,
    )

    resultado = ambiente.service.reativar(tenant.id)

    assert resultado is not None
    assert resultado.estado == TenantState.ATIVO
    assert resultado.identificador_institucional == "IDENT-REAT-OK"

    from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository

    with ambiente.session_factory() as session:
        carregado = SqlAlchemyTenantRepository(session).find_by_id(tenant.id)
    assert carregado is not None
    assert carregado.estado == TenantState.ATIVO

    acoes = _acoes_auditoria(ambiente.session_factory)
    assert "reativar.inicio" in acoes
    assert "reativar.sucesso" in acoes
    assert "reativar.falha" not in acoes


def test_inativar_tenant_inexistente_sem_auditoria(ambiente: _Ambiente) -> None:
    resultado = ambiente.service.inativar(uuid.uuid4())

    assert resultado is None
    assert _acoes_auditoria(ambiente.session_factory) == set()


def test_reativar_tenant_inexistente_sem_auditoria(ambiente: _Ambiente) -> None:
    resultado = ambiente.service.reativar(uuid.uuid4())

    assert resultado is None
    assert _acoes_auditoria(ambiente.session_factory) == set()


def test_inativar_estado_divergente_conflito_sem_dados_parciais(
    ambiente: _Ambiente,
) -> None:
    """Inativar Tenant já Inativo: conflito, rollback e trilha de falha (ADR-002)."""
    tenant = _criar_tenant(
        ambiente.session_factory,
        identificador="IDENT-INAT-CONFLITO",
        estado=TenantState.INATIVO,
    )

    with pytest.raises(TransicaoEstadoInvalidaError):
        ambiente.service.inativar(tenant.id)

    from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository

    with ambiente.session_factory() as session:
        carregado = SqlAlchemyTenantRepository(session).find_by_id(tenant.id)
    assert carregado is not None
    assert carregado.estado == TenantState.INATIVO

    acoes = _acoes_auditoria(ambiente.session_factory)
    assert "inativar.inicio" in acoes
    assert "inativar.falha" in acoes
    assert "inativar.sucesso" not in acoes


def test_reativar_estado_divergente_conflito_sem_dados_parciais(
    ambiente: _Ambiente,
) -> None:
    """Reativar Tenant já Ativo: conflito, rollback e trilha de falha (ADR-002)."""
    tenant = _criar_tenant(ambiente.session_factory, identificador="IDENT-REAT-CONFLITO")

    with pytest.raises(TransicaoEstadoInvalidaError):
        ambiente.service.reativar(tenant.id)

    from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository

    with ambiente.session_factory() as session:
        carregado = SqlAlchemyTenantRepository(session).find_by_id(tenant.id)
    assert carregado is not None
    assert carregado.estado == TenantState.ATIVO

    acoes = _acoes_auditoria(ambiente.session_factory)
    assert "reativar.inicio" in acoes
    assert "reativar.falha" in acoes
    assert "reativar.sucesso" not in acoes


def test_ciclo_completo_inativar_reativar(ambiente: _Ambiente) -> None:
    """US-013 + US-014: ciclo completo restaura Ativo preservando tudo."""
    tenant = _criar_tenant(ambiente.session_factory, identificador="IDENT-CICLO")
    id_original = tenant.id
    criado_em = tenant.criado_em

    ambiente.service.inativar(tenant.id)
    resultado = ambiente.service.reativar(tenant.id)

    assert resultado is not None
    assert resultado.estado == TenantState.ATIVO
    assert resultado.id == id_original
    assert resultado.identificador_institucional == "IDENT-CICLO"
    assert resultado.nome == "Financeira ABC"
    assert resultado.criado_em == criado_em

    acoes = _acoes_auditoria(ambiente.session_factory)
    assert {"inativar.inicio", "inativar.sucesso", "reativar.inicio", "reativar.sucesso"} <= acoes
