"""add idempotency_key and audit_log

Revision ID: 0003_idempotency_audit
Revises: 0002_usuario_perfil_acesso
Create Date: 2026-08-02

Fase 3 (TASK-043): tabelas da camada de Aplicação — Idempotency-Key (AD-002,
IMP-015) com constraint único em `chave`, e trilha de auditoria append-only
(IMP-016).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_idempotency_audit"
down_revision: str | None = "0002_usuario_perfil_acesso"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "idempotency_key",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chave", sa.String(length=255), nullable=False),
        sa.Column("escopo", sa.String(length=50), nullable=False),
        sa.Column("solicitacao_hash", sa.String(length=64), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("resultado", sa.String(length=2000), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chave", name="uq_idempotency_key_chave"),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entidade", sa.String(length=50), nullable=False),
        sa.Column("entidade_id", sa.Uuid(), nullable=True),
        sa.Column("acao", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("detalhes", sa.String(length=2000), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("idempotency_key")
