"""initial platform and credit context schema

Revision ID: 0001_platform_credit
Revises:
Create Date: 2026-08-01

Tabelas da Fase 1 (IMP-001..IMP-007): tenant, usuario, configuracao, carteira.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_platform_credit"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identificador_institucional", sa.String(length=120), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "identificador_institucional", name="uq_tenant_identificador_institucional"
        ),
    )
    op.create_table(
        "usuario",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_usuario_tenant_email"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_usuario_tenant"),
    )
    op.create_index("ix_usuario_tenant_id", "usuario", ["tenant_id"])
    op.create_table(
        "configuracao",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("chave", sa.String(length=120), nullable=False),
        sa.Column("valor", sa.String(length=500), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "chave", name="uq_configuracao_tenant_chave"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_configuracao_tenant"),
    )
    op.create_index("ix_configuracao_tenant_id", "configuracao", ["tenant_id"])
    op.create_table(
        "carteira",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_carteira_tenant"),
    )
    op.create_index("ix_carteira_tenant_id", "carteira", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_carteira_tenant_id", table_name="carteira")
    op.drop_table("carteira")
    op.drop_index("ix_configuracao_tenant_id", table_name="configuracao")
    op.drop_table("configuracao")
    op.drop_index("ix_usuario_tenant_id", table_name="usuario")
    op.drop_table("usuario")
    op.drop_table("tenant")
