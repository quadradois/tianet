"""Formaliza o canal WhatsApp usado pelo comprovante do lancamento.

Revision ID: 0018_comprovante_whatsapp
Revises: 0017_remove_plano_de_parcelas
Create Date: 2026-08-20
"""

from __future__ import annotations

from alembic import op

revision = "0018_comprovante_whatsapp"
down_revision = "0017_remove_plano_de_parcelas"
branch_labels = None
depends_on = None

CANAIS = ("telefone", "email", "whatsapp", "chat", "presencial")


def upgrade() -> None:
    valores = ", ".join(f"'{canal}'" for canal in CANAIS)
    op.create_check_constraint(
        "ck_comunicacao_canal",
        "comunicacao_registro",
        f"canal IN ({valores})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_comunicacao_canal",
        "comunicacao_registro",
        type_="check",
    )
