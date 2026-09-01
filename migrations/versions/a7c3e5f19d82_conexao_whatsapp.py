"""cria a tabela conexao_whatsapp

Revision ID: a7c3e5f19d82
Revises: f3a81c62d94e
Create Date: 2026-09-01 09:20:00.000000

IMP-365 do PLAN-034. Da ao token da instancia do WhatsApp um lugar para morar,
cifrado, para que a conexao sobreviva a um restart sem alguem editar o `.env` na
mao — que e o atrito que a tela de QR vem eliminar (DR-006).

Aditiva: nenhuma tabela existente e tocada. O downgrade e `DROP TABLE`, e nao
perde nada que exista em outro lugar — o token pode ser regenerado reconectando
pela tela, e o `EVOLUTION_INSTANCE_TOKEN` do ambiente continua sendo a origem
para o worker ate o IMP-370 fechar.

`token_cifrado` e `LargeBinary` e nao texto: cifra e binario, e guardar binario
como texto convida a corrupcao por encoding — que so apareceria no dia em que o
token nao abrisse mais, ja em producao.

`UNIQUE (tenant_id)` expressa no banco o escopo que a ADR-003 decidiu: um
Credor, um Tenant, uma instancia. A restricao esta aqui, e nao so na aplicacao,
porque invariante que vive apenas em codigo e invariante que a proxima escrita
concorrente pode violar.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c3e5f19d82"
down_revision: str | None = "f3a81c62d94e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conexao_whatsapp",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("instancia_id", sa.String(length=64), nullable=False),
        sa.Column("instancia_nome", sa.String(length=100), nullable=False),
        sa.Column("token_cifrado", sa.LargeBinary(), nullable=False),
        sa.Column("numero_pareado", sa.String(length=32), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_conexao_whatsapp_tenant"),
    )
    op.create_index(
        op.f("ix_conexao_whatsapp_tenant_id"),
        "conexao_whatsapp",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_conexao_whatsapp_tenant_id"), table_name="conexao_whatsapp")
    op.drop_table("conexao_whatsapp")
