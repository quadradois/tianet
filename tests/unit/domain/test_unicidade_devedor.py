"""Testes unitários do UnicidadeDevedorService (IMP-046, DOMAIN-023)."""

from __future__ import annotations

import uuid

import pytest

from emprestimo.domain.common.errors import DevedorJaExisteError
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.ports import DevedorUniquenessChecker
from emprestimo.domain.credit.unicidade_devedor import UnicidadeDevedorService

CARTEIRA_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DOCUMENTO = Documento.from_str("52998224725")
OUTRO_DOCUMENTO = Documento.from_str("11144477735")


class _FakeChecker(DevedorUniquenessChecker):
    """Fake do port para testes."""

    def __init__(self, existente: bool) -> None:
        self._existente = existente

    def exists_by_documento_carteira(self, documento: Documento, carteira_id: uuid.UUID) -> bool:
        assert carteira_id == CARTEIRA_ID
        return self._existente


def test_documento_disponivel_nao_levanta_erro() -> None:
    checker = _FakeChecker(existente=False)
    service = UnicidadeDevedorService(checker)

    service.verificar_documento_disponivel(DOCUMENTO, CARTEIRA_ID)


def test_documento_ja_existente_levanta_erro() -> None:
    checker = _FakeChecker(existente=True)
    service = UnicidadeDevedorService(checker)

    with pytest.raises(DevedorJaExisteError) as exc:
        service.verificar_documento_disponivel(DOCUMENTO, CARTEIRA_ID)

    assert exc.value.documento == DOCUMENTO.valor
    assert exc.value.carteira_id == CARTEIRA_ID


def test_verificacao_independe_do_estado_do_devedor() -> None:
    """RN-002: verificação considera Ativos e Inativos (o checker simula isso)."""
    checker = _FakeChecker(existente=True)
    service = UnicidadeDevedorService(checker)

    with pytest.raises(DevedorJaExisteError):
        service.verificar_documento_disponivel(DOCUMENTO, CARTEIRA_ID)


def test_outro_documento_na_mesma_carteira_nao_conflita() -> None:
    checker_outro = _FakeChecker(existente=False)
    service = UnicidadeDevedorService(checker_outro)

    service.verificar_documento_disponivel(OUTRO_DOCUMENTO, CARTEIRA_ID)
