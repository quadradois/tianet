"""alarga status do audit_log de 20 para 40

Revision ID: c47f1a2b8e30
Revises: a2109be3d0df
Create Date: 2026-08-25 18:40:00.000000

IMP-350. `audit_log.status` era VARCHAR(20) e o vocabulario que a Application
grava ali ja passava disso: `ResultadoExecucao.RESULTADO_DESCONHECIDO` vale
`resultado_desconhecido`, 22 caracteres.

O `comprovante.py` contornava no call site, mapeando aquele caso para
`desconhecido` antes de auditar. O `notifications.py`, escrito depois, copiou o
padrao de auditoria e **nao** copiou o contorno — entao o caminho de resultado
desconhecido do aviso de sobra estourava a coluna com `DataError` e derrubava a
entrega. Ninguem viu porque o handler nao tinha teste.

Alargar a coluna resolve para todos os chamadores, presentes e futuros, em vez
de exigir que cada um lembre de um remendo. O contorno do comprovante sai junto.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c47f1a2b8e30"
down_revision: str | None = "a2109be3d0df"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "audit_log",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Reversivel enquanto nenhum registro passar de 20 caracteres. Depois do
    # upgrade, registros novos podem passar — o downgrade e para desfazer um
    # deploy recente, nao para voltar anos de trilha.
    op.alter_column(
        "audit_log",
        "status",
        existing_type=sa.String(length=40),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
