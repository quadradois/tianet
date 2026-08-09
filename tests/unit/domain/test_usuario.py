"""Testes unitários da Entity Usuário (IMP-002)."""

from __future__ import annotations

import uuid

import pytest

from emprestimo.domain.platform.usuario import Usuario, UsuarioState


def test_criacao_usuario_exige_tenant() -> None:
    tenant_id = uuid.uuid4()
    usuario = Usuario(tenant_id=tenant_id, nome="Maria", email="maria@exemplo.com")

    assert usuario.tenant_id == tenant_id
    assert usuario.nome == "Maria"
    assert usuario.email == "maria@exemplo.com"


def test_estado_inicial_do_usuario_e_convidado() -> None:
    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")

    assert usuario.estado == UsuarioState.CONVIDADO


def test_ciclo_de_vida_aceita_estados_oficiais() -> None:
    ativo = Usuario(
        tenant_id=uuid.uuid4(), nome="A", email="a@exemplo.com", estado=UsuarioState.ATIVO
    )
    inativo = Usuario(
        tenant_id=uuid.uuid4(), nome="B", email="b@exemplo.com", estado=UsuarioState.INATIVO
    )
    removido = Usuario(
        tenant_id=uuid.uuid4(), nome="C", email="c@exemplo.com", estado=UsuarioState.REMOVIDO
    )

    assert ativo.estado == UsuarioState.ATIVO
    assert inativo.estado == UsuarioState.INATIVO
    assert removido.estado == UsuarioState.REMOVIDO


def test_perfil_de_acesso_default_e_none() -> None:
    """RN-002: perfil não é auto-atribuído; o Aggregate o define (IMP-011)."""
    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")

    assert usuario.perfil_acesso is None


# --------------------------------------------------------------------------- #
# Transição de estado (DOMAIN-018 §4)
# --------------------------------------------------------------------------- #


def test_usuario_nasce_convidado() -> None:
    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")
    assert usuario.estado is UsuarioState.CONVIDADO
    assert usuario.ativo is False


def test_transicao_convidado_para_ativo() -> None:
    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")
    usuario.ativar()
    assert usuario.estado is UsuarioState.ATIVO
    assert usuario.ativo is True


def test_transicao_ativo_para_inativo() -> None:
    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")
    usuario.ativar()
    usuario.inativar()
    assert usuario.estado is UsuarioState.INATIVO
    assert usuario.ativo is False


def test_transicao_inativo_para_ativo() -> None:
    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")
    usuario.ativar()
    usuario.inativar()
    usuario.reativar()
    assert usuario.estado is UsuarioState.ATIVO


def test_transicao_inativo_para_removido() -> None:
    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")
    usuario.ativar()
    usuario.inativar()
    usuario.remover()
    assert usuario.estado is UsuarioState.REMOVIDO


def test_transicao_invalida_convidado_para_inativo() -> None:
    from emprestimo.domain.common.errors import ViolacaoInvarianteError

    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")
    with pytest.raises(ViolacaoInvarianteError):
        usuario.inativar()


def test_transicao_invalida_convidado_para_removido() -> None:
    from emprestimo.domain.common.errors import ViolacaoInvarianteError

    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")
    with pytest.raises(ViolacaoInvarianteError):
        usuario.remover()


def test_transicao_invalida_reativar_convidado() -> None:
    from emprestimo.domain.common.errors import ViolacaoInvarianteError

    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")
    with pytest.raises(ViolacaoInvarianteError):
        usuario.reativar()


def test_transicao_invalida_reativar_ativo() -> None:
    from emprestimo.domain.common.errors import ViolacaoInvarianteError

    usuario = Usuario(tenant_id=uuid.uuid4(), nome="Maria", email="maria@exemplo.com")
    usuario.ativar()
    with pytest.raises(ViolacaoInvarianteError):
        usuario.reativar()
