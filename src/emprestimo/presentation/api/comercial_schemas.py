"""DTOs da API REST do contexto Comercial (EPIC-003/P5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState


class SimulacaoComercialCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parametros: dict[str, object] = Field(min_length=1)


class PropostaComercialCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parametros: dict[str, object] = Field(default_factory=dict)
    simulacao_id: uuid.UUID | None = None


class PropostaComercialUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parametros: dict[str, object] = Field(min_length=1)


class DecisaoComercialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str | None = Field(default=None, min_length=1, max_length=500)


class SimulacaoComercialResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    criada_por_usuario_id: uuid.UUID
    parametros: dict[str, object]
    criado_em: datetime


class PropostaComercialResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    criada_por_usuario_id: uuid.UUID
    simulacao_id: uuid.UUID | None
    estado: PropostaComercialState
    parametros: dict[str, object]
    criado_em: datetime
    atualizado_em: datetime | None
    aprovada_por_usuario_id: uuid.UUID | None
    aprovada_em: datetime | None
    total_decisoes: int


class PropostaComercialListagemResponse(BaseModel):
    items: list[PropostaComercialResponse]
    total: int
    page: int
    size: int
    pages: int


class PropostaAprovadaLogicaResponse(BaseModel):
    proposta_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    parametros_aprovados: dict[str, object]
    aprovada_por_usuario_id: uuid.UUID
    aprovada_em: datetime
