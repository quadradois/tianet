"""correlacao na trilha de tool-calls (IMP-356-F slice 4)

Revision ID: e5f6a7b8c9d0
Revises: d4e6f8a1b3c5
Create Date: 2026-09-16 00:00:00.000000

Adiciona `correlation_id` em `tool_call_exec` (ADR-016 ponta a ponta).
Aditiva e reversível: o downgrade remove só a coluna.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e6f8a1b3c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tool_call_exec",
        sa.Column("correlation_id", sa.String(64), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("tool_call_exec", "correlation_id")
