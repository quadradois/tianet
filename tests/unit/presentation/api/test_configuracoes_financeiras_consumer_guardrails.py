"""Guardrails de APIs consumidoras contra regra financeira livre (IMP-203)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from emprestimo.presentation.api.comercial_schemas import (
    PropostaComercialCreateRequest,
    PropostaComercialUpdateRequest,
    SimulacaoComercialCreateRequest,
)
from emprestimo.presentation.api.motor_schemas import RenegociacaoCreateRequest


def test_comercial_recusa_regra_financeira_livre_em_simulacao() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SimulacaoComercialCreateRequest.model_validate(
            {
                "parametros": {
                    "valor_solicitado": "1000.00",
                    "regra_calculo": {"tipo": "livre"},
                }
            }
        )

    assert "regra_calculo" in str(exc_info.value)


def test_comercial_recusa_regra_financeira_livre_em_proposta() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PropostaComercialCreateRequest.model_validate(
            {
                "parametros": {
                    "valor_solicitado": "1000.00",
                    "politica": {"memoria_calculo": {"passos": []}},
                }
            }
        )

    assert "memoria_calculo" in str(exc_info.value)


def test_comercial_recusa_atualizacao_com_resultado_financeiro_livre() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PropostaComercialUpdateRequest.model_validate(
            {
                "parametros": {
                    "valor_solicitado": "1000.00",
                    "resultado": {"juros": "10.00"},
                }
            }
        )

    assert "juros" in str(exc_info.value)


def test_comercial_aceita_parametros_operacionais_sem_regra_livre() -> None:
    request = SimulacaoComercialCreateRequest.model_validate(
        {
            "parametros": {
                "valor_solicitado": "1000.00",
                "parcelas": 6,
                "quantidade_parcelas": 6,
                "moeda": "BRL",
            }
        }
    )

    assert request.parametros["parcelas"] == 6
    assert request.parametros["quantidade_parcelas"] == 6


def test_motor_mantem_rejeicao_de_regra_financeira_livre_na_renegociacao() -> None:
    with pytest.raises(ValidationError) as exc_info:
        RenegociacaoCreateRequest.model_validate(
            {
                "novos_parametros": {
                    "valor_contratado": "8500.00",
                    "regra_calculo": {"tipo": "livre"},
                },
                "renegociado_em": "2026-08-09T12:00:00Z",
            }
        )

    assert "regra_calculo" in str(exc_info.value)
