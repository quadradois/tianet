"""Adiciona soft-delete em contato.

Revision ID: 0006_contato_removido_em
Revises: 0005_idempotency_key_escopo
Create Date: 2026-08-08 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_contato_removido_em"
down_revision = "0005_idempotency_key_escopo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contato", sa.Column("removido_em", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("contato", "removido_em")
