"""memoria e referencias da sessao do agente (IMP-356-F slice 1)

Revision ID: c8d3e5f7a2b4
Revises: e7f8a9b0c1d2
Create Date: 2026-09-15 00:00:00.000000

Cria `mensagem_conversa` (memória da sessão, texto sob expurgo),
`tool_call_exec` (registro operacional sem dinheiro) e
`referencia_sessao` (ref opaca → devedor por sessão, TTL curto).
Aditiva e reversível: o downgrade remove as três tabelas, e só isso.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8d3e5f7a2b4"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mensagem_conversa",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("sessao_id", postgresql.UUID(), nullable=False),
        sa.Column("inbox_id", postgresql.UUID(), nullable=True),
        sa.Column("indice", sa.Integer(), nullable=False),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sessao_id"], ["sessao_conversa.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sessao_id", "indice", name="uq_mensagem_conversa_ordem"),
    )
    op.create_index("ix_mensagem_conversa_sessao", "mensagem_conversa", ["sessao_id"])
    op.create_table(
        "tool_call_exec",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("sessao_id", postgresql.UUID(), nullable=False),
        sa.Column("inbox_id", postgresql.UUID(), nullable=False),
        sa.Column("call_id", sa.String(128), nullable=False),
        sa.Column("ferramenta", sa.String(64), nullable=False),
        sa.Column("schema_versao", sa.String(64), nullable=False),
        sa.Column("parametros", postgresql.JSON(), nullable=False),
        sa.Column("resultado", postgresql.JSON(), nullable=False),
        sa.Column("latencia_ms", sa.Integer(), nullable=False),
        sa.Column("completa", sa.Boolean(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sessao_id"], ["sessao_conversa.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sessao_id", "call_id", name="uq_tool_call_exec_chamada"),
    )
    op.create_index("ix_tool_call_exec_sessao", "tool_call_exec", ["sessao_id"])
    op.create_table(
        "referencia_sessao",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("sessao_id", postgresql.UUID(), nullable=False),
        sa.Column("ref", sa.String(64), nullable=False),
        sa.Column("devedor_id", postgresql.UUID(), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sessao_id"], ["sessao_conversa.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sessao_id", "ref", name="uq_referencia_sessao_ref"),
    )
    op.create_index("ix_referencia_sessao_expira", "referencia_sessao", ["expira_em"])


def downgrade() -> None:
    op.drop_index("ix_referencia_sessao_expira", table_name="referencia_sessao")
    op.drop_table("referencia_sessao")
    op.drop_index("ix_tool_call_exec_sessao", table_name="tool_call_exec")
    op.drop_table("tool_call_exec")
    op.drop_index("ix_mensagem_conversa_sessao", table_name="mensagem_conversa")
    op.drop_table("mensagem_conversa")
