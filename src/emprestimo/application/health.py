"""Healthcheck operacional do backend (EPIC-008, IMP-191/192)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

HealthStatus = Literal["healthy", "degraded", "unhealthy"]

IDADE_MAXIMA_HEARTBEAT = timedelta(minutes=2)
"""Silencio tolerado do worker antes do heartbeat contar como parado (IMP-343).

Folga generosa sobre o intervalo de ciclo: um heartbeat atrasado por um ciclo
lento nao deve virar alarme.
"""


@dataclass(frozen=True)
class HealthReport:
    """Resultado minimo de saude operacional, sem dados sensiveis."""

    status: HealthStatus
    checks: dict[str, HealthStatus]

    @property
    def http_status(self) -> int:
        """`degraded` responde 200 de proposito (IMP-343).

        503 tira a API de rotacao. O worker parado degrada a operacao mas nao
        impede a API de servir; quem precisa da distincao le `checks`.
        """
        return 503 if self.status == "unhealthy" else 200


class HealthService:
    """Verifica dependencias tecnicas essenciais da API."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def verificar(self) -> HealthReport:
        database_status = self._verificar_database()
        if database_status != "healthy":
            # Sem banco nao ha como ler o heartbeat: nao invente um veredito.
            return HealthReport(status="unhealthy", checks={"database": database_status})
        try:
            worker_status = self._verificar_worker()
        except SQLAlchemyError:
            # O `SELECT 1` passou e esta consulta falhou: o banco esta no ar mas
            # sem o schema esperado — migracao que nao rodou. E defeito do banco,
            # nao worker parado, e por isso a culpa vai para `database`. Erro
            # classificado (503, dependencia indisponivel) em vez de 500 generico
            # ou de um `unhealthy` no worker que mandaria o diagnostico para o
            # lugar errado.
            return HealthReport(status="unhealthy", checks={"database": "unhealthy"})
        status: HealthStatus = "healthy" if worker_status == "healthy" else "degraded"
        return HealthReport(
            status=status,
            checks={"database": database_status, "worker": worker_status},
        )

    def _verificar_database(self) -> HealthStatus:
        try:
            with self._session_factory() as session:
                session.execute(text("SELECT 1"))
        except Exception:
            return "unhealthy"
        return "healthy"

    def _verificar_worker(self) -> HealthStatus:
        """Da consumidor ao heartbeat que o scheduler ja persistia (IMP-343).

        SQL cru pelo mesmo motivo de `_verificar_database`: a Application nao
        precisa do modelo ORM para ler duas colunas.

        **Nao trata excecao aqui, de proposito.** Aqui o banco ja respondeu ao
        `SELECT 1`, entao falha nesta consulta e defeito de schema — e nao
        worker parado. Devolver `unhealthy` faria um deploy incompleto parecer
        worker offline, mandando o diagnostico para o lugar errado. Quem
        classifica e `verificar`, que atribui a falha ao `database`.
        """
        with self._session_factory() as session:
            linha = session.execute(
                text(
                    "SELECT estado, ultimo_heartbeat_em "
                    "FROM scheduler_worker_heartbeat "
                    "ORDER BY ultimo_heartbeat_em DESC "
                    "LIMIT 1"
                )
            ).first()
        if linha is None:
            # Nenhum worker jamais bateu ponto: jobs agendados nao rodam.
            return "unhealthy"
        estado, ultimo_heartbeat_em = linha
        if _idade(ultimo_heartbeat_em) > IDADE_MAXIMA_HEARTBEAT:
            # Heartbeat velho vale menos que o estado que ele carrega.
            return "unhealthy"
        if estado == "healthy":
            return "healthy"
        if estado == "degraded":
            return "degraded"
        return "unhealthy"


def _idade(instante: datetime) -> timedelta:
    referencia = instante if instante.tzinfo else instante.replace(tzinfo=UTC)
    return datetime.now(UTC) - referencia
