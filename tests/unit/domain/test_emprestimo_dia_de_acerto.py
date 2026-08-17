"""O Emprestimo conhece o proprio dia de acerto (DR-004, PLAN-030 fase 1)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.emprestimo import Emprestimo

CRIADO_EM = datetime(2026, 8, 17, tzinfo=UTC)


def _emprestimo(**parametros: object) -> Emprestimo:
    emprestimo = Emprestimo(
        contrato_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        carteira_id=uuid.uuid4(),
        devedor_id=uuid.uuid4(),
        principal_original=Decimal("10000"),
        moeda="BRL",
        _parametros_financeiros={
            "valor_contratado": Decimal("10000"),
            "taxa_juros_mensal": Decimal("0.05"),
            "moeda": "BRL",
            **parametros,
        },
    )
    emprestimo.criado_em = CRIADO_EM
    return emprestimo


def test_emprestimo_sem_dia_combinado_nao_tem_acerto() -> None:
    """Estado legitimo enquanto os dois modelos convivem.

    Os emprestimos anteriores a DR-004 nasceram com plano de parcelas e nao tem
    dia combinado. Ausencia nao pode ser tratada como erro ate o plano sair.
    """
    emprestimo = _emprestimo()

    assert emprestimo.dia_de_acerto is None
    assert emprestimo.proximo_acerto_em(date(2026, 9, 1)) is None
    assert emprestimo.acerto_vigente_em(date(2026, 9, 1)) is None


def test_primeiro_acerto_conta_da_data_do_emprestimo() -> None:
    # O caso do Credor: emprestado em 17/08, acerta todo dia 10.
    emprestimo = _emprestimo(dia_de_acerto=10)

    assert emprestimo.dia_de_acerto == 10
    assert emprestimo.proximo_acerto_em(CRIADO_EM.date()) == date(2026, 9, 10)


def test_acerto_vigente_e_o_ultimo_que_ja_deveria_ter_ocorrido() -> None:
    emprestimo = _emprestimo(dia_de_acerto=10)

    # Antes do primeiro acerto ainda nao ha nada devido.
    assert emprestimo.acerto_vigente_em(date(2026, 9, 9)) is None
    # No proprio dia ja ha.
    assert emprestimo.acerto_vigente_em(date(2026, 9, 10)) == date(2026, 9, 10)
    # Em atraso, continua sendo o de setembro ate outubro chegar.
    assert emprestimo.acerto_vigente_em(date(2026, 10, 9)) == date(2026, 9, 10)
    assert emprestimo.acerto_vigente_em(date(2026, 10, 10)) == date(2026, 10, 10)
    # Meses depois, o vigente acompanha.
    assert emprestimo.acerto_vigente_em(date(2027, 1, 15)) == date(2027, 1, 10)


def test_dia_invalido_e_recusado_ao_ser_lido() -> None:
    emprestimo = _emprestimo(dia_de_acerto=32)

    with pytest.raises(ViolacaoInvarianteError):
        _ = emprestimo.dia_de_acerto


def test_parametros_permanecem_protegidos_contra_mutacao_externa() -> None:
    emprestimo = _emprestimo(dia_de_acerto=10)

    parametros = emprestimo.parametros_financeiros
    parametros["dia_de_acerto"] = 25

    assert emprestimo.dia_de_acerto == 10
