"""Testes unitarios do CredenciaisService (IMP-087)."""

from __future__ import annotations

import uuid
from unittest.mock import Mock

import pytest

from emprestimo.application.credenciais import CredenciaisService
from emprestimo.application.errors import (
    AcessoNegadoError,
    CredencialInvalidaError,
    TransicaoEstadoInvalidaError,
    UsuarioNaoEncontradoError,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.sessao import Sessao
from emprestimo.domain.platform.usuario import Usuario, UsuarioState

TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OUTRO_TENANT_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USUARIO_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
SOLICITANTE_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


def _usuario(
    usuario_id: uuid.UUID = USUARIO_ID,
    *,
    tenant_id: uuid.UUID = TENANT_ID,
    estado: UsuarioState = UsuarioState.CONVIDADO,
    perfil_acesso: str | None = None,
) -> Usuario:
    return Usuario(
        id=usuario_id,
        tenant_id=tenant_id,
        nome="Usuario Teste",
        email=f"{usuario_id.hex[:8]}@exemplo.com",
        estado=estado,
        perfil_acesso=perfil_acesso,
    )


def _perfil_redefinicao(tenant_id: uuid.UUID = TENANT_ID) -> PerfilAcesso:
    perfil = PerfilAcesso(tenant_id=tenant_id, nome="Administrador")
    perfil.adicionar_permissao(
        Permissao(codigo="credencial.redefinir", descricao="Redefinir credenciais")
    )
    return perfil


def _uow(
    *,
    usuarios: dict[uuid.UUID, Usuario] | None = None,
    credenciais: dict[uuid.UUID, Credencial] | None = None,
    sessoes: dict[uuid.UUID, list[Sessao]] | None = None,
) -> Mock:
    uow = Mock(spec=UnitOfWork)
    uow.usuario = Mock()
    uow.credencial = Mock()
    uow.sessao = Mock()
    uow.perfil_acesso = Mock()
    uow.commit = Mock()
    uow.rollback = Mock()
    uow.close = Mock()
    uow.__enter__ = Mock(return_value=uow)
    uow.__exit__ = Mock(return_value=None)

    usuarios = usuarios or {}
    credenciais = credenciais or {}
    sessoes = sessoes or {}
    credenciais_salvas: dict[uuid.UUID, Credencial] = {}
    sessoes_salvas: list[Sessao] = []

    uow.usuario.find_by_id.side_effect = lambda usuario_id: usuarios.get(usuario_id)
    uow.credencial.find_by_usuario_id.side_effect = lambda usuario_id: credenciais.get(usuario_id)
    uow.sessao.find_by_usuario_id.side_effect = lambda usuario_id: list(sessoes.get(usuario_id, []))
    uow.perfil_acesso.find_by_tenant_nome.return_value = None

    def salvar_credencial(credencial: Credencial) -> None:
        credenciais_salvas[credencial.usuario_id] = credencial
        credenciais[credencial.usuario_id] = credencial

    def salvar_sessao(sessao: Sessao) -> None:
        sessoes_salvas.append(sessao)

    uow.credencial.save.side_effect = salvar_credencial
    uow.sessao.save.side_effect = salvar_sessao
    uow._credenciais_salvas = credenciais_salvas
    uow._sessoes_salvas = sessoes_salvas
    return uow


def _auditoria() -> Mock:
    return Mock(spec=AuditoriaRegistro)


def _service(uow: Mock, auditoria: Mock | None = None) -> CredenciaisService:
    return CredenciaisService(lambda: uow, auditoria or _auditoria())


def _assert_auditoria_sem_segredo(auditoria: Mock, segredo: str) -> None:
    for call in auditoria.registrar.call_args_list:
        detalhes = call.kwargs.get("detalhes")
        if detalhes is not None:
            assert segredo not in detalhes


def test_alterar_propria_credencial_exige_credencial_atual() -> None:
    usuario = _usuario(estado=UsuarioState.ATIVO)
    credencial = Credencial.definir(usuario_id=usuario.id, segredo="Senha antiga 123")
    uow = _uow(usuarios={usuario.id: usuario}, credenciais={usuario.id: credencial})
    service = _service(uow)

    with pytest.raises(CredencialInvalidaError):
        service.alterar_propria(
            tenant_id=TENANT_ID,
            usuario_id=usuario.id,
            segredo_atual="senha errada",
            novo_segredo="Senha nova 123",
        )

    assert credencial.verificar("Senha antiga 123")
    uow.credencial.save.assert_not_called()
    uow.commit.assert_not_called()


def test_alterar_propria_credencial_de_outro_tenant_responde_404() -> None:
    usuario = _usuario(tenant_id=OUTRO_TENANT_ID, estado=UsuarioState.ATIVO)
    uow = _uow(usuarios={usuario.id: usuario})
    service = _service(uow)

    with pytest.raises(UsuarioNaoEncontradoError):
        service.alterar_propria(
            tenant_id=TENANT_ID,
            usuario_id=usuario.id,
            segredo_atual="Senha antiga 123",
            novo_segredo="Senha nova 123",
        )

    uow.credencial.save.assert_not_called()
    uow.commit.assert_not_called()


def test_alterar_propria_credencial_rejeita_usuario_inativo() -> None:
    usuario = _usuario(estado=UsuarioState.INATIVO)
    uow = _uow(usuarios={usuario.id: usuario})
    service = _service(uow)

    with pytest.raises(CredencialInvalidaError):
        service.alterar_propria(
            tenant_id=TENANT_ID,
            usuario_id=usuario.id,
            segredo_atual="Senha antiga 123",
            novo_segredo="Senha nova 123",
        )

    uow.credencial.save.assert_not_called()
    uow.commit.assert_not_called()


def test_alterar_propria_credencial_redefine_hash_e_revoga_sessoes() -> None:
    usuario = _usuario(estado=UsuarioState.ATIVO)
    credencial = Credencial.definir(usuario_id=usuario.id, segredo="Senha antiga 123")
    sessao = Sessao.iniciar(
        usuario_id=usuario.id,
        tenant_id=TENANT_ID,
        refresh_token="refresh-token",
    )
    uow = _uow(
        usuarios={usuario.id: usuario},
        credenciais={usuario.id: credencial},
        sessoes={usuario.id: [sessao]},
    )
    auditoria = _auditoria()
    service = _service(uow, auditoria)

    resultado = service.alterar_propria(
        tenant_id=TENANT_ID,
        usuario_id=usuario.id,
        segredo_atual="Senha antiga 123",
        novo_segredo="Senha nova 123",
    )

    assert resultado.estado is UsuarioState.ATIVO
    assert not credencial.verificar("Senha antiga 123")
    assert credencial.verificar("Senha nova 123")
    assert sessao.revogado_em is not None
    assert uow._sessoes_salvas == [sessao]
    uow.credencial.save.assert_called_once_with(credencial)
    uow.commit.assert_called_once()
    _assert_auditoria_sem_segredo(auditoria, "Senha nova 123")


def test_redefinir_usuario_exige_perfil_com_permissao() -> None:
    solicitante = _usuario(SOLICITANTE_ID, estado=UsuarioState.ATIVO)
    alvo = _usuario(USUARIO_ID, estado=UsuarioState.ATIVO)
    uow = _uow(usuarios={solicitante.id: solicitante, alvo.id: alvo})
    service = _service(uow)

    with pytest.raises(AcessoNegadoError):
        service.redefinir_usuario(
            tenant_id=TENANT_ID,
            solicitante_id=SOLICITANTE_ID,
            usuario_id=USUARIO_ID,
            novo_segredo="Senha nova 123",
        )

    uow.perfil_acesso.find_by_tenant_nome.assert_not_called()
    uow.commit.assert_not_called()


def test_redefinir_usuario_do_mesmo_tenant_redefine_e_revoga_sessoes() -> None:
    solicitante = _usuario(
        SOLICITANTE_ID,
        estado=UsuarioState.ATIVO,
        perfil_acesso="Administrador",
    )
    alvo = _usuario(USUARIO_ID, estado=UsuarioState.ATIVO)
    credencial = Credencial.definir(usuario_id=alvo.id, segredo="Senha antiga 123")
    sessao = Sessao.iniciar(
        usuario_id=alvo.id,
        tenant_id=TENANT_ID,
        refresh_token="refresh-token",
    )
    uow = _uow(
        usuarios={solicitante.id: solicitante, alvo.id: alvo},
        credenciais={alvo.id: credencial},
        sessoes={alvo.id: [sessao]},
    )
    uow.perfil_acesso.find_by_usuario_id.return_value = _perfil_redefinicao()
    auditoria = _auditoria()
    service = _service(uow, auditoria)

    resultado = service.redefinir_usuario(
        tenant_id=TENANT_ID,
        solicitante_id=solicitante.id,
        usuario_id=alvo.id,
        novo_segredo="Senha nova 123",
    )

    assert resultado.usuario_id == alvo.id
    assert resultado.estado is UsuarioState.ATIVO
    assert not credencial.verificar("Senha antiga 123")
    assert credencial.verificar("Senha nova 123")
    assert sessao.revogado_em is not None
    uow.credencial.save.assert_called_once_with(credencial)
    uow.commit.assert_called_once()
    _assert_auditoria_sem_segredo(auditoria, "Senha nova 123")


def test_redefinir_usuario_de_outro_tenant_responde_404() -> None:
    solicitante = _usuario(
        SOLICITANTE_ID,
        estado=UsuarioState.ATIVO,
        perfil_acesso="Administrador",
    )
    alvo = _usuario(USUARIO_ID, tenant_id=OUTRO_TENANT_ID, estado=UsuarioState.ATIVO)
    uow = _uow(usuarios={solicitante.id: solicitante, alvo.id: alvo})
    uow.perfil_acesso.find_by_usuario_id.return_value = _perfil_redefinicao()
    service = _service(uow)

    with pytest.raises(UsuarioNaoEncontradoError):
        service.redefinir_usuario(
            tenant_id=TENANT_ID,
            solicitante_id=solicitante.id,
            usuario_id=alvo.id,
            novo_segredo="Senha nova 123",
        )

    uow.credencial.save.assert_not_called()
    uow.commit.assert_not_called()


def test_redefinir_usuario_inativo_rejeita_transicao() -> None:
    solicitante = _usuario(
        SOLICITANTE_ID,
        estado=UsuarioState.ATIVO,
        perfil_acesso="Administrador",
    )
    alvo = _usuario(USUARIO_ID, estado=UsuarioState.INATIVO)
    uow = _uow(usuarios={solicitante.id: solicitante, alvo.id: alvo})
    uow.perfil_acesso.find_by_usuario_id.return_value = _perfil_redefinicao()
    service = _service(uow)

    with pytest.raises(TransicaoEstadoInvalidaError):
        service.redefinir_usuario(
            tenant_id=TENANT_ID,
            solicitante_id=solicitante.id,
            usuario_id=alvo.id,
            novo_segredo="Senha nova 123",
        )

    uow.credencial.save.assert_not_called()
    uow.commit.assert_not_called()


def test_redefinir_usuario_com_perfil_sem_permissao_responde_403() -> None:
    solicitante = _usuario(
        SOLICITANTE_ID,
        estado=UsuarioState.ATIVO,
        perfil_acesso="Operador",
    )
    alvo = _usuario(USUARIO_ID, estado=UsuarioState.ATIVO)
    perfil = PerfilAcesso(tenant_id=TENANT_ID, nome="Operador")
    uow = _uow(usuarios={solicitante.id: solicitante, alvo.id: alvo})
    uow.perfil_acesso.find_by_usuario_id.return_value = perfil
    service = _service(uow)

    with pytest.raises(AcessoNegadoError):
        service.redefinir_usuario(
            tenant_id=TENANT_ID,
            solicitante_id=solicitante.id,
            usuario_id=alvo.id,
            novo_segredo="Senha nova 123",
        )

    uow.credencial.save.assert_not_called()
    uow.commit.assert_not_called()


def test_redefinir_a_propria_credencial_pelo_fluxo_administrativo_responde_403() -> None:
    solicitante = _usuario(
        SOLICITANTE_ID,
        estado=UsuarioState.ATIVO,
        perfil_acesso="Administrador",
    )
    uow = _uow(usuarios={solicitante.id: solicitante})
    uow.perfil_acesso.find_by_usuario_id.return_value = _perfil_redefinicao()
    service = _service(uow)

    with pytest.raises(AcessoNegadoError):
        service.redefinir_usuario(
            tenant_id=TENANT_ID,
            solicitante_id=solicitante.id,
            usuario_id=solicitante.id,
            novo_segredo="Senha nova 123",
        )

    uow.credencial.save.assert_not_called()
    uow.commit.assert_not_called()
