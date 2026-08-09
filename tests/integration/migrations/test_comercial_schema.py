"""Testes de migration do schema Comercial (IMP-110)."""

from __future__ import annotations

import uuid
from importlib import import_module
from typing import Any, cast

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine.reflection import Inspector

comercial_schema = cast(Any, import_module("migrations.versions.0009_comercial_schema"))

COMERCIAL_TABLES = {
    "simulacao_comercial",
    "proposta_comercial",
    "decisao_comercial",
}


def test_comercial_schema_upgrade_e_downgrade(engine: Engine) -> None:
    schema = f"test_comercial_{uuid.uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        conn.execute(text("CREATE TABLE tenant (id uuid PRIMARY KEY)"))
        conn.execute(text("""
                CREATE TABLE usuario (
                    id uuid PRIMARY KEY,
                    tenant_id uuid NOT NULL REFERENCES tenant(id)
                )
                """))
        conn.execute(text("""
                CREATE TABLE carteira (
                    id uuid PRIMARY KEY,
                    tenant_id uuid NOT NULL REFERENCES tenant(id)
                )
                """))
        conn.execute(text("""
                CREATE TABLE devedor (
                    id uuid PRIMARY KEY,
                    carteira_id uuid NOT NULL REFERENCES carteira(id)
                )
                """))

        context = MigrationContext.configure(conn)
        operations = Operations(context)
        op_original = comercial_schema.op
        comercial_schema.op = operations
        try:
            comercial_schema.upgrade()
            inspector = inspect(conn)
            tabelas = set(inspector.get_table_names(schema=schema))

            assert tabelas >= COMERCIAL_TABLES
            assert _colunas(inspector, schema, "simulacao_comercial") >= {
                "id",
                "tenant_id",
                "carteira_id",
                "devedor_id",
                "criada_por_usuario_id",
                "parametros",
                "criado_em",
            }
            assert _colunas(inspector, schema, "proposta_comercial") >= {
                "id",
                "tenant_id",
                "carteira_id",
                "devedor_id",
                "criada_por_usuario_id",
                "simulacao_id",
                "estado",
                "parametros",
                "criado_em",
                "atualizado_em",
                "aprovada_por_usuario_id",
                "aprovada_em",
            }
            assert _colunas(inspector, schema, "decisao_comercial") >= {
                "id",
                "proposta_id",
                "usuario_id",
                "estado_anterior",
                "estado_posterior",
                "ordem",
                "motivo",
                "criado_em",
            }
            assert _indexes(inspector, schema, "proposta_comercial") >= {
                "ix_proposta_comercial_tenant_id",
                "ix_proposta_comercial_carteira_id",
                "ix_proposta_comercial_devedor_id",
                "ix_proposta_comercial_estado",
            }
            assert _foreign_keys(inspector, schema, "decisao_comercial") >= {
                "proposta_comercial",
                "usuario",
            }

            comercial_schema.downgrade()
            tabelas_apos_downgrade = set(inspect(conn).get_table_names(schema=schema))
            assert COMERCIAL_TABLES.isdisjoint(tabelas_apos_downgrade)
        finally:
            comercial_schema.op = op_original
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))


def _colunas(inspector: Inspector, schema: str, tabela: str) -> set[str]:
    return {coluna["name"] for coluna in inspector.get_columns(tabela, schema=schema)}


def _indexes(inspector: Inspector, schema: str, tabela: str) -> set[str]:
    return {
        index["name"]
        for index in inspector.get_indexes(tabela, schema=schema)
        if index["name"] is not None
    }


def _foreign_keys(inspector: Inspector, schema: str, tabela: str) -> set[str]:
    return {
        fk["referred_table"]
        for fk in inspector.get_foreign_keys(tabela, schema=schema)
        if fk["referred_table"] is not None
    }
