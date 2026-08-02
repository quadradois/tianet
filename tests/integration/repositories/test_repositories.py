"""Testes de integração dos repositórios (IMP-004..IMP-007) — PostgreSQL."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.factories import (
    CarteiraFactory,
    ConfiguracaoFactory,
    TenantFactory,
    UsuarioFactory,
)

from emprestimo.domain.common.errors import TenantJaExisteError
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.usuario import Usuario
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyConfiguracaoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)


def test_tenant_repository_round_trip(session: Session) -> None:
    repo = SqlAlchemyTenantRepository(session)
    tenant = TenantFactory.build()

    repo.save(tenant)
    session.commit()

    carregado = repo.find_by_id(tenant.id)
    assert carregado is not None
    assert carregado.id == tenant.id
    assert carregado.identificador_institucional == tenant.identificador_institucional
    assert carregado.nome == tenant.nome
    assert carregado.estado == tenant.estado


def test_tenant_repository_find_all(session: Session) -> None:
    repo = SqlAlchemyTenantRepository(session)
    a = TenantFactory.build()
    b = TenantFactory.build()
    repo.save(a)
    repo.save(b)
    session.commit()

    todos = repo.find_all()

    assert {t.id for t in todos} == {a.id, b.id}


def test_tenant_repository_unicidade_do_identificador(session: Session) -> None:
    """IMP-008: violação de constraint em corrida → TenantJaExisteError (AD-002)."""
    repo = SqlAlchemyTenantRepository(session)
    primeiro = TenantFactory.build(identificador_institucional="IDENT-UNICO")
    repo.save(primeiro)
    session.commit()

    duplicado = TenantFactory.build(identificador_institucional="IDENT-UNICO")
    with pytest.raises(TenantJaExisteError):
        repo.save(duplicado)
    session.rollback()


def test_tenant_repository_busca_por_identificador(session: Session) -> None:
    """IMP-008: consulta de unicidade pelo identificador institucional (UC-002)."""
    repo = SqlAlchemyTenantRepository(session)
    tenant = TenantFactory.build(identificador_institucional="IDENT-CONSULTA")
    repo.save(tenant)
    session.commit()

    encontrado = repo.find_by_identificador_institucional("IDENT-CONSULTA")

    assert encontrado is not None
    assert encontrado.id == tenant.id
    assert repo.find_by_identificador_institucional("IDENT-AUSENTE") is None


def test_usuario_repository_round_trip(session: Session) -> None:
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(tenant_id=tenant.id)
    SqlAlchemyUsuarioRepository(session).save(usuario)
    session.commit()

    carregado = SqlAlchemyUsuarioRepository(session).find_by_id(usuario.id)

    assert carregado is not None
    assert carregado.tenant_id == tenant.id
    assert carregado.email == usuario.email
    assert carregado.perfil_acesso is None


def test_usuario_repository_persiste_perfil_de_acesso(session: Session) -> None:
    """IMP-011: perfil Administrador do primeiro Usuário persistido (RN-002)."""
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    admin = UsuarioFactory.build(tenant_id=tenant.id, perfil_acesso="administrador")
    SqlAlchemyUsuarioRepository(session).save(admin)
    session.commit()

    carregado = SqlAlchemyUsuarioRepository(session).find_by_id(admin.id)

    assert carregado is not None
    assert carregado.perfil_acesso == "administrador"


def test_usuario_repository_busca_por_tenant(session: Session) -> None:
    repo = SqlAlchemyUsuarioRepository(session)
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    u1 = UsuarioFactory.build(tenant_id=tenant.id)
    u2 = UsuarioFactory.build(tenant_id=tenant.id)
    repo.save(u1)
    repo.save(u2)
    session.commit()

    usuarios = repo.find_by_tenant_id(tenant.id)

    assert {u.id for u in usuarios} == {u1.id, u2.id}


def test_usuario_repository_email_duplicado_no_mesmo_tenant(session: Session) -> None:
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    repo = SqlAlchemyUsuarioRepository(session)
    repo.save(UsuarioFactory.build(tenant_id=tenant.id, email="duplicado@exemplo.com"))
    session.commit()

    repo.save(UsuarioFactory.build(tenant_id=tenant.id, email="duplicado@exemplo.com"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_configuracao_repository_round_trip(session: Session) -> None:
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    config = ConfiguracaoFactory.build(tenant_id=tenant.id)
    SqlAlchemyConfiguracaoRepository(session).save(config)
    session.commit()

    carregado = SqlAlchemyConfiguracaoRepository(session).find_by_id(config.id)

    assert carregado is not None
    assert carregado.tenant_id == tenant.id
    assert carregado.chave == config.chave
    assert carregado.valor == config.valor


def test_configuracao_repository_chave_duplicada_no_mesmo_tenant(session: Session) -> None:
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    repo = SqlAlchemyConfiguracaoRepository(session)
    repo.save(ConfiguracaoFactory.build(tenant_id=tenant.id, chave="moeda"))
    session.commit()

    repo.save(ConfiguracaoFactory.build(tenant_id=tenant.id, chave="moeda"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_carteira_repository_round_trip(session: Session) -> None:
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    session.commit()

    carregada = SqlAlchemyCarteiraRepository(session).find_by_id(carteira.id)

    assert carregada is not None
    assert carregada.tenant_id == tenant.id
    assert carregada.nome == carteira.nome


def test_carteira_repository_sem_tenant_viola_fk(session: Session) -> None:
    """BR-004 (DOMAIN-019): nenhuma Carteira sem Tenant — FK NOT NULL."""
    carteira = Carteira(tenant_id=uuid.uuid4(), nome="Carteira Órfã")

    SqlAlchemyCarteiraRepository(session).save(carteira)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_usuario_repository_sem_tenant_viola_fk(session: Session) -> None:
    """DOMAIN-017 INV-001: todo Usuário pertence exatamente a um Tenant."""
    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Órfão", email="orfao@exemplo.com")

    SqlAlchemyUsuarioRepository(session).save(usuario)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_configuracao_repository_sem_tenant_viola_fk(session: Session) -> None:
    config = Configuracao(tenant_id=uuid.uuid4(), chave="moeda", valor="BRL")

    SqlAlchemyConfiguracaoRepository(session).save(config)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
