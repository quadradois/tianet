"""audit log append only

Revision ID: bb9262033324
Revises: d954b1907cad
Create Date: 2026-08-23 06:44:39.340170

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "bb9262033324"
down_revision: str | None = "d954b1907cad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("""
            CREATE FUNCTION reject_audit_log_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'audit_log is append-only: % is not allowed', TG_OP;
            END;
            $$
            """))
    op.execute(sa.text("""
            CREATE TRIGGER audit_log_append_only
            BEFORE UPDATE OR DELETE ON audit_log
            FOR EACH ROW
            EXECUTE FUNCTION reject_audit_log_mutation()
            """))


def downgrade() -> None:
    # Uma migration que precise alterar audit_log deve remover a protecao
    # explicitamente e recria-la depois; falhar sem isso e intencional.
    op.execute(sa.text("DROP TRIGGER audit_log_append_only ON audit_log"))
    op.execute(sa.text("DROP FUNCTION reject_audit_log_mutation()"))
