"""Permite solicitacao transacional sem lembrete nem template.

Revision ID: 0019_notificacao_transacional
Revises: 0018_comprovante_whatsapp
Create Date: 2026-08-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_notificacao_transacional"
down_revision = "0018_comprovante_whatsapp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "solicitacao_notificacao",
        "lembrete_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.alter_column(
        "solicitacao_notificacao",
        "template_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "solicitacao_notificacao",
        "template_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.alter_column(
        "solicitacao_notificacao",
        "lembrete_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
