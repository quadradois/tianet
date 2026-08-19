"""Remove o plano de parcelas (DR-004, PLAN-030).

O emprestimo deixou de ser um plano de parcelas e passou a ser livre, com
acerto mensal no dia combinado: o devedor deve, no minimo, os juros do periodo
sobre o saldo devedor, e amortiza quando puder.

Esta migracao **e destrutiva**, ao contrario da regra "aditivas apenas" do
repositorio. A excecao esta autorizada na DR-004 e se sustenta em que o raio de
estrago e zero — o sistema nunca foi implantado, e o dado local e de teste.
Manter a tabela vazia deixaria exatamente o legado que a decisao mandou nao
deixar: alguem a encontraria depois, presumiria proposito e reintroduziria o
conceito. Ver PLAN-030 secao 5.1.

O downgrade recria a estrutura. O que ele nao devolve e dado, e nao ha dado a
devolver.

Revision ID: 0017_remove_plano_de_parcelas
Revises: 0016_automacao_permissoes
Create Date: 2026-08-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_remove_plano_de_parcelas"
down_revision = "0016_automacao_permissoes"
branch_labels = None
depends_on = None

# Tabelas que referenciavam a parcela. A coluna sai junto com a chave: sem a
# parcela ela nao teria a que se referir, e permaneceria sempre nula.
REFERENTES = (
    ("cobranca_acao", "cobranca_acao_parcela_id_fkey"),
    ("comunicacao_registro", "comunicacao_registro_parcela_id_fkey"),
    ("promessa_apropriacao", "promessa_apropriacao_parcela_id_fkey"),
    ("promessa_pagamento", "promessa_pagamento_parcela_id_fkey"),
)

PERMISSOES_REMOVIDAS = ("motor.parcela.gerar", "motor.parcela.ler")


def upgrade() -> None:
    for tabela, restricao in REFERENTES:
        op.drop_constraint(restricao, tabela, type_="foreignkey")
        op.drop_column(tabela, "parcela_id")

    op.drop_table("parcela")

    # As permissoes perdem objeto: nao ha mais parcela para gerar nem ler.
    perfil_permissao = sa.table(
        "perfil_permissao",
        sa.column("permissao_codigo", sa.String),
    )
    permissao = sa.table("permissao", sa.column("codigo", sa.String))
    op.execute(
        perfil_permissao.delete().where(
            perfil_permissao.c.permissao_codigo.in_(PERMISSOES_REMOVIDAS)
        )
    )
    op.execute(permissao.delete().where(permissao.c.codigo.in_(PERMISSOES_REMOVIDAS)))


def downgrade() -> None:
    op.create_table(
        "parcela",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("emprestimo_id", sa.Uuid(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("vencimento", sa.Date(), nullable=False),
        sa.Column("valor_previsto", sa.Numeric(18, 2), nullable=False),
        sa.Column("principal", sa.Numeric(18, 2), nullable=False),
        sa.Column("juros", sa.Numeric(18, 2), nullable=False),
        sa.Column("encargos", sa.Numeric(18, 2), nullable=False),
        sa.Column("valor_liquidado", sa.Numeric(18, 2), nullable=False),
        sa.Column("estado", sa.String(length=40), nullable=False),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fim", sa.Date(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["emprestimo_id"], ["emprestimo.id"]),
        sa.UniqueConstraint("emprestimo_id", "numero", name="parcela_emprestimo_numero_uk"),
    )
    for tabela, restricao in REFERENTES:
        op.add_column(tabela, sa.Column("parcela_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(restricao, tabela, "parcela", ["parcela_id"], ["id"])

    permissao = sa.table(
        "permissao",
        sa.column("codigo", sa.String),
        sa.column("descricao", sa.String),
    )
    op.bulk_insert(
        permissao,
        [
            {"codigo": "motor.parcela.gerar", "descricao": "Gerar plano de parcelas"},
            {"codigo": "motor.parcela.ler", "descricao": "Consultar parcelas"},
        ],
    )
