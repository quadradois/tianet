"""CobrancaPix (IMP-373): invariantes do Pix do acerto e transicoes terminais."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.cobranca_pix import (
    CobrancaPix,
    CobrancaPixState,
    OrigemCobrancaPix,
)

AGORA = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
JURO = Decimal("450.00")
QUITACAO = Decimal("5200.00")


def _criar(valor: str = "800.00") -> CobrancaPix:
    return CobrancaPix.criar(
        tenant_id=uuid.uuid4(),
        carteira_id=uuid.uuid4(),
        emprestimo_id=uuid.uuid4(),
        devedor_id=uuid.uuid4(),
        valor=Decimal(valor),
        juro_periodo=JURO,
        quitacao=QUITACAO,
        origem=OrigemCobrancaPix.COPILOT_DEVEDOR,
        criado_por=uuid.uuid4(),
        agora=AGORA,
    )


def test_nasce_pendente_com_validade_de_60_minutos_e_referencia_propria() -> None:
    cobranca = _criar()

    assert cobranca.estado is CobrancaPixState.PENDENTE
    assert cobranca.expira_em == AGORA + timedelta(minutes=60)
    assert cobranca.external_reference == str(cobranca.id)
    assert cobranca.divergente is False


def test_aceita_o_piso_e_o_teto_apurados_pelo_motor() -> None:
    assert _criar("450.00").valor == JURO
    assert _criar("5200.00").valor == QUITACAO


@pytest.mark.parametrize("valor", ["449.99", "0.00", "-1.00", "5200.01", "9999.00"])
def test_recusa_valor_fora_do_intervalo_do_motor(valor: str) -> None:
    """INV-001: o devedor deve no minimo o juro e nunca mais que a quitacao."""
    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        _criar(valor)

    assert excinfo.value.codigo == "INV-001"


def test_pagar_registra_identificador_do_provedor_e_valor_recebido() -> None:
    cobranca = _criar()

    cobranca.pagar(mp_payment_id="1234567890", valor_recebido=Decimal("800.00"))

    assert cobranca.estado is CobrancaPixState.PAGO
    assert cobranca.mp_payment_id == "1234567890"
    assert cobranca.divergente is False


def test_valor_recebido_diferente_marca_divergente_sem_recusar_o_dinheiro() -> None:
    cobranca = _criar()

    cobranca.pagar(mp_payment_id="1", valor_recebido=Decimal("750.00"))

    assert cobranca.estado is CobrancaPixState.PAGO
    assert cobranca.valor_recebido == Decimal("750.00")
    assert cobranca.divergente is True


def test_expira_somente_depois_da_validade() -> None:
    cobranca = _criar()

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        cobranca.expirar(agora=AGORA + timedelta(minutes=59))
    assert excinfo.value.codigo == "INV-003"

    cobranca.expirar(agora=AGORA + timedelta(minutes=61))
    assert cobranca.estado is CobrancaPixState.EXPIRADO


@pytest.mark.parametrize("terminal", ["pagar", "expirar", "cancelar"])
def test_estado_terminal_nao_transiciona_de_novo(terminal: str) -> None:
    """INV-002: pago, expirado e cancelado sao finais — inclusive para si mesmos."""
    cobranca = _criar()
    fora_da_validade = AGORA + timedelta(minutes=61)
    if terminal == "pagar":
        cobranca.pagar(mp_payment_id="1", valor_recebido=Decimal("800.00"))
    elif terminal == "expirar":
        cobranca.expirar(agora=fora_da_validade)
    else:
        cobranca.cancelar()

    acoes: list[Callable[[], None]] = [
        lambda: cobranca.pagar(mp_payment_id="2", valor_recebido=Decimal("800.00")),
        lambda: cobranca.expirar(agora=fora_da_validade),
        lambda: cobranca.cancelar(),
    ]
    for acao in acoes:
        with pytest.raises(ViolacaoInvarianteError) as excinfo:
            acao()
        assert excinfo.value.codigo == "INV-002"


def test_pagamento_tardio_vence_a_expiracao_porque_o_dinheiro_entrou() -> None:
    """O provedor pode confirmar depois da validade; recusar seria perder o pagamento."""
    cobranca = _criar()
    cobranca.expirar(agora=AGORA + timedelta(minutes=61))

    assert cobranca.estado is CobrancaPixState.EXPIRADO
    with pytest.raises(ViolacaoInvarianteError):
        cobranca.pagar(mp_payment_id="1", valor_recebido=Decimal("800.00"))
