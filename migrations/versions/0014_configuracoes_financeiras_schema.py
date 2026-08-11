"""Schema de configuracoes financeiras e calendario operacional (EPIC-009/P2).

Revision ID: 0014_config_fin_schema
Revises: 0013_operacao_diaria_schema
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014_config_fin_schema"
down_revision = "0013_operacao_diaria_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "modalidade_financeira",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=True),
        sa.Column("codigo", sa.String(80), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("codigo <> ''", name="ck_modalidade_financeira_codigo"),
        sa.CheckConstraint("nome <> ''", name="ck_modalidade_financeira_nome"),
        sa.UniqueConstraint(
            "tenant_id",
            "carteira_id",
            "codigo",
            name="uq_modalidade_financeira_tenant_carteira_codigo",
        ),
    )
    op.create_index("ix_modalidade_financeira_tenant_id", "modalidade_financeira", ["tenant_id"])
    op.create_index(
        "ix_modalidade_financeira_carteira_id",
        "modalidade_financeira",
        ["carteira_id"],
    )
    op.create_index("ix_modalidade_financeira_codigo", "modalidade_financeira", ["codigo"])

    op.create_table(
        "calendario_financeiro",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=True),
        sa.Column("codigo", sa.String(80), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("feriados", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("codigo <> ''", name="ck_calendario_financeiro_codigo"),
        sa.CheckConstraint("nome <> ''", name="ck_calendario_financeiro_nome"),
        sa.UniqueConstraint(
            "tenant_id",
            "carteira_id",
            "codigo",
            name="uq_calendario_financeiro_tenant_carteira_codigo",
        ),
    )
    op.create_index("ix_calendario_financeiro_tenant_id", "calendario_financeiro", ["tenant_id"])
    op.create_index(
        "ix_calendario_financeiro_carteira_id",
        "calendario_financeiro",
        ["carteira_id"],
    )
    op.create_index("ix_calendario_financeiro_codigo", "calendario_financeiro", ["codigo"])

    op.create_table(
        "configuracao_financeira",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=True),
        sa.Column("modalidade_codigo", sa.String(80), nullable=False),
        sa.Column(
            "calendario_id", sa.Uuid(), sa.ForeignKey("calendario_financeiro.id"), nullable=False
        ),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=True),
        sa.Column("taxas", sa.JSON(), nullable=False),
        sa.Column("parametros", sa.JSON(), nullable=False),
        sa.Column("politica_arredondamento", sa.JSON(), nullable=False),
        sa.Column("criada_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("atualizada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aprovada_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("aprovada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("programada_para", sa.Date(), nullable=True),
        sa.Column("ativada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("substituida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inativada_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("versao > 0", name="ck_configuracao_financeira_versao"),
        sa.UniqueConstraint(
            "tenant_id",
            "carteira_id",
            "modalidade_codigo",
            "versao",
            name="uq_configuracao_financeira_escopo_versao",
        ),
    )
    op.create_index(
        "ix_configuracao_financeira_tenant_id", "configuracao_financeira", ["tenant_id"]
    )
    op.create_index(
        "ix_configuracao_financeira_carteira_id",
        "configuracao_financeira",
        ["carteira_id"],
    )
    op.create_index("ix_configuracao_financeira_estado", "configuracao_financeira", ["estado"])
    op.create_index(
        "ix_configuracao_financeira_modalidade",
        "configuracao_financeira",
        ["modalidade_codigo"],
    )
    op.create_index(
        "ix_configuracao_financeira_vigencia",
        "configuracao_financeira",
        ["vigencia_inicio", "vigencia_fim"],
    )

    op.create_table(
        "configuracao_financeira_evento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "configuracao_id",
            sa.Uuid(),
            sa.ForeignKey("configuracao_financeira.id"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=True),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("tipo", sa.String(80), nullable=False),
        sa.Column("motivo", sa.String(500), nullable=True),
        sa.Column("versao_anterior", sa.Integer(), nullable=True),
        sa.Column("versao_nova", sa.Integer(), nullable=True),
        sa.Column("correlation_id", sa.String(255), nullable=True),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_configuracao_financeira_evento_configuracao_id",
        "configuracao_financeira_evento",
        ["configuracao_id"],
    )
    op.create_index(
        "ix_configuracao_financeira_evento_tenant_id",
        "configuracao_financeira_evento",
        ["tenant_id"],
    )

    op.create_table(
        "snapshot_configuracao_contratual",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "configuracao_id",
            sa.Uuid(),
            sa.ForeignKey("configuracao_financeira.id"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=True),
        sa.Column("modalidade", sa.String(80), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("parametros", sa.JSON(), nullable=False),
        sa.Column("hash_parametros", sa.String(64), nullable=False),
        sa.Column("capturado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "capturado_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False
        ),
        sa.Column("motivo", sa.String(500), nullable=True),
    )
    op.create_index(
        "ix_snapshot_configuracao_contratual_configuracao_id",
        "snapshot_configuracao_contratual",
        ["configuracao_id"],
    )
    op.create_index(
        "ix_snapshot_configuracao_contratual_tenant_id",
        "snapshot_configuracao_contratual",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_table("snapshot_configuracao_contratual")
    op.drop_table("configuracao_financeira_evento")
    op.drop_table("configuracao_financeira")
    op.drop_table("calendario_financeiro")
    op.drop_table("modalidade_financeira")
