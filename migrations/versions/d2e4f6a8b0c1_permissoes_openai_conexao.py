"""permissoes openai.conexao.ler e openai.conexao.gerir

Revision ID: d2e4f6a8b0c1
Revises: c1d2e3f4a5b6
Create Date: 2026-09-09 23:55:00.000000

Concede leitura e gestão aos perfis administrativos já persistidos. Não cria
tabela nem persiste credencial OpenAI; a sessão pertence ao volume do agent.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2e4f6a8b0c1"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERFIS_ADMIN = ("administrador", "administrador_plataforma")
NOVAS = (
    ("openai.conexao.ler", "Consultar a conexao e os limites OpenAI"),
    ("openai.conexao.gerir", "Conectar e desconectar a conta OpenAI"),
)


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
