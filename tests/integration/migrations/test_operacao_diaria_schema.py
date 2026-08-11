"""Testes de migration do schema Operacao Diaria (IMP-174)."""

from __future__ import annotations

import uuid
from importlib import import_module
from typing import Any, cast

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine.reflection import Inspector

operacao_diaria_schema = cast(Any, import_module("migrations.versions.0013_operacao_diaria_schema"))

OPERACAO_DIARIA_TABLES = {
    "cobranca_caso",
    "cobranca_acao",
    "promessa_pagamento",
    "promessa_apropriacao",
    "agenda_item",
    "lembrete",
    "comunicacao_registro",
    "relatorio_operacional_cache",
}


def test_operacao_diaria_schema_upgrade_e_downgrade(engine: Engine) -> None:
    schema = f"test_operacao_diaria_{uuid.uuid4().hex}"
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
        conn.execute(text("CREATE TABLE emprestimo (id uuid PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE parcela (id uuid PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE pagamento (id uuid PRIMARY KEY)"))

        context = MigrationContext.configure(conn)
        operations = Operations(context)
        op_original = operacao_diaria_schema.op
        operacao_diaria_schema.op = operations
        try:
            operacao_diaria_schema.upgrade()
            inspector = inspect(conn)
            tabelas = set(inspector.get_table_names(schema=schema))

            assert tabelas >= OPERACAO_DIARIA_TABLES
            assert _colunas(inspector, schema, "cobranca_caso") >= {
                "id",
                "tenant_id",
                "carteira_id",
                "devedor_id",
                "emprestimo_id",
                "titulo",
                "estado",
                "total_pendente",
                "origem",
                "criado_em",
                "atualizado_em",
            }
            assert _colunas(inspector, schema, "cobranca_acao") >= {
                "id",
                "cobranca_caso_id",
                "tenant_id",
                "carteira_id",
                "devedor_id",
                "emprestimo_id",
                "criado_por_usuario_id",
                "tipo",
                "resultado",
                "parcela_id",
                "estado",
                "registrada_em",
            }
            assert _colunas(inspector, schema, "promessa_pagamento") >= {
                "id",
                "tenant_id",
                "carteira_id",
                "devedor_id",
                "emprestimo_id",
                "valor_declarado",
                "data_promessa",
                "estado",
                "observacao",
                "parcela_id",
                "criado_por_usuario_id",
                "criada_em",
                "atualizado_em",
            }
            assert _colunas(inspector, schema, "promessa_apropriacao") >= {
                "id",
                "promessa_id",
                "pagamento_id",
                "valor",
                "realizado_em",
                "parcela_id",
                "criada_em",
                "idempotencia",
            }
            assert _colunas(inspector, schema, "agenda_item") >= {
                "id",
                "tenant_id",
                "carteira_id",
                "devedor_id",
                "emprestimo_id",
                "titulo",
                "previsto_para",
                "estado",
                "criado_em",
                "atualizado_em",
                "usuario_solicitante_id",
            }
            assert _colunas(inspector, schema, "lembrete") >= {
                "id",
                "tenant_id",
                "carteira_id",
                "agenda_item_id",
                "horario",
                "enviado_por_usuario_id",
                "mensagem",
                "estado",
                "criado_em",
            }
            assert _colunas(inspector, schema, "comunicacao_registro") >= {
                "id",
                "tenant_id",
                "carteira_id",
                "devedor_id",
                "emprestimo_id",
                "responsavel_id",
                "canal",
                "resumo",
                "resultado",
                "ocorrido_em",
                "parcela_id",
                "cobranca_acao_id",
                "agenda_item_id",
            }
            assert _colunas(inspector, schema, "relatorio_operacional_cache") >= {
                "id",
                "tenant_id",
                "carteira_id",
                "janela_referencia",
                "familia_relatorio",
                "payload_json",
                "gerado_em",
            }

            assert _indexes(inspector, schema, "cobranca_caso") >= {
                "ix_cobranca_caso_tenant_id",
                "ix_cobranca_caso_estado",
            }
            assert _indexes(inspector, schema, "agenda_item") >= {
                "ix_agenda_item_estado",
                "ix_agenda_item_previsto_para",
            }
            assert _indexes(inspector, schema, "comunicacao_registro") >= {
                "ix_comunicacao_canal",
                "ix_comunicacao_ocorrido_em",
            }

            _unique = {
                constraint["name"]
                for constraint in inspector.get_unique_constraints(
                    "promessa_apropriacao", schema=schema
                )
            }
            assert "uq_promessa_pagamento_pagamento" in _unique
            _unique = {
                constraint["name"]
                for constraint in inspector.get_unique_constraints("cobranca_caso", schema=schema)
            }
            assert "uq_cobranca_caso_devedor" in _unique

            assert _foreign_keys(inspector, schema, "promessa_pagamento") >= {
                "tenant",
                "carteira",
                "devedor",
                "emprestimo",
                "usuario",
                "parcela",
            }
            assert _foreign_keys(inspector, schema, "lembrete") >= {"agenda_item", "usuario"}
            assert _foreign_keys(inspector, schema, "agenda_item") >= {
                "tenant",
                "carteira",
                "devedor",
                "emprestimo",
                "usuario",
            }

            operacao_diaria_schema.downgrade()
            tabelas_apos_downgrade = set(inspect(conn).get_table_names(schema=schema))
            assert OPERACAO_DIARIA_TABLES.isdisjoint(tabelas_apos_downgrade)
        finally:
            operacao_diaria_schema.op = op_original
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
