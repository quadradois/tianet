"""Schema Comercial (EPIC-003/P3).

Revision ID: 0009_comercial_schema
Revises: 0008_iam_operacional
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_comercial_schema"
down_revision = "0008_iam_operacional"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulacao_comercial",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column("criada_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("parametros", sa.JSON(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_simulacao_comercial_tenant_id", "simulacao_comercial", ["tenant_id"])
    op.create_index("ix_simulacao_comercial_carteira_id", "simulacao_comercial", ["carteira_id"])
    op.create_index("ix_simulacao_comercial_devedor_id", "simulacao_comercial", ["devedor_id"])
    op.create_index(
        "ix_simulacao_comercial_criada_por_usuario_id",
        "simulacao_comercial",
        ["criada_por_usuario_id"],
    )

    op.create_table(
        "proposta_comercial",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column("criada_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column(
            "simulacao_id",
            sa.Uuid(),
            sa.ForeignKey("simulacao_comercial.id"),
            nullable=True,
        ),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("parametros", sa.JSON(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aprovada_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("aprovada_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_proposta_comercial_tenant_id", "proposta_comercial", ["tenant_id"])
    op.create_index("ix_proposta_comercial_carteira_id", "proposta_comercial", ["carteira_id"])
    op.create_index("ix_proposta_comercial_devedor_id", "proposta_comercial", ["devedor_id"])
    op.create_index(
        "ix_proposta_comercial_criada_por_usuario_id",
        "proposta_comercial",
        ["criada_por_usuario_id"],
    )
    op.create_index("ix_proposta_comercial_simulacao_id", "proposta_comercial", ["simulacao_id"])
    op.create_index("ix_proposta_comercial_estado", "proposta_comercial", ["estado"])
    op.create_index(
        "ix_proposta_comercial_aprovada_por_usuario_id",
        "proposta_comercial",
        ["aprovada_por_usuario_id"],
    )

    op.create_table(
        "decisao_comercial",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "proposta_id",
            sa.Uuid(),
            sa.ForeignKey("proposta_comercial.id"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("estado_anterior", sa.String(30), nullable=False),
        sa.Column("estado_posterior", sa.String(30), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(500), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_decisao_comercial_proposta_id", "decisao_comercial", ["proposta_id"])
    op.create_index("ix_decisao_comercial_usuario_id", "decisao_comercial", ["usuario_id"])


def downgrade() -> None:
    op.drop_table("decisao_comercial")
    op.drop_table("proposta_comercial")
    op.drop_table("simulacao_comercial")
