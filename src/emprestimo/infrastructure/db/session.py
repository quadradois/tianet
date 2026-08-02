"""Engine e session factory (SQLAlchemy 2.x) para o PostgreSQL.

A URL padrão reflete o Docker Compose; pode ser sobrescrita por
DATABASE_URL (ver .env.example). O Unit of Work e o controle transacional
pertencem à fase de Aplicação (IMP-014).
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg://emprestimo:emprestimo@localhost:5432/emprestimo"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def database_url() -> str:
    """URL do banco a partir de DATABASE_URL (ou padrão do Docker Compose)."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine() -> Engine:
    """Engine única do processo (lazy)."""
    global _engine
    if _engine is None:
        _engine = create_engine(database_url())
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Session factory única do processo (lazy)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def create_session() -> Session:
    """Cria uma nova sessão."""
    return get_session_factory()()
