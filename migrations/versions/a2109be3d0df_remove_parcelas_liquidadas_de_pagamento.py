"""remove parcelas_liquidadas de pagamento

Revision ID: a2109be3d0df
Revises: bb9262033324
Create Date: 2026-08-23 09:08:42.412614

Residuo do plano de parcelas removido pela DR-004. A coluna sobreviveu ao
IMP-327 e a migration 0017; nenhum emprestimo livre a preenche.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a2109be3d0df"
down_revision: str | None = "bb9262033324"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("pagamento", "parcelas_liquidadas")


def downgrade() -> None:
    op.add_column(
        "pagamento",
        sa.Column(
            "parcelas_liquidadas",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.alter_column("pagamento", "parcelas_liquidadas", server_default=None)
