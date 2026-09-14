"""inbox e sessao conversacional do agente (IMP-356-A)

Revision ID: c9a4f2e71b83d
Revises: d2e4f6a8b0c1
Create Date: 2026-09-13 00:00:00.000000

Cria `inbox_conversa` (entrada do webhook antes do ACK, com unicidade por
Tenant/instancia-resolvida/ID-do-provedor) e `sessao_conversa` (contexto por
remetente e classe, nunca compartilhada entre Operadora e PreCadastro).
Aditiva e reversivel: o downgrade remove as duas tabelas, e so elas — nenhum
dado de credito e tocado.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9a4f2e71b83d"
down_revision: str | None = "d2e4f6a8b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inbox_conversa",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False),
        sa.Column("instancia_ref", sa.String(length=64), nullable=False),
        sa.Column("envelope_instance_id", sa.String(length=128), nullable=False),
        sa.Column("provider_input_id", sa.String(length=128), nullable=False),
        sa.Column("remetente_normalizado", sa.String(length=64), nullable=False),
        sa.Column("classe", sa.String(length=20), nullable=False),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=40), nullable=False),
        sa.Column("motivo_descarte", sa.String(length=64), nullable=True),
        sa.Column(
            "recebido_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "instancia_ref",
            "provider_input_id",
            name="uq_inbox_conversa_entrada",
        ),
    )
    op.create_index("ix_inbox_conversa_tenant_id", "inbox_conversa", ["tenant_id"])
    op.create_table(
        "sessao_conversa",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False),
        sa.Column("instancia_ref", sa.String(length=64), nullable=False),
        sa.Column("classe", sa.String(length=20), nullable=False),
        sa.Column("remetente_normalizado", sa.String(length=64), nullable=False),
        sa.Column("referencia_pendente", sa.String(length=64), nullable=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "instancia_ref",
            "classe",
            "remetente_normalizado",
            name="uq_sessao_conversa_chave",
        ),
    )
    op.create_index("ix_sessao_conversa_tenant_id", "sessao_conversa", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_sessao_conversa_tenant_id", table_name="sessao_conversa")
    op.drop_table("sessao_conversa")
    op.drop_index("ix_inbox_conversa_tenant_id", table_name="inbox_conversa")
    op.drop_table("inbox_conversa")
