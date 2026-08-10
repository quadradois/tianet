"""Schema Motor Financeiro (EPIC-005/P3).

Revision ID: 0011_motor_financeiro_schema
Revises: 0010_contratos_schema
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_motor_financeiro_schema"
down_revision = "0010_contratos_schema"
branch_labels = None
depends_on = None

VALOR_MONETARIO = sa.Numeric(18, 2)


def upgrade() -> None:
    op.create_table(
        "emprestimo",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column(
            "contrato_id",
            sa.Uuid(),
            sa.ForeignKey("contrato_credito.id"),
            nullable=False,
        ),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("principal_original", VALOR_MONETARIO, nullable=False),
        sa.Column("moeda", sa.String(3), nullable=False),
        sa.Column("parametros_financeiros", sa.JSON(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_processamento_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_pagamento_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proximo_vencimento_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quitado_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("contrato_id", name="uq_emprestimo_contrato"),
        sa.CheckConstraint("principal_original > 0", name="ck_emprestimo_principal_positivo"),
    )
    op.create_index("ix_emprestimo_tenant_id", "emprestimo", ["tenant_id"])
    op.create_index("ix_emprestimo_carteira_id", "emprestimo", ["carteira_id"])
    op.create_index("ix_emprestimo_devedor_id", "emprestimo", ["devedor_id"])
    op.create_index("ix_emprestimo_estado", "emprestimo", ["estado"])
    op.create_index("ix_emprestimo_contrato_id", "emprestimo", ["contrato_id"])

    op.create_table(
        "parcela",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("valor_previsto", VALOR_MONETARIO, nullable=False),
        sa.Column("principal", VALOR_MONETARIO, nullable=False, server_default="0"),
        sa.Column("juros", VALOR_MONETARIO, nullable=False, server_default="0"),
        sa.Column("encargos", VALOR_MONETARIO, nullable=False, server_default="0"),
        sa.Column("valor_liquidado", VALOR_MONETARIO, nullable=False, server_default="0"),
        sa.Column("periodo", sa.JSON(), nullable=True),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column(
            "criada_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("atualizada_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("emprestimo_id", "numero", name="uq_parcela_emprestimo_numero"),
        sa.CheckConstraint("numero > 0", name="ck_parcela_numero_positivo"),
        sa.CheckConstraint("valor_previsto > 0", name="ck_parcela_valor_previsto_positivo"),
        sa.CheckConstraint("principal >= 0", name="ck_parcela_principal_nao_negativo"),
        sa.CheckConstraint("juros >= 0", name="ck_parcela_juros_nao_negativo"),
        sa.CheckConstraint("encargos >= 0", name="ck_parcela_encargos_nao_negativo"),
        sa.CheckConstraint(
            "valor_liquidado >= 0",
            name="ck_parcela_valor_liquidado_nao_negativo",
        ),
    )
    op.create_index("ix_parcela_emprestimo_id", "parcela", ["emprestimo_id"])
    op.create_index("ix_parcela_vencimento", "parcela", ["vencimento"])
    op.create_index("ix_parcela_estado", "parcela", ["estado"])

    op.create_table(
        "pagamento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=False),
        sa.Column("valor_recebido", VALOR_MONETARIO, nullable=False),
        sa.Column("recebido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valor_juros", VALOR_MONETARIO, nullable=False, server_default="0"),
        sa.Column("valor_amortizacao", VALOR_MONETARIO, nullable=False, server_default="0"),
        sa.Column("valor_encargos", VALOR_MONETARIO, nullable=False, server_default="0"),
        sa.Column("chave_idempotencia", sa.String(255), nullable=False),
        sa.Column("parcelas_liquidadas", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("distribuicao", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "emprestimo_id",
            "chave_idempotencia",
            name="uq_pagamento_emprestimo_chave_idempotencia",
        ),
        sa.CheckConstraint("valor_recebido > 0", name="ck_pagamento_valor_recebido_positivo"),
        sa.CheckConstraint("valor_juros >= 0", name="ck_pagamento_juros_nao_negativo"),
        sa.CheckConstraint(
            "valor_amortizacao >= 0",
            name="ck_pagamento_amortizacao_nao_negativa",
        ),
        sa.CheckConstraint("valor_encargos >= 0", name="ck_pagamento_encargos_nao_negativo"),
    )
    op.create_index("ix_pagamento_emprestimo_id", "pagamento", ["emprestimo_id"])
    op.create_index("ix_pagamento_usuario_id", "pagamento", ["usuario_id"])
    op.create_index("ix_pagamento_recebido_em", "pagamento", ["recebido_em"])

    op.create_table(
        "memoria_calculo",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=False),
        sa.Column("pagamento_id", sa.Uuid(), sa.ForeignKey("pagamento.id"), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("data_referencia", sa.Date(), nullable=True),
        sa.Column("entradas", sa.JSON(), nullable=False),
        sa.Column("regra", sa.JSON(), nullable=False),
        sa.Column("periodos", sa.JSON(), nullable=False),
        sa.Column("passos", sa.JSON(), nullable=False),
        sa.Column("arredondamentos", sa.JSON(), nullable=False),
        sa.Column("resultados", sa.JSON(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_memoria_calculo_emprestimo_id", "memoria_calculo", ["emprestimo_id"])
    op.create_index("ix_memoria_calculo_pagamento_id", "memoria_calculo", ["pagamento_id"])
    op.create_index("ix_memoria_calculo_tipo", "memoria_calculo", ["tipo"])

    op.create_table(
        "evento_financeiro",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column(
            "memoria_calculo_id",
            sa.Uuid(),
            sa.ForeignKey("memoria_calculo.id"),
            nullable=True,
        ),
        sa.Column("pagamento_id", sa.Uuid(), sa.ForeignKey("pagamento.id"), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("estado_anterior", sa.String(30), nullable=True),
        sa.Column("estado_posterior", sa.String(30), nullable=True),
        sa.Column("valor", VALOR_MONETARIO, nullable=True),
        sa.Column("detalhes", sa.JSON(), nullable=True),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evento_financeiro_emprestimo_id", "evento_financeiro", ["emprestimo_id"])
    op.create_index("ix_evento_financeiro_tenant_id", "evento_financeiro", ["tenant_id"])
    op.create_index("ix_evento_financeiro_tipo", "evento_financeiro", ["tipo"])
    op.create_index("ix_evento_financeiro_ocorrido_em", "evento_financeiro", ["ocorrido_em"])


def downgrade() -> None:
    op.drop_table("evento_financeiro")
    op.drop_table("memoria_calculo")
    op.drop_table("pagamento")
    op.drop_table("parcela")
    op.drop_table("emprestimo")
