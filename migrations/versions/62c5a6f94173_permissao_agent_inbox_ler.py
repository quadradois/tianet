"""permissao agent.inbox.ler

Revision ID: 62c5a6f94173
Revises: f6a7b8c9d0e1
Create Date: 2026-09-19 07:49:11.920504

S3: a tela /app/agent consulta resumo + recentes da inbox. Sem a linha em
banco inicializado, o operador tomaria 403 sem motivo aparente (IMP-367).
Somente leitura na v1: sem gerir.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "62c5a6f94173"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERFIS_ADMIN = ("administrador", "administrador_plataforma")
NOVAS = (("agent.inbox.ler", "Consultar a inbox do agente"),)


def upgrade() -> None:
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
