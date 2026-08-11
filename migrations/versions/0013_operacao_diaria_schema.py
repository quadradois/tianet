"""Schema de operaÃ§Ã£o diÃ¡ria (EPIC-007/P2).

Revision ID: 0013_operacao_diaria_schema
Revises: 0012_motor_financeiro_permissoes
Create Date: 2026-08-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013_operacao_diaria_schema"
down_revision = "0012_motor_financeiro_permissoes"
branch_labels = None
depends_on = None

VALOR_MONETARIO = sa.Numeric(18, 2)


def upgrade() -> None:
    op.create_table(
        "cobranca_caso",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=True),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("total_pendente", VALOR_MONETARIO, nullable=False, server_default="0"),
        sa.Column("origem", sa.String(50), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("total_pendente >= 0", name="ck_cobranca_caso_total_pendente_n"),
        sa.UniqueConstraint(
            "tenant_id", "carteira_id", "devedor_id", name="uq_cobranca_caso_devedor"
        ),
    )
    op.create_index("ix_cobranca_caso_tenant_id", "cobranca_caso", ["tenant_id"])
    op.create_index("ix_cobranca_caso_carteira_id", "cobranca_caso", ["carteira_id"])
    op.create_index("ix_cobranca_caso_devedor_id", "cobranca_caso", ["devedor_id"])
    op.create_index("ix_cobranca_caso_emprestimo_id", "cobranca_caso", ["emprestimo_id"])
    op.create_index("ix_cobranca_caso_estado", "cobranca_caso", ["estado"])

    op.create_table(
        "cobranca_acao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cobranca_caso_id", sa.Uuid(), sa.ForeignKey("cobranca_caso.id"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=False),
        sa.Column("criado_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("resultado", sa.Text(), nullable=False),
        sa.Column("parcela_id", sa.Uuid(), sa.ForeignKey("parcela.id"), nullable=True),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column(
            "registrada_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("resultado <> ''", name="ck_cobranca_acao_resultado"),
    )
    op.create_index("ix_cobranca_acao_tenant_id", "cobranca_acao", ["tenant_id"])
    op.create_index("ix_cobranca_acao_carteira_id", "cobranca_acao", ["carteira_id"])
    op.create_index("ix_cobranca_acao_devedor_id", "cobranca_acao", ["devedor_id"])
    op.create_index("ix_cobranca_acao_emprestimo_id", "cobranca_acao", ["emprestimo_id"])
    op.create_index("ix_cobranca_acao_usuario_id", "cobranca_acao", ["criado_por_usuario_id"])
    op.create_index("ix_cobranca_acao_estado", "cobranca_acao", ["estado"])

    op.create_table(
        "promessa_pagamento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=False),
        sa.Column("valor_declarado", VALOR_MONETARIO, nullable=False),
        sa.Column("data_promessa", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("parcela_id", sa.Uuid(), sa.ForeignKey("parcela.id"), nullable=True),
        sa.Column("criado_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("valor_declarado > 0", name="ck_promessa_valor_declarado_positivo"),
    )
    op.create_index("ix_promessa_tenant_id", "promessa_pagamento", ["tenant_id"])
    op.create_index("ix_promessa_carteira_id", "promessa_pagamento", ["carteira_id"])
    op.create_index("ix_promessa_devedor_id", "promessa_pagamento", ["devedor_id"])
    op.create_index("ix_promessa_emprestimo_id", "promessa_pagamento", ["emprestimo_id"])
    op.create_index("ix_promessa_estado", "promessa_pagamento", ["estado"])
    op.create_index("ix_promessa_parcela_id", "promessa_pagamento", ["parcela_id"])

    op.create_table(
        "promessa_apropriacao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("promessa_id", sa.Uuid(), sa.ForeignKey("promessa_pagamento.id"), nullable=False),
        sa.Column("pagamento_id", sa.Uuid(), sa.ForeignKey("pagamento.id"), nullable=True),
        sa.Column("valor", VALOR_MONETARIO, nullable=False),
        sa.Column("realizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parcela_id", sa.Uuid(), sa.ForeignKey("parcela.id"), nullable=False),
        sa.Column(
            "criada_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("idempotencia", sa.String(255), nullable=False),
        sa.CheckConstraint("valor > 0", name="ck_promessa_apropriacao_valor_positivo"),
        sa.UniqueConstraint("promessa_id", "pagamento_id", name="uq_promessa_pagamento_pagamento"),
    )
    op.create_index("ix_promessa_apropriacao_promessa_id", "promessa_apropriacao", ["promessa_id"])
    op.create_index(
        "ix_promessa_apropriacao_pagamento_id", "promessa_apropriacao", ["pagamento_id"]
    )
    op.create_index("ix_promessa_apropriacao_parcela_id", "promessa_apropriacao", ["parcela_id"])

    op.create_table(
        "agenda_item",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=True),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("previsto_para", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usuario_solicitante_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.CheckConstraint("titulo <> ''", name="ck_agenda_item_titulo"),
    )
    op.create_index("ix_agenda_item_tenant_id", "agenda_item", ["tenant_id"])
    op.create_index("ix_agenda_item_carteira_id", "agenda_item", ["carteira_id"])
    op.create_index("ix_agenda_item_devedor_id", "agenda_item", ["devedor_id"])
    op.create_index("ix_agenda_item_emprestimo_id", "agenda_item", ["emprestimo_id"])
    op.create_index("ix_agenda_item_usuario_id", "agenda_item", ["usuario_solicitante_id"])
    op.create_index("ix_agenda_item_estado", "agenda_item", ["estado"])
    op.create_index("ix_agenda_item_previsto_para", "agenda_item", ["previsto_para"])

    op.create_table(
        "lembrete",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("agenda_item_id", sa.Uuid(), sa.ForeignKey("agenda_item.id"), nullable=False),
        sa.Column("horario", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enviado_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("mensagem <> ''", name="ck_lembrete_mensagem"),
    )
    op.create_index("ix_lembrete_tenant_id", "lembrete", ["tenant_id"])
    op.create_index("ix_lembrete_carteira_id", "lembrete", ["carteira_id"])
    op.create_index("ix_lembrete_agenda_item_id", "lembrete", ["agenda_item_id"])
    op.create_index("ix_lembrete_horario", "lembrete", ["horario"])
    op.create_index("ix_lembrete_estado", "lembrete", ["estado"])

    op.create_table(
        "comunicacao_registro",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=True),
        sa.Column("responsavel_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("canal", sa.String(50), nullable=False),
        sa.Column("resumo", sa.String(500), nullable=False),
        sa.Column("resultado", sa.Text(), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parcela_id", sa.Uuid(), sa.ForeignKey("parcela.id"), nullable=True),
        sa.Column("cobranca_acao_id", sa.Uuid(), sa.ForeignKey("cobranca_acao.id"), nullable=True),
        sa.Column("agenda_item_id", sa.Uuid(), sa.ForeignKey("agenda_item.id"), nullable=True),
        sa.CheckConstraint("resumo <> ''", name="ck_comunicacao_resumo"),
    )
    op.create_index("ix_comunicacao_tenant_id", "comunicacao_registro", ["tenant_id"])
    op.create_index("ix_comunicacao_carteira_id", "comunicacao_registro", ["carteira_id"])
    op.create_index("ix_comunicacao_devedor_id", "comunicacao_registro", ["devedor_id"])
    op.create_index("ix_comunicacao_emprestimo_id", "comunicacao_registro", ["emprestimo_id"])
    op.create_index("ix_comunicacao_responsavel_id", "comunicacao_registro", ["responsavel_id"])
    op.create_index("ix_comunicacao_canal", "comunicacao_registro", ["canal"])
    op.create_index("ix_comunicacao_ocorrido_em", "comunicacao_registro", ["ocorrido_em"])

    op.create_table(
        "relatorio_operacional_cache",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("janela_referencia", sa.Date(), nullable=False),
        sa.Column("familia_relatorio", sa.String(80), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "gerado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("familia_relatorio <> ''", name="ck_relatorio_familia_relatorio"),
    )
    op.create_index("ix_relatorio_cache_tenant_id", "relatorio_operacional_cache", ["tenant_id"])
    op.create_index(
        "ix_relatorio_cache_carteira_id",
        "relatorio_operacional_cache",
        ["carteira_id"],
    )
    op.create_index(
        "ix_relatorio_cache_familia",
        "relatorio_operacional_cache",
        ["familia_relatorio"],
    )
    op.create_index(
        "ix_relatorio_cache_janela", "relatorio_operacional_cache", ["janela_referencia"]
    )


def downgrade() -> None:
    op.drop_table("relatorio_operacional_cache")
    op.drop_table("comunicacao_registro")
    op.drop_table("lembrete")
    op.drop_table("agenda_item")
    op.drop_table("promessa_apropriacao")
    op.drop_table("promessa_pagamento")
    op.drop_table("cobranca_acao")
    op.drop_table("cobranca_caso")
