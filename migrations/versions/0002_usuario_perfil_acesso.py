"""add usuario.perfil_acesso

Revision ID: 0002_usuario_perfil_acesso
Revises: 0001_platform_credit
Create Date: 2026-08-02

Fase 2 (IMP-011): coluna de perfil de acesso do Usuário (DOMAIN-018 RN-002),
preenchida no provisionamento do primeiro Usuário Administrador.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_usuario_perfil_acesso"
down_revision: str | None = "0001_platform_credit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column("perfil_acesso", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usuario", "perfil_acesso")
