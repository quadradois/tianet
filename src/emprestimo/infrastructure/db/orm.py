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

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
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


class CredencialORM(Base):
    """Tabela `credencial` - hash de acesso do Usuario (IMP-085)."""

    __tablename__ = "credencial"
    __table_args__ = (UniqueConstraint("usuario_id", name="uq_credencial_usuario"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    hash_credencial: Mapped[str] = mapped_column(String(255), nullable=False)
    algoritmo: Mapped[str] = mapped_column(String(50), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SessaoORM(Base):
    """Tabela `sessao` - refresh token persistido e revogavel (IMP-085)."""

    __tablename__ = "sessao"
    __table_args__ = (UniqueConstraint("refresh_token_hash", name="uq_sessao_refresh_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PermissaoORM(Base):
    """Tabela `permissao` - catalogo de operacoes autorizaveis (IMP-085)."""

    __tablename__ = "permissao"

    codigo: Mapped[str] = mapped_column(String(120), primary_key=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)


class PerfilAcessoORM(Base):
    """Tabela `perfil_acesso` - Perfil RBAC por Tenant (IMP-085)."""

    __tablename__ = "perfil_acesso"
    __table_args__ = (UniqueConstraint("tenant_id", "nome", name="uq_perfil_tenant_nome"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PerfilPermissaoORM(Base):
    """Tabela `perfil_permissao` - associacao N:N entre Perfil e Permissao."""

    __tablename__ = "perfil_permissao"

    perfil_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("perfil_acesso.id"), primary_key=True
    )
    permissao_codigo: Mapped[str] = mapped_column(
        String(120), ForeignKey("permissao.codigo"), primary_key=True
    )


class UsuarioPerfilORM(Base):
    """Tabela `usuario_perfil` - Perfil operacional atribuido ao Usuario."""

    __tablename__ = "usuario_perfil"

    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuario.id"), primary_key=True)
    perfil_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("perfil_acesso.id"), nullable=False, index=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TokenAtivacaoORM(Base):
    """Token de ativacao armazenado somente por hash."""

    __tablename__ = "token_ativacao"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    utilizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    __table_args__ = (UniqueConstraint("chave", "escopo", name="uq_idempotency_key_chave_escopo"),)

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


class DevedorORM(Base):
    """Tabela `devedor` — Aggregate Root Devedor (DOMAIN-020, IMP-042)."""

    __tablename__ = "devedor"
    __table_args__ = (
        UniqueConstraint("carteira_id", "documento", name="uq_devedor_carteira_documento"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    carteira_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=False, index=True
    )
    documento: Mapped[str] = mapped_column(String(11), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ContatoORM(Base):
    """Tabela `contato` — Entity Contato (DOMAIN-021, IMP-042)."""

    __tablename__ = "contato"
    __table_args__ = (
        UniqueConstraint("devedor_id", "tipo", "valor", name="uq_contato_devedor_tipo_valor"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    devedor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devedor.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    valor: Mapped[str] = mapped_column(String(254), nullable=False)
    preferencial: Mapped[bool] = mapped_column(nullable=False, default=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SimulacaoComercialORM(Base):
    """Tabela `simulacao_comercial` - registro nao vinculante Comercial."""

    __tablename__ = "simulacao_comercial"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=False, index=True
    )
    devedor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devedor.id"), nullable=False, index=True
    )
    criada_por_usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    parametros: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PropostaComercialORM(Base):
    """Tabela `proposta_comercial` - aggregate Comercial sem contrato real."""

    __tablename__ = "proposta_comercial"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=False, index=True
    )
    devedor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devedor.id"), nullable=False, index=True
    )
    criada_por_usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    simulacao_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("simulacao_comercial.id"), nullable=True, index=True
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    parametros: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aprovada_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=True, index=True
    )
    aprovada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DecisaoComercialORM(Base):
    """Tabela `decisao_comercial` - trilha append-only de decisoes."""

    __tablename__ = "decisao_comercial"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    proposta_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("proposta_comercial.id"), nullable=False, index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    estado_anterior: Mapped[str] = mapped_column(String(30), nullable=False)
    estado_posterior: Mapped[str] = mapped_column(String(30), nullable=False)
    ordem: Mapped[int] = mapped_column(nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
