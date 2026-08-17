"""Teste de valor da base de normalizacao dos juros (DR-003, PLAN-028).

Este arquivo existe porque a DR-003 encontrou a regra de juros sem
especificacao e sem nenhum teste que fixasse resultado: os testes do Motor
cobriam tipos, periodicidade e estrutura, nunca o numero. Sem isto, qualquer
alteracao futura da formula volta a passar despercebida.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from emprestimo.domain.credit.emprestimo import Emprestimo
from emprestimo.domain.credit.motor_financeiro import MotorFinanceiro

TAXA = Decimal("0.05")
VALOR = Decimal("10000")


def _emprestimo(parcelas: int, primeiro_vencimento: str) -> Emprestimo:
    return Emprestimo(
        contrato_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        carteira_id=uuid.uuid4(),
        devedor_id=uuid.uuid4(),
        principal_original=VALOR,
        moeda="BRL",
        _parametros_financeiros={
            "valor_contratado": VALOR,
            "taxa_juros_mensal": TAXA,
            "quantidade_parcelas": parcelas,
            "primeiro_vencimento": date.fromisoformat(primeiro_vencimento),
            "moeda": "BRL",
        },
    )


def test_mes_calendario_cheio_custa_exatamente_a_taxa_contratada() -> None:
    """A taxa e contratada "por mes": um mes corrido custa um mes de juros.

    Com o divisor anterior — dias do mes de vencimento — o periodo 01/01 a 01/02
    custava 55,36 (1,107 mes) porque 31 dias eram normalizados por fevereiro, e
    o periodo seguinte custava 45,16 (0,903 mes). Ver DR-003 secao 4.1.
    """
    plano = MotorFinanceiro().gerar_plano_parcelas(
        emprestimo=_emprestimo(10, "2026-09-01"),
        data_referencia=date(2026, 8, 17),
    )

    juros = [p.juros for p in plano.parcelas]

    # Primeira parcela e parcial: 15 dias de agosto, que tem 31.
    assert juros[0] == Decimal("24.19")
    # Da segunda em diante, todo periodo cobre um mes calendario inteiro.
    assert juros[1:] == [Decimal("50.00")] * 9


@pytest.mark.parametrize(
    ("primeiro_vencimento", "esperado"),
    [
        # Fevereiro era o pior caso da formula anterior, nos dois sentidos.
        ("2027-02-01", Decimal("50.00")),
        ("2027-03-01", Decimal("50.00")),
        # Mes de 31 dias tampouco pode custar mais que um mes.
        ("2027-01-01", Decimal("50.00")),
    ],
)
def test_mes_curto_ou_longo_nao_altera_o_custo_de_um_mes(
    primeiro_vencimento: str, esperado: Decimal
) -> None:
    inicio = date.fromisoformat(primeiro_vencimento)
    anterior = date(
        inicio.year if inicio.month > 1 else inicio.year - 1,
        inicio.month - 1 if inicio.month > 1 else 12,
        1,
    )

    plano = MotorFinanceiro().gerar_plano_parcelas(
        emprestimo=_emprestimo(1, primeiro_vencimento),
        data_referencia=anterior,
    )

    assert plano.parcelas[0].juros == esperado * Decimal(10)


def test_periodo_parcial_permanece_proporcional_aos_dias_reais() -> None:
    """A correcao remove a distorcao, nao a proporcionalidade por dias."""
    plano = MotorFinanceiro().gerar_plano_parcelas(
        emprestimo=_emprestimo(1, "2026-09-16"),
        data_referencia=date(2026, 9, 1),
    )

    # 15 dias de setembro, que tem 30: metade de um mes de juros sobre 10000.
    assert plano.parcelas[0].juros == Decimal("250.00")
