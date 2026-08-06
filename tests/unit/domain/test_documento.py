"""Testes unitários do Value Object Documento (IMP-043)."""

from __future__ import annotations

import pytest

from emprestimo.domain.common.errors import DocumentoInvalidoError
from emprestimo.domain.credit.documento import Documento

# --------------------------------------------------------------------------- #
# Criação e normalização
# --------------------------------------------------------------------------- #


def test_cria_documento_com_valor_normalizado() -> None:
    doc = Documento(valor="52998224725")

    assert doc.valor == "52998224725"
    assert str(doc) == "52998224725"


def test_from_str_remove_mascara() -> None:
    doc = Documento.from_str("529.982.247-25")

    assert doc.valor == "52998224725"


def test_from_str_aceita_valor_ja_normalizado() -> None:
    doc = Documento.from_str("52998224725")

    assert doc.valor == "52998224725"


# --------------------------------------------------------------------------- #
# Igualdade e hash
# --------------------------------------------------------------------------- #


def test_documentos_iguais_quando_valor_canonico_igual() -> None:
    com_mascara = Documento.from_str("529.982.247-25")
    sem_mascara = Documento.from_str("52998224725")

    assert com_mascara == sem_mascara
    assert hash(com_mascara) == hash(sem_mascara)


def test_documentos_diferentes_quando_valor_diferente() -> None:
    a = Documento.from_str("52998224725")
    b = Documento.from_str("11144477735")

    assert a != b


# --------------------------------------------------------------------------- #
# Validação VO-022-VAL-001 (formato)
# --------------------------------------------------------------------------- #


def test_rejeita_comprimento_diferente_de_11() -> None:
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("1234567890")

    assert "11 dígitos" in exc.value.motivo


def test_rejeita_valor_vazio() -> None:
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("")

    assert "11 dígitos" in exc.value.motivo


def test_rejeita_letras_na_mascara() -> None:
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("529.982.247-XX")

    assert "11 dígitos" in exc.value.motivo


# --------------------------------------------------------------------------- #
# Validação VO-022-VAL-002 (dígitos verificadores)
# --------------------------------------------------------------------------- #


def test_rejeita_cpf_com_digitos_repetidos() -> None:
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("111.111.111-11")

    assert "todos os dígitos iguais" in exc.value.motivo


def test_rejeita_digito_verificador_incorreto() -> None:
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("529.982.247-26")

    assert "dígito verificador" in exc.value.motivo


# --------------------------------------------------------------------------- #
# Imutabilidade
# --------------------------------------------------------------------------- #


def test_documento_e_imutavel() -> None:
    doc = Documento.from_str("52998224725")

    with pytest.raises(AttributeError):
        doc.valor = "11144477735"  # type: ignore[misc]
