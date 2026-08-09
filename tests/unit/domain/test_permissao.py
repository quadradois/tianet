"""Testes unitarios do Value Object Permissao (IMP-084, FEATURE-011)."""

from __future__ import annotations

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.permissao import Permissao


def test_permissao_normaliza_codigo_de_operacao() -> None:
    permissao = Permissao(codigo="  DEVEDOR.CRIAR  ", descricao="Criar devedor")

    assert permissao.codigo == "devedor.criar"
    assert permissao.descricao == "Criar devedor"


def test_rejeita_codigo_vazio() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Permissao(codigo=" ", descricao="Sem codigo")

    assert exc.value.codigo == "FEATURE-011"


def test_rejeita_descricao_vazia() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Permissao(codigo="devedor.criar", descricao=" ")

    assert exc.value.codigo == "FEATURE-011"
