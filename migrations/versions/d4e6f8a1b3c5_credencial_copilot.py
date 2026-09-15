"""refresh cifrado do copiloto (IMP-356-F slice 2)

Revision ID: d4e6f8a1b3c5
Revises: c8d3e5f7a2b4
Create Date: 2026-09-15 00:00:00.000000

Cria `credencial_copilot` (refresh cifrado por tenant/instância, com
`chave_id` para rotação). Aditiva e reversível: o downgrade remove a
tabela, e só ela.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e6f8a1b3c5"
down_revision: str | None = "c8d3e5f7a2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "credencial_copilot",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False),
        sa.Column("instancia_ref", sa.String(64), nullable=False),
        sa.Column("refresh_cifrado", sa.LargeBinary(), nullable=False),
        sa.Column("chave_id", sa.String(32), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "instancia_ref", name="uq_credencial_copilot_dono"),
    )


def downgrade() -> None:
    op.drop_table("credencial_copilot")
