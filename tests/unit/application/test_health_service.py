"""Testes do consumidor do heartbeat do worker (IMP-343, EPIC-008)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from emprestimo.application.health import HealthService


class _SessionFake:
    """Session minima: devolve a linha combinada e conta o SELECT 1 do banco."""

    def __init__(
        self,
        linha: tuple[str, datetime] | None,
        falhar: bool,
        *,
        falhar_no_heartbeat: bool = False,
    ) -> None:
        self._linha = linha
        self._falhar = falhar
        self._falhar_no_heartbeat = falhar_no_heartbeat

    def __enter__(self) -> _SessionFake:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, statement: Any) -> _SessionFake:
        if self._falhar:
            raise RuntimeError("banco indisponivel")
        if self._falhar_no_heartbeat and "scheduler_worker_heartbeat" in str(statement):
            raise ProgrammingError("SELECT ...", {}, Exception("relation does not exist"))
        return self

    def first(self) -> tuple[str, datetime] | None:
        return self._linha


def _servico(
    linha: tuple[str, datetime] | None = None,
    *,
    falhar: bool = False,
    falhar_no_heartbeat: bool = False,
) -> HealthService:
    def factory() -> Session:
        return cast(Session, _SessionFake(linha, falhar, falhar_no_heartbeat=falhar_no_heartbeat))

    return HealthService(factory)


def _agora(delta: timedelta = timedelta()) -> datetime:
    return datetime.now(UTC) - delta


def test_worker_batendo_ponto_deixa_a_api_healthy() -> None:
    report = _servico(("healthy", _agora(timedelta(seconds=5)))).verificar()

    assert report.status == "healthy"
    assert report.checks == {"database": "healthy", "worker": "healthy"}
    assert report.http_status == 200


def test_worker_degradado_degrada_a_api_sem_tirar_da_rotacao() -> None:
    report = _servico(("degraded", _agora(timedelta(seconds=5)))).verificar()

    assert report.status == "degraded"
    assert report.checks["worker"] == "degraded"
    assert report.http_status == 200, "503 tiraria a API do ar por um worker atrasado"


def test_heartbeat_velho_vale_menos_que_o_estado_que_carrega() -> None:
    report = _servico(("healthy", _agora(timedelta(minutes=30)))).verificar()

    assert report.checks["worker"] == "unhealthy"
    assert report.status == "degraded"


def test_worker_que_nunca_bateu_ponto_e_unhealthy() -> None:
    report = _servico(None).verificar()

    assert report.checks["worker"] == "unhealthy"
    assert report.status == "degraded"


def test_banco_fora_nao_inventa_veredito_sobre_o_worker() -> None:
    report = _servico(falhar=True).verificar()

    assert report.status == "unhealthy"
    assert report.checks == {"database": "unhealthy"}
    assert report.http_status == 503
    assert "worker" not in report.checks, "sem banco nao ha leitura de heartbeat"


def test_schema_faltando_acusa_o_banco_e_nao_o_worker() -> None:
    """IMP-343: migracao que nao rodou nao pode se disfarcar de worker parado."""
    report = _servico(falhar_no_heartbeat=True).verificar()

    assert report.checks == {"database": "unhealthy"}, "a culpa e do banco, nao do worker"
    assert report.status == "unhealthy"
    assert report.http_status == 503, "dependencia indisponivel, nao erro inesperado (500)"
