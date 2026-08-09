"""Cria schema persistente do IAM.

Revision ID: 0007_iam_schema
Revises: 0006_contato_removido_em
Create Date: 2026-08-08 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_iam_schema"
down_revision = "0006_contato_removido_em"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credencial",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("hash_credencial", sa.String(length=255), nullable=False),
        sa.Column("algoritmo", sa.String(length=50), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", name="uq_credencial_usuario"),
    )
    op.create_index(
        op.f("ix_credencial_usuario_id"),
        "credencial",
        ["usuario_id"],
        unique=False,
    )

    op.create_table(
        "sessao",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_token_hash", name="uq_sessao_refresh_hash"),
    )
    op.create_index(op.f("ix_sessao_tenant_id"), "sessao", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_sessao_usuario_id"), "sessao", ["usuario_id"], unique=False)

    op.create_table(
        "permissao",
        sa.Column("codigo", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("codigo"),
    )

    op.create_table(
        "perfil_acesso",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "nome", name="uq_perfil_tenant_nome"),
    )
    op.create_index(
        op.f("ix_perfil_acesso_tenant_id"),
        "perfil_acesso",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "perfil_permissao",
        sa.Column("perfil_id", sa.Uuid(), nullable=False),
        sa.Column("permissao_codigo", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["perfil_id"], ["perfil_acesso.id"]),
        sa.ForeignKeyConstraint(["permissao_codigo"], ["permissao.codigo"]),
        sa.PrimaryKeyConstraint("perfil_id", "permissao_codigo"),
    )

    op.create_table(
        "usuario_perfil",
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("perfil_id", sa.Uuid(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["perfil_id"], ["perfil_acesso.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("usuario_id"),
    )
    op.create_index(
        op.f("ix_usuario_perfil_perfil_id"),
        "usuario_perfil",
        ["perfil_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_usuario_perfil_perfil_id"), table_name="usuario_perfil")
    op.drop_table("usuario_perfil")
    op.drop_table("perfil_permissao")
    op.drop_index(op.f("ix_perfil_acesso_tenant_id"), table_name="perfil_acesso")
    op.drop_table("perfil_acesso")
    op.drop_table("permissao")
    op.drop_index(op.f("ix_sessao_usuario_id"), table_name="sessao")
    op.drop_index(op.f("ix_sessao_tenant_id"), table_name="sessao")
    op.drop_table("sessao")
    op.drop_index(op.f("ix_credencial_usuario_id"), table_name="credencial")
    op.drop_table("credencial")
