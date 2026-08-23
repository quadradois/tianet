"""DTOs da API REST do Motor Financeiro (EPIC-005/P5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from emprestimo.domain.credit.emprestimo import EmprestimoState
from emprestimo.domain.credit.pagamento import PagamentoState
from emprestimo.presentation.api.financial_guardrails import chaves_financeiras_livres


class PagamentoCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valor: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)
    recebido_em: datetime


class EstornoPagamentoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valor: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)


class QuitacaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recebido_em: datetime


class ConsultaDataReferenciaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_referencia: date


class RenegociacaoCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    novos_parametros: dict[str, object] = Field(min_length=1)
    renegociado_em: datetime

    @model_validator(mode="after")
    def recusar_regra_financeira_arbitraria(self) -> Self:
        proibidas = chaves_financeiras_livres(self.novos_parametros)
        if proibidas:
            raise ValueError(
                "novos_parametros nao pode definir regra, memoria ou resultado financeiro: "
                + ", ".join(proibidas)
            )
        return self


class EmprestimoResponse(BaseModel):
    id: uuid.UUID
    contrato_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    estado: EmprestimoState
    principal_original: Decimal
    moeda: str
    parametros_financeiros: dict[str, object]
    criado_em: datetime
    dia_de_acerto: int | None = None
    proximo_acerto_em: date | None = None
    acerto_pendente_desde: date | None = None


class EmprestimoListagemResponse(BaseModel):
    items: list[EmprestimoResponse]
    total: int
    page: int
    size: int
    pages: int


class PassoCalculoResponse(BaseModel):
    nome: str
    entradas: dict[str, object]
    saidas: dict[str, object]
    arredondamento: str | None


class MemoriaCalculoResponse(BaseModel):
    id: uuid.UUID
    tipo: str
    entradas: dict[str, object]
    regra: dict[str, object]
    periodos: list[dict[str, object]]
    passos: list[PassoCalculoResponse]
    arredondamentos: list[str]
    resultados: dict[str, object]
    criado_em: datetime


class PagamentoResponse(BaseModel):
    id: uuid.UUID
    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    valor_recebido: Decimal
    recebido_em: datetime
    valor_juros: Decimal
    valor_amortizacao: Decimal
    valor_encargos: Decimal
    valor_devolvido: Decimal
    valor_estornado: Decimal
    valor_sobra: Decimal
    reconciliado: bool
    estado: PagamentoState
    chave_idempotencia: str | None
    memoria: MemoriaCalculoResponse | None = None


class SaldoResponse(BaseModel):
    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    data_referencia: date
    principal: Decimal
    juros: Decimal
    encargos: Decimal
    total: Decimal
    memoria: MemoriaCalculoResponse


class ValorQuitacaoResponse(BaseModel):
    valor_total: Decimal
    moeda: str
    data_referencia: date
    componentes: dict[str, Decimal]


class QuitacaoCalculadaResponse(BaseModel):
    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    valor_quitacao: ValorQuitacaoResponse
    memoria: MemoriaCalculoResponse


class QuitacaoResponse(BaseModel):
    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    estado: EmprestimoState
    pagamento: PagamentoResponse
    memoria_quitacao: MemoriaCalculoResponse


class RenegociacaoResponse(BaseModel):
    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    novos_parametros: dict[str, object]
    memoria: MemoriaCalculoResponse
