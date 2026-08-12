import threading
import uuid
from types import SimpleNamespace
from typing import cast

import pytest

from emprestimo.application.scheduler import ClaimScheduler
from emprestimo.worker.scheduler_worker import WorkerSettings, _DaemonExecutor


def test_worker_valida_limites_de_concorrencia_e_batch() -> None:
    assert WorkerSettings(concurrency=4, batch_size=20).concurrency == 4
    with pytest.raises(ValueError, match="concurrency"):
        WorkerSettings(concurrency=0)
    with pytest.raises(ValueError, match="batch_size"):
        WorkerSettings(batch_size=101)
    with pytest.raises(ValueError, match="lease_renewal"):
        WorkerSettings(lease_renewal_seconds=0)
    with pytest.raises(ValueError, match="runtime"):
        WorkerSettings(lease_renewal_seconds=10, max_attempt_runtime_seconds=10)


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
