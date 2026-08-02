"""Mapeamento ORM (SQLAlchemy 2.x) das entidades do Platform/Credit Context.

Fase 1 (IMP-001..IMP-007): estrutura persistente e relacionamentos.
Constraints estruturais aplicadas:
- tenant.identificador_institucional UNIQUE (IMP-004);
- usuario.tenant_id FK NOT NULL + UNIQUE(tenant_id, email) — identidade única
  dentro do Tenant (DOMAIN-018 §2);
- configuracao.tenant_id FK NOT NULL + UNIQUE(tenant_id, chave) — um parâmetro
  por chave por Tenant;
- carteira.tenant_id FK NOT NULL (BR-004 — nenhuma Carteira sem Tenant).

Regras de negócio (unicidade, invariantes, idempotência, transações) pertencem
às fases seguintes (IMP-008+).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from emprestimo.infrastructure.db.base import Base


class TenantORM(Base):
    """Tabela `tenant` — Aggregate Tenant (DOMAIN-017)."""

    __tablename__ = "tenant"
    __table_args__ = (
        UniqueConstraint(
            "identificador_institucional", name="uq_tenant_identificador_institucional"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    identificador_institucional: Mapped[str] = mapped_column(String(120), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UsuarioORM(Base):
    """Tabela `usuario` — Entity Usuário (DOMAIN-018)."""

    __tablename__ = "usuario"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_usuario_tenant_email"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    perfil_acesso: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ConfiguracaoORM(Base):
    """Tabela `configuracao` — Entity Configuração (FOUNDATION-002 §Configuração)."""

    __tablename__ = "configuracao"
    __table_args__ = (UniqueConstraint("tenant_id", "chave", name="uq_configuracao_tenant_chave"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    chave: Mapped[str] = mapped_column(String(120), nullable=False)
    valor: Mapped[str] = mapped_column(String(500), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CarteiraORM(Base):
    """Tabela `carteira` — Aggregate Carteira (DOMAIN-001), com vínculo
    obrigatório com Tenant (BR-004).
    """

    __tablename__ = "carteira"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IdempotencyKeyORM(Base):
    """Tabela `idempotency_key` — Idempotency-Key (AD-002, IMP-015).

    Constraint único em ``chave``: impede provisionamentos duplicados mesmo
    em corrida. Registro compartilha a transação do caso de uso.
    """

    __tablename__ = "idempotency_key"
    __table_args__ = (UniqueConstraint("chave", name="uq_idempotency_key_chave"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    chave: Mapped[str] = mapped_column(String(255), nullable=False)
    escopo: Mapped[str] = mapped_column(String(50), nullable=False)
    solicitacao_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    resultado: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditoriaLogORM(Base):
    """Tabela `audit_log` — trilha append-only do provisionamento (IMP-016).

    Somente INSERT (imutável); registros de início/falha/rollback persistem
    em sessão independente e sobrevivem ao rollback da transação de negócio.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    entidade: Mapped[str] = mapped_column(String(50), nullable=False)
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    acao: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    detalhes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
