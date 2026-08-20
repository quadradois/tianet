"""Testes do texto do comprovante do lancamento (IMP-307)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from emprestimo.application.comprovante import (
    ComprovanteLancamento,
    montar_texto_comprovante,
)


def test_monta_texto_exclusivamente_com_o_snapshot_recebido() -> None:
    emprestimo_id = uuid.UUID("11111111-1111-4111-8111-111111111111")
    comprovante = ComprovanteLancamento(
        tenant_id=uuid.uuid4(),
        carteira_id=uuid.uuid4(),
        devedor_id=uuid.uuid4(),
        nome_devedor="Maria da Silva",
        destinatario_whatsapp="+5511999999999",
        emprestimo_id=emprestimo_id,
        valor_contratado=Decimal("6000.00"),
        moeda="BRL",
        taxa_juros_mensal_percentual=Decimal("3.0000"),
        dia_de_acerto=10,
        primeiro_acerto_em=date(2026, 9, 10),
    )

    assert montar_texto_comprovante(comprovante) == (
        "Comprovante do lancamento\n"
        "Devedor: Maria da Silva\n"
        f"Emprestimo: {emprestimo_id}\n"
        "Valor contratado: BRL 6.000,00\n"
        "Taxa de juros mensal: 3,00%\n"
        "Dia de acerto: 10\n"
        "Primeiro acerto: 10/09/2026"
    )
