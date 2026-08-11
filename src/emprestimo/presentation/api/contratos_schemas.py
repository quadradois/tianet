"""DTOs da API REST do contexto Contratos (EPIC-004/P5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState


class ContratoCreditoCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposta_comercial_id: uuid.UUID


class DecisaoContratoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str | None = Field(default=None, min_length=1, max_length=500)


class ContratoCreditoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    proposta_comercial_id: uuid.UUID
    criado_por_usuario_id: uuid.UUID
    estado: ContratoCreditoState
    parametros: dict[str, object]
    criado_em: datetime
    atualizado_em: datetime | None
    formalizado_por_usuario_id: uuid.UUID | None
    formalizado_em: datetime | None
    assinado_por_usuario_id: uuid.UUID | None
    assinado_em: datetime | None
    liberado_por_usuario_id: uuid.UUID | None
    liberado_em: datetime | None
    motivo_encerramento: str | None
    total_eventos: int


class ContratoCreditoListagemResponse(BaseModel):
    items: list[ContratoCreditoResponse]
    total: int
    page: int
    size: int
    pages: int


class EventoContratoResponse(BaseModel):
    id: uuid.UUID
    contrato_id: uuid.UUID
    usuario_id: uuid.UUID
    tipo: str
    estado_anterior: ContratoCreditoState
    estado_posterior: ContratoCreditoState
    motivo: str | None
    criado_em: datetime


class ContratoLiberadoLogicoResponse(BaseModel):
    contrato_id: uuid.UUID
    proposta_comercial_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    parametros_contratados: dict[str, object]
    liberado_por_usuario_id: uuid.UUID
    liberado_em: datetime
