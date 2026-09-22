"""Expurgo do comprovante na quitacao (IMP-390, decisao D15).

"Quitou, limpou" — mas so a imagem. O `Pagamento`, a memoria de calculo e a
trilha de auditoria permanecem: sao eles a prova contabil, e nenhum depende do
documento. Este arquivo existe para provar as duas metades juntas; provar so a
primeira deixaria passar um expurgo que levasse a prova junto.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker
from tests.integration.repositories.test_operacao_diaria_repositories import _contexto_operacao

from emprestimo.application.motor_financeiro import QuitacaoRenegociacaoService
from emprestimo.domain.credit.comprovante import (
    ComprovantePagamento,
    ComprovanteState,
    TipoMidiaComprovante,
)
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

CONTEUDO = b"imagem-do-comprovante-real"
AGORA = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _comprovante(contexto: object, conteudo: bytes = CONTEUDO) -> ComprovantePagamento:
    ctx = contexto
    return ComprovantePagamento.receber(
        tenant_id=ctx.tenant_id,  # type: ignore[attr-defined]
        emprestimo_id=ctx.emprestimo_id,  # type: ignore[attr-defined]
        devedor_id=ctx.devedor_id,  # type: ignore[attr-defined]
        conteudo=conteudo,
        sha256=hashlib.sha256(conteudo).hexdigest(),
        tipo_midia=TipoMidiaComprovante.IMAGEM_JPEG,
        valor_extraido=Decimal("1627.00"),
        valor_informado=Decimal("1627.00"),
        agora=AGORA,
    )


def test_quitacao_apaga_a_imagem_e_preserva_pagamento_memoria_e_trilha(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    comprovante = _comprovante(contexto)
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.comprovante_pagamento.save(comprovante)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        pagamentos_antes = len(uow.pagamento.find_by_emprestimo_id(contexto.emprestimo_id))

    QuitacaoRenegociacaoService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        SqlAlchemyAuditoriaRegistro(session_factory),
    ).quitar(
        emprestimo_id=contexto.emprestimo_id,
        tenant_id=contexto.tenant_id,
        usuario_id=contexto.usuario_id,
        recebido_em=AGORA,
        idempotency_key=str(uuid.uuid4()),
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        lido = uow.comprovante_pagamento.find_by_id(comprovante.id)
        pagamentos = uow.pagamento.find_by_emprestimo_id(contexto.emprestimo_id)
        memorias = uow.memoria_calculo.find_by_emprestimo_id(contexto.emprestimo_id)

    assert lido is not None, "a linha fica: o vinculo sobrevive ao documento"
    assert lido.conteudo is None
    assert lido.valor_extraido is None
    assert lido.expurgado_em is not None
    # A prova contabil nao depende da imagem.
    assert len(pagamentos) > pagamentos_antes
    assert memorias


def test_expurgo_alcanca_todos_os_comprovantes_do_emprestimo(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    primeiro = _comprovante(contexto, b"primeiro-comprovante")
    segundo = _comprovante(contexto, b"segundo-comprovante")
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.comprovante_pagamento.save(primeiro)
        uow.comprovante_pagamento.save(segundo)
        uow.commit()

    QuitacaoRenegociacaoService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        SqlAlchemyAuditoriaRegistro(session_factory),
    ).quitar(
        emprestimo_id=contexto.emprestimo_id,
        tenant_id=contexto.tenant_id,
        usuario_id=contexto.usuario_id,
        recebido_em=AGORA,
        idempotency_key=str(uuid.uuid4()),
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        todos = uow.comprovante_pagamento.listar_por_emprestimo(contexto.emprestimo_id)

    assert len(todos) == 2
    assert all(item.conteudo is None and item.expurgado_em is not None for item in todos)


def test_emprestimo_vivo_mantem_o_comprovante(session_factory: sessionmaker[Session]) -> None:
    """Sem quitacao, nada e apagado — o expurgo e da quitacao, nao do tempo."""
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    comprovante = _comprovante(contexto)
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.comprovante_pagamento.save(comprovante)
        uow.commit()

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        lido = uow.comprovante_pagamento.find_by_id(comprovante.id)

    assert lido is not None
    assert lido.conteudo == CONTEUDO
    assert lido.estado is ComprovanteState.RECEBIDO
