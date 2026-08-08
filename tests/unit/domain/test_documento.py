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

    assert "caracteres inválidos" in exc.value.motivo


def test_rejeita_letras_misturadas_ao_cpf_valido() -> None:
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("abc529.982.247-25xyz")

    assert "caracteres inválidos" in exc.value.motivo


def test_rejeita_espacos_no_meio_do_cpf() -> None:
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("529 982 247 25")

    assert "caracteres inválidos" in exc.value.motivo


def test_aceita_cpf_com_espacos_ao_redor() -> None:
    doc = Documento.from_str("  529.982.247-25  ")

    assert doc.valor == "52998224725"


def test_rejeita_caracteres_especiais_nao_da_mascara() -> None:
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("529.982.247/25")

    assert "caracteres inválidos" in exc.value.motivo


# --------------------------------------------------------------------------- #
# Validação VO-022-VAL-002 (dígitos verificadores)
# --------------------------------------------------------------------------- #


def test_rejeita_cpf_com_digitos_repetidos() -> None:
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("111.111.111-11")

    assert "todos os dígitos iguais" in exc.value.motivo


def test_rejeita_digito_verificador_incorreto() -> None:
    """Erra o SEGUNDO dígito verificador (último)."""
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("529.982.247-26")

    assert "dígito verificador" in exc.value.motivo


def test_rejeita_primeiro_digito_verificador_incorreto() -> None:
    """Erra o PRIMEIRO dígito verificador (décimo) — caminho distinto do acima.

    O CPF válido é 529.982.247-25; aqui o décimo dígito vira 3, de modo que a
    validação falha antes de chegar ao segundo verificador (IMP-063).
    """
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento.from_str("529.982.247-35")

    assert "dígito verificador" in exc.value.motivo


# --------------------------------------------------------------------------- #
# Imutabilidade
# --------------------------------------------------------------------------- #


def test_documento_e_imutavel() -> None:
    doc = Documento.from_str("52998224725")

    with pytest.raises(AttributeError):
        doc.valor = "11144477735"  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Igualdade com outros tipos e validação direta (IMP-063)
# --------------------------------------------------------------------------- #


def test_comparacao_com_outro_tipo_nao_e_igual() -> None:
    """``__eq__`` devolve NotImplemented, e o Python conclui por desigualdade."""
    doc = Documento.from_str("52998224725")

    assert doc != "52998224725"
    assert doc != 52998224725
    assert doc is not None


def test_rejeita_construcao_direta_com_nao_digitos() -> None:
    """A validação de dígitos vale também sem passar por ``from_str``.

    ``from_str`` remove a máscara antes de validar; construir direto expõe o
    caminho em que o valor chega com caracteres não numéricos.
    """
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento(valor="5299822472a")

    assert "apenas dígitos" in str(exc.value)


def test_rejeita_construcao_direta_com_digitos_repetidos() -> None:
    with pytest.raises(DocumentoInvalidoError) as exc:
        Documento(valor="11111111111")

    assert "dígitos iguais" in str(exc.value)
