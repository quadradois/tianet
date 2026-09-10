"""adiciona queda_detectada_em em conexao_whatsapp

Revision ID: c1d2e3f4a5b6
Revises: b58e3f21c4d7
Create Date: 2026-09-08 00:00:00.000000

IMP-370 Slice 1 (PLAN-034). Da ao estado ativo de queda um lugar para morar:
`NULL` significa sem alerta ativo; o instante marca a primeira observacao
pareada -> nao pareada.

Aditiva: nenhuma tabela existente e tocada alem da coluna nova, que nasce
nullable sem default — linhas antigas passam a ler `NULL`, ou seja, sem alerta.
O downgrade remove somente esta coluna.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b58e3f21c4d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conexao_whatsapp",
        sa.Column("queda_detectada_em", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conexao_whatsapp", "queda_detectada_em")
