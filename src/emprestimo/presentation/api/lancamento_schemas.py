"""DTOs do lancamento composto de emprestimo (IMP-306, PLAN-027)."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DevedorNovoRequest(BaseModel):
    """Devedor cadastrado no proprio wizard.

    O contato de WhatsApp e obrigatorio: sem numero nao ha destino para o
    comprovante (PLAN-027, decisao formal 2).
    """

    model_config = ConfigDict(extra="forbid")

    documento: str = Field(min_length=1, max_length=32)
    nome: str = Field(min_length=1, max_length=200)
    contato_whatsapp: str = Field(min_length=8, max_length=20)


class CondicoesLancamentoRequest(BaseModel):
    """Os quatro parametros digitados pelo Credor no ato.

    Campos tipados, nao JSON opaco: aqui o vocabulario do Motor e explicito e o
    erro aparece na entrada, nao tres telas adiante.
    """

    model_config = ConfigDict(extra="forbid")

    valor_contratado: str = Field(min_length=1, max_length=32)
    taxa_juros_mensal: str = Field(min_length=1, max_length=32)
    quantidade_parcelas: int = Field(ge=1, le=360)
    primeiro_vencimento: date
    moeda: str = Field(default="BRL", min_length=3, max_length=3)


class LancamentoCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condicoes: CondicoesLancamentoRequest
    data_referencia: date
    devedor_id: uuid.UUID | None = None
    devedor_novo: DevedorNovoRequest | None = None

    @model_validator(mode="after")
    def _exatamente_um_devedor(self) -> LancamentoCreateRequest:
        if (self.devedor_id is None) == (self.devedor_novo is None):
            raise ValueError("informe devedor_id ou devedor_novo, nunca ambos nem nenhum")
        return self


class LancamentoResponse(BaseModel):
    """Identificadores da cadeia criada, para navegacao e comprovante."""

    devedor_id: uuid.UUID
    proposta_id: uuid.UUID
    contrato_id: uuid.UUID
    emprestimo_id: uuid.UUID
    quantidade_parcelas: int
