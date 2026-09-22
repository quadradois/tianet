"""configuracao do mercado pago por tenant (IMP-388)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-22 16:20:00.000000

Aditiva. A integracao nasce DESLIGADA: `habilitado` tem server_default false,
entao todo Tenant existente continua sem receber por Pix ate alguem ligar no
painel. Segredos em LargeBinary pelo mesmo motivo da conexao_whatsapp — cifra
e binario, e guardar binario como texto convida a corrupcao por encoding.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERFIS_ADMIN = ("administrador", "administrador_plataforma")
NOVAS = (("mercadopago.configurar", "Configurar o recebimento por Pix (Mercado Pago)"),)


def upgrade() -> None:
    op.create_table(
        "configuracao_mercadopago",
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), primary_key=True),
        sa.Column("habilitado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("access_token_cifrado", sa.LargeBinary(), nullable=True),
        sa.Column("webhook_secret_cifrado", sa.LargeBinary(), nullable=True),
        sa.Column("testado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_por", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=True),
    )
    bind = op.get_bind()
    for codigo, descricao in NOVAS:
        bind.execute(
            sa.text(
                "INSERT INTO permissao (codigo, descricao) VALUES (:codigo, :descricao) "
                "ON CONFLICT (codigo) DO UPDATE SET descricao = EXCLUDED.descricao"
            ),
            {"codigo": codigo, "descricao": descricao},
        )
        bind.execute(
            sa.text(
                "INSERT INTO perfil_permissao (perfil_id, permissao_codigo) "
                "SELECT id, :codigo FROM perfil_acesso "
                "WHERE lower(nome) = ANY(:perfis) "
                "ON CONFLICT DO NOTHING"
            ),
            {"codigo": codigo, "perfis": list(PERFIS_ADMIN)},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for codigo, _ in NOVAS:
        bind.execute(
            sa.text("DELETE FROM perfil_permissao WHERE permissao_codigo = :codigo"),
            {"codigo": codigo},
        )
        bind.execute(sa.text("DELETE FROM permissao WHERE codigo = :codigo"), {"codigo": codigo})
    op.drop_table("configuracao_mercadopago")
