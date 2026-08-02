"""Fixtures de integração — PostgreSQL real (DATABASE_URL, padrão Docker Compose).

Schema criado/destruído por sessão de teste via Base.metadata; cada teste
inicia com as tabelas truncadas. O commit é controlado pelo Unit of Work
nos testes de aplicação (AD-001).
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.infrastructure.db import orm  # noqa: F401 — registra tabelas no metadata
from emprestimo.infrastructure.db.base import Base
from emprestimo.infrastructure.db.session import database_url

TABELAS_TRUNCATE = (
    "idempotency_key",
    "audit_log",
    "usuario",
    "configuracao",
    "carteira",
    "tenant",
)


@pytest.fixture(scope="session")
def engine() -> Engine:
    e = create_engine(database_url())
    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Session:
    s = session_factory()
    s.execute(sa.text(f"TRUNCATE TABLE {', '.join(TABELAS_TRUNCATE)}"))
    s.commit()
    yield s
    s.rollback()
    s.close()
