"""ComprovantePagamento (IMP-390): alegacao do devedor, nunca prova.

O comprovante e uma imagem — forja-lo e trivial. Ele entra no fluxo como o que
o devedor DIZ ter pago; quem verifica e a Credora, conferindo a propria conta.
Estes testes fixam essa natureza: o objeto guarda, correlaciona e some na
quitacao, mas nao autentica nada.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.comprovante import (
    ComprovantePagamento,
    ComprovanteState,
    TipoMidiaComprovante,
)

AGORA = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
CONTEUDO = b"imagem-do-comprovante"
SHA = "a" * 64


def _novo(valor_extraido: str | None = "1627.00") -> ComprovantePagamento:
    return ComprovantePagamento.receber(
        tenant_id=uuid.uuid4(),
        emprestimo_id=uuid.uuid4(),
        devedor_id=uuid.uuid4(),
        conteudo=CONTEUDO,
        sha256=SHA,
        tipo_midia=TipoMidiaComprovante.IMAGEM_JPEG,
        valor_extraido=Decimal(valor_extraido) if valor_extraido else None,
        valor_informado=Decimal("1627.00"),
        agora=AGORA,
    )


def test_nasce_recebido_sem_pagamento_associado() -> None:
    comprovante = _novo()

    assert comprovante.estado is ComprovanteState.RECEBIDO
    assert comprovante.pagamento_id is None
    assert comprovante.tamanho == len(CONTEUDO)


def test_conteudo_vazio_nao_e_comprovante() -> None:
    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        ComprovantePagamento.receber(
            tenant_id=uuid.uuid4(),
            emprestimo_id=uuid.uuid4(),
            devedor_id=uuid.uuid4(),
            conteudo=b"",
            sha256=SHA,
            tipo_midia=TipoMidiaComprovante.IMAGEM_JPEG,
            valor_extraido=None,
            valor_informado=None,
            agora=AGORA,
        )

    assert excinfo.value.codigo == "INV-001"


def test_valor_ilegivel_e_estado_valido_porque_a_credora_decide() -> None:
    """Nao conseguir ler o valor nao invalida o comprovante: ela ve a imagem."""
    comprovante = _novo(valor_extraido=None)

    assert comprovante.valor_extraido is None
    assert comprovante.divergente is False


def test_valor_lido_diferente_do_informado_fica_marcado_sem_escolher_um() -> None:
    comprovante = ComprovantePagamento.receber(
        tenant_id=uuid.uuid4(),
        emprestimo_id=uuid.uuid4(),
        devedor_id=uuid.uuid4(),
        conteudo=CONTEUDO,
        sha256=SHA,
        tipo_midia=TipoMidiaComprovante.PDF,
        valor_extraido=Decimal("1627.00"),
        valor_informado=Decimal("1600.00"),
        agora=AGORA,
    )

    assert comprovante.divergente is True
    assert comprovante.valor_extraido == Decimal("1627.00")
    assert comprovante.valor_informado == Decimal("1600.00")


def test_lancar_associa_o_pagamento_da_credora() -> None:
    comprovante = _novo()
    pagamento_id = uuid.uuid4()

    comprovante.lancar(pagamento_id=pagamento_id, agora=AGORA)

    assert comprovante.estado is ComprovanteState.LANCADO
    assert comprovante.pagamento_id == pagamento_id


def test_recusar_guarda_o_motivo_e_nao_associa_pagamento() -> None:
    comprovante = _novo()

    comprovante.recusar(motivo="nao encontrei na conta", agora=AGORA)

    assert comprovante.estado is ComprovanteState.RECUSADO
    assert comprovante.motivo_recusa == "nao encontrei na conta"
    assert comprovante.pagamento_id is None


@pytest.mark.parametrize("terminal", ["lancar", "recusar"])
def test_estado_terminal_nao_muda_de_ideia(terminal: str) -> None:
    comprovante = _novo()
    if terminal == "lancar":
        comprovante.lancar(pagamento_id=uuid.uuid4(), agora=AGORA)
    else:
        comprovante.recusar(motivo="nao encontrei", agora=AGORA)

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        comprovante.lancar(pagamento_id=uuid.uuid4(), agora=AGORA)
    assert excinfo.value.codigo == "INV-002"

    with pytest.raises(ViolacaoInvarianteError):
        comprovante.recusar(motivo="outro", agora=AGORA)


def test_expurgar_apaga_a_imagem_e_preserva_a_correlacao() -> None:
    """Quitou, limpou — mas o vinculo com o Pagamento fica.

    A prova contabil e o Pagamento, a memoria de calculo e a trilha; nenhum
    deles depende da imagem. Guardar documento de terceiro depois que a divida
    acabou e risco sem contrapartida.
    """
    comprovante = _novo()
    pagamento_id = uuid.uuid4()
    comprovante.lancar(pagamento_id=pagamento_id, agora=AGORA)

    comprovante.expurgar(agora=AGORA)

    assert comprovante.conteudo is None
    assert comprovante.valor_extraido is None
    assert comprovante.valor_informado is None
    assert comprovante.expurgado_em == AGORA
    assert comprovante.pagamento_id == pagamento_id
    assert comprovante.estado is ComprovanteState.LANCADO


def test_expurgo_e_idempotente() -> None:
    comprovante = _novo()
    comprovante.expurgar(agora=AGORA)
    primeiro = comprovante.expurgado_em

    comprovante.expurgar(agora=datetime(2026, 12, 1, tzinfo=UTC))

    assert comprovante.expurgado_em == primeiro


def test_repr_nao_despeja_o_binario() -> None:
    assert "imagem-do-comprovante" not in repr(_novo())
