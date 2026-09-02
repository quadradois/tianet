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

# Dois nomes, porque duas geracoes de instalacao. O bootstrap atual cria
# `administrador_plataforma`; bancos migrados pelo `0008_iam_operacional` tem
# `administrador`, com a capitalizacao preservada — aquele arquivo compara com
# `casefold()`, e aqui vale o mesmo. Restringir a um so deixaria justamente a
# instalacao antiga sem as permissoes que esta migration existe para conceder.
PERFIS_ADMIN = ("administrador_plataforma", "administrador")
NOVAS_DESTA_MIGRATION = (
    ("whatsapp.conexao.ler", "Consultar a conexao de WhatsApp"),
    ("whatsapp.conexao.gerir", "Conectar e desconectar o WhatsApp"),
)
# Reparo do IMP-355, que entrou no catalogo sem migration. Separada porque o
# downgrade nao pode remove-la: ela pode preceder esta migration.
REPARO_IMP_355 = (("usuario.criar", "Criar Usuarios do Tenant"),)
NOVAS = NOVAS_DESTA_MIGRATION + REPARO_IMP_355


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
    """Remove SOMENTE as duas permissoes que esta migration introduziu.

    `usuario.criar` fica. Ela pode ja existir de antes — um banco inicializado
    pelo bootstrap depois do IMP-355 a tem —, e nesse caso o `ON CONFLICT` do
    upgrade nao criou nada. Apaga-la aqui tiraria capacidade que nao veio daqui,
    e um rollback quebraria `POST /iam/usuarios`.

    O preco e um vinculo que pode sobrar em perfil que nao o tinha. Sobrar
    permissao de um catalogo que ja a declara e menos grave que remover uma em
    uso, e a versao anterior do codigo continua reconhecendo o codigo.
    """
    bind = op.get_bind()
    for codigo, _ in NOVAS_DESTA_MIGRATION:
        bind.execute(
            sa.text("DELETE FROM perfil_permissao WHERE permissao_codigo = :codigo"),
            {"codigo": codigo},
        )
        bind.execute(sa.text("DELETE FROM permissao WHERE codigo = :codigo"), {"codigo": codigo})
