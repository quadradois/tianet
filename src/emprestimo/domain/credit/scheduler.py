"""Dominio do Scheduler duravel do EPIC-010."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from emprestimo.domain.common.errors import ViolacaoInvarianteError


class EstadoJob(StrEnum):
    AGENDADO = "agendado"
    EM_EXECUCAO = "em_execucao"
    CONCLUIDO = "concluido"
    FALHA_TEMPORARIA = "falha_temporaria"
    FALHA_PERMANENTE = "falha_permanente"
    CANCELADO = "cancelado"


class EstadoTentativaJob(StrEnum):
    INICIADA = "iniciada"
    SUCESSO = "sucesso"
    FALHA_TEMPORARIA = "falha_temporaria"
    FALHA_PERMANENTE = "falha_permanente"
    RESULTADO_DESCONHECIDO = "resultado_desconhecido"


ESTADOS_TERMINAIS_JOB = {
    EstadoJob.CONCLUIDO,
    EstadoJob.FALHA_PERMANENTE,
    EstadoJob.CANCELADO,
}


@dataclass
class TentativaJob:
    job_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    lease_token: uuid.UUID
    execution_id: uuid.UUID
    numero: int
    iniciada_em: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    estado: EstadoTentativaJob = EstadoTentativaJob.INICIADA
    finalizada_em: datetime | None = None
    erro_codigo: str | None = None

    def finalizar(
        self,
        estado: EstadoTentativaJob,
        *,
        agora: datetime,
        erro_codigo: str | None = None,
    ) -> None:
        if self.estado is not EstadoTentativaJob.INICIADA:
            raise ViolacaoInvarianteError("EPIC-010", "tentativa ja finalizada")
        if estado is EstadoTentativaJob.INICIADA:
            raise ViolacaoInvarianteError("EPIC-010", "estado final de tentativa invalido")
        _exigir_utc(agora, "agora")
        self.estado = estado
        self.finalizada_em = agora
        self.erro_codigo = erro_codigo


@dataclass
class JobAgendado:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    tipo: str
    executar_em: datetime
    correlation_id: str
    payload: dict[str, Any]
    origem_tipo: str
    origem_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    estado: EstadoJob = EstadoJob.AGENDADO
    max_tentativas: int = 5
    tentativas: int = 0
    proxima_execucao_em: datetime | None = None
    lease_token: uuid.UUID | None = None
    lease_ate: datetime | None = None
    cancelamento_solicitado: bool = False
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None

    def __post_init__(self) -> None:
        _exigir_uuid(self.tenant_id, "tenant_id")
        _exigir_uuid(self.carteira_id, "carteira_id")
        _exigir_uuid(self.origem_id, "origem_id")
        _exigir_utc(self.executar_em, "executar_em")
        if self.proxima_execucao_em is None:
            self.proxima_execucao_em = self.executar_em
        else:
            _exigir_utc(self.proxima_execucao_em, "proxima_execucao_em")
        if not self.tipo.strip() or not self.origem_tipo.strip():
            raise ViolacaoInvarianteError("EPIC-010", "tipo e origem do job sao obrigatorios")
        if not self.correlation_id.strip() or len(self.correlation_id) > 255:
            raise ViolacaoInvarianteError("EPIC-010", "correlation_id invalido")
        if self.max_tentativas < 1 or self.max_tentativas > 5:
            raise ViolacaoInvarianteError("EPIC-010", "max_tentativas deve estar entre 1 e 5")

    def reivindicar(self, *, agora: datetime, duracao: timedelta) -> TentativaJob:
        _exigir_utc(agora, "agora")
        if duracao <= timedelta(0):
            raise ViolacaoInvarianteError("EPIC-010", "duracao do lease deve ser positiva")
        if not self.elegivel(agora):
            raise ViolacaoInvarianteError("EPIC-010", "job nao esta elegivel para claim")
        self.tentativas += 1
        self.estado = EstadoJob.EM_EXECUCAO
        self.lease_token = uuid.uuid4()
        self.lease_ate = agora + duracao
        self.atualizado_em = agora
        return TentativaJob(
            job_id=self.id,
            tenant_id=self.tenant_id,
            carteira_id=self.carteira_id,
            lease_token=self.lease_token,
            execution_id=uuid.uuid4(),
            numero=self.tentativas,
            iniciada_em=agora,
        )

    def elegivel(self, agora: datetime) -> bool:
        _exigir_utc(agora, "agora")
        if self.cancelamento_solicitado or self.estado in ESTADOS_TERMINAIS_JOB:
            return False
        if self.tentativas >= self.max_tentativas:
            return False
        if self.estado is EstadoJob.EM_EXECUCAO and self.lease_ate is not None:
            return self.lease_ate <= agora
        return self.proxima_execucao_em is not None and self.proxima_execucao_em <= agora

    def renovar_lease(
        self,
        token: uuid.UUID,
        *,
        agora: datetime,
        duracao: timedelta,
    ) -> None:
        self._exigir_lease(token, agora)
        if duracao <= timedelta(0):
            raise ViolacaoInvarianteError("EPIC-010", "duracao do lease deve ser positiva")
        self.lease_ate = agora + duracao
        self.atualizado_em = agora

    def concluir(self, token: uuid.UUID, *, agora: datetime) -> None:
        self._exigir_lease(token, agora)
        if self.cancelamento_solicitado:
            raise ViolacaoInvarianteError("EPIC-010", "job cancelado nao pode ser concluido")
        self.estado = EstadoJob.CONCLUIDO
        self._liberar_lease(agora)

    def falhar(
        self,
        token: uuid.UUID,
        *,
        agora: datetime,
        temporaria: bool,
        proxima_execucao_em: datetime | None = None,
    ) -> None:
        self._exigir_lease(token, agora)
        if temporaria and self.tentativas < self.max_tentativas:
            if proxima_execucao_em is None or proxima_execucao_em <= agora:
                raise ViolacaoInvarianteError("EPIC-010", "retry deve ocorrer no futuro")
            _exigir_utc(proxima_execucao_em, "proxima_execucao_em")
            self.estado = EstadoJob.FALHA_TEMPORARIA
            self.proxima_execucao_em = proxima_execucao_em
        else:
            self.estado = EstadoJob.FALHA_PERMANENTE
        self._liberar_lease(agora)

    def solicitar_cancelamento(self, *, agora: datetime) -> None:
        _exigir_utc(agora, "agora")
        if self.estado in ESTADOS_TERMINAIS_JOB:
            raise ViolacaoInvarianteError("EPIC-010", "job terminal nao pode ser cancelado")
        self.cancelamento_solicitado = True
        if self.estado is not EstadoJob.EM_EXECUCAO:
            self.estado = EstadoJob.CANCELADO
        self.atualizado_em = agora

    def confirmar_cancelamento(self, token: uuid.UUID, *, agora: datetime) -> None:
        self._exigir_lease(token, agora)
        if not self.cancelamento_solicitado:
            raise ViolacaoInvarianteError("EPIC-010", "cancelamento nao solicitado")
        self.estado = EstadoJob.CANCELADO
        self._liberar_lease(agora)

    def reconciliar_conclusao(self, *, agora: datetime) -> None:
        """Conclui efeito externo confirmado depois de resultado desconhecido."""

        _exigir_utc(agora, "agora")
        if self.estado is not EstadoJob.FALHA_PERMANENTE or self.lease_token is not None:
            raise ViolacaoInvarianteError(
                "EPIC-010", "somente falha terminal sem lease pode ser conciliada"
            )
        self.estado = EstadoJob.CONCLUIDO
        self.atualizado_em = agora

    def _exigir_lease(self, token: uuid.UUID, agora: datetime) -> None:
        _exigir_utc(agora, "agora")
        if self.estado is not EstadoJob.EM_EXECUCAO:
            raise ViolacaoInvarianteError("EPIC-010", "job nao esta em execucao")
        if self.lease_token != token or self.lease_ate is None or self.lease_ate <= agora:
            raise ViolacaoInvarianteError("EPIC-010", "lease expirado ou token invalido")

    def _liberar_lease(self, agora: datetime) -> None:
        self.lease_token = None
        self.lease_ate = None
        self.atualizado_em = agora


def calcular_backoff(numero_tentativa: int, *, jitter_segundos: int = 0) -> timedelta:
    if numero_tentativa < 1 or numero_tentativa > 5:
        raise ViolacaoInvarianteError("EPIC-010", "numero de tentativa invalido")
    if jitter_segundos < 0 or jitter_segundos > 30:
        raise ViolacaoInvarianteError("EPIC-010", "jitter fora do limite")
    return timedelta(seconds=min(15 * (2 ** (numero_tentativa - 1)), 300) + jitter_segundos)


def _exigir_uuid(valor: uuid.UUID, nome: str) -> None:
    if not isinstance(valor, uuid.UUID) or valor.int == 0:
        raise ViolacaoInvarianteError("EPIC-010", f"{nome} invalido")


def _exigir_utc(valor: datetime, nome: str) -> None:
    if valor.tzinfo is None or valor.utcoffset() is None:
        raise ViolacaoInvarianteError("EPIC-010", f"{nome} deve possuir timezone")
