"""Testes da migration de permissoes IAM do Motor Financeiro (IMP-163)."""

from __future__ import annotations

import uuid
from importlib import import_module
from typing import Any, cast

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Engine, text

motor_permissoes = cast(
    Any,
    import_module("migrations.versions.0012_motor_financeiro_permissoes"),
)


def test_motor_financeiro_permissoes_upgrade_e_downgrade(engine: Engine) -> None:
    schema = f"test_motor_permissoes_{uuid.uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        conn.execute(text("CREATE TABLE permissao (codigo text PRIMARY KEY, descricao text)"))
        conn.execute(text("""
                CREATE TABLE perfil_permissao (
                    perfil_id uuid NOT NULL,
                    permissao_codigo text NOT NULL REFERENCES permissao(codigo)
                )
                """))

        context = MigrationContext.configure(conn)
        operations = Operations(context)
        op_original = motor_permissoes.op
        motor_permissoes.op = operations
        try:
            motor_permissoes.upgrade()
            permissoes = set(conn.execute(text("SELECT codigo FROM permissao")).scalars())
            esperadas = {codigo for codigo, _ in motor_permissoes.PERMISSOES_MOTOR}
            assert permissoes == esperadas

            conn.execute(
                text(
                    "INSERT INTO perfil_permissao (perfil_id, permissao_codigo) "
                    "VALUES (:perfil_id, :codigo)"
                ),
                {
                    "perfil_id": uuid.uuid4(),
                    "codigo": "motor.emprestimo.criar",
                },
            )

            motor_permissoes.downgrade()

            assert set(conn.execute(text("SELECT codigo FROM permissao")).scalars()) == set()
            assert conn.execute(text("SELECT COUNT(*) FROM perfil_permissao")).scalar_one() == 0
        finally:
            motor_permissoes.op = op_original
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
