"""Regua de lembrete de atraso (IMP-373): D+1, depois de tres em tres dias."""

from __future__ import annotations

import pytest

from emprestimo.domain.credit.regua_lembrete import elegivel_lembrete


@pytest.mark.parametrize("dias", [1, 4, 7, 10, 31])
def test_dias_elegiveis(dias: int) -> None:
    assert elegivel_lembrete(dias) is True


@pytest.mark.parametrize("dias", [0, 2, 3, 5, 6, 8, 9, 30])
def test_dias_nao_elegiveis(dias: int) -> None:
    assert elegivel_lembrete(dias) is False


@pytest.mark.parametrize("dias", [-1, -10])
def test_antes_do_vencimento_nunca_lembra(dias: int) -> None:
    assert elegivel_lembrete(dias) is False
