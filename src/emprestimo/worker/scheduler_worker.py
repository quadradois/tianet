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
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.application.comprovante import TIPO_JOB_COMPROVANTE, EntregaComprovanteService
from emprestimo.application.notifications import (
    TIPO_JOB_AVISO_SOBRA,
    EntregaAvisoSobraPagamentoService,
    FakeNotificationChannel,
    NotificationService,
)
from emprestimo.application.scheduler import ClaimScheduler, ResultadoExecucao, SchedulerService
from emprestimo.application.varredura_cobranca import (
    TIPO_JOB_VARREDURA_COBRANCA,
    AgendadorVarreduraCobranca,
    VarreduraCobrancaService,
)
from emprestimo.composition import resolver_canal_email
from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import JobAgendadoORM, SchedulerWorkerHeartbeatORM
from emprestimo.infrastructure.db.session import database_url
from emprestimo.infrastructure.notifications import (
    EvolutionWhatsAppNotificationChannel,
)
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
    batch_size: int = 4
    poll_interval_seconds: float = 1.0
    heartbeat_seconds: float = 10.0
    graceful_shutdown_seconds: float = 30.0
    lease_seconds: float = 60.0
    lease_renewal_seconds: float = 20.0
    max_attempt_runtime_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.concurrency < 1 or self.concurrency > 16:
            raise ValueError("concurrency deve estar entre 1 e 16")
        if self.batch_size < 1 or self.batch_size > 16:
            raise ValueError("batch_size deve estar entre 1 e 16")
        if self.poll_interval_seconds < 1 or self.poll_interval_seconds > 30:
            raise ValueError("poll_interval_seconds deve estar entre 1 e 30")
        if self.lease_seconds < 30 or self.lease_seconds > 300:
            raise ValueError("lease_seconds deve estar entre 30 e 300")
        if self.lease_renewal_seconds <= 0 or self.lease_renewal_seconds > self.lease_seconds / 3:
            raise ValueError("lease_renewal_seconds deve ser no maximo um terco do lease")
        if self.graceful_shutdown_seconds < 5 or self.graceful_shutdown_seconds > 120:
            raise ValueError("graceful_shutdown_seconds deve estar entre 5 e 120")
        if self.max_attempt_runtime_seconds < 30 or self.max_attempt_runtime_seconds > 1800:
            raise ValueError("max_attempt_runtime_seconds deve estar entre 30 e 1800")

    @classmethod
    def from_env(cls) -> WorkerSettings:
        return cls(
            concurrency=int(os.environ.get("SCHEDULER_CONCURRENCY", "4")),
            batch_size=int(os.environ.get("SCHEDULER_BATCH_SIZE", "4")),
            poll_interval_seconds=float(os.environ.get("SCHEDULER_POLL_INTERVAL_SECONDS", "1")),
            graceful_shutdown_seconds=float(
                os.environ.get("SCHEDULER_SHUTDOWN_GRACE_SECONDS", "30")
            ),
            lease_seconds=float(os.environ.get("SCHEDULER_LEASE_SECONDS", "60")),
            lease_renewal_seconds=float(os.environ.get("SCHEDULER_LEASE_RENEW_SECONDS", "20")),
            max_attempt_runtime_seconds=float(
                os.environ.get("SCHEDULER_MAX_ATTEMPT_RUNTIME_SECONDS", "300")
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
        before_cycle: Callable[[], None] | None = None,
    ) -> None:
        self._service = service
        self._handlers = handlers
        self._settings = settings
        self._heartbeat = heartbeat or (lambda _ativos, _falha: None)
        self._before_cycle = before_cycle or (lambda: None)
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
        self._before_cycle()
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
                if not future.cancelled() and (exc := future.exception()) is not None:
                    self._supervisor_unhealthy = True
                    logger.error(
                        "scheduler_execution_failed",
                        exc_info=(type(exc), exc, exc.__traceback__),
                        extra={
                            "job_id": str(claim.job.id),
                            "execution_id": str(claim.tentativa.execution_id),
                            "correlation_id": claim.job.correlation_id,
                        },
                    )
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


class SemeadorDiarioCobranca:
    """Cria jobs diarios no scheduler existente, uma vez por data e processo."""

    def __init__(
        self,
        agendador: AgendadorVarreduraCobranca,
        *,
        agora: Callable[[], datetime] | None = None,
    ) -> None:
        self._agendador = agendador
        self._agora = agora or (lambda: datetime.now(UTC))
        self._ultima_data: date | None = None

    def semear(self) -> None:
        instante = self._agora()
        data_referencia = instante.date()
        if self._ultima_data == data_referencia:
            return
        self._agendador.agendar_dia(
            data_referencia=data_referencia,
            executar_em=instante,
        )
        self._ultima_data = data_referencia


def main() -> None:
    settings = WorkerSettings.from_env()
    engine = create_engine(
        database_url(),
        pool_size=settings.concurrency + 2,
        max_overflow=0,
        pool_pre_ping=True,
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    service = SchedulerService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria,
        lease_duration=timedelta(seconds=settings.lease_seconds),
    )
    app_env = os.environ.get("APP_ENV", "development")
    email_channel = resolver_canal_email()
    notifications = NotificationService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        email_channel,
        auditoria,
    )

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    evolution_token = os.environ.get("EVOLUTION_INSTANCE_TOKEN")
    if evolution_token:
        whatsapp_channel: NotificationChannel = EvolutionWhatsAppNotificationChannel(
            host=os.environ.get("EVOLUTION_HOST", "https://diamondgreen.com.br"),
            instance_token=evolution_token,
        )
    elif app_env == "production":
        raise RuntimeError("EVOLUTION_INSTANCE_TOKEN e obrigatorio em producao")
    else:
        whatsapp_channel = FakeNotificationChannel()
    comprovantes = EntregaComprovanteService(
        uow_factory,
        whatsapp_channel,
        auditoria,
    )
    avisos_sobra = EntregaAvisoSobraPagamentoService(
        uow_factory,
        whatsapp_channel,
        auditoria,
    )
    varredura = VarreduraCobrancaService(
        uow_factory,
        auditoria,
    )
    semeador_cobranca = SemeadorDiarioCobranca(AgendadorVarreduraCobranca(uow_factory, auditoria))
    worker_id = f"scheduler-{uuid.uuid4()}"
    heartbeat = HeartbeatStore(worker_id, session_factory)
    worker = SchedulerWorker(
        service,
        handlers={
            "enviar_lembrete": notifications.processar_lembrete,
            TIPO_JOB_COMPROVANTE: comprovantes.processar_comprovante,
            TIPO_JOB_AVISO_SOBRA: avisos_sobra.processar_aviso,
            TIPO_JOB_VARREDURA_COBRANCA: varredura.processar_job,
        },
        settings=settings,
        before_cycle=semeador_cobranca.semear,
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
