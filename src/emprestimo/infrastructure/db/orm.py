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
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
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


class ContratoCreditoORM(Base):
    """Tabela `contrato_credito` - aggregate Contratos sem Motor Financeiro."""

    __tablename__ = "contrato_credito"
    __table_args__ = (
        UniqueConstraint("proposta_comercial_id", name="uq_contrato_credito_proposta"),
    )

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
    proposta_comercial_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("proposta_comercial.id"), nullable=False, index=True
    )
    criado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    parametros: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    formalizado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=True
    )
    formalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assinado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=True
    )
    assinado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    liberado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=True
    )
    liberado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_encerramento: Mapped[str | None] = mapped_column(String(500), nullable=True)


class EventoContratoORM(Base):
    """Tabela `evento_contrato` - trilha append-only de Contratos."""

    __tablename__ = "evento_contrato"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("contrato_credito.id"), nullable=False, index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    estado_anterior: Mapped[str] = mapped_column(String(30), nullable=False)
    estado_posterior: Mapped[str] = mapped_column(String(30), nullable=False)
    ordem: Mapped[int] = mapped_column(nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EmprestimoORM(Base):
    """Tabela `emprestimo` - aggregate financeiro do EPIC-005."""

    __tablename__ = "emprestimo"
    __table_args__ = (
        UniqueConstraint("contrato_id", name="uq_emprestimo_contrato"),
        CheckConstraint("principal_original > 0", name="ck_emprestimo_principal_positivo"),
    )

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
    contrato_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("contrato_credito.id"), nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    principal_original: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moeda: Mapped[str] = mapped_column(String(3), nullable=False)
    parametros_financeiros: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_processamento_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultimo_pagamento_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    proximo_vencimento_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    quitado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ParcelaORM(Base):
    """Tabela `parcela` - obrigacao prevista do Emprestimo."""

    __tablename__ = "parcela"
    __table_args__ = (
        UniqueConstraint("emprestimo_id", "numero", name="uq_parcela_emprestimo_numero"),
        CheckConstraint("numero > 0", name="ck_parcela_numero_positivo"),
        CheckConstraint("valor_previsto > 0", name="ck_parcela_valor_previsto_positivo"),
        CheckConstraint("principal >= 0", name="ck_parcela_principal_nao_negativo"),
        CheckConstraint("juros >= 0", name="ck_parcela_juros_nao_negativo"),
        CheckConstraint("encargos >= 0", name="ck_parcela_encargos_nao_negativo"),
        CheckConstraint(
            "valor_liquidado >= 0",
            name="ck_parcela_valor_liquidado_nao_negativo",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    emprestimo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("emprestimo.id"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    vencimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    valor_previsto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    principal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    juros: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    encargos: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    valor_liquidado: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    periodo: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PagamentoORM(Base):
    """Tabela `pagamento` - fato financeiro processado pelo Motor."""

    __tablename__ = "pagamento"
    __table_args__ = (
        UniqueConstraint(
            "emprestimo_id",
            "chave_idempotencia",
            name="uq_pagamento_emprestimo_chave_idempotencia",
        ),
        CheckConstraint("valor_recebido > 0", name="ck_pagamento_valor_recebido_positivo"),
        CheckConstraint("valor_juros >= 0", name="ck_pagamento_juros_nao_negativo"),
        CheckConstraint(
            "valor_amortizacao >= 0",
            name="ck_pagamento_amortizacao_nao_negativa",
        ),
        CheckConstraint("valor_encargos >= 0", name="ck_pagamento_encargos_nao_negativo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    emprestimo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("emprestimo.id"), nullable=False, index=True
    )
    valor_recebido: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    recebido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    valor_juros: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    valor_amortizacao: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    valor_encargos: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    chave_idempotencia: Mapped[str] = mapped_column(String(255), nullable=False)
    parcelas_liquidadas: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    distribuicao: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MemoriaCalculoORM(Base):
    """Tabela `memoria_calculo` - memoria auditavel dos calculos."""

    __tablename__ = "memoria_calculo"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    emprestimo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("emprestimo.id"), nullable=False, index=True
    )
    pagamento_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("pagamento.id"), nullable=True, index=True
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    data_referencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    entradas: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    regra: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    periodos: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    passos: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    arredondamentos: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    resultados: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EventoFinanceiroORM(Base):
    """Tabela `evento_financeiro` - trilha append-only do Motor."""

    __tablename__ = "evento_financeiro"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    emprestimo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("emprestimo.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=False, index=True
    )
    devedor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devedor.id"), nullable=False, index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    memoria_calculo_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("memoria_calculo.id"), nullable=True, index=True
    )
    pagamento_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("pagamento.id"), nullable=True, index=True
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    estado_anterior: Mapped[str | None] = mapped_column(String(30), nullable=True)
    estado_posterior: Mapped[str | None] = mapped_column(String(30), nullable=True)
    valor: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    detalhes: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CobrancaCasoORM(Base):
    """Tabela `cobranca_caso` - aggregate de acompanhamento de cobranÃ§a."""

    __tablename__ = "cobranca_caso"

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
    emprestimo_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("emprestimo.id"), nullable=True, index=True
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    total_pendente: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    origem: Mapped[str] = mapped_column(String(50), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "carteira_id", "devedor_id", name="uq_cobranca_caso_devedor"),
        CheckConstraint("total_pendente >= 0", name="ck_cobranca_caso_total_pendente_n"),
    )


class AcaoCobrancaORM(Base):
    """Tabela `cobranca_acao` - log de aÃ§Ãµes manuais em cobranÃ§a."""

    __tablename__ = "cobranca_acao"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    cobranca_caso_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cobranca_caso.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=False, index=True
    )
    devedor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devedor.id"), nullable=False, index=True
    )
    emprestimo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("emprestimo.id"), nullable=False, index=True
    )
    criado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    resultado: Mapped[str] = mapped_column(Text, nullable=False)
    parcela_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("parcela.id"), nullable=True, index=True
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    registrada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (CheckConstraint("resultado <> ''", name="ck_cobranca_acao_resultado"),)


class PromessaPagamentoORM(Base):
    """Tabela `promessa_pagamento` - compromisso de pagamento operacional."""

    __tablename__ = "promessa_pagamento"

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
    emprestimo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("emprestimo.id"), nullable=False, index=True
    )
    valor_declarado: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    data_promessa: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    parcela_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("parcela.id"), nullable=True, index=True
    )
    criado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("valor_declarado > 0", name="ck_promessa_valor_declarado_positivo"),
    )


class ApropriacaoPagamentoORM(Base):
    """Tabela `promessa_apropriacao` - alocaÃ§Ã£o de pagamento em promessa."""

    __tablename__ = "promessa_apropriacao"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    promessa_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("promessa_pagamento.id"), nullable=False, index=True
    )
    pagamento_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("pagamento.id"), nullable=True, index=True
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    realizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parcela_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("parcela.id"), nullable=False, index=True
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    idempotencia: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint("promessa_id", "pagamento_id", name="uq_promessa_pagamento_pagamento"),
        CheckConstraint("valor > 0", name="ck_promessa_apropriacao_valor_positivo"),
    )


class AgendaItemORM(Base):
    """Tabela `agenda_item` - compromissos operacionais da carteira."""

    __tablename__ = "agenda_item"

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
    emprestimo_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("emprestimo.id"), nullable=True, index=True
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    previsto_para: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usuario_solicitante_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )

    __table_args__ = (CheckConstraint("titulo <> ''", name="ck_agenda_item_titulo"),)


class LembreteORM(Base):
    """Tabela `lembrete` - lembrete para compromissos."""

    __tablename__ = "lembrete"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=False, index=True
    )
    agenda_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agenda_item.id"), nullable=False, index=True
    )
    horario: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    enviado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False, index=True
    )
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RegistroComunicacaoORM(Base):
    """Tabela `comunicacao_registro` - comunicação manual registrada."""

    __tablename__ = "comunicacao_registro"

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
    emprestimo_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("emprestimo.id"), nullable=True, index=True
    )
    responsavel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False
    )
    canal: Mapped[str] = mapped_column(String(50), nullable=False)
    resumo: Mapped[str] = mapped_column(String(500), nullable=False)
    resultado: Mapped[str] = mapped_column(Text, nullable=False)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    parcela_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("parcela.id"), nullable=True, index=True
    )
    cobranca_acao_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("cobranca_acao.id"), nullable=True, index=True
    )
    agenda_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agenda_item.id"), nullable=True, index=True
    )

    __table_args__ = (CheckConstraint("resumo <> ''", name="ck_comunicacao_resumo"),)


class RelatorioOperacionalCacheORM(Base):
    """Tabela `relatorio_operacional_cache` - cache de consultas."""

    __tablename__ = "relatorio_operacional_cache"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=False, index=True
    )
    janela_referencia: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    familia_relatorio: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    gerado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("familia_relatorio <> ''", name="ck_relatorio_familia_relatorio"),
    )


class ModalidadeFinanceiraORM(Base):
    """Tabela `modalidade_financeira` - modalidade governada do EPIC-009."""

    __tablename__ = "modalidade_financeira"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "carteira_id",
            "codigo",
            name="uq_modalidade_financeira_tenant_carteira_codigo",
        ),
        CheckConstraint("codigo <> ''", name="ck_modalidade_financeira_codigo"),
        CheckConstraint("nome <> ''", name="ck_modalidade_financeira_nome"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=True, index=True
    )
    codigo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    ativa: Mapped[bool] = mapped_column(nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CalendarioFinanceiroORM(Base):
    """Tabela `calendario_financeiro` - calendario operacional governado."""

    __tablename__ = "calendario_financeiro"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "carteira_id",
            "codigo",
            name="uq_calendario_financeiro_tenant_carteira_codigo",
        ),
        CheckConstraint("codigo <> ''", name="ck_calendario_financeiro_codigo"),
        CheckConstraint("nome <> ''", name="ck_calendario_financeiro_nome"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=True, index=True
    )
    codigo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    feriados: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ConfiguracaoFinanceiraORM(Base):
    """Tabela `configuracao_financeira` - aggregate versionado do EPIC-009."""

    __tablename__ = "configuracao_financeira"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "carteira_id",
            "modalidade_codigo",
            "versao",
            name="uq_configuracao_financeira_escopo_versao",
        ),
        CheckConstraint("versao > 0", name="ck_configuracao_financeira_versao"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=True, index=True
    )
    modalidade_codigo: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    calendario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("calendario_financeiro.id"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    versao: Mapped[int] = mapped_column(Integer, nullable=False)
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    taxas: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    parametros: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    politica_arredondamento: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    criada_por_usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False
    )
    criada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aprovada_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=True
    )
    aprovada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    programada_para: Mapped[date | None] = mapped_column(Date, nullable=True)
    ativada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    substituida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inativada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EventoConfiguracaoFinanceiraORM(Base):
    """Tabela `configuracao_financeira_evento` - trilha append-only."""

    __tablename__ = "configuracao_financeira_evento"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    configuracao_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("configuracao_financeira.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=True, index=True
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("usuario.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(80), nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    versao_anterior: Mapped[int | None] = mapped_column(Integer, nullable=True)
    versao_nova: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SnapshotConfiguracaoContratualORM(Base):
    """Tabela `snapshot_configuracao_contratual` - snapshot imutavel."""

    __tablename__ = "snapshot_configuracao_contratual"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    configuracao_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("configuracao_financeira.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenant.id"), nullable=False, index=True
    )
    carteira_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("carteira.id"), nullable=True, index=True
    )
    modalidade: Mapped[str] = mapped_column(String(80), nullable=False)
    versao: Mapped[int] = mapped_column(Integer, nullable=False)
    parametros: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    hash_parametros: Mapped[str] = mapped_column(String(64), nullable=False)
    capturado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capturado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("usuario.id"), nullable=False
    )
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True)
