"""Permissoes IAM da automacao operacional.

Revision ID: 0016_automacao_permissoes
Revises: 0015_automacao_schema
Create Date: 2026-08-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016_automacao_permissoes"
down_revision = "0015_automacao_schema"
branch_labels = None
depends_on = None

PERMISSOES_AUTOMACAO = (
    ("automacao.job.consultar", "Consultar jobs de automacao"),
    ("automacao.job.cancelar", "Cancelar jobs de automacao"),
    ("automacao.job.retry", "Repetir jobs de automacao"),
    ("notificacao.consultar", "Consultar notificacoes"),
    ("notificacao.conciliar", "Conciliar notificacoes"),
    ("notificacao.template.gerir", "Gerir templates de notificacao"),
)


def upgrade() -> None:
    bind = op.get_bind()
    for codigo, descricao in PERMISSOES_AUTOMACAO:
        bind.execute(
            sa.text(
                "INSERT INTO permissao (codigo, descricao) VALUES (:codigo, :descricao) "
                "ON CONFLICT (codigo) DO UPDATE SET descricao = EXCLUDED.descricao"
            ),
            {"codigo": codigo, "descricao": descricao},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for codigo, _ in PERMISSOES_AUTOMACAO:
        bind.execute(
            sa.text("DELETE FROM perfil_permissao WHERE permissao_codigo = :codigo"),
            {"codigo": codigo},
        )
        bind.execute(sa.text("DELETE FROM permissao WHERE codigo = :codigo"), {"codigo": codigo})
