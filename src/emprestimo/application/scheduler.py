"""Orquestracao do Scheduler duravel."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from emprestimo.application.auditoria_escrita import auditar_escrita
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.credit.scheduler import (
    EstadoTentativaJob,
    JobAgendado,
    TentativaJob,
    calcular_backoff,
)


class ResultadoExecucao(StrEnum):
    FINALIZADO = "finalizado"
    SUCESSO = "sucesso"
    FALHA_TEMPORARIA = "falha_temporaria"
    FALHA_PERMANENTE = "falha_permanente"
    RESULTADO_DESCONHECIDO = "resultado_desconhecido"


@dataclass(frozen=True)
class ClaimScheduler:
    job: JobAgendado
    tentativa: TentativaJob
    cancelamento: threading.Event = field(default_factory=threading.Event, compare=False)


class SchedulerService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
        *,
        lease_duration: timedelta = timedelta(seconds=30),
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria
        self._lease_duration = lease_duration

    @auditar_escrita("scheduler", "reivindicar")
    def reivindicar(
        self,
        *,
        slots_livres: int,
        batch_size: int,
        agora: datetime | None = None,
    ) -> list[ClaimScheduler]:
        instante = agora or datetime.now(UTC)
        limite = max(0, min(slots_livres, batch_size))
        with self._uow_factory() as uow:
            claims = uow.job_agendado.claim(
                agora=instante,
                limite=limite,
                duracao=self._lease_duration,
            )
            uow.commit()
        return [ClaimScheduler(job, tentativa) for job, tentativa in claims]

    @auditar_escrita("scheduler", "renovar")
    def renovar(self, claim: ClaimScheduler, *, agora: datetime | None = None) -> bool:
        instante = agora or datetime.now(UTC)
        with self._uow_factory() as uow:
            renovado = uow.job_agendado.renovar_lease(
                claim.job.id,
                claim.tentativa.lease_token,
                agora=instante,
                duracao=self._lease_duration,
            )
            uow.commit()
            return renovado

    def finalizar(
        self,
        claim: ClaimScheduler,
        resultado: ResultadoExecucao,
        *,
        erro_codigo: str | None = None,
        agora: datetime | None = None,
    ) -> bool:
        if resultado is ResultadoExecucao.FINALIZADO:
            return True
        return self._finalizar(
            claim,
            resultado,
            erro_codigo=erro_codigo,
            agora=agora,
        )

    @auditar_escrita("scheduler", "finalizar")
    def _finalizar(
        self,
        claim: ClaimScheduler,
        resultado: ResultadoExecucao,
        *,
        erro_codigo: str | None = None,
        agora: datetime | None = None,
    ) -> bool:
        instante = agora or datetime.now(UTC)
        job = claim.job
        tentativa = claim.tentativa
        if resultado is ResultadoExecucao.FINALIZADO:
            return True
        if resultado is ResultadoExecucao.SUCESSO:
            job.concluir(tentativa.lease_token, agora=instante)
            tentativa.finalizar(EstadoTentativaJob.SUCESSO, agora=instante)
        elif resultado is ResultadoExecucao.FALHA_TEMPORARIA:
            job.falhar(
                tentativa.lease_token,
                agora=instante,
                temporaria=True,
                proxima_execucao_em=instante + calcular_backoff(job.tentativas),
            )
            tentativa.finalizar(
                EstadoTentativaJob.FALHA_TEMPORARIA,
                agora=instante,
                erro_codigo=erro_codigo,
            )
        elif resultado is ResultadoExecucao.RESULTADO_DESCONHECIDO:
            job.falhar(tentativa.lease_token, agora=instante, temporaria=False)
            tentativa.finalizar(
                EstadoTentativaJob.RESULTADO_DESCONHECIDO,
                agora=instante,
                erro_codigo=erro_codigo,
            )
        else:
            job.falhar(tentativa.lease_token, agora=instante, temporaria=False)
            tentativa.finalizar(
                EstadoTentativaJob.FALHA_PERMANENTE,
                agora=instante,
                erro_codigo=erro_codigo,
            )
        with self._uow_factory() as uow:
            if not uow.job_agendado.finalizar_com_fencing(job, tentativa.lease_token):
                return False
            uow.tentativa_job.save(tentativa)
            uow.commit()
            return True
