"""comprovante de pagamento do devedor (IMP-390)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-22 23:10:00.000000

Aditiva. O binario fica em `bytea` de proposito: sao poucas imagens por mes,
e um bucket externo traria credencial, ciclo de vida e uma peca a mais para
manter — o backup do Postgres ja cobre este dado, que alias tem prazo de
validade curto (some na quitacao do emprestimo).

Unico em (emprestimo_id, sha256): o mesmo arquivo reenviado pelo devedor —
retry de rede, ou ele mandando duas vezes — converge para o mesmo registro.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERFIS_ADMIN = ("administrador", "administrador_plataforma")
NOVAS = (("comprovante.registrar", "Registrar comprovante de pagamento do Devedor"),)


def upgrade() -> None:
    op.create_table(
        "comprovante_pagamento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id"), nullable=False),
        sa.Column("emprestimo_id", sa.Uuid(), sa.ForeignKey("emprestimo.id"), nullable=False),
        sa.Column("devedor_id", sa.Uuid(), sa.ForeignKey("devedor.id"), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("tipo_midia", sa.String(40), nullable=False),
        sa.Column("tamanho", sa.Integer(), nullable=False),
        sa.Column("conteudo", sa.LargeBinary(), nullable=True),
        sa.Column("valor_extraido", sa.Numeric(18, 2), nullable=True),
        sa.Column("valor_informado", sa.Numeric(18, 2), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("pagamento_id", sa.Uuid(), sa.ForeignKey("pagamento.id"), nullable=True),
        sa.Column("motivo_recusa", sa.String(255), nullable=True),
        sa.Column("recebido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expurgado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("tamanho > 0", name="ck_comprovante_tamanho_positivo"),
    )
    op.create_index(
        "uq_comprovante_emprestimo_sha256",
        "comprovante_pagamento",
        ["emprestimo_id", "sha256"],
        unique=True,
    )
    op.create_index("ix_comprovante_tenant", "comprovante_pagamento", ["tenant_id"])
    op.create_index("ix_comprovante_devedor", "comprovante_pagamento", ["devedor_id"])
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
    op.drop_index("ix_comprovante_devedor", table_name="comprovante_pagamento")
    op.drop_index("ix_comprovante_tenant", table_name="comprovante_pagamento")
    op.drop_index("uq_comprovante_emprestimo_sha256", table_name="comprovante_pagamento")
    op.drop_table("comprovante_pagamento")
