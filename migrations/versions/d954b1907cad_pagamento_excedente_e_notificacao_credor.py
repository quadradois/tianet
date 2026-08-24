"""pagamento excedente e notificacao credor

Revision ID: d954b1907cad
Revises: 0019_notificacao_transacional
Create Date: 2026-08-22 21:49:47.091485

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d954b1907cad"
down_revision: str | None = "0019_notificacao_transacional"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pagamento",
        sa.Column(
            "valor_devolvido",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
    )
    op.add_column(
        "pagamento",
        sa.Column(
            "valor_estornado",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
    )
    # Preserva pagamentos historicos, inclusive excedentes anteriores ao IMP-332:
    # a diferenca ja recebida passa a ficar explicitamente destinada a devolucao.
    op.execute(
        sa.text(
            "UPDATE pagamento "
            "SET valor_devolvido = valor_recebido - valor_juros "
            "- valor_amortizacao - valor_encargos"
        )
    )
    op.create_check_constraint(
        "ck_pagamento_devolvido_nao_negativo",
        "pagamento",
        "valor_devolvido >= 0",
    )
    op.create_check_constraint(
        "ck_pagamento_estornado_nao_negativo",
        "pagamento",
        "valor_estornado >= 0",
    )
    op.create_check_constraint(
        "ck_pagamento_valor_reconciliado",
        "pagamento",
        "valor_juros + valor_amortizacao + valor_encargos + valor_devolvido " "= valor_recebido",
    )
    op.create_check_constraint(
        "ck_pagamento_estorno_dentro_devolucao",
        "pagamento",
        "valor_estornado <= valor_devolvido",
    )


def downgrade() -> None:

    op.drop_constraint(
        "ck_pagamento_estorno_dentro_devolucao",
        "pagamento",
        type_="check",
    )
    op.drop_constraint(
        "ck_pagamento_valor_reconciliado",
        "pagamento",
        type_="check",
    )
    op.drop_constraint(
        "ck_pagamento_estornado_nao_negativo",
        "pagamento",
        type_="check",
    )
    op.drop_constraint(
        "ck_pagamento_devolvido_nao_negativo",
        "pagamento",
        type_="check",
    )
    op.drop_column("pagamento", "valor_estornado")
    op.drop_column("pagamento", "valor_devolvido")
