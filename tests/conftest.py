"""Fixtures de integração — PostgreSQL real (DATABASE_URL, padrão Docker Compose).

Schema criado/destruído por sessão de teste via Base.metadata; cada teste
inicia com as tabelas truncadas. O commit é controlado pelo Unit of Work
nos testes de aplicação (AD-001).
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.infrastructure.db import orm  # noqa: F401 — registra tabelas no metadata
from emprestimo.infrastructure.db.base import Base
from emprestimo.infrastructure.db.session import database_url

TABELAS_TRUNCATE = (
    "contato",
    "devedor",
    "idempotency_key",
    "audit_log",
    "usuario",
    "configuracao",
    "carteira",
    "tenant",
)

TABELAS_DROP = (
    "contato",
    "devedor",
    "idempotency_key",
    "audit_log",
    "usuario",
    "configuracao",
    "carteira",
    "tenant",
)


def _get_existing_tables(engine: Engine) -> set[str]:
    """Retorna conjunto de tabelas que existem no banco."""
    insp = inspect(engine)
    return set(insp.get_table_names())


@pytest.fixture(scope="session")
def engine() -> Engine:
    e = create_engine(database_url())
    Base.metadata.create_all(e)
    yield e
    # Drop tables in FK-respecting order to avoid FK constraint errors
    existing = _get_existing_tables(e)
    with e.begin() as conn:
        for tabela in TABELAS_DROP:
            if tabela in existing:
                conn.execute(sa.text(f"DROP TABLE IF EXISTS {tabela} CASCADE"))


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Session:
    s = session_factory()
    # Truncate only tables that exist in the database
    existing = _get_existing_tables(s.bind)
    truncate_list = [t for t in TABELAS_TRUNCATE if t in existing]
    if truncate_list:
        s.execute(sa.text(f"TRUNCATE TABLE {', '.join(truncate_list)} CASCADE"))
        s.commit()
    yield s
    s.rollback()
    s.close()
