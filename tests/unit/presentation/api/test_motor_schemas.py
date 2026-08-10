"""Contratos dos DTOs REST do Motor Financeiro (IMP-164)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from emprestimo.presentation.api.motor_schemas import (
    ConsultaDataReferenciaRequest,
    PagamentoCreateRequest,
    PlanoParcelasRequest,
    RenegociacaoCreateRequest,
)


def test_schemas_motor_recusam_campos_extras_de_calculo_financeiro() -> None:
    with pytest.raises(ValidationError):
        PagamentoCreateRequest.model_validate(
            {
                "valor": "100.00",
                "recebido_em": "2026-08-09T12:00:00Z",
                "regra_calculo": {"tipo": "livre"},
            }
        )


@pytest.mark.parametrize("valor", ["0.00", "-1.00"])
def test_pagamento_recusa_valor_nao_positivo(valor: str) -> None:
    with pytest.raises(ValidationError):
        PagamentoCreateRequest(valor=Decimal(valor), recebido_em=datetime(2026, 8, 9, 12, 0))


def test_renegociacao_recusa_regra_memoria_ou_resultado_financeiro_arbitrario() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RenegociacaoCreateRequest.model_validate(
            {
                "novos_parametros": {
                    "valor_contratado": "8500.00",
                    "regra_calculo": {"tipo": "juros_simples_periodo_real"},
                    "memoria_calculo": {"passos": []},
                },
                "renegociado_em": "2026-08-09T12:00:00Z",
            }
        )

    assert "regra_calculo" in str(exc_info.value)
    assert "memoria_calculo" in str(exc_info.value)


def test_renegociacao_aceita_parametros_operacionais_sem_calculo_definitivo() -> None:
    request = RenegociacaoCreateRequest.model_validate(
        {
            "novos_parametros": {
                "valor_contratado": "8500.00",
                "quantidade_parcelas": 8,
                "moeda": "BRL",
            },
            "renegociado_em": "2026-08-09T12:00:00Z",
        }
    )

    assert request.novos_parametros["quantidade_parcelas"] == 8


def test_requests_de_data_referencia_sao_restritos() -> None:
    assert PlanoParcelasRequest(data_referencia=date(2026, 8, 9)).data_referencia == date(
        2026, 8, 9
    )
    assert ConsultaDataReferenciaRequest(data_referencia=date(2026, 8, 9)).data_referencia == date(
        2026, 8, 9
    )
    with pytest.raises(ValidationError):
        ConsultaDataReferenciaRequest.model_validate(
            {"data_referencia": "2026-08-09", "juros": "10.00"}
        )
