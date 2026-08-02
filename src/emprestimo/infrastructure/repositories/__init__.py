"""Implementações dos repositórios (Repository Pattern — ADR-001).

Os repositórios apenas adicionam/flusham na sessão; o commit e o controle
transacional pertencem ao Unit of Work da fase de Aplicação (IMP-014).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.ports import CarteiraRepository
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.ports import (
    ConfiguracaoRepository,
    TenantRepository,
    UsuarioRepository,
)
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.db.orm import CarteiraORM, ConfiguracaoORM, TenantORM, UsuarioORM


class SqlAlchemyTenantRepository(TenantRepository):
    """Implementação SQLAlchemy do TenantRepository (IMP-004)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, tenant: Tenant) -> None:
        self._session.merge(
            TenantORM(
                id=tenant.id,
                identificador_institucional=tenant.identificador_institucional,
                nome=tenant.nome,
                estado=tenant.estado.value,
                criado_em=tenant.criado_em,
            )
        )

    def find_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        row = self._session.get(TenantORM, tenant_id)
        return _to_tenant(row) if row is not None else None

    def find_all(self) -> list[Tenant]:
        rows = self._session.scalars(select(TenantORM).order_by(TenantORM.criado_em)).all()
        return [_to_tenant(row) for row in rows]


class SqlAlchemyUsuarioRepository(UsuarioRepository):
    """Implementação SQLAlchemy do UsuarioRepository (IMP-005)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, usuario: Usuario) -> None:
        self._session.merge(
            UsuarioORM(
                id=usuario.id,
                tenant_id=usuario.tenant_id,
                nome=usuario.nome,
                email=usuario.email,
                estado=usuario.estado.value,
                criado_em=usuario.criado_em,
            )
        )

    def find_by_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        row = self._session.get(UsuarioORM, usuario_id)
        return _to_usuario(row) if row is not None else None

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Usuario]:
        rows = self._session.scalars(
            select(UsuarioORM).where(UsuarioORM.tenant_id == tenant_id)
        ).all()
        return [_to_usuario(row) for row in rows]


class SqlAlchemyConfiguracaoRepository(ConfiguracaoRepository):
    """Implementação SQLAlchemy do ConfiguracaoRepository (IMP-006)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, configuracao: Configuracao) -> None:
        self._session.merge(
            ConfiguracaoORM(
                id=configuracao.id,
                tenant_id=configuracao.tenant_id,
                chave=configuracao.chave,
                valor=configuracao.valor,
                criado_em=configuracao.criado_em,
            )
        )

    def find_by_id(self, configuracao_id: uuid.UUID) -> Configuracao | None:
        row = self._session.get(ConfiguracaoORM, configuracao_id)
        return _to_configuracao(row) if row is not None else None

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Configuracao]:
        rows = self._session.scalars(
            select(ConfiguracaoORM).where(ConfiguracaoORM.tenant_id == tenant_id)
        ).all()
        return [_to_configuracao(row) for row in rows]


class SqlAlchemyCarteiraRepository(CarteiraRepository):
    """Implementação SQLAlchemy do CarteiraRepository (IMP-007)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, carteira: Carteira) -> None:
        self._session.merge(
            CarteiraORM(
                id=carteira.id,
                tenant_id=carteira.tenant_id,
                nome=carteira.nome,
                criado_em=carteira.criado_em,
            )
        )

    def find_by_id(self, carteira_id: uuid.UUID) -> Carteira | None:
        row = self._session.get(CarteiraORM, carteira_id)
        return _to_carteira(row) if row is not None else None

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Carteira]:
        rows = self._session.scalars(
            select(CarteiraORM).where(CarteiraORM.tenant_id == tenant_id)
        ).all()
        return [_to_carteira(row) for row in rows]


def _to_tenant(row: TenantORM) -> Tenant:
    return Tenant(
        id=row.id,
        identificador_institucional=row.identificador_institucional,
        nome=row.nome,
        estado=TenantState(row.estado),
        criado_em=row.criado_em,
    )


def _to_usuario(row: UsuarioORM) -> Usuario:
    return Usuario(
        id=row.id,
        tenant_id=row.tenant_id,
        nome=row.nome,
        email=row.email,
        estado=UsuarioState(row.estado),
        criado_em=row.criado_em,
    )


def _to_configuracao(row: ConfiguracaoORM) -> Configuracao:
    return Configuracao(
        id=row.id,
        tenant_id=row.tenant_id,
        chave=row.chave,
        valor=row.valor,
        criado_em=row.criado_em,
    )


def _to_carteira(row: CarteiraORM) -> Carteira:
    return Carteira(
        id=row.id,
        tenant_id=row.tenant_id,
        nome=row.nome,
        criado_em=row.criado_em,
    )
