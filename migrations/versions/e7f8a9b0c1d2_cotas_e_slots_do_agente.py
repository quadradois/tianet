"""cotas por janela e slots de concorrencia do agente (IMP-356-C)

Revision ID: e7f8a9b0c1d2
Revises: c9a4f2e71b83d
Create Date: 2026-09-13 00:00:00.000000

Cria `cota_evento` (uma linha por admissao, sem agregados mutaveis) e
`slot_execucao` com as 2 vagas semeadas (1 reservada a Operadora).
Aditiva e reversivel: o downgrade remove tabelas e vagas, e so isso.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7f8a9b0c1d2"
down_revision: str | None = "c9a4f2e71b83d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cota_evento",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False),
        sa.Column("instancia_ref", sa.String(length=64), nullable=False),
        sa.Column("escopo", sa.String(length=40), nullable=False),
        sa.Column("chave", sa.String(length=128), nullable=False),
        sa.Column("instante", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cota_evento_janela", "cota_evento", ["escopo", "chave", "instante"])
    op.create_index("ix_cota_evento_tenant_id", "cota_evento", ["tenant_id"])
    op.create_table(
        "slot_execucao",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=False),
        sa.Column("reservado_operadora", sa.Boolean(), nullable=False),
        sa.Column("dono_sessao", sa.String(length=128), nullable=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO slot_execucao (id, reservado_operadora, dono_sessao, expira_em) "
            "VALUES (1, false, NULL, NULL), (2, true, NULL, NULL) "
            "ON CONFLICT (id) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_cota_evento_tenant_id", table_name="cota_evento")
    op.drop_index("ix_cota_evento_janela", table_name="cota_evento")
    op.drop_table("cota_evento")
    op.drop_table("slot_execucao")
