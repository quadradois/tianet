"""cobranca pix do acerto (IMP-374)

Revision ID: a1b2c3d4e5f6
Revises: 62c5a6f94173
Create Date: 2026-09-22 14:10:00.000000

Aditiva. O indice unico PARCIAL sobre (emprestimo_id) WHERE estado='pendente'
e a INV-004 do DOMAIN-031: o Aggregate sozinho nao ve conjunto, e dois Pix
vivos para o mesmo emprestimo produziriam pagamento duplicado sem que nenhum
dos dois estivesse errado isoladamente.

`pagamento.origem` entra com default 'manual' para nao exigir backfill: o que
existe hoje foi lancado a mao, e e isso que a coluna passa a dizer.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "62c5a6f94173"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cobranca_pix",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column("valor", sa.Numeric(18, 2), nullable=False),
        sa.Column("valor_recebido", sa.Numeric(18, 2), nullable=True),
        sa.Column("external_reference", sa.String(64), nullable=False),
        sa.Column("mp_payment_id", sa.String(64), nullable=True),
        sa.Column("copia_cola", sa.Text(), nullable=True),
        sa.Column("qr_base64", sa.Text(), nullable=True),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("divergente", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("criado_por", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("valor > 0", name="ck_cobranca_pix_valor_positivo"),
    )
    op.create_index(
        "uq_cobranca_pix_external_reference",
        "cobranca_pix",
        ["external_reference"],
        unique=True,
    )
    op.create_index(
        "uq_cobranca_pix_mp_payment_id",
        "cobranca_pix",
        ["mp_payment_id"],
        unique=True,
        postgresql_where=sa.text("mp_payment_id IS NOT NULL"),
    )
    op.create_index(
        "uq_cobranca_pix_pendente_por_emprestimo",
        "cobranca_pix",
        ["emprestimo_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'pendente'"),
    )
    op.create_index("ix_cobranca_pix_tenant", "cobranca_pix", ["tenant_id"])
    op.create_index("ix_cobranca_pix_devedor", "cobranca_pix", ["devedor_id"])
    op.add_column(
        "pagamento",
        sa.Column("origem", sa.String(20), nullable=False, server_default="manual"),
    )


def downgrade() -> None:
    op.drop_column("pagamento", "origem")
    op.drop_index("ix_cobranca_pix_devedor", table_name="cobranca_pix")
    op.drop_index("ix_cobranca_pix_tenant", table_name="cobranca_pix")
    op.drop_index("uq_cobranca_pix_pendente_por_emprestimo", table_name="cobranca_pix")
    op.drop_index("uq_cobranca_pix_mp_payment_id", table_name="cobranca_pix")
    op.drop_index("uq_cobranca_pix_external_reference", table_name="cobranca_pix")
    op.drop_table("cobranca_pix")
