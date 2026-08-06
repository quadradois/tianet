"""add devedor and contato tables

Revision ID: 0004_devedor_contato
Revises: 0003_idempotency_audit
Create Date: 2026-08-06

Fase 4 (IMP-042): tabelas do contexto Cadastro — Devedor (Aggregate Root) e
Contato (entidade filha), com constraints UNIQUE e FKs aditivas.
Tabelas: devedor (Aggregate Root do Cadastro) e contato (entidade filha).
Regras: UNIQUE (carteira_id, documento) para unicidade do documento na Carteira;
UNIQUE (devedor_id, tipo, valor) para unicidade do contato por tipo/valor.
Downgrade reversível (drop aditivo).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_devedor_contato"
down_revision: str | None = "0003_idempotency_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devedor",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), nullable=False),
        sa.Column("documento", sa.String(length=11), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("carteira_id", "documento", name="uq_devedor_carteira_documento"),
        sa.ForeignKeyConstraint(["carteira_id"], ["carteira.id"], name="fk_devedor_carteira"),
    )
    op.create_index("ix_devedor_carteira_id", "devedor", ["carteira_id"])

    op.create_table(
        "contato",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("valor", sa.String(length=254), nullable=False),
        sa.Column("preferencial", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("devedor_id", "tipo", "valor", name="uq_contato_devedor_tipo_valor"),
        sa.ForeignKeyConstraint(["devedor_id"], ["devedor.id"], name="fk_contato_devedor"),
    )
    op.create_index("ix_contato_devedor_id", "contato", ["devedor_id"])


def downgrade() -> None:
    op.drop_index("ix_contato_devedor_id", table_name="contato")
    op.drop_table("contato")
    op.drop_index("ix_devedor_carteira_id", table_name="devedor")
    op.drop_table("devedor")