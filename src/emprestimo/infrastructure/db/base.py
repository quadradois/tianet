"""Base declarativa do SQLAlchemy — fonte única de metadados (Alembic)."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa do monólito modular."""


metadata = Base.metadata
