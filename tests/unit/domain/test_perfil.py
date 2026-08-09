"""Testes unitarios da Entity PerfilAcesso (IMP-084, FEATURE-011)."""

from __future__ import annotations

import uuid

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.perfil import PerfilAcesso, PerfilState
from emprestimo.domain.platform.permissao import Permissao

TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _permissao(codigo: str = "devedor.criar") -> Permissao:
    return Permissao(codigo=codigo, descricao=f"Permite {codigo}")


def test_cria_perfil_ativo_sem_permissoes() -> None:
    perfil = PerfilAcesso(tenant_id=TENANT_ID, nome="Administrador")

    assert perfil.tenant_id == TENANT_ID
    assert perfil.nome == "Administrador"
    assert perfil.estado is PerfilState.ATIVO
    assert perfil.permissoes == ()


def test_adiciona_permissao_e_autoriza_por_codigo() -> None:
    perfil = PerfilAcesso(tenant_id=TENANT_ID, nome="Operador")
    perfil.adicionar_permissao(_permissao("devedor.criar"))

    assert perfil.permite("devedor.criar") is True
    assert perfil.permite("devedor.remover") is False


def test_permissao_duplicada_e_idempotente() -> None:
    perfil = PerfilAcesso(tenant_id=TENANT_ID, nome="Operador")
    perfil.adicionar_permissao(_permissao("devedor.criar"))

    perfil.adicionar_permissao(_permissao("DEVEDOR.CRIAR"))

    assert [permissao.codigo for permissao in perfil.permissoes] == ["devedor.criar"]


def test_remove_permissao_sem_excluir_catalogo() -> None:
    perfil = PerfilAcesso(tenant_id=TENANT_ID, nome="Operador")
    permissao = _permissao("devedor.criar")
    perfil.adicionar_permissao(permissao)

    perfil.remover_permissao("devedor.criar")

    assert perfil.permissoes == ()
    assert permissao.codigo == "devedor.criar"


def test_perfil_inativo_nao_autoriza_operacao() -> None:
    perfil = PerfilAcesso(tenant_id=TENANT_ID, nome="Operador")
    perfil.adicionar_permissao(_permissao("devedor.criar"))

    perfil.inativar()

    assert perfil.estado is PerfilState.INATIVO
    assert perfil.permite("devedor.criar") is False


def test_rejeita_nome_vazio() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        PerfilAcesso(tenant_id=TENANT_ID, nome=" ")

    assert exc.value.codigo == "FEATURE-011"
