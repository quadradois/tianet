"""Portas de persistencia e integracao do EPIC-010."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

from emprestimo.domain.credit.notifications import (
    PreferenciaNotificacao,
    ResultadoEnvio,
    SolicitacaoNotificacao,
    TemplateNotificacao,
)
from emprestimo.domain.credit.scheduler import JobAgendado, TentativaJob


@dataclass(frozen=True)
class AutomacaoFiltros:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    page: int = 1
    size: int = 20


@dataclass(frozen=True)
class ResultadoPaginado[T]:
    items: list[T]
    total: int
    page: int
    size: int


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime: ...


class JobAgendadoRepository(ABC):
    @abstractmethod
    def save(self, job: JobAgendado) -> None: ...

    @abstractmethod
    def find_scoped(self, job_id: uuid.UUID, tenant_id: uuid.UUID) -> JobAgendado | None: ...

    @abstractmethod
    def find_by_origem(
        self,
        *,
        tenant_id: uuid.UUID,
        origem_tipo: str,
        origem_id: uuid.UUID,
    ) -> JobAgendado | None: ...

    @abstractmethod
    def listar(self, filtros: AutomacaoFiltros) -> ResultadoPaginado[JobAgendado]: ...

    @abstractmethod
    def claim(
        self,
        *,
        agora: datetime,
        limite: int,
        duracao: timedelta,
    ) -> list[tuple[JobAgendado, TentativaJob]]: ...

    @abstractmethod
    def renovar_lease(
        self,
        job_id: uuid.UUID,
        lease_token: uuid.UUID,
        *,
        agora: datetime,
        duracao: timedelta,
    ) -> bool: ...

    @abstractmethod
    def finalizar_com_fencing(self, job: JobAgendado, lease_token: uuid.UUID) -> bool: ...

    @abstractmethod
    def purgar_terminais_antes(self, limite: datetime) -> int: ...


class TentativaJobRepository(ABC):
    @abstractmethod
    def save(self, tentativa: TentativaJob) -> None: ...

    @abstractmethod
    def listar_por_job(self, job_id: uuid.UUID) -> list[TentativaJob]: ...


class PreferenciaNotificacaoRepository(ABC):
    @abstractmethod
    def save(self, preferencia: PreferenciaNotificacao) -> None: ...

    @abstractmethod
    def find_by_contato(
        self,
        contato_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> PreferenciaNotificacao | None: ...


class TemplateNotificacaoRepository(ABC):
    @abstractmethod
    def save(self, template: TemplateNotificacao) -> None: ...

    @abstractmethod
    def find_scoped(
        self,
        template_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> TemplateNotificacao | None: ...

    @abstractmethod
    def find_by_codigo_versao(
        self, tenant_id: uuid.UUID, codigo: str, versao: int
    ) -> TemplateNotificacao | None: ...

    @abstractmethod
    def find_ativo(self, tenant_id: uuid.UUID, codigo: str) -> TemplateNotificacao | None: ...

    @abstractmethod
    def listar(self, filtros: AutomacaoFiltros) -> ResultadoPaginado[TemplateNotificacao]: ...


class SolicitacaoNotificacaoRepository(ABC):
    @abstractmethod
    def save(self, solicitacao: SolicitacaoNotificacao) -> None: ...

    @abstractmethod
    def find_scoped(
        self,
        solicitacao_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> SolicitacaoNotificacao | None: ...

    @abstractmethod
    def find_scoped_for_update(
        self, solicitacao_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SolicitacaoNotificacao | None: ...

    @abstractmethod
    def find_by_chave(self, chave: str) -> SolicitacaoNotificacao | None: ...

    @abstractmethod
    def listar(self, filtros: AutomacaoFiltros) -> ResultadoPaginado[SolicitacaoNotificacao]: ...


class NotificationChannel(ABC):
    @abstractmethod
    def enviar(
        self,
        *,
        destinatario: str,
        assunto: str,
        corpo: str,
        chave_idempotente: str,
    ) -> ResultadoEnvio: ...

    @abstractmethod
    def consultar_status(self, provider_message_id: str) -> ResultadoEnvio: ...
