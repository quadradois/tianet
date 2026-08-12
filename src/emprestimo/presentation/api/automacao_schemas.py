"""Schemas administrativos de Scheduler e Notification."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from emprestimo.domain.credit.notifications import (
    EstadoSolicitacaoNotificacao,
    EstadoTemplateNotificacao,
)
from emprestimo.domain.credit.scheduler import EstadoJob


class MotivoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motivo: str = Field(min_length=1, max_length=500)


class ConciliacaoRequest(MotivoRequest):
    provider_message_id: str = Field(min_length=1, max_length=255)


class ConciliacaoLegadaRequest(ConciliacaoRequest):
    notification_id: uuid.UUID


class JobResponse(BaseModel):
    id: uuid.UUID
    carteira_id: uuid.UUID
    tipo: str
    origem_tipo: str
    origem_id: uuid.UUID
    estado: EstadoJob
    executar_em: datetime
    proxima_execucao_em: datetime | None
    tentativas: int
    max_tentativas: int
    cancelamento_solicitado: bool
    correlation_id: str


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    size: int
    pages: int


class NotificacaoResponse(BaseModel):
    id: uuid.UUID
    carteira_id: uuid.UUID
    lembrete_id: uuid.UUID
    job_id: uuid.UUID
    estado: EstadoSolicitacaoNotificacao
    provider_message_id: str | None
    resultado_em: datetime | None
    codigo_resultado: str | None


class NotificacaoListResponse(BaseModel):
    items: list[NotificacaoResponse]
    total: int
    page: int
    size: int
    pages: int


class TemplateCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str = Field(min_length=1, max_length=120)
    versao: int = Field(ge=1)
    assunto: str = Field(min_length=1, max_length=300)
    corpo: str = Field(min_length=1, max_length=5000)
    parametros_permitidos: tuple[str, ...] = (
        "data_hora",
        "canal_atendimento",
    )


class TemplateResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    versao: int
    estado: EstadoTemplateNotificacao
    hash_conteudo: str
    aprovado_em: datetime | None
    ativado_em: datetime | None


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
    total: int
    page: int
    size: int
    pages: int
