"""Persistencia da CobrancaPix (IMP-374).

O ponto do arquivo e a INV-004: um unico Pix `pendente` por emprestimo. Ela
nao cabe no Aggregate — dois Pix vivos estariam certos isoladamente e errados
em conjunto —, entao quem a garante e o indice unico parcial. Um teste que so
exercitasse o objeto em memoria nao provaria nada.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.repositories.test_operacao_diaria_repositories import (
    _contexto_operacao,
)

from emprestimo.domain.credit.cobranca_pix import (
    CobrancaPix,
    CobrancaPixState,
    OrigemCobrancaPix,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

AGORA = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)


def _cobranca(contexto: object, valor: str = "500.00") -> CobrancaPix:
    ctx = contexto
    return CobrancaPix.criar(
        tenant_id=ctx.tenant_id,  # type: ignore[attr-defined]
        carteira_id=ctx.carteira_id,  # type: ignore[attr-defined]
        emprestimo_id=ctx.emprestimo_id,  # type: ignore[attr-defined]
        devedor_id=ctx.devedor_id,  # type: ignore[attr-defined]
        valor=Decimal(valor),
        juro_periodo=Decimal("100.00"),
        quitacao=Decimal("5000.00"),
        origem=OrigemCobrancaPix.COPILOT_DEVEDOR,
        criado_por=ctx.usuario_id,  # type: ignore[attr-defined]
        agora=AGORA,
    )


def test_ida_e_volta_preserva_estado_valores_e_referencia(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    cobranca = _cobranca(contexto)
    cobranca.registrar_no_provedor(mp_payment_id="mp-1", copia_cola="000201...", qr_base64="AAA")

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.cobranca_pix.save(cobranca)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        lida = uow.cobranca_pix.find_by_external_reference(cobranca.external_reference)

    assert lida is not None
    assert lida.id == cobranca.id
    assert lida.estado is CobrancaPixState.PENDENTE
    assert lida.valor == Decimal("500.00")
    assert lida.origem is OrigemCobrancaPix.COPILOT_DEVEDOR
    assert lida.mp_payment_id == "mp-1"
    assert lida.copia_cola == "000201..."
    assert lida.expira_em == AGORA + timedelta(minutes=60)


def test_inv_004_o_banco_recusa_o_segundo_pendente_do_mesmo_emprestimo(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.cobranca_pix.save(_cobranca(contexto))
        uow.commit()

    with pytest.raises(IntegrityError), SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.cobranca_pix.save(_cobranca(contexto, valor="700.00"))
        uow.commit()


def test_terminal_libera_o_emprestimo_para_um_pix_novo(
    session_factory: sessionmaker[Session],
) -> None:
    """Expirado nao ocupa a vaga: o devedor pede outro, como a D3 previu."""
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    primeira = _cobranca(contexto)

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.cobranca_pix.save(primeira)
        uow.commit()

    primeira.expirar(agora=AGORA + timedelta(minutes=61))
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.cobranca_pix.save(primeira)
        uow.cobranca_pix.save(_cobranca(contexto, valor="700.00"))
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        pendente = uow.cobranca_pix.find_pendente_por_emprestimo(contexto.emprestimo_id)
        todas = uow.cobranca_pix.listar_por_emprestimo(contexto.emprestimo_id)

    assert pendente is not None and pendente.valor == Decimal("700.00")
    assert len(todas) == 2


def test_listar_pendentes_expirados_so_traz_quem_passou_da_validade(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.cobranca_pix.save(_cobranca(contexto))
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        dentro = uow.cobranca_pix.listar_pendentes_expirados(AGORA + timedelta(minutes=59))
        fora = uow.cobranca_pix.listar_pendentes_expirados(AGORA + timedelta(minutes=61))

    assert all(item.emprestimo_id != contexto.emprestimo_id for item in dentro)
    assert any(item.emprestimo_id == contexto.emprestimo_id for item in fora)


def test_pagamento_divergente_persiste_o_valor_recebido_e_a_marca(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    cobranca = _cobranca(contexto)
    cobranca.pagar(mp_payment_id="mp-2", valor_recebido=Decimal("480.00"))

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.cobranca_pix.save(cobranca)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        lida = uow.cobranca_pix.find_by_id(cobranca.id)

    assert lida is not None
    assert lida.estado is CobrancaPixState.PAGO
    assert lida.valor_recebido == Decimal("480.00")
    assert lida.divergente is True
