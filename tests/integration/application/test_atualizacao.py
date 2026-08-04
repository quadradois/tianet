"""Testes de integração da atualização cadastral de Tenant (IMP-030/031).

PostgreSQL real: persistência correta, trilha de auditoria append-only e
sobrevivência dos eventos de falha ao rollback (ADR-002).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.application.atualizacao import TenantAtualizacaoService
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import AuditoriaLogORM
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@dataclass
class _Ambiente:
    service: TenantAtualizacaoService
    session_factory: sessionmaker[Session]


@pytest.fixture
def ambiente(session_factory: sessionmaker[Session], session: Session) -> _Ambiente:
    # `session` é solicitado apenas para disparar o TRUNCATE por teste (conftest)
    del session
    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    service = TenantAtualizacaoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=auditoria,
    )
    return _Ambiente(service, session_factory)


def _criar_tenant(
    session_factory: sessionmaker[Session],
    identificador: str = "IDENT-INTEG",
    nome: str = "Financeira ABC",
) -> Tenant:
    """Persiste um Tenant ativo diretamente via UoW."""
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        tenant = Tenant(
            identificador_institucional=identificador,
            nome=nome,
            estado=TenantState.ATIVO,
        )
        uow.tenant.save(tenant)
        uow.commit()
        return tenant


def _acoes_auditoria(session_factory: sessionmaker[Session]) -> set[str]:
    with session_factory() as session:
        return set(session.scalars(select(AuditoriaLogORM.acao)).all())


def test_atualizacao_persiste_e_audita_sucesso(ambiente: _Ambiente) -> None:
    tenant = _criar_tenant(ambiente.session_factory)

    resultado = ambiente.service.atualizar_nome(tenant.id, "Financeira Atualizada")

    assert resultado is not None
    assert resultado.nome == "Financeira Atualizada"
    assert resultado.estado == TenantState.ATIVO
    assert resultado.identificador_institucional == "IDENT-INTEG"

    # Confirma a persistência real via repositório
    from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository

    with ambiente.session_factory() as session:
        carregado = SqlAlchemyTenantRepository(session).find_by_id(tenant.id)
    assert carregado is not None
    assert carregado.nome == "Financeira Atualizada"
    assert carregado.estado == TenantState.ATIVO

    acoes = _acoes_auditoria(ambiente.session_factory)
    assert "atualizar.inicio" in acoes
    assert "atualizar.sucesso" in acoes
    assert "atualizar.falha" not in acoes


def test_atualizacao_tenant_inexistente_sem_auditoria(ambiente: _Ambiente) -> None:
    import uuid

    resultado = ambiente.service.atualizar_nome(uuid.uuid4(), "Qualquer Nome")

    assert resultado is None
    assert _acoes_auditoria(ambiente.session_factory) == set()


def test_atualizacao_parcial_preserva_identificador_e_estado(ambiente: _Ambiente) -> None:
    """Atualização parcial altera apenas o nome; identidade e estado permanecem."""
    tenant = _criar_tenant(ambiente.session_factory, identificador="IDENT-PARCIAL")
    criado_em = tenant.criado_em
    id_original = tenant.id

    resultado = ambiente.service.atualizar_nome(tenant.id, "Novo Nome")

    assert resultado.id == id_original
    assert resultado.identificador_institucional == "IDENT-PARCIAL"
    assert resultado.estado == TenantState.ATIVO
    assert resultado.criado_em == criado_em


def test_auditoria_de_falha_sobrevive_ao_rollback(ambiente: _Ambiente) -> None:
    """ADR-002: eventos de falha persistem mesmo após rollback da transação."""
    tenant = _criar_tenant(ambiente.session_factory)

    with pytest.raises(ViolacaoInvarianteError):
        ambiente.service.atualizar_nome(tenant.id, "")

    # Nome não foi alterado no banco (rollback)
    from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository

    with ambiente.session_factory() as session:
        carregado = SqlAlchemyTenantRepository(session).find_by_id(tenant.id)
    assert carregado is not None
    assert carregado.nome == "Financeira ABC"

    # A trilha de falha sobreviveu ao rollback (ADR-002)
    acoes = _acoes_auditoria(ambiente.session_factory)
    assert "atualizar.inicio" in acoes
    assert "atualizar.falha" in acoes
    assert "atualizar.sucesso" not in acoes
