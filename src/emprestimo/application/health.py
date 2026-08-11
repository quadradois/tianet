"""Healthcheck operacional do backend (EPIC-008, IMP-191/192)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

HealthStatus = Literal["healthy", "degraded", "unhealthy"]


@dataclass(frozen=True)
class HealthReport:
    """Resultado minimo de saude operacional, sem dados sensiveis."""

    status: HealthStatus
    checks: dict[str, HealthStatus]

    @property
    def http_status(self) -> int:
        return 200 if self.status == "healthy" else 503


class HealthService:
    """Verifica dependencias tecnicas essenciais da API."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def verificar(self) -> HealthReport:
        database_status = self._verificar_database()
        status: HealthStatus = "healthy" if database_status == "healthy" else "unhealthy"
        return HealthReport(status=status, checks={"database": database_status})

    def _verificar_database(self) -> HealthStatus:
        try:
            with self._session_factory() as session:
                session.execute(text("SELECT 1"))
        except Exception:
            return "unhealthy"
        return "healthy"
