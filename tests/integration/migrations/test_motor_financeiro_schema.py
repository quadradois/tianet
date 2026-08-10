"""Testes de migration do schema Motor Financeiro (IMP-155)."""

from __future__ import annotations

import uuid
from importlib import import_module
from typing import Any, cast

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine.reflection import Inspector

motor_schema = cast(Any, import_module("migrations.versions.0011_motor_financeiro_schema"))

MOTOR_TABLES = {
    "emprestimo",
    "parcela",
    "pagamento",
    "memoria_calculo",
    "evento_financeiro",
}


def test_motor_financeiro_schema_upgrade_e_downgrade(engine: Engine) -> None:
    schema = f"test_motor_{uuid.uuid4().hex}"
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
        conn.execute(text("CREATE TABLE contrato_credito (id uuid PRIMARY KEY)"))

        context = MigrationContext.configure(conn)
        operations = Operations(context)
        op_original = motor_schema.op
        motor_schema.op = operations
        try:
            motor_schema.upgrade()
            inspector = inspect(conn)
            tabelas = set(inspector.get_table_names(schema=schema))

            assert tabelas >= MOTOR_TABLES
            assert _colunas(inspector, schema, "emprestimo") >= {
                "id",
                "tenant_id",
                "carteira_id",
                "devedor_id",
                "contrato_id",
                "estado",
                "principal_original",
                "moeda",
                "parametros_financeiros",
                "criado_em",
                "atualizado_em",
                "ultimo_processamento_em",
                "ultimo_pagamento_em",
                "proximo_vencimento_em",
                "quitado_em",
            }
            assert _colunas(inspector, schema, "parcela") >= {
                "id",
                "emprestimo_id",
                "numero",
                "vencimento",
                "valor_previsto",
                "principal",
                "juros",
                "encargos",
                "valor_liquidado",
                "periodo",
                "estado",
                "criada_em",
                "atualizada_em",
            }
            assert _colunas(inspector, schema, "pagamento") >= {
                "id",
                "emprestimo_id",
                "valor_recebido",
                "recebido_em",
                "valor_juros",
                "valor_amortizacao",
                "valor_encargos",
                "chave_idempotencia",
                "parcelas_liquidadas",
                "distribuicao",
                "usuario_id",
                "estado",
                "criado_em",
            }
            assert _colunas(inspector, schema, "memoria_calculo") >= {
                "id",
                "emprestimo_id",
                "pagamento_id",
                "tipo",
                "data_referencia",
                "entradas",
                "regra",
                "periodos",
                "passos",
                "arredondamentos",
                "resultados",
                "criado_em",
            }
            assert _colunas(inspector, schema, "evento_financeiro") >= {
                "id",
                "emprestimo_id",
                "tenant_id",
                "carteira_id",
                "devedor_id",
                "usuario_id",
                "memoria_calculo_id",
                "pagamento_id",
                "tipo",
                "estado_anterior",
                "estado_posterior",
                "valor",
                "detalhes",
                "ocorrido_em",
            }
            assert _indexes(inspector, schema, "emprestimo") >= {
                "ix_emprestimo_tenant_id",
                "ix_emprestimo_carteira_id",
                "ix_emprestimo_devedor_id",
                "ix_emprestimo_estado",
            }
            assert _indexes(inspector, schema, "parcela") >= {
                "ix_parcela_emprestimo_id",
                "ix_parcela_vencimento",
                "ix_parcela_estado",
            }
            assert _indexes(inspector, schema, "pagamento") >= {
                "ix_pagamento_emprestimo_id",
                "ix_pagamento_usuario_id",
                "ix_pagamento_recebido_em",
            }
            assert _indexes(inspector, schema, "memoria_calculo") >= {
                "ix_memoria_calculo_emprestimo_id",
                "ix_memoria_calculo_pagamento_id",
                "ix_memoria_calculo_tipo",
            }
            assert _indexes(inspector, schema, "evento_financeiro") >= {
                "ix_evento_financeiro_emprestimo_id",
                "ix_evento_financeiro_tenant_id",
                "ix_evento_financeiro_tipo",
            }
            assert {
                constraint["name"]
                for constraint in inspector.get_unique_constraints("emprestimo", schema=schema)
            } >= {"uq_emprestimo_contrato"}
            assert {
                constraint["name"]
                for constraint in inspector.get_unique_constraints("parcela", schema=schema)
            } >= {"uq_parcela_emprestimo_numero"}
            assert {
                constraint["name"]
                for constraint in inspector.get_unique_constraints("pagamento", schema=schema)
            } >= {"uq_pagamento_emprestimo_chave_idempotencia"}
            assert _foreign_keys(inspector, schema, "evento_financeiro") >= {
                "emprestimo",
                "tenant",
                "carteira",
                "devedor",
                "usuario",
                "memoria_calculo",
                "pagamento",
            }

            motor_schema.downgrade()
            tabelas_apos_downgrade = set(inspect(conn).get_table_names(schema=schema))
            assert MOTOR_TABLES.isdisjoint(tabelas_apos_downgrade)
        finally:
            motor_schema.op = op_original
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
