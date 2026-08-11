"""Permissoes IAM do Motor Financeiro.

Revision ID: 0012_motor_financeiro_permissoes
Revises: 0011_motor_financeiro_schema
Create Date: 2026-08-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_motor_financeiro_permissoes"
down_revision = "0011_motor_financeiro_schema"
branch_labels = None
depends_on = None


PERMISSOES_MOTOR = (
    ("motor.emprestimo.criar", "Criar emprestimos no Motor Financeiro"),
    ("motor.emprestimo.ler", "Consultar emprestimos no Motor Financeiro"),
    ("motor.parcela.gerar", "Gerar plano de parcelas no Motor Financeiro"),
    ("motor.parcela.ler", "Consultar parcelas no Motor Financeiro"),
    ("motor.pagamento.registrar", "Registrar pagamentos no Motor Financeiro"),
    ("motor.saldo.ler", "Consultar saldo financeiro"),
    ("motor.memoria.ler", "Consultar memoria de calculo financeira"),
    ("motor.quitacao.executar", "Executar quitacao financeira"),
    ("motor.renegociacao.criar", "Criar renegociacao financeira"),
)


def upgrade() -> None:
    bind = op.get_bind()
    for codigo, descricao in PERMISSOES_MOTOR:
        bind.execute(
            sa.text(
                "INSERT INTO permissao (codigo, descricao) "
                "VALUES (:codigo, :descricao) "
                "ON CONFLICT (codigo) DO UPDATE SET descricao = EXCLUDED.descricao"
            ),
            {"codigo": codigo, "descricao": descricao},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for codigo, _ in PERMISSOES_MOTOR:
        bind.execute(
            sa.text("DELETE FROM perfil_permissao WHERE permissao_codigo = :codigo"),
            {"codigo": codigo},
        )
        bind.execute(
            sa.text("DELETE FROM permissao WHERE codigo = :codigo"),
            {"codigo": codigo},
        )
