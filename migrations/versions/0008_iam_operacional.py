"""Completa persistencia operacional do IAM.

Revision ID: 0008_iam_operacional
Revises: 0007_iam_schema
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0008_iam_operacional"
down_revision = "0007_iam_schema"
branch_labels = None
depends_on = None


CATALOGO_PERMISSOES = (
    ("tenant.criar", "Provisionar Tenants"),
    ("tenant.ler", "Consultar Tenants"),
    ("tenant.atualizar", "Atualizar Tenants"),
    ("tenant.inativar", "Inativar Tenants"),
    ("tenant.reativar", "Reativar Tenants"),
    ("devedor.criar", "Criar Devedores"),
    ("devedor.ler", "Consultar Devedores"),
    ("devedor.atualizar", "Atualizar Devedores"),
    ("devedor.inativar", "Inativar Devedores"),
    ("devedor.reativar", "Reativar Devedores"),
    ("credencial.redefinir", "Redefinir credenciais"),
    ("perfil.gerir", "Gerir perfis e atribuicoes"),
    ("perfil.ler", "Consultar perfis e permissoes"),
)
PERMISSOES_ADMIN_TENANT = tuple(
    (codigo, descricao)
    for codigo, descricao in CATALOGO_PERMISSOES
    if not codigo.startswith("tenant.")
)


def upgrade() -> None:
    op.create_table(
        "token_ativacao",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("utilizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_token_ativacao_usuario_id"), "token_ativacao", ["usuario_id"])
    op.create_index(op.f("ix_token_ativacao_tenant_id"), "token_ativacao", ["tenant_id"])

    bind = op.get_bind()
    _semear_catalogo(bind)
    _migrar_perfis_legados(bind)


def downgrade() -> None:
    # O downgrade remove o schema introduzido por 0008. O backfill permanece nas
    # tabelas de 0007 para nao apagar perfis que possam ter sido alterados depois.
    op.drop_index(op.f("ix_token_ativacao_tenant_id"), table_name="token_ativacao")
    op.drop_index(op.f("ix_token_ativacao_usuario_id"), table_name="token_ativacao")
    op.drop_table("token_ativacao")


def _semear_catalogo(bind: sa.Connection) -> None:
    codigos_existentes = set(bind.execute(sa.text("SELECT codigo FROM permissao")).scalars())
    for codigo, descricao in CATALOGO_PERMISSOES:
        if codigo in codigos_existentes:
            continue
        bind.execute(
            sa.text("INSERT INTO permissao (codigo, descricao) VALUES (:codigo, :descricao)"),
            {"codigo": codigo, "descricao": descricao},
        )
        _registrar(bind, "permissao", codigo, permissao_codigo=codigo)


def _migrar_perfis_legados(bind: sa.Connection) -> None:
    pares = bind.execute(
        sa.text(
            "SELECT DISTINCT tenant_id, btrim(perfil_acesso) AS nome "
            "FROM usuario "
            "WHERE perfil_acesso IS NOT NULL AND btrim(perfil_acesso) <> ''"
        )
    ).mappings()

    for par in pares:
        tenant_id = par["tenant_id"]
        nome = par["nome"]
        perfil_id = bind.execute(
            sa.text(
                "SELECT id FROM perfil_acesso " "WHERE tenant_id = :tenant_id AND nome = :nome"
            ),
            {"tenant_id": tenant_id, "nome": nome},
        ).scalar_one_or_none()

        if perfil_id is None:
            perfil_id = uuid.uuid4()
            bind.execute(
                sa.text(
                    "INSERT INTO perfil_acesso (id, tenant_id, nome, estado) "
                    "VALUES (:id, :tenant_id, :nome, 'ativo')"
                ),
                {"id": perfil_id, "tenant_id": tenant_id, "nome": nome},
            )
            _registrar(bind, "perfil", str(perfil_id), perfil_id=perfil_id)

        usuarios = bind.execute(
            sa.text(
                "SELECT id FROM usuario "
                "WHERE tenant_id = :tenant_id AND btrim(perfil_acesso) = :nome"
            ),
            {"tenant_id": tenant_id, "nome": nome},
        ).scalars()
        for usuario_id in usuarios:
            vinculo = bind.execute(
                sa.text("SELECT perfil_id FROM usuario_perfil WHERE usuario_id = :usuario_id"),
                {"usuario_id": usuario_id},
            ).scalar_one_or_none()
            if vinculo is None:
                bind.execute(
                    sa.text(
                        "INSERT INTO usuario_perfil (usuario_id, perfil_id) "
                        "VALUES (:usuario_id, :perfil_id)"
                    ),
                    {"usuario_id": usuario_id, "perfil_id": perfil_id},
                )
                _registrar(
                    bind,
                    "usuario_perfil",
                    str(usuario_id),
                    perfil_id=perfil_id,
                    usuario_id=usuario_id,
                )

        if nome.casefold() == "administrador":
            _atribuir_catalogo_administrador(bind, perfil_id)


def _atribuir_catalogo_administrador(bind: sa.Connection, perfil_id: uuid.UUID) -> None:
    existentes = set(
        bind.execute(
            sa.text("SELECT permissao_codigo FROM perfil_permissao WHERE perfil_id = :perfil_id"),
            {"perfil_id": perfil_id},
        ).scalars()
    )
    for codigo, _ in PERMISSOES_ADMIN_TENANT:
        if codigo in existentes:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO perfil_permissao (perfil_id, permissao_codigo) "
                "VALUES (:perfil_id, :codigo)"
            ),
            {"perfil_id": perfil_id, "codigo": codigo},
        )
        _registrar(
            bind,
            "perfil_permissao",
            f"{perfil_id}:{codigo}",
            perfil_id=perfil_id,
            permissao_codigo=codigo,
        )


def _registrar(
    bind: sa.Connection,
    tipo: str,
    chave: str,
    *,
    perfil_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    permissao_codigo: str | None = None,
) -> None:
    del bind, tipo, chave, perfil_id, usuario_id, permissao_codigo
