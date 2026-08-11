"""DTOs da API REST do Motor Financeiro (EPIC-005/P5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from emprestimo.domain.credit.emprestimo import EmprestimoState
from emprestimo.domain.credit.pagamento import PagamentoState
from emprestimo.domain.credit.parcela import ParcelaState

CHAVES_FINANCEIRAS_PROIBIDAS = frozenset(
    {
        "arredondamento",
        "arredondamentos",
        "calculo",
        "componentes_quitacao",
        "distribuicao",
        "encargos",
        "juros",
        "memoria",
        "memoria_calculo",
        "parcelas",
        "regra",
        "regra_calculo",
        "saldo_devedor",
        "valor_quitacao",
    }
)


class PlanoParcelasRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_referencia: date


class PagamentoCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valor: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)
    recebido_em: datetime


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
        chaves = _coletar_chaves(self.novos_parametros)
        proibidas = sorted(chaves & CHAVES_FINANCEIRAS_PROIBIDAS)
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


class EmprestimoListagemResponse(BaseModel):
    items: list[EmprestimoResponse]
    total: int
    page: int
    size: int
    pages: int


class ParcelaResponse(BaseModel):
    id: uuid.UUID
    emprestimo_id: uuid.UUID
    numero: int
    vencimento: date
    valor_previsto: Decimal
    principal: Decimal
    juros: Decimal
    encargos: Decimal
    valor_liquidado: Decimal
    estado: ParcelaState


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


class PlanoParcelasResponse(BaseModel):
    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    parcelas: list[ParcelaResponse]
    memoria: MemoriaCalculoResponse | None = None


class PagamentoResponse(BaseModel):
    id: uuid.UUID
    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    valor_recebido: Decimal
    recebido_em: datetime
    valor_juros: Decimal
    valor_amortizacao: Decimal
    valor_encargos: Decimal
    estado: PagamentoState
    chave_idempotencia: str | None
    parcelas_liquidadas: list[uuid.UUID]
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


def _coletar_chaves(valor: object) -> set[str]:
    if isinstance(valor, dict):
        chaves = {str(chave).strip().lower() for chave in valor}
        for item in valor.values():
            chaves |= _coletar_chaves(item)
        return chaves
    if isinstance(valor, list | tuple):
        chaves_coletadas: set[str] = set()
        for item in valor:
            chaves_coletadas |= _coletar_chaves(item)
        return chaves_coletadas
    return set()
