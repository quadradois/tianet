"""intencao duravel de egress (IMP-356-E slice 2)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-16 00:00:00.000000

Cria `egress_conversa` (intenção + payload + estados com `em_envio`).
Aditiva e reversível: o downgrade remove a tabela, e só ela.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "egress_conversa",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("inbox_id", postgresql.UUID(), nullable=False),
        sa.Column("sessao_id", postgresql.UUID(), nullable=False),
        sa.Column("indice", sa.Integer(), nullable=False),
        sa.Column("chave", sa.String(128), nullable=False),
        sa.Column("payload_canonico", sa.Text(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False),
        sa.Column("carteira_id", postgresql.UUID(), nullable=True),
        sa.Column("instancia_ref", sa.String(64), nullable=False),
        sa.Column("classe", sa.String(20), nullable=False),
        sa.Column("principal_id", postgresql.UUID(), nullable=True),
        sa.Column("destinatario", sa.String(32), nullable=False),
        sa.Column("ferramenta", sa.String(64), nullable=True),
        sa.Column("call_id", sa.String(128), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("tentativas", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.String(128), nullable=True),
        sa.Column("codigo", sa.String(64), nullable=True),
        sa.Column("conciliacao_chave", sa.String(128), nullable=True),
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
        sa.ForeignKeyConstraint(["inbox_id"], ["inbox_conversa.id"]),
        sa.ForeignKeyConstraint(["sessao_id"], ["sessao_conversa.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inbox_id", "indice", name="uq_egress_conversa_destino"),
        sa.UniqueConstraint("chave", name="uq_egress_conversa_chave"),
    )
    op.create_index("ix_egress_conversa_sessao", "egress_conversa", ["sessao_id"])


def downgrade() -> None:
    op.drop_index("ix_egress_conversa_sessao", table_name="egress_conversa")
    op.drop_table("egress_conversa")
