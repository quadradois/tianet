"""Juros sobre saldo devedor, acumulados por trecho (DR-004, PLAN-030).

O Credor descreveu o produto: o devedor toma o valor, na data de pagamento pede
a atualizacao, paga o quanto puder, e o sistema separa juros de amortizacao ate
quitar. Este arquivo fixa o que esse modelo exige do Motor.

A DR-004 encontrou a acumulacao medindo sempre da criacao do emprestimo ate a
data de referencia, com o saldo **atual** aplicado sobre **todo** o periodo
decorrido — o que devolve retroativamente juros ja corretamente cobrados a cada
amortizacao.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from emprestimo.domain.credit.emprestimo import Emprestimo
from emprestimo.domain.credit.motor_financeiro import MotorFinanceiro

TAXA = Decimal("0.05")
VALOR = Decimal("10000")
CRIADO_EM = datetime(2026, 8, 1, tzinfo=UTC)


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


def test_primeiro_periodo_cobra_a_taxa_sobre_o_valor_emprestado() -> None:
    saldo = MotorFinanceiro().consultar_saldo(
        emprestimo=_emprestimo(),
        data_referencia=date(2026, 9, 1),
    )

    assert saldo.principal == Decimal("10000.00")
    assert saldo.juros == Decimal("500.00")


def test_pagamento_separa_juros_de_amortizacao_pela_ordem_do_dominio() -> None:
    emprestimo = _emprestimo()
    motor = MotorFinanceiro()

    resultado = motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=Decimal("5000.00"),
        recebido_em=datetime(2026, 9, 1, tzinfo=UTC),
        chave_idempotencia="acerto-1",
        usuario_id=uuid.uuid4(),
    )

    # Juros primeiro, amortizacao com o que sobra: o devedor nunca amortiza
    # enquanto houver juros do periodo em aberto.
    assert resultado.pagamento.valor_juros == Decimal("500.00")
    assert resultado.pagamento.valor_amortizacao == Decimal("4500.00")


def test_periodo_seguinte_cobra_sobre_o_saldo_que_ficou_e_nao_reabre_o_anterior() -> None:
    """O caso que a DR-004 mediu: 41,13 onde deveriam ser 275,00.

    Depois de amortizar 4.500, o saldo e 5.500. Um mes de setembro sobre 5.500 a
    5% custa 275,00. A acumulacao anterior aplicava 5.500 tambem sobre agosto,
    mes em que o devedor ainda devia 10.000, e depois descontava os 500 ja
    pagos — devolvendo juros que estavam corretos.
    """
    emprestimo = _emprestimo()
    motor = MotorFinanceiro()
    motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=Decimal("5000.00"),
        recebido_em=datetime(2026, 9, 1, tzinfo=UTC),
        chave_idempotencia="acerto-1",
        usuario_id=uuid.uuid4(),
    )

    saldo = motor.consultar_saldo(emprestimo=emprestimo, data_referencia=date(2026, 10, 1))

    assert saldo.principal == Decimal("5500.00")
    assert saldo.juros == Decimal("275.00")


def test_dois_acertos_seguidos_mantem_cada_trecho_no_seu_saldo() -> None:
    emprestimo = _emprestimo()
    motor = MotorFinanceiro()
    usuario = uuid.uuid4()
    motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=Decimal("5000.00"),
        recebido_em=datetime(2026, 9, 1, tzinfo=UTC),
        chave_idempotencia="acerto-1",
        usuario_id=usuario,
    )
    # Segundo acerto: 275,00 de juros de setembro mais 1.725,00 de amortizacao.
    motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=Decimal("2000.00"),
        recebido_em=datetime(2026, 10, 1, tzinfo=UTC),
        chave_idempotencia="acerto-2",
        usuario_id=usuario,
    )

    saldo = motor.consultar_saldo(emprestimo=emprestimo, data_referencia=date(2026, 11, 1))

    # 5.500 - 1.725 = 3.775; um mes de outubro a 5% sobre 3.775 = 188,75.
    assert saldo.principal == Decimal("3775.00")
    assert saldo.juros == Decimal("188.75")


def test_sem_pagamento_a_acumulacao_continua_sobre_o_valor_cheio() -> None:
    saldo = MotorFinanceiro().consultar_saldo(
        emprestimo=_emprestimo(),
        data_referencia=date(2026, 10, 1),
    )

    # Agosto (31/31) e setembro (30/30) cheios sobre 10.000: 500,00 + 500,00.
    assert saldo.principal == Decimal("10000.00")
    assert saldo.juros == Decimal("1000.00")
