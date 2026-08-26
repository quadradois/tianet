"""remove a tabela token_ativacao

Revision ID: e91c4d7a2b58
Revises: c47f1a2b8e30
Create Date: 2026-08-26 08:15:00.000000

IMP-351. O token de ativacao existia para um unico fluxo: `POST /platform/tenants`
emitia um token de 24h e o administrador do Tenant novo definia a credencial por
`POST /auth/ativar`.

Decisao do fundador em 2026-08-26: o Administrador da Plataforma e o **unico**
Tenant, e nao havera outros. O Tenant nasce pela CLI `bootstrap_plataforma`, que
define a credencial diretamente e nunca emitiu token. Com isso o fluxo inteiro
deixou de descrever o produto.

Nao era so codigo sem uso: `credencial.redefinir` exige estado ATIVO, entao um
administrador convidado cujo token expirasse ficaria **sem nenhuma saida** — a
CLI recusa quando a raiz ja existe. Manter o fluxo era manter um beco sem saida
documentado como se fosse recurso.

A tabela nunca teve linha em producao — o unico caminho que a preenchia era o
provisionamento por API, que sai nesta mesma mudanca.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e91c4d7a2b58"
down_revision: str | None = "c47f1a2b8e30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_token_ativacao_tenant_id"), table_name="token_ativacao")
    op.drop_index(op.f("ix_token_ativacao_usuario_id"), table_name="token_ativacao")
    op.drop_table("token_ativacao")


def downgrade() -> None:
    # Recria a estrutura exatamente como a 0008 a criou. Volta vazia, e isso e
    # correto: nao ha dado a preservar, porque nao ha caminho que a preenchesse.
    op.create_table(
        "token_ativacao",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("utilizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_token_ativacao_usuario_id"), "token_ativacao", ["usuario_id"])
    op.create_index(op.f("ix_token_ativacao_tenant_id"), "token_ativacao", ["tenant_id"])
