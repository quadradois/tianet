"""Testes de integração da camada de Aplicação (IMP-013..IMP-016).

PostgreSQL real: provisionamento completo em transação única (AD-001),
replay da Idempotency-Key (AD-002), rollback sem estados parciais e trilha
de auditoria que sobrevive ao rollback.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.provisioning import TenantProvisionado, TenantProvisioningService
from emprestimo.domain.common.errors import TenantJaExisteError
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.domain.platform.unicidade import UnicidadeTenantService
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import (
    AuditoriaLogORM,
    CarteiraORM,
    ConfiguracaoORM,
    IdempotencyKeyORM,
    TenantORM,
    UsuarioORM,
)
from emprestimo.infrastructure.repositories import (
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@dataclass
class _Ambiente:
    service: TenantProvisioningService
    session_factory: sessionmaker[Session]


@pytest.fixture
def ambiente(session_factory: sessionmaker[Session], session: Session) -> _Ambiente:
    unicidade = UnicidadeTenantService(SqlAlchemyTenantRepository(session))
    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    service = TenantProvisioningService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        unicidade=unicidade,
        auditoria=auditoria,
    )
    return _Ambiente(service, session_factory)


def _provisionar(service: TenantProvisioningService, chave: str = "chave-1") -> TenantProvisionado:
    return service.provisionar(
        identificador_institucional="IDENT-INTEG",
        nome="Financeira ABC",
        nome_administrador="Maria",
        email_administrador="maria@exemplo.com",
        idempotency_key=chave,
    )


def _contar(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_provisionamento_completo_persiste_tudo(ambiente: _Ambiente) -> None:
    resultado = _provisionar(ambiente.service)

    assert resultado.estado == TenantState.ATIVO
    with ambiente.session_factory() as session:
        tenant = session.get(TenantORM, resultado.tenant_id)
        assert tenant is not None
        assert tenant.estado == "ativo"
        assert _contar(session, CarteiraORM) == 1
        assert _contar(session, UsuarioORM) == 1
        assert _contar(session, ConfiguracaoORM) == 1
        chave = session.scalar(
            select(IdempotencyKeyORM).where(IdempotencyKeyORM.chave == "chave-1")
        )
        assert chave is not None
        assert chave.estado == "finished"
        assert chave.resultado is not None
        assert str(resultado.tenant_id) in chave.resultado


def test_trilha_de_auditoria_gravada_no_sucesso(ambiente: _Ambiente) -> None:
    _provisionar(ambiente.service)

    with ambiente.session_factory() as session:
        acoes = set(session.scalars(select(AuditoriaLogORM.acao)).all())
        assert "provisionar.inicio" in acoes
        assert "provisionar.dados_validados" in acoes
        assert "provisionar.carteira_criada" in acoes
        assert "provisionar.usuario_administrador_criado" in acoes
        assert "provisionar.configuracoes_aplicadas" in acoes
        assert "provisionar.confirmado" in acoes
        assert "provisionar.sucesso" in acoes


def test_replay_retorna_mesmo_resultado_sem_duplicar(ambiente: _Ambiente) -> None:
    primeiro = _provisionar(ambiente.service, chave="chave-replay")
    segundo = _provisionar(ambiente.service, chave="chave-replay")

    assert segundo.tenant_id == primeiro.tenant_id
    with ambiente.session_factory() as session:
        assert _contar(session, TenantORM) == 1
        assert _contar(session, IdempotencyKeyORM) == 1


def test_chave_com_payload_divergente_gera_conflito(ambiente: _Ambiente) -> None:
    _provisionar(ambiente.service, chave="chave-divergente")

    with pytest.raises(IdempotenciaConflitoError):
        ambiente.service.provisionar(
            identificador_institucional="OUTRO-IDENT",
            nome="Outra Financeira",
            nome_administrador="João",
            email_administrador="joao@exemplo.com",
            idempotency_key="chave-divergente",
        )
    with ambiente.session_factory() as session:
        assert _contar(session, TenantORM) == 1


def test_falha_de_unicidade_faz_rollback_total(ambiente: _Ambiente) -> None:
    _provisionar(ambiente.service, chave="chave-base")

    with pytest.raises(TenantJaExisteError):
        ambiente.service.provisionar(
            identificador_institucional="IDENT-INTEG",
            nome="Financeira ABC",
            nome_administrador="Outro",
            email_administrador="outro@exemplo.com",
            idempotency_key="chave-rollback",
        )

    with ambiente.session_factory() as session:
        assert _contar(session, TenantORM) == 1  # nenhum Tenant duplicado
        assert _contar(session, UsuarioORM) == 1  # nenhum usuário parcial
        assert _contar(session, CarteiraORM) == 1
        assert _contar(session, ConfiguracaoORM) == 1
        assert _contar(session, IdempotencyKeyORM) == 1  # chave falha não ficou


def test_auditoria_sobrevive_ao_rollback(ambiente: _Ambiente) -> None:
    _provisionar(ambiente.service, chave="chave-base")

    with pytest.raises(TenantJaExisteError):
        ambiente.service.provisionar(
            identificador_institucional="IDENT-INTEG",
            nome="Financeira ABC",
            nome_administrador="Outro",
            email_administrador="outro@exemplo.com",
            idempotency_key="chave-falha",
        )

    with ambiente.session_factory() as session:
        acoes = session.scalars(
            select(AuditoriaLogORM.acao).where(
                AuditoriaLogORM.acao.in_(["provisionar.falha", "provisionar.rollback"])
            )
        ).all()
        assert "provisionar.falha" in acoes
        assert "provisionar.rollback" in acoes


def test_usuario_administrador_com_perfil_persistido(ambiente: _Ambiente) -> None:
    resultado = _provisionar(ambiente.service)

    with ambiente.session_factory() as session:
        usuario = session.scalar(
            select(UsuarioORM).where(UsuarioORM.tenant_id == resultado.tenant_id)
        )
        assert usuario is not None
        assert usuario.perfil_acesso == "administrador"
        assert usuario.email == "maria@exemplo.com"
        assert str(usuario.id) is not None
        perfil = SqlAlchemyPerfilAcessoRepository(session).find_by_usuario_id(usuario.id)
        assert perfil is not None
        assert not perfil.permite("tenant.criar")
        assert perfil.permite("perfil.gerir")


def test_tenant_e_recuperavel_pelo_repositorio(ambiente: _Ambiente) -> None:
    resultado = _provisionar(ambiente.service)

    with ambiente.session_factory() as session:
        carregado = SqlAlchemyTenantRepository(session).find_by_id(resultado.tenant_id)

    assert carregado is not None
    assert carregado.estado == TenantState.ATIVO
    assert carregado.id == resultado.tenant_id
