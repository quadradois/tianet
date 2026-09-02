"""permissoes whatsapp.conexao.ler e whatsapp.conexao.gerir

Revision ID: b58e3f21c4d7
Revises: a7c3e5f19d82
Create Date: 2026-09-02 12:00:00.000000

IMP-367. Acrescentar codigos ao `CATALOGO_PERMISSOES` alcanca apenas o catalogo
em memoria e o bootstrap de um banco novo. `AutorizacaoService.exigir_permissao`
consulta o **perfil persistido** — entao, num banco ja inicializado, o operador
tomaria 403 nas rotas do PLAN-034 sem que nada indicasse o motivo.

Concede as duas ao perfil `administrador_plataforma`, coerente com a decisao do
fundador em 2026-08-27 (`bootstrap_plataforma`): o sistema e de uso pessoal, com
um Tenant e um usuario, e separar papeis so produziria o deadlock que o IMP-363
corrigiu.

**Inclui `usuario.criar`, do IMP-355.** Aquele item entrou no catalogo sem
migration, e a mesma lacuna existe la: em banco ja inicializado, `POST
/iam/usuarios` responde 403. Uma linha aqui evita repetir a investigacao depois.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b58e3f21c4d7"
down_revision: str | None = "a7c3e5f19d82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERFIL_ADMIN = "administrador_plataforma"
NOVAS = (
    ("whatsapp.conexao.ler", "Consultar a conexao de WhatsApp"),
    ("whatsapp.conexao.gerir", "Conectar e desconectar o WhatsApp"),
    ("usuario.criar", "Criar Usuarios do Tenant"),
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
                "SELECT id, :codigo FROM perfil_acesso WHERE nome = :perfil "
                "ON CONFLICT DO NOTHING"
            ),
            {"codigo": codigo, "perfil": PERFIL_ADMIN},
        )


def downgrade() -> None:
    # Aditivo puro: remover os vinculos e os codigos devolve o estado anterior.
    # `usuario.criar` sai junto — antes desta migration ele nao existia no banco,
    # ainda que existisse no catalogo em memoria.
    bind = op.get_bind()
    for codigo, _ in NOVAS:
        bind.execute(
            sa.text("DELETE FROM perfil_permissao WHERE permissao_codigo = :codigo"),
            {"codigo": codigo},
        )
        bind.execute(sa.text("DELETE FROM permissao WHERE codigo = :codigo"), {"codigo": codigo})
