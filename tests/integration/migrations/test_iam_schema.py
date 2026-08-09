"""Testes de migration do schema IAM (IMP-085)."""

from __future__ import annotations

import uuid
from importlib import import_module
from typing import Any, cast

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine.reflection import Inspector

iam_schema = cast(Any, import_module("migrations.versions.0007_iam_schema"))
iam_operacional = cast(Any, import_module("migrations.versions.0008_iam_operacional"))


IAM_TABLES = {
    "credencial",
    "sessao",
    "permissao",
    "perfil_acesso",
    "perfil_permissao",
    "usuario_perfil",
}


def test_iam_schema_upgrade_e_downgrade(engine: Engine) -> None:
    schema = f"test_iam_{uuid.uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        conn.execute(text("""
                CREATE TABLE tenant (
                    id uuid PRIMARY KEY
                )
                """))
        conn.execute(text("""
                CREATE TABLE usuario (
                    id uuid PRIMARY KEY,
                    tenant_id uuid NOT NULL REFERENCES tenant(id)
                )
                """))

        context = MigrationContext.configure(conn)
        operations = Operations(context)
        op_original = iam_schema.op
        iam_schema.op = operations
        try:
            iam_schema.upgrade()
            inspector = inspect(conn)
            tabelas = set(inspector.get_table_names(schema=schema))

            assert tabelas >= IAM_TABLES
            assert _colunas(inspector, schema, "credencial") >= {
                "id",
                "usuario_id",
                "hash_credencial",
                "algoritmo",
                "criado_em",
                "atualizado_em",
            }
            assert _colunas(inspector, schema, "sessao") >= {
                "id",
                "usuario_id",
                "tenant_id",
                "refresh_token_hash",
                "expira_em",
                "criado_em",
                "revogado_em",
            }
            assert _colunas(inspector, schema, "perfil_acesso") >= {
                "id",
                "tenant_id",
                "nome",
                "estado",
                "criado_em",
                "atualizado_em",
            }
            assert _unique_constraints(inspector, schema, "credencial") >= {"uq_credencial_usuario"}
            assert _unique_constraints(inspector, schema, "sessao") >= {"uq_sessao_refresh_hash"}
            assert _unique_constraints(inspector, schema, "perfil_acesso") >= {
                "uq_perfil_tenant_nome"
            }

            iam_schema.downgrade()
            tabelas_apos_downgrade = set(inspect(conn).get_table_names(schema=schema))
            assert IAM_TABLES.isdisjoint(tabelas_apos_downgrade)
        finally:
            iam_schema.op = op_original
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))


def test_iam_operacional_upgrade_e_downgrade(engine: Engine) -> None:
    schema = f"test_iam_operacional_{uuid.uuid4().hex}"
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    admin_a_1 = uuid.uuid4()
    admin_a_2 = uuid.uuid4()
    operador_a = uuid.uuid4()
    manual_a = uuid.uuid4()
    admin_b = uuid.uuid4()
    operador_perfil_id = uuid.uuid4()
    manual_perfil_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        conn.execute(text("CREATE TABLE tenant (id uuid PRIMARY KEY)"))
        conn.execute(text("""
                CREATE TABLE usuario (
                    id uuid PRIMARY KEY,
                    tenant_id uuid NOT NULL REFERENCES tenant(id),
                    perfil_acesso varchar(50)
                )
                """))

        context = MigrationContext.configure(conn)
        operations = Operations(context)
        schema_op_original = iam_schema.op
        operacional_op_original = iam_operacional.op
        iam_schema.op = operations
        iam_operacional.op = operations
        try:
            iam_schema.upgrade()
            conn.execute(
                text("INSERT INTO tenant (id) VALUES (:tenant_a), (:tenant_b)"),
                {"tenant_a": tenant_a, "tenant_b": tenant_b},
            )
            conn.execute(
                text(
                    "INSERT INTO usuario (id, tenant_id, perfil_acesso) VALUES "
                    "(:admin_a_1, :tenant_a, 'administrador'), "
                    "(:admin_a_2, :tenant_a, 'administrador'), "
                    "(:operador_a, :tenant_a, 'operador'), "
                    "(:manual_a, :tenant_a, 'manual'), "
                    "(:admin_b, :tenant_b, 'administrador')"
                ),
                {
                    "admin_a_1": admin_a_1,
                    "admin_a_2": admin_a_2,
                    "operador_a": operador_a,
                    "manual_a": manual_a,
                    "admin_b": admin_b,
                    "tenant_a": tenant_a,
                    "tenant_b": tenant_b,
                },
            )
            conn.execute(
                text(
                    "INSERT INTO permissao (codigo, descricao) "
                    "VALUES ('custom.ler', 'Permissao preexistente')"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO perfil_acesso (id, tenant_id, nome, estado) VALUES "
                    "(:operador_id, :tenant_id, 'operador', 'ativo'), "
                    "(:manual_id, :tenant_id, 'manual', 'ativo')"
                ),
                {
                    "operador_id": operador_perfil_id,
                    "manual_id": manual_perfil_id,
                    "tenant_id": tenant_a,
                },
            )
            conn.execute(
                text(
                    "INSERT INTO perfil_permissao (perfil_id, permissao_codigo) "
                    "VALUES (:manual_id, 'custom.ler')"
                ),
                {"manual_id": manual_perfil_id},
            )
            conn.execute(
                text(
                    "INSERT INTO usuario_perfil (usuario_id, perfil_id) "
                    "VALUES (:usuario_id, :perfil_id)"
                ),
                {"usuario_id": manual_a, "perfil_id": manual_perfil_id},
            )

            iam_operacional.upgrade()
            inspector = inspect(conn)

            assert "token_ativacao" in inspector.get_table_names(schema=schema)
            assert "iam_0008_backfill" not in inspector.get_table_names(schema=schema)
            assert _colunas(inspector, schema, "token_ativacao") >= {
                "id",
                "usuario_id",
                "tenant_id",
                "token_hash",
                "expira_em",
                "criado_em",
                "utilizado_em",
            }
            assert {
                index["name"] for index in inspector.get_indexes("token_ativacao", schema=schema)
            } >= {
                "ix_token_ativacao_usuario_id",
                "ix_token_ativacao_tenant_id",
            }

            perfis = (
                conn.execute(text("SELECT id, tenant_id, nome FROM perfil_acesso")).mappings().all()
            )
            assert {(row["tenant_id"], row["nome"]) for row in perfis} == {
                (tenant_a, "administrador"),
                (tenant_a, "operador"),
                (tenant_a, "manual"),
                (tenant_b, "administrador"),
            }
            assert set(conn.execute(text("SELECT estado FROM perfil_acesso")).scalars()) == {
                "ativo"
            }

            vinculos: dict[uuid.UUID, uuid.UUID] = {
                row.usuario_id: row.perfil_id
                for row in conn.execute(text("SELECT usuario_id, perfil_id FROM usuario_perfil"))
            }
            perfil_por_tenant_nome = {(row["tenant_id"], row["nome"]): row["id"] for row in perfis}
            assert vinculos == {
                admin_a_1: perfil_por_tenant_nome[(tenant_a, "administrador")],
                admin_a_2: perfil_por_tenant_nome[(tenant_a, "administrador")],
                operador_a: operador_perfil_id,
                manual_a: manual_perfil_id,
                admin_b: perfil_por_tenant_nome[(tenant_b, "administrador")],
            }

            catalogo = {codigo for codigo, _ in iam_operacional.PERMISSOES_ADMIN_TENANT}
            for tenant_id in (tenant_a, tenant_b):
                permissoes_admin = set(
                    conn.execute(
                        text(
                            "SELECT permissao_codigo FROM perfil_permissao "
                            "WHERE perfil_id = :perfil_id"
                        ),
                        {"perfil_id": perfil_por_tenant_nome[(tenant_id, "administrador")]},
                    ).scalars()
                )
                assert permissoes_admin == catalogo

            iam_operacional.downgrade()
            tabelas = inspect(conn).get_table_names(schema=schema)
            assert "token_ativacao" not in tabelas
            assert "iam_0008_backfill" not in tabelas
            assert set(conn.execute(text("SELECT id FROM perfil_acesso")).scalars()) == {
                row["id"] for row in perfis
            }
            assert {
                row.usuario_id: row.perfil_id
                for row in conn.execute(text("SELECT usuario_id, perfil_id FROM usuario_perfil"))
            } == vinculos
            assert set(conn.execute(text("SELECT codigo FROM permissao")).scalars()) == {
                "custom.ler"
            } | {codigo for codigo, _ in iam_operacional.CATALOGO_PERMISSOES}

            iam_schema.downgrade()
        finally:
            iam_schema.op = schema_op_original
            iam_operacional.op = operacional_op_original
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))


def _colunas(inspector: Inspector, schema: str, tabela: str) -> set[str]:
    return {coluna["name"] for coluna in inspector.get_columns(tabela, schema=schema)}


def _unique_constraints(inspector: Inspector, schema: str, tabela: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(tabela, schema=schema)
        if constraint["name"] is not None
    }
