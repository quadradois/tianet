"""Testes unitários da Entity Contato (IMP-044, DOMAIN-021)."""

from __future__ import annotations

import uuid

import pytest

from emprestimo.domain.credit.contato import (
    Contato,
    ContatoInvalidoError,
    DevedorIdInvalidoError,
    TipoContato,
    TipoContatoInvalidoError,
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


# --------------------------------------------------------------------------- #
# Validações de precisão (TASK-091-A)
# --------------------------------------------------------------------------- #


def test_rejeita_tipo_invalido() -> None:
    with pytest.raises(TipoContatoInvalidoError):
        Contato(devedor_id=DEVEDOR_ID, tipo="telefone", valor="(11) 1234-5678")  # type: ignore[arg-type]


def test_rejeita_tipo_nulo() -> None:
    with pytest.raises(TipoContatoInvalidoError):
        Contato(devedor_id=DEVEDOR_ID, tipo=None, valor="(11) 1234-5678")  # type: ignore[arg-type]


def test_rejeita_devedor_id_invalido() -> None:
    with pytest.raises(DevedorIdInvalidoError):
        Contato(devedor_id="nao-uuid", tipo=TipoContato.TELEFONE, valor="(11) 1234-5678")  # type: ignore[arg-type]


def test_rejeita_devedor_id_nulo() -> None:
    with pytest.raises(DevedorIdInvalidoError):
        Contato(devedor_id=None, tipo=TipoContato.TELEFONE, valor="(11) 1234-5678")  # type: ignore[arg-type]


def test_rejeita_telefone_apenas_mascara_sem_digitos_reais() -> None:
    with pytest.raises(ContatoInvalidoError) as exc:
        Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.TELEFONE, valor="(  )      -    ")

    assert exc.value.tipo == TipoContato.TELEFONE
    assert "10 dígitos" in exc.value.motivo


def test_rejeita_telefone_com_poucos_digitos_reais() -> None:
    with pytest.raises(ContatoInvalidoError) as exc:
        Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.TELEFONE, valor="(11) 1234-567")

    assert exc.value.tipo == TipoContato.TELEFONE
    assert "10 dígitos" in exc.value.motivo


def test_normaliza_valor_com_espacos_ao_redor() -> None:
    contato = Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.EMAIL, valor="  joao@exemplo.com  ")

    assert contato.valor == "joao@exemplo.com"


# --------------------------------------------------------------------------- #
# Soft-delete (RN-006/INV-003, DOMAIN-021 §141) — TASK-099
# --------------------------------------------------------------------------- #


def test_contato_criado_nao_esta_removido() -> None:
    contato = Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.TELEFONE, valor="(11) 1234-5678")
    assert contato.removido_em is None
    assert contato.removido is False


def test_remover_marca_removido_em() -> None:
    contato = Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.TELEFONE, valor="(11) 1234-5678")

    contato.remover()

    assert contato.removido_em is not None
    assert contato.removido is True


def test_remover_e_idempotente() -> None:
    contato = Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.TELEFONE, valor="(11) 1234-5678")

    contato.remover()
    primeira_marca = contato.removido_em
    contato.remover()

    assert contato.removido_em == primeira_marca  # não muda na segunda chamada


def test_contato_removido_pode_ser_lido() -> None:
    """A remoção é soft-delete: o registro permanece e pode ser lido (§141)."""
    contato = Contato(devedor_id=DEVEDOR_ID, tipo=TipoContato.TELEFONE, valor="(11) 1234-5678")
    contato.remover()

    # a linha continua com seus dados
    assert contato.valor == "(11) 1234-5678"
    assert contato.tipo == TipoContato.TELEFONE
