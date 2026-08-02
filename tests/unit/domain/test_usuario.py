"""Testes unitários da Entity Usuário (IMP-002)."""

from __future__ import annotations

import uuid

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
