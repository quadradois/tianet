"""Testes de migration do schema Contratos (IMP-130)."""

from __future__ import annotations

import uuid
from importlib import import_module
from typing import Any, cast

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine.reflection import Inspector

contratos_schema = cast(Any, import_module("migrations.versions.0010_contratos_schema"))

CONTRATOS_TABLES = {"contrato_credito", "evento_contrato"}


def test_contratos_schema_upgrade_e_downgrade(engine: Engine) -> None:
    schema = f"test_contratos_{uuid.uuid4().hex}"
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
        conn.execute(text("CREATE TABLE proposta_comercial (id uuid PRIMARY KEY)"))

        context = MigrationContext.configure(conn)
        operations = Operations(context)
        op_original = contratos_schema.op
        contratos_schema.op = operations
        try:
            contratos_schema.upgrade()
            inspector = inspect(conn)
            tabelas = set(inspector.get_table_names(schema=schema))

            assert tabelas >= CONTRATOS_TABLES
            assert _colunas(inspector, schema, "contrato_credito") >= {
                "id",
                "tenant_id",
                "carteira_id",
                "devedor_id",
                "proposta_comercial_id",
                "criado_por_usuario_id",
                "estado",
                "parametros",
                "criado_em",
                "atualizado_em",
                "formalizado_por_usuario_id",
                "formalizado_em",
                "assinado_por_usuario_id",
                "assinado_em",
                "liberado_por_usuario_id",
                "liberado_em",
                "motivo_encerramento",
            }
            assert _colunas(inspector, schema, "evento_contrato") >= {
                "id",
                "contrato_id",
                "usuario_id",
                "tipo",
                "estado_anterior",
                "estado_posterior",
                "ordem",
                "motivo",
                "criado_em",
            }
            assert _indexes(inspector, schema, "contrato_credito") >= {
                "ix_contrato_credito_tenant_id",
                "ix_contrato_credito_carteira_id",
                "ix_contrato_credito_devedor_id",
                "ix_contrato_credito_estado",
            }
            assert _foreign_keys(inspector, schema, "evento_contrato") >= {
                "contrato_credito",
                "usuario",
            }
            assert {
                constraint["name"]
                for constraint in inspector.get_unique_constraints(
                    "contrato_credito", schema=schema
                )
            } >= {"uq_contrato_credito_proposta"}

            contratos_schema.downgrade()
            tabelas_apos_downgrade = set(inspect(conn).get_table_names(schema=schema))
            assert CONTRATOS_TABLES.isdisjoint(tabelas_apos_downgrade)
        finally:
            contratos_schema.op = op_original
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
