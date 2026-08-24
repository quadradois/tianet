"""Servicos administrativos de automacao operacional."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from emprestimo.application.errors import (
    JobAgendadoNaoEncontradoError,
    TransicaoEstadoInvalidaError,
)
from emprestimo.application.idempotencia import (
    concluir_idempotencia,
    dataclass_do_resultado,
    iniciar_idempotencia,
    resultado_de_dataclass,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.automacao_ports import AutomacaoFiltros, ResultadoPaginado
from emprestimo.domain.credit.scheduler import EstadoJob, JobAgendado


class AutomacaoAdminService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def listar(self, filtros: AutomacaoFiltros) -> ResultadoPaginado[JobAgendado]:
        with self._uow_factory() as uow:
            return uow.job_agendado.listar(filtros)

    def obter(self, *, tenant_id: uuid.UUID, job_id: uuid.UUID) -> JobAgendado:
        with self._uow_factory() as uow:
            job = uow.job_agendado.find_scoped(job_id, tenant_id)
        if job is None:
            raise JobAgendadoNaoEncontradoError(job_id)
        return job

    def cancelar(
        self,
        *,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str,
        idempotency_key: str | None = None,
    ) -> JobAgendado:
        return self._mutar(
            tenant_id=tenant_id,
            job_id=job_id,
            usuario_id=usuario_id,
            motivo=motivo,
            acao="cancelar",
            idempotency_key=idempotency_key,
        )

    def retry(
        self,
        *,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str,
        idempotency_key: str | None = None,
    ) -> JobAgendado:
        return self._mutar(
            tenant_id=tenant_id,
            job_id=job_id,
            usuario_id=usuario_id,
            motivo=motivo,
            acao="retry",
            idempotency_key=idempotency_key,
        )

    def _mutar(
        self,
        *,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str,
        acao: str,
        idempotency_key: str | None = None,
    ) -> JobAgendado:
        if not motivo.strip():
            raise TransicaoEstadoInvalidaError(job_id, acao, "motivo obrigatorio")
        self._auditoria.registrar(
            "job_agendado",
            job_id,
            f"{acao}.inicio",
            "iniciado",
            detalhes=json.dumps({"usuario_id": str(usuario_id), "motivo": motivo}),
        )
        try:
            with self._uow_factory() as uow:
                job = uow.job_agendado.find_scoped(job_id, tenant_id)
                if job is None:
                    raise JobAgendadoNaoEncontradoError(job_id)
                escopo = f"automacao-job-{acao}"
                replay = iniciar_idempotencia(
                    uow,
                    chave=idempotency_key,
                    escopo=escopo,
                    solicitacao={
                        "tenant_id": tenant_id,
                        "job_id": job_id,
                        "usuario_id": usuario_id,
                        "motivo": motivo,
                    },
                )
                if replay is not None:
                    return dataclass_do_resultado(
                        replay,
                        JobAgendado,
                        chave=idempotency_key,
                    )
                anterior = job.estado
                try:
                    if acao == "cancelar":
                        job.solicitar_cancelamento(agora=datetime.now(UTC))
                    else:
                        if job.estado is not EstadoJob.FALHA_TEMPORARIA:
                            raise ViolacaoInvarianteError(
                                "EPIC-010",
                                "retry administrativo aceita apenas falha temporaria",
                            )
                        job.estado = EstadoJob.AGENDADO
                        job.proxima_execucao_em = datetime.now(UTC) + timedelta(seconds=1)
                        job.atualizado_em = datetime.now(UTC)
                except ViolacaoInvarianteError as exc:
                    raise TransicaoEstadoInvalidaError(job_id, acao, str(exc)) from exc
                uow.job_agendado.save(job)
                concluir_idempotencia(
                    uow,
                    chave=idempotency_key,
                    escopo=escopo,
                    resultado=resultado_de_dataclass(job),
                )
                uow.commit()
            self._auditoria.registrar(
                "job_agendado",
                job_id,
                f"{acao}.sucesso",
                "ok",
                detalhes=json.dumps({"anterior": anterior.value, "novo": job.estado.value}),
            )
            return job
        except Exception:
            self._auditoria.registrar(
                "job_agendado", job_id, f"{acao}.rollback", "rollback_aplicado"
            )
            raise
