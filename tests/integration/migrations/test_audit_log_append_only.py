"""Garantia de append-only da trilha de auditoria no PostgreSQL (IMP-335)."""

from __future__ import annotations

import uuid
from importlib import import_module
from typing import Any, cast

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

audit_log_append_only = cast(
    Any,
    import_module("migrations.versions.bb9262033324_audit_log_append_only"),
)


def test_audit_log_rejeita_update_e_delete_diretos(engine: Engine) -> None:
    schema = f"test_audit_append_only_{uuid.uuid4().hex}"
    registro_id = uuid.uuid4()

    with engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET search_path TO "{schema}"'))
        conn.execute(
            text("CREATE TABLE audit_log (" "id uuid PRIMARY KEY, " "detalhes text NOT NULL" ")")
        )
        conn.commit()

        context = MigrationContext.configure(conn)
        operations = Operations(context)
        op_original = audit_log_append_only.op
        audit_log_append_only.op = operations
        try:
            audit_log_append_only.upgrade()
            conn.execute(
                text("INSERT INTO audit_log (id, detalhes) VALUES (:id, :detalhes)"),
                {"id": registro_id, "detalhes": "original"},
            )
            assert (
                conn.execute(
                    text("SELECT detalhes FROM audit_log WHERE id = :id"),
                    {"id": registro_id},
                ).scalar_one()
                == "original"
            )
            conn.commit()

            with pytest.raises(DBAPIError) as update_error:
                conn.execute(
                    text("UPDATE audit_log SET detalhes = 'alterado' WHERE id = :id"),
                    {"id": registro_id},
                )
            assert "audit_log is append-only: UPDATE is not allowed" in str(update_error.value.orig)
            conn.rollback()

            with pytest.raises(DBAPIError) as delete_error:
                conn.execute(
                    text("DELETE FROM audit_log WHERE id = :id"),
                    {"id": registro_id},
                )
            assert "audit_log is append-only: DELETE is not allowed" in str(delete_error.value.orig)
            conn.rollback()

            audit_log_append_only.downgrade()
            conn.execute(
                text("UPDATE audit_log SET detalhes = 'alterado' WHERE id = :id"),
                {"id": registro_id},
            )
            conn.execute(
                text("DELETE FROM audit_log WHERE id = :id"),
                {"id": registro_id},
            )
            assert conn.execute(text("SELECT COUNT(*) FROM audit_log")).scalar_one() == 0
            conn.commit()
        finally:
            audit_log_append_only.op = op_original
            if conn.in_transaction():
                conn.rollback()
            conn.execute(text("SET search_path TO public"))
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            conn.commit()
