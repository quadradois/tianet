"""Schema Contratos (EPIC-004/P3).

Revision ID: 0010_contratos_schema
Revises: 0009_comercial_schema
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_contratos_schema"
down_revision = "0009_comercial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contrato_credito",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column(
            "proposta_comercial_id",
            sa.Uuid(),
            sa.ForeignKey("proposta_comercial.id"),
            nullable=False,
        ),
        sa.Column("criado_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("parametros", sa.JSON(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "formalizado_por_usuario_id",
            sa.Uuid(),
            sa.ForeignKey("usuario.id"),
            nullable=True,
        ),
        sa.Column("formalizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "assinado_por_usuario_id",
            sa.Uuid(),
            sa.ForeignKey("usuario.id"),
            nullable=True,
        ),
        sa.Column("assinado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "liberado_por_usuario_id",
            sa.Uuid(),
            sa.ForeignKey("usuario.id"),
            nullable=True,
        ),
        sa.Column("liberado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_encerramento", sa.String(500), nullable=True),
        sa.UniqueConstraint("proposta_comercial_id", name="uq_contrato_credito_proposta"),
    )
    op.create_index("ix_contrato_credito_tenant_id", "contrato_credito", ["tenant_id"])
    op.create_index("ix_contrato_credito_carteira_id", "contrato_credito", ["carteira_id"])
    op.create_index("ix_contrato_credito_devedor_id", "contrato_credito", ["devedor_id"])
    op.create_index("ix_contrato_credito_estado", "contrato_credito", ["estado"])
    op.create_index("ix_contrato_credito_criado_em", "contrato_credito", ["criado_em"])
    op.create_index(
        "ix_contrato_credito_criado_por_usuario_id",
        "contrato_credito",
        ["criado_por_usuario_id"],
    )

    op.create_table(
        "evento_contrato",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "contrato_id",
            sa.Uuid(),
            sa.ForeignKey("contrato_credito.id"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("estado_anterior", sa.String(30), nullable=False),
        sa.Column("estado_posterior", sa.String(30), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(500), nullable=True),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_evento_contrato_contrato_id", "evento_contrato", ["contrato_id"])
    op.create_index("ix_evento_contrato_usuario_id", "evento_contrato", ["usuario_id"])


def downgrade() -> None:
    op.drop_table("evento_contrato")
    op.drop_table("contrato_credito")
