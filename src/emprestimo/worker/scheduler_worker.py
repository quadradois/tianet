"""Worker Scheduler executado em processo separado da API."""

from __future__ import annotations

import logging
import os
import signal
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.application.notifications import FakeNotificationChannel, NotificationService
from emprestimo.application.scheduler import ClaimScheduler, ResultadoExecucao, SchedulerService
from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.infrastructure.db.orm import JobAgendadoORM, SchedulerWorkerHeartbeatORM
from emprestimo.infrastructure.db.session import database_url
from emprestimo.infrastructure.notifications import ResendNotificationChannel
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)
Handler = Callable[[ClaimScheduler], ResultadoExecucao]


class _DaemonExecutor:
    """Executor minimo cujos handlers nao prolongam o processo apos o grace period."""

    def __init__(self) -> None:
        self._futures: set[Future[None]] = set()

    def submit(self, func: Callable[[ClaimScheduler], None], claim: ClaimScheduler) -> Future[None]:
        future: Future[None] = Future()

        def executar() -> None:
            if not future.set_running_or_notify_cancel():
                return
            try:
                func(claim)
                future.set_result(None)
            except BaseException as exc:
                future.set_exception(exc)

        thread = threading.Thread(
            target=executar,
            name=f"scheduler-{claim.tentativa.execution_id}",
            daemon=True,
        )
        self._futures.add(future)
        thread.start()
        return future

    def shutdown(self, *, cancel_futures: bool) -> None:
        if cancel_futures:
            for future in self._futures:
                future.cancel()


@dataclass(frozen=True)
class WorkerSettings:
    concurrency: int = 4
    batch_size: int = 20
    poll_interval_seconds: float = 2.0
    heartbeat_seconds: float = 10.0
    graceful_shutdown_seconds: float = 30.0
    lease_renewal_seconds: float = 10.0
    max_attempt_runtime_seconds: float = 120.0

    def __post_init__(self) -> None:
        if self.concurrency < 1 or self.concurrency > 32:
            raise ValueError("concurrency deve estar entre 1 e 32")
        if self.batch_size < 1 or self.batch_size > 100:
            raise ValueError("batch_size deve estar entre 1 e 100")
        if self.lease_renewal_seconds <= 0:
            raise ValueError("lease_renewal_seconds deve ser positivo")
        if self.max_attempt_runtime_seconds <= self.lease_renewal_seconds:
            raise ValueError("max_attempt_runtime_seconds deve exceder a renovacao")

    @classmethod
    def from_env(cls) -> WorkerSettings:
        return cls(
            concurrency=int(os.environ.get("SCHEDULER_CONCURRENCY", "4")),
            batch_size=int(os.environ.get("SCHEDULER_BATCH_SIZE", "20")),
            poll_interval_seconds=float(os.environ.get("SCHEDULER_POLL_SECONDS", "2")),
            lease_renewal_seconds=float(os.environ.get("SCHEDULER_LEASE_RENEW_SECONDS", "10")),
            max_attempt_runtime_seconds=float(
                os.environ.get("SCHEDULER_MAX_ATTEMPT_RUNTIME_SECONDS", "120")
            ),
        )


def avaliar_estado_worker(*, lag_segundos: int, ciclos_lag: int, falha_supervisor: bool) -> str:
    if falha_supervisor:
        return "unhealthy"
    if lag_segundos > 60 and ciclos_lag >= 3:
        return "degraded"
    return "healthy"


class SchedulerWorker:
    def __init__(
        self,
        service: SchedulerService,
        handlers: dict[str, Handler],
        settings: WorkerSettings,
        *,
        heartbeat: Callable[[int, bool], None] | None = None,
    ) -> None:
        self._service = service
        self._handlers = handlers
        self._settings = settings
        self._heartbeat = heartbeat or (lambda _ativos, _falha: None)
        self._stop = threading.Event()
        self._executor = _DaemonExecutor()
        self._futures: dict[Future[None], tuple[ClaimScheduler, float, float]] = {}
        self._last_heartbeat = 0.0
        self._supervisor_unhealthy = False

    def run(self) -> None:
        while not self._stop.is_set():
            self.cycle()
            self._stop.wait(self._settings.poll_interval_seconds)
        self._drain()

    def cycle(self) -> int:
        self._supervise()
        slots = self._settings.concurrency - len(self._futures)
        claims = self._service.reivindicar(
            slots_livres=slots,
            batch_size=self._settings.batch_size,
        )
        for claim in claims:
            future = self._executor.submit(self._execute, claim)
            iniciado = time.monotonic()
            self._futures[future] = (claim, iniciado, iniciado)
        agora = time.monotonic()
        if agora - self._last_heartbeat >= self._settings.heartbeat_seconds:
            self._heartbeat(len(self._futures), self._supervisor_unhealthy)
            self._last_heartbeat = agora
        return len(claims)

    def stop(self) -> None:
        self._stop.set()
        for claim, _, _ in self._futures.values():
            claim.cancelamento.set()

    def _execute(self, claim: ClaimScheduler) -> None:
        handler = self._handlers.get(claim.job.tipo)
        if handler is None:
            self._service.finalizar(
                claim,
                ResultadoExecucao.FALHA_PERMANENTE,
                erro_codigo="handler_ausente",
            )
            return
        try:
            resultado = handler(claim)
        except Exception:
            logger.exception(
                "scheduler_handler_failed",
                extra={
                    "job_id": str(claim.job.id),
                    "execution_id": str(claim.tentativa.execution_id),
                    "correlation_id": claim.job.correlation_id,
                },
            )
            resultado = ResultadoExecucao.FALHA_TEMPORARIA
        if resultado is not ResultadoExecucao.FINALIZADO:
            self._service.finalizar(claim, resultado)

    def _supervise(self) -> None:
        agora = time.monotonic()
        ativos: dict[Future[None], tuple[ClaimScheduler, float, float]] = {}
        for future, (claim, iniciado, ultima_renovacao) in self._futures.items():
            if future.done():
                continue
            duracao = agora - iniciado
            if duracao >= self._settings.max_attempt_runtime_seconds:
                claim.cancelamento.set()
                self._supervisor_unhealthy = True
                ativos[future] = (claim, iniciado, ultima_renovacao)
                continue
            if agora - ultima_renovacao >= self._settings.lease_renewal_seconds:
                if not self._service.renovar(claim):
                    claim.cancelamento.set()
                    self._supervisor_unhealthy = True
                ultima_renovacao = agora
            ativos[future] = (claim, iniciado, ultima_renovacao)
        self._futures = ativos

    def _drain(self) -> None:
        limite = time.monotonic() + self._settings.graceful_shutdown_seconds
        while self._futures and time.monotonic() < limite:
            self._supervise()
            time.sleep(0.05)
        self._executor.shutdown(cancel_futures=True)


class HeartbeatStore:
    def __init__(self, worker_id: str, session_factory: sessionmaker[Session]) -> None:
        self._worker_id = worker_id
        self._session_factory = session_factory
        self._ciclos_lag = 0

    def registrar(
        self, em_execucao: int, *, concorrencia: int, falha_supervisor: bool = False
    ) -> None:
        with self._session_factory() as session:
            agora = session.scalar(select(func.clock_timestamp())) or datetime.now(UTC)
            mais_antigo = session.scalar(
                select(func.min(JobAgendadoORM.proxima_execucao_em)).where(
                    JobAgendadoORM.estado.in_(["agendado", "falha_temporaria"]),
                    JobAgendadoORM.proxima_execucao_em <= func.clock_timestamp(),
                )
            )
            lag = max(0, int((agora - mais_antigo).total_seconds())) if mais_antigo else 0
            self._ciclos_lag = self._ciclos_lag + 1 if lag > 60 else 0
            session.merge(
                SchedulerWorkerHeartbeatORM(
                    worker_id=self._worker_id,
                    estado=avaliar_estado_worker(
                        lag_segundos=lag,
                        ciclos_lag=self._ciclos_lag,
                        falha_supervisor=falha_supervisor,
                    ),
                    concorrencia=concorrencia,
                    em_execucao=em_execucao,
                    ultimo_heartbeat_em=agora,
                    lag_segundos=lag,
                )
            )
            session.execute(
                delete(SchedulerWorkerHeartbeatORM).where(
                    SchedulerWorkerHeartbeatORM.ultimo_heartbeat_em < agora - timedelta(hours=24)
                )
            )
            session.commit()


def main() -> None:
    settings = WorkerSettings.from_env()
    engine = create_engine(
        database_url(),
        pool_size=settings.concurrency + 2,
        max_overflow=0,
        pool_pre_ping=True,
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    service = SchedulerService(lambda: SqlAlchemyUnitOfWork(session_factory))
    api_key = os.environ.get("RESEND_API_KEY")
    remetente = os.environ.get("RESEND_FROM")
    if api_key and remetente:
        channel: NotificationChannel = ResendNotificationChannel(
            api_key=api_key, remetente=remetente
        )
    elif os.environ.get("APP_ENV", "development") == "production":
        raise RuntimeError("RESEND_API_KEY e RESEND_FROM sao obrigatorios em producao")
    else:
        channel = FakeNotificationChannel()
    notifications = NotificationService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        channel,
    )
    worker_id = f"scheduler-{uuid.uuid4()}"
    heartbeat = HeartbeatStore(worker_id, session_factory)
    worker = SchedulerWorker(
        service,
        handlers={"enviar_lembrete": notifications.processar_lembrete},
        settings=settings,
        heartbeat=lambda ativos, falha: heartbeat.registrar(
            ativos,
            concorrencia=settings.concurrency,
            falha_supervisor=falha,
        ),
    )
    signal.signal(signal.SIGTERM, lambda *_: worker.stop())
    signal.signal(signal.SIGINT, lambda *_: worker.stop())
    worker.run()


if __name__ == "__main__":
    main()
