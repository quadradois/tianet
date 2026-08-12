"""Schema duravel de Scheduler e Notification (EPIC-010).

Revision ID: 0015_automacao_schema
Revises: 0014_config_fin_schema
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_automacao_schema"
down_revision = "0014_config_fin_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_agendado",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("tipo", sa.String(80), nullable=False),
        sa.Column("executar_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("origem_tipo", sa.String(80), nullable=False),
        sa.Column("origem_id", sa.Uuid(), nullable=False),
        sa.Column("estado", sa.String(40), nullable=False),
        sa.Column("max_tentativas", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("proxima_execucao_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("lease_ate", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancelamento_solicitado", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("max_tentativas BETWEEN 1 AND 5", name="ck_job_max_tentativas"),
        sa.CheckConstraint("tentativas >= 0", name="ck_job_tentativas"),
        sa.UniqueConstraint("tenant_id", "origem_tipo", "origem_id", name="uq_job_origem_tenant"),
    )
    op.create_index("ix_job_tenant_carteira", "job_agendado", ["tenant_id", "carteira_id"])
    op.create_index(
        "ix_job_claim",
        "job_agendado",
        ["estado", "proxima_execucao_em", "lease_ate", "criado_em", "id"],
    )

    op.create_table(
        "tentativa_job",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("job_agendado.id"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("lease_token", sa.Uuid(), nullable=False, unique=True),
        sa.Column("execution_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(40), nullable=False),
        sa.Column("iniciada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalizada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("erro_codigo", sa.String(120), nullable=True),
        sa.UniqueConstraint("job_id", "numero", name="uq_tentativa_job_numero"),
    )
    op.create_index("ix_tentativa_job_job_id", "tentativa_job", ["job_id"])

    op.create_table(
        "scheduler_worker_heartbeat",
        sa.Column("worker_id", sa.String(120), primary_key=True),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("concorrencia", sa.Integer(), nullable=False),
        sa.Column("em_execucao", sa.Integer(), nullable=False),
        sa.Column("ultimo_heartbeat_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lag_segundos", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_worker_heartbeat_instante",
        "scheduler_worker_heartbeat",
        ["ultimo_heartbeat_em"],
    )

    op.create_table(
        "preferencia_notificacao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("contato_id", sa.Uuid(), sa.ForeignKey("contato.id"), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("evidencia", sa.String(500), nullable=False),
        sa.Column("origem", sa.String(120), nullable=False),
        sa.Column("ator_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("registrada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogada_em", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "contato_id", name="uq_preferencia_tenant_contato"),
    )
    op.create_index(
        "ix_preferencia_tenant_carteira",
        "preferencia_notificacao",
        ["tenant_id", "carteira_id"],
    )

    op.create_table(
        "template_notificacao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("codigo", sa.String(120), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("assunto", sa.String(300), nullable=False),
        sa.Column("corpo", sa.Text(), nullable=False),
        sa.Column("parametros_permitidos", sa.JSON(), nullable=False),
        sa.Column("hash_conteudo", sa.String(64), nullable=False),
        sa.Column("criado_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False),
        sa.Column("aprovado_por_usuario_id", sa.Uuid(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("aprovado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ativado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_aprovacao", sa.String(500), nullable=True),
        sa.UniqueConstraint("tenant_id", "codigo", "versao", name="uq_template_versao"),
    )
    op.create_index("ix_template_ativo", "template_notificacao", ["tenant_id", "codigo", "estado"])

    op.create_table(
        "solicitacao_notificacao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("lembrete_id", sa.Uuid(), sa.ForeignKey("lembrete.id"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("job_agendado.id"), nullable=False),
        sa.Column("tentativa_job_id", sa.Uuid(), sa.ForeignKey("tentativa_job.id"), nullable=False),
        sa.Column("contato_id", sa.Uuid(), sa.ForeignKey("contato.id"), nullable=False),
        sa.Column(
            "template_id", sa.Uuid(), sa.ForeignKey("template_notificacao.id"), nullable=False
        ),
        sa.Column("chave_idempotente", sa.String(255), nullable=False, unique=True),
        sa.Column("payload_canonico", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("versao_solicitacao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("preparada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(40), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("resultado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("codigo_resultado", sa.String(120), nullable=True),
        sa.Column("conciliacao_chave", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_solicitacao_tenant_carteira",
        "solicitacao_notificacao",
        ["tenant_id", "carteira_id"],
    )

    op.create_table(
        "notificacao_evidencia",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "solicitacao_id", sa.Uuid(), sa.ForeignKey("solicitacao_notificacao.id"), nullable=False
        ),
        sa.Column("tentativa_job_id", sa.Uuid(), sa.ForeignKey("tentativa_job.id"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("carteira_id", sa.Uuid(), sa.ForeignKey("carteira.id"), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("chave_idempotente", sa.String(255), nullable=False),
        sa.Column("ocorrido_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("comunicacao_registro", sa.Column("ator_tipo", sa.String(30), nullable=True))
    op.add_column(
        "comunicacao_registro", sa.Column("ator_identificador", sa.String(120), nullable=True)
    )
    op.add_column(
        "comunicacao_registro",
        sa.Column(
            "notification_id",
            sa.Uuid(),
            sa.ForeignKey("solicitacao_notificacao.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "comunicacao_registro",
        sa.Column(
            "template_id",
            sa.Uuid(),
            sa.ForeignKey("template_notificacao.id"),
            nullable=True,
        ),
    )
    op.add_column("comunicacao_registro", sa.Column("template_versao", sa.Integer(), nullable=True))
    op.add_column(
        "comunicacao_registro", sa.Column("provider_message_id", sa.String(255), nullable=True)
    )
    op.create_unique_constraint(
        "uq_comunicacao_notification", "comunicacao_registro", ["notification_id"]
    )
    op.alter_column(
        "comunicacao_registro", "responsavel_id", existing_type=sa.Uuid(), nullable=True
    )
    op.create_check_constraint(
        "ck_comunicacao_ator",
        "comunicacao_registro",
        "(responsavel_id IS NOT NULL AND ator_tipo IS NULL AND ator_identificador IS NULL) "
        "OR (responsavel_id IS NULL AND ator_tipo IS NOT NULL AND ator_identificador IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_comunicacao_ator", "comunicacao_registro", type_="check")
    op.alter_column(
        "comunicacao_registro", "responsavel_id", existing_type=sa.Uuid(), nullable=False
    )
    op.drop_constraint("uq_comunicacao_notification", "comunicacao_registro", type_="unique")
    op.drop_column("comunicacao_registro", "provider_message_id")
    op.drop_column("comunicacao_registro", "template_versao")
    op.drop_column("comunicacao_registro", "template_id")
    op.drop_column("comunicacao_registro", "notification_id")
    op.drop_column("comunicacao_registro", "ator_identificador")
    op.drop_column("comunicacao_registro", "ator_tipo")
    op.drop_table("notificacao_evidencia")
    op.drop_table("solicitacao_notificacao")
    op.drop_table("template_notificacao")
    op.drop_table("preferencia_notificacao")
    op.drop_table("scheduler_worker_heartbeat")
    op.drop_table("tentativa_job")
    op.drop_table("job_agendado")
