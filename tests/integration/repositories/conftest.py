"""Fixtures de integração — PostgreSQL real (DATABASE_URL, padrão Docker Compose).

Schema criado/destruído por sessão de teste via Base.metadata; o commit é
feito explicitamente nos testes (o UoW pertence à fase de Aplicação).
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


@pytest.fixture(scope="session")
def engine() -> Engine:
    e = create_engine(database_url())
    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)


@pytest.fixture
def session(engine: Engine) -> Session:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    s = factory()
    s.execute(sa.text("TRUNCATE TABLE usuario, configuracao, carteira, tenant"))
    s.commit()
    yield s
    s.rollback()
    s.close()
