"""separa comercial.proposta.submeter de comercial.proposta.decidir

Revision ID: f3a81c62d94e
Revises: e91c4d7a2b58
Create Date: 2026-08-27 15:10:00.000000

IMP-360. `POST /credit/propostas-comerciais/{id}/enviar-para-analise` exigia
`comercial.proposta.decidir` — a mesma permissao de aprovar e recusar. Quem
podia submeter uma proposta podia aprova-la: nao havia segregacao entre propor e
decidir.

O defeito e anterior ao Copilot e existe para operadores humanos. A revisao
adversarial do PLAN-033 o encontrou ao verificar se a regra "o copilot nunca
aprova o que propos" tinha garantia tecnica — nao tinha, e a falta atingia todo
mundo.

**Migracao sem perda, e essa e a parte que exige cuidado:** todo perfil que hoje
tem `decidir` recebe `submeter` junto. Ninguem perde capacidade nesta migration.
A separacao passa a existir para perfis novos — como o `copilot`, que recebera
`submeter` e nunca `decidir`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a81c62d94e"
down_revision: str | None = "e91c4d7a2b58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CODIGO_SUBMETER = "comercial.proposta.submeter"
CODIGO_DECIDIR = "comercial.proposta.decidir"
DESCRICAO_SUBMETER = "Submeter propostas comerciais para analise"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO permissao (codigo, descricao) VALUES (:codigo, :descricao) "
            "ON CONFLICT (codigo) DO UPDATE SET descricao = EXCLUDED.descricao"
        ),
        {"codigo": CODIGO_SUBMETER, "descricao": DESCRICAO_SUBMETER},
    )
    # Sem esta linha, todo perfil que submetia perderia a capacidade no deploy.
    bind.execute(
        sa.text(
            "INSERT INTO perfil_permissao (perfil_id, permissao_codigo) "
            "SELECT perfil_id, :submeter FROM perfil_permissao "
            "WHERE permissao_codigo = :decidir "
            "ON CONFLICT DO NOTHING"
        ),
        {"submeter": CODIGO_SUBMETER, "decidir": CODIGO_DECIDIR},
    )


def downgrade() -> None:
    # Volta ao estado anterior: `decidir` sozinho autoriza submeter de novo,
    # entao remover o vinculo e a permissao nao tira capacidade de ninguem.
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM perfil_permissao WHERE permissao_codigo = :codigo"),
        {"codigo": CODIGO_SUBMETER},
    )
    bind.execute(
        sa.text("DELETE FROM permissao WHERE codigo = :codigo"), {"codigo": CODIGO_SUBMETER}
    )
