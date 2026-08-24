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

# 127.0.0.1 em vez de localhost de proposito: localhost resolve ::1 primeiro e
# espera o timeout inteiro antes de cair para IPv4, o que faz a suite parecer
# travada em vez de falhar (caveat 4.1 do handoff de 2026-08-20).
DEFAULT_DATABASE_URL = "postgresql+psycopg://emprestimo:emprestimo@127.0.0.1:5432/emprestimo"

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
