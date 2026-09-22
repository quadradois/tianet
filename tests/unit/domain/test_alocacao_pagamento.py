"""Alocacao juro/amortizacao como leitura (IMP-389).

O agente precisa dizer "R$ 627 de juros e R$ 1.000 de amortizacao" ANTES de
lancar. Hoje essa conta so existe dentro de `registrar_pagamento`. Estes testes
fixam que a extracao para funcao pura nao mudou o resultado e que a previsao
bate com o pagamento que de fato sera registrado.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from emprestimo.domain.credit.emprestimo import Emprestimo
from emprestimo.domain.credit.motor_financeiro import MotorFinanceiro, prever_alocacao

TAXA = Decimal("0.05")
VALOR = Decimal("10000")
CRIADO_EM = datetime(2026, 8, 1, tzinfo=UTC)
RECEBIDO_EM = datetime(2026, 9, 1, tzinfo=UTC)


def _emprestimo() -> Emprestimo:
    emprestimo = Emprestimo(
        contrato_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        carteira_id=uuid.uuid4(),
        devedor_id=uuid.uuid4(),
        principal_original=VALOR,
        moeda="BRL",
        _parametros_financeiros={
            "valor_contratado": VALOR,
            "taxa_juros_mensal": TAXA,
            "quantidade_parcelas": 10,
            "primeiro_vencimento": date(2026, 9, 1),
            "moeda": "BRL",
        },
    )
    emprestimo.criado_em = CRIADO_EM
    return emprestimo


@pytest.mark.parametrize(
    "valor",
    ["100.00", "500.00", "1500.00", "10500.00", "99999.00"],
)
def test_previsao_bate_com_o_pagamento_realmente_registrado(valor: str) -> None:
    """Caracterizacao: a extracao nao mudou o resultado de registrar_pagamento."""
    motor = MotorFinanceiro()
    emprestimo = _emprestimo()

    previsto = prever_alocacao(
        motor=motor,
        emprestimo=emprestimo,
        valor=Decimal(valor),
        data_referencia=RECEBIDO_EM.date(),
    )
    resultado = motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=Decimal(valor),
        recebido_em=RECEBIDO_EM,
        chave_idempotencia=f"chave-{valor}",
        usuario_id=uuid.uuid4(),
    )
    pagamento = resultado.pagamento

    assert previsto.valor_juros == pagamento.valor_juros
    assert previsto.valor_encargos == pagamento.valor_encargos
    assert previsto.valor_amortizacao == pagamento.valor_amortizacao
    assert previsto.valor_devolvido == pagamento.valor_devolvido


def test_valor_abaixo_do_juro_nao_amortiza_nada() -> None:
    motor = MotorFinanceiro()
    saldo = motor.consultar_saldo(emprestimo=_emprestimo(), data_referencia=RECEBIDO_EM.date())
    valor = saldo.juros - Decimal("1.00")

    previsto = prever_alocacao(
        motor=motor,
        emprestimo=_emprestimo(),
        valor=valor,
        data_referencia=RECEBIDO_EM.date(),
    )

    assert previsto.valor_juros == valor
    assert previsto.valor_amortizacao == Decimal("0.00")
    assert previsto.valor_devolvido == Decimal("0.00")


def test_valor_acima_da_quitacao_devolve_a_sobra() -> None:
    motor = MotorFinanceiro()
    saldo = motor.consultar_saldo(emprestimo=_emprestimo(), data_referencia=RECEBIDO_EM.date())
    sobra = Decimal("250.00")

    previsto = prever_alocacao(
        motor=motor,
        emprestimo=_emprestimo(),
        valor=saldo.total + sobra,
        data_referencia=RECEBIDO_EM.date(),
    )

    assert previsto.valor_devolvido == sobra
    assert previsto.valor_amortizacao == saldo.principal
    assert previsto.valor_juros == saldo.juros


def test_previsao_nao_registra_pagamento_nem_move_o_emprestimo() -> None:
    """Leitura pura: prever duas vezes nao cria nada nem muda o saldo."""
    motor = MotorFinanceiro()
    emprestimo = _emprestimo()
    antes = motor.consultar_saldo(emprestimo=emprestimo, data_referencia=RECEBIDO_EM.date())

    for _ in range(2):
        prever_alocacao(
            motor=motor,
            emprestimo=emprestimo,
            valor=Decimal("1500.00"),
            data_referencia=RECEBIDO_EM.date(),
        )

    depois = motor.consultar_saldo(emprestimo=emprestimo, data_referencia=RECEBIDO_EM.date())
    assert depois.total == antes.total
    assert emprestimo.ultimo_pagamento_em is None
