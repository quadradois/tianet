"""idempotency key unique por (chave, escopo)

Revision ID: 0005_idempotency_key_escopo
Revises: 0004_devedor_contato
Create Date: 2026-08-08

TASK-100: alinha a persistência ao contrato da AD-002. A identidade de um
registro de idempotência é o par ``(chave, escopo)``, não a chave sozinha — a
mesma chave em casos de uso distintos designa operações distintas.

A constraint anterior, ``UNIQUE(chave)``, permitia que um cadastro e uma
inativação com a mesma Idempotency-Key disputassem o mesmo registro, gerando
409 indevido. O campo ``escopo`` já existia e era gravado, mas não compunha nem
a busca nem a unicidade.

Downgrade reversível: restaura ``UNIQUE(chave)``. Atenção — se houver linhas com
a mesma chave em escopos diferentes (situação que esta migration passa a
permitir), o downgrade falhará por violação de unicidade; nesse caso é preciso
resolver os duplicados antes de reverter.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_idempotency_key_escopo"
down_revision: str | None = "0004_devedor_contato"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_idempotency_key_chave", "idempotency_key", type_="unique")
    op.create_unique_constraint(
        "uq_idempotency_key_chave_escopo",
        "idempotency_key",
        ["chave", "escopo"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_idempotency_key_chave_escopo", "idempotency_key", type_="unique")
    op.create_unique_constraint("uq_idempotency_key_chave", "idempotency_key", ["chave"])
