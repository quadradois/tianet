import threading
import time
import uuid
from concurrent.futures import Future
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest

from emprestimo.application.scheduler import ClaimScheduler
from emprestimo.application.varredura_cobranca import AgendadorVarreduraCobranca
from emprestimo.worker.scheduler_worker import (
    SchedulerWorker,
    SemeadorDiarioCobranca,
    WorkerSettings,
    _DaemonExecutor,
)


def test_semeador_cria_no_maximo_um_lote_por_dia() -> None:
    instante = [datetime(2026, 8, 22, 8, 0, tzinfo=UTC)]
    chamadas: list[tuple[object, object]] = []
    agendador = cast(
        AgendadorVarreduraCobranca,
        SimpleNamespace(
            agendar_dia=lambda **dados: chamadas.append(
                (dados["data_referencia"], dados["executar_em"])
            )
        ),
    )
    semeador = SemeadorDiarioCobranca(agendador, agora=lambda: instante[0])

    semeador.semear()
    semeador.semear()
    instante[0] += timedelta(days=1)
    semeador.semear()

    assert [item[0] for item in chamadas] == [
        datetime(2026, 8, 22, tzinfo=UTC).date(),
        datetime(2026, 8, 23, tzinfo=UTC).date(),
    ]


def test_worker_valida_limites_de_concorrencia_e_batch() -> None:
    settings = WorkerSettings()
    assert settings.poll_interval_seconds == 1
    assert settings.batch_size == 4
    assert settings.concurrency == 4
    assert settings.lease_seconds == 60
    assert settings.lease_renewal_seconds == 20
    assert settings.graceful_shutdown_seconds == 30
    assert settings.max_attempt_runtime_seconds == 300

    assert WorkerSettings(concurrency=4, batch_size=16).concurrency == 4
    with pytest.raises(ValueError, match="concurrency"):
        WorkerSettings(concurrency=0)
    with pytest.raises(ValueError, match="batch_size"):
        WorkerSettings(batch_size=17)
    with pytest.raises(ValueError, match="lease_renewal"):
        WorkerSettings(lease_renewal_seconds=0)
    with pytest.raises(ValueError, match="lease_renewal"):
        WorkerSettings(lease_seconds=30, lease_renewal_seconds=11)
    with pytest.raises(ValueError, match="max_attempt_runtime"):
        WorkerSettings(max_attempt_runtime_seconds=29)


def test_worker_carrega_contrato_operacional_da_adr_007(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCHEDULER_POLL_INTERVAL_SECONDS", "3")
    monkeypatch.setenv("SCHEDULER_BATCH_SIZE", "8")
    monkeypatch.setenv("SCHEDULER_CONCURRENCY", "6")
    monkeypatch.setenv("SCHEDULER_LEASE_SECONDS", "90")
    monkeypatch.setenv("SCHEDULER_LEASE_RENEW_SECONDS", "30")
    monkeypatch.setenv("SCHEDULER_SHUTDOWN_GRACE_SECONDS", "45")
    monkeypatch.setenv("SCHEDULER_MAX_ATTEMPT_RUNTIME_SECONDS", "600")

    settings = WorkerSettings.from_env()

    assert settings.poll_interval_seconds == 3
    assert settings.batch_size == 8
    assert settings.concurrency == 6
    assert settings.lease_seconds == 90
    assert settings.lease_renewal_seconds == 30
    assert settings.graceful_shutdown_seconds == 45
    assert settings.max_attempt_runtime_seconds == 600


def test_executor_nao_impede_shutdown_apos_grace_period() -> None:
    liberar = threading.Event()
    execution_id = uuid.uuid4()

    def bloquear(_: ClaimScheduler) -> None:
        liberar.wait(1)

    claim = cast(
        ClaimScheduler,
        SimpleNamespace(tentativa=SimpleNamespace(execution_id=execution_id)),
    )
    executor = _DaemonExecutor()

    executor.submit(bloquear, claim)
    thread = next(
        item for item in threading.enumerate() if item.name == f"scheduler-{execution_id}"
    )
    executor.shutdown(cancel_futures=True)

    assert thread.daemon
    liberar.set()


def test_supervisor_registra_future_com_excecao_como_unhealthy() -> None:
    claim = cast(
        ClaimScheduler,
        SimpleNamespace(
            job=SimpleNamespace(tipo="teste", id=uuid.uuid4(), correlation_id="corr-test"),
            tentativa=SimpleNamespace(execution_id=uuid.uuid4()),
        ),
    )
    future: Future[None] = Future()
    future.set_exception(RuntimeError("falha de persistencia"))
    worker = SchedulerWorker(
        cast(Any, SimpleNamespace()),
        {},
        WorkerSettings(),
    )
    instante = time.monotonic()
    worker._futures[future] = (claim, instante, instante)

    worker._supervise()

    assert worker._supervisor_unhealthy
    assert future not in worker._futures
