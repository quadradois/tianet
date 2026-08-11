"""DTOs REST de Configuracoes Financeiras (EPIC-009/P4)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from emprestimo.domain.credit.configuracoes_financeiras import ConfiguracaoFinanceiraState
from emprestimo.presentation.api.financial_guardrails import chaves_financeiras_livres


class ModalidadeFinanceiraCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(min_length=1, max_length=80)
    nome: str = Field(min_length=1, max_length=200)
    carteira_id: uuid.UUID | None = None


class ModalidadeFinanceiraResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None
    codigo: str
    nome: str
    ativa: bool


class CalendarioFinanceiroCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(min_length=1, max_length=80)
    nome: str = Field(min_length=1, max_length=200)
    feriados: list[date] = Field(default_factory=list)
    carteira_id: uuid.UUID | None = None


class CalendarioFinanceiroResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None
    codigo: str
    nome: str
    feriados: list[date]


class TaxaFinanceiraRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=80)
    valor: Decimal = Field(ge=Decimal("0.00"))
    periodicidade: str = Field(min_length=1, max_length=40)


class ParametroFinanceiroRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=80)
    valor: Any


class PoliticaArredondamentoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modo: str = Field(min_length=1, max_length=40)
    escala: int = Field(ge=0, le=12)


class ConfiguracaoFinanceiraCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modalidade: str = Field(min_length=1, max_length=80)
    calendario_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    vigencia_inicio: date
    vigencia_fim: date | None = None
    taxas: list[TaxaFinanceiraRequest] = Field(min_length=1)
    parametros: list[ParametroFinanceiroRequest] = Field(min_length=1)
    politica_arredondamento: PoliticaArredondamentoRequest

    @model_validator(mode="after")
    def recusar_regra_financeira_livre(self) -> Self:
        nomes = {parametro.nome: parametro.valor for parametro in self.parametros}
        proibidas = chaves_financeiras_livres(nomes)
        if proibidas:
            raise ValueError(
                "parametros nao podem definir regra, memoria ou resultado financeiro: "
                + ", ".join(proibidas)
            )
        return self


class DecisaoConfiguracaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str | None = Field(default=None, min_length=1, max_length=500)


class ProgramarConfiguracaoRequest(DecisaoConfiguracaoRequest):
    data_ativacao: date


class CapturaSnapshotConfiguracaoRequest(DecisaoConfiguracaoRequest):
    configuracao_id: uuid.UUID


class ConfiguracaoFinanceiraResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None
    modalidade: str
    calendario_id: uuid.UUID
    estado: ConfiguracaoFinanceiraState
    versao: int
    vigencia_inicio: date
    vigencia_fim: date | None
    parametros: dict[str, object]
    criada_por_usuario_id: uuid.UUID
    criada_em: datetime
    atualizada_em: datetime | None
    aprovada_por_usuario_id: uuid.UUID | None
    aprovada_em: datetime | None
    total_eventos: int


class ConfiguracaoFinanceiraVigenteResponse(BaseModel):
    configuracao_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None
    modalidade: str
    versao: int
    parametros: dict[str, object]
    consultada_em: datetime


class SnapshotConfiguracaoContratualResponse(BaseModel):
    configuracao_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None
    modalidade: str
    versao: int
    parametros: dict[str, object]
    hash_parametros: str
    capturado_em: datetime
    capturado_por_usuario_id: uuid.UUID
    motivo: str | None
