"""Testes unitários da Entity Contato (IMP-044, DOMAIN-021)."""

from __future__ import annotations

import uuid

from emprestimo.domain.credit.contato import (
    Contato,
    ContatoInvalidoError,
    TipoContato,
)

DEVEDOR_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")


# --------------------------------------------------------------------------- #
# Criação e atributos
# --------------------------------------------------------------------------- #


def test_cria_contato_telefone_valid() -> None:
    contato = Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.TELEFONE, valor="(11) 1234-5678")

    assert contato.devedor_id == DEVEDOR_ID
    assert contato.tipo == TipoContato.TELEFONE
    assert contato.valor == "(11) 1234-5678"
    assert contato.id is not None


def test_preferencial_default_e_false() -> None:
    contato = Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.EMAIL, valor="a@b.com")

    assert contato.preferencial is False


def test_cria_contato_email() -> None:
    contato = Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.EMAIL, valor="joao@exemplo.com")

    assert contato.tipo == TipoContato.EMAIL
    assert contato.valor == "joao@exemplo.com"


# --------------------------------------------------------------------------- #
# RN-004 — valor conforme o tipo (DOMAIN-021)
# --------------------------------------------------------------------------- #


def test_aceita_telefone_fixo() -> None:
    contato = Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.TELEFONE, valor="(11) 1234-5678")

    assert contato.valor == "(11) 1234-5678"


def test_aceita_celular_com_plus() -> None:
    contato = Contato(
        devedor_id=DEVEDOR_ID,
        tipo=TipoContato.WHATSAPP,
        valor="+55 11 98765-4321",
    )

    assert contato.valor == "+55 11 98765-4321"


def test_rejeita_telefone_com_letras() -> None:
    try:
        Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.TELEFONE, valor="abc12345")
        raise AssertionError("esperava-se ContatoInvalidoError")
    except ContatoInvalidoError as exc:
        assert exc.tipo == TipoContato.TELEFONE


def test_rejeita_email_invalido() -> None:
    try:
        Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.EMAIL, valor="email-errado")
        raise AssertionError("esperava-se ContatoInvalidoError")
    except ContatoInvalidoError as exc:
        assert exc.tipo == TipoContato.EMAIL


def test_rejeita_email_sem_arroba() -> None:
    try:
        Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.EMAIL, valor="joaoexemplo.com")
        raise AssertionError("esperava-se ContatoInvalidoError")
    except ContatoInvalidoError as exc:
        assert exc.tipo == TipoContato.EMAIL


def test_rejeita_valor_vazio() -> None:
    try:
        Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.TELEFONE, valor="   ")
        raise AssertionError("esperava-se ContatoInvalidoError")
    except ContatoInvalidoError as exc:
        assert exc.tipo == TipoContato.TELEFONE
