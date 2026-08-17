"""Calendario do acerto mensal (DR-004, PLAN-030)."""

from __future__ import annotations

from datetime import date

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.dia_de_acerto import proximo_acerto, validar_dia_de_acerto


def test_emprestimo_antes_do_dia_escolhido_acerta_no_mesmo_mes() -> None:
    # Emprestado em 05/08 com acerto todo dia 10: cinco dias de juros no
    # primeiro periodo.
    assert proximo_acerto(date(2026, 8, 5), 10) == date(2026, 8, 10)


def test_emprestimo_depois_do_dia_escolhido_acerta_no_mes_seguinte() -> None:
    # O caso do Credor: emprestado em 17/08, acerto todo dia 10 -> 10/09.
    assert proximo_acerto(date(2026, 8, 17), 10) == date(2026, 9, 10)


def test_emprestimo_no_proprio_dia_de_acerto_vai_para_o_mes_seguinte() -> None:
    """Um periodo de zero dia nao teria juros a cobrar."""
    assert proximo_acerto(date(2026, 8, 10), 10) == date(2026, 9, 10)


@pytest.mark.parametrize(
    ("a_partir_de", "dia", "esperado"),
    [
        # Fevereiro nao tem 30 nem 31: o acerto cai no ultimo dia do mes, e nao
        # escorrega para marco — senao fevereiro ficaria sem acerto nenhum.
        (date(2027, 2, 5), 31, date(2027, 2, 28)),
        (date(2027, 2, 5), 30, date(2027, 2, 28)),
        (date(2028, 2, 5), 31, date(2028, 2, 29)),
        # Abril tem 30 dias.
        (date(2026, 4, 5), 31, date(2026, 4, 30)),
        # Depois do ultimo dia do mes curto, o proximo e no mes cheio seguinte.
        (date(2027, 2, 28), 31, date(2027, 3, 31)),
    ],
)
def test_dia_inexistente_no_mes_cai_no_ultimo_dia(
    a_partir_de: date, dia: int, esperado: date
) -> None:
    assert proximo_acerto(a_partir_de, dia) == esperado


def test_dezembro_vira_o_ano() -> None:
    assert proximo_acerto(date(2026, 12, 20), 10) == date(2027, 1, 10)


@pytest.mark.parametrize("dia", [0, 32, -1, 100])
def test_dia_fora_da_faixa_e_recusado(dia: int) -> None:
    with pytest.raises(ViolacaoInvarianteError):
        validar_dia_de_acerto(dia)


def test_booleano_nao_passa_por_inteiro() -> None:
    # `True` e instancia de int em Python; sem a guarda, viraria "dia 1".
    with pytest.raises(ViolacaoInvarianteError):
        validar_dia_de_acerto(True)
