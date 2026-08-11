"""Testes de estados e reavaliacao de promessa (IMP-173)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.promessa import (
    ApropriacaoPagamento,
    PromessaPagamento,
    PromessaPagamentoState,
)

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CARTEIRA_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEVEDOR_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EMPRESTIMO_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
USUARIO_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _base_promessa(data_promessa: date | None = None) -> PromessaPagamento:
    return PromessaPagamento.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        emprestimo_id=EMPRESTIMO_ID,
        criado_por_usuario_id=USUARIO_ID,
        valor_declarado=Decimal("150.00"),
        data_promessa=(data_promessa or (datetime.now(UTC).date() + timedelta(days=7))),
    )


def test_nao_cria_promessa_com_valor_zero() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        PromessaPagamento.criar(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
            emprestimo_id=EMPRESTIMO_ID,
            criado_por_usuario_id=USUARIO_ID,
            valor_declarado=Decimal("0.00"),
            data_promessa=datetime.now(UTC).date(),
        )

    assert exc.value.codigo == "EPIC-007"


def test_descumprida_apos_data_com_saldo_incompleto() -> None:
    promessa = _base_promessa()

    promessa.apropriar_pagamento(
        ApropriacaoPagamento(
            promessa_id=promessa.id,
            pagamento_id=uuid.uuid4(),
            valor=Decimal("40.00"),
            realizado_em=datetime.now(UTC),
        )
    )

    assert promessa.reavaliar_por_referencia(
        data_referencia=promessa.data_promessa + timedelta(days=1)
    )
    assert promessa.estado is PromessaPagamentoState.DESCUMPRIDA


def test_descumprimento_nao_altera_cumprida() -> None:
    data_futura = datetime.now(UTC).date() + timedelta(days=5)
    promessa = _base_promessa(data_promessa=data_futura)
    promessa.apropriar_pagamento(
        ApropriacaoPagamento(
            promessa_id=promessa.id,
            pagamento_id=uuid.uuid4(),
            valor=Decimal("150.00"),
            realizado_em=datetime.now(UTC),
        )
    )
    promessa.reavaliar_por_referencia(data_referencia=promessa.data_promessa + timedelta(days=10))
    assert promessa.estado is PromessaPagamentoState.CUMPRIDA


def test_retrocesso_por_estorno_de_pagamento_gera_invalidacao() -> None:
    promessa = _base_promessa()
    pagamento_id = uuid.uuid4()
    promessa.apropriar_pagamento(
        ApropriacaoPagamento(
            promessa_id=promessa.id,
            pagamento_id=pagamento_id,
            valor=Decimal("150.00"),
            realizado_em=datetime.now(UTC),
        )
    )
    assert promessa.estado is PromessaPagamentoState.CUMPRIDA

    invalidou = promessa.desfazer_apropriacao(
        pagamento_id=pagamento_id,
        estorno_id=uuid.uuid4(),
        data_referencia=promessa.data_promessa,
    )
    assert invalidou
    assert _estado(promessa) is PromessaPagamentoState.PENDENTE
    assert len(promessa.invalidacoes) == 1


def _estado(promessa: PromessaPagamento) -> PromessaPagamentoState:
    return promessa.estado
