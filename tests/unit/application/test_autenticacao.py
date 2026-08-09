"""Testes unitarios do AutenticacaoService (IMP-088)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import Mock

import pytest

from emprestimo.application.autenticacao import (
    ACCESS_TOKEN_MINUTOS,
    AutenticacaoResultado,
    AutenticacaoService,
    HmacAccessTokenService,
    RenovacaoResultado,
)
from emprestimo.application.errors import AutenticacaoRecusadaError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.sessao import REFRESH_TOKEN_DIAS, Sessao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState

TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USUARIO_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
AGORA = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
EMAIL = "maria@exemplo.com"
IDENTIFICADOR = "IDENT-AUTH"
SEGREDO = "Senha forte 123"
JWT_SECRET = "segredo-local-de-teste"


def _usuario(
    *,
    estado: UsuarioState = UsuarioState.ATIVO,
    perfil_acesso: str | None = "Operador",
) -> Usuario:
    return Usuario(
        id=USUARIO_ID,
        tenant_id=TENANT_ID,
        nome="Maria",
        email=EMAIL,
        estado=estado,
        perfil_acesso=perfil_acesso,
    )


def _tenant(*, estado: TenantState = TenantState.ATIVO) -> Tenant:
    return Tenant(
        id=TENANT_ID,
        identificador_institucional=IDENTIFICADOR,
        nome="Tenant Auth",
        estado=estado,
    )


def _uow(
    *,
    usuario: Usuario | None = None,
    credencial: Credencial | None = None,
    sessoes: dict[uuid.UUID, Sessao] | None = None,
    tenant: Tenant | None = None,
) -> Mock:
    uow = Mock(spec=UnitOfWork)
    uow.usuario = Mock()
    uow.tenant = Mock()
    uow.credencial = Mock()
    uow.sessao = Mock()
    uow.commit = Mock()
    uow.rollback = Mock()
    uow.close = Mock()
    uow.__enter__ = Mock(return_value=uow)
    uow.__exit__ = Mock(return_value=None)

    sessoes = sessoes or {}
    sessoes_salvas: dict[uuid.UUID, Sessao] = {}

    tenant = tenant or (_tenant() if usuario is not None else None)
    uow.tenant.find_by_identificador_institucional.side_effect = lambda identificador: (
        tenant
        if tenant is not None and identificador == tenant.identificador_institucional
        else None
    )
    uow.tenant.find_by_id.side_effect = lambda tenant_id: (
        tenant if tenant is not None and tenant_id == tenant.id else None
    )
    uow.usuario.find_by_tenant_id.side_effect = lambda tenant_id: (
        [usuario] if usuario is not None and usuario.tenant_id == tenant_id else []
    )
    uow.usuario.find_by_id.side_effect = lambda usuario_id: (
        usuario if usuario is not None and usuario_id == usuario.id else None
    )
    uow.credencial.find_by_usuario_id.side_effect = lambda usuario_id: (
        credencial if usuario_id == USUARIO_ID else None
    )
    uow.sessao.find_by_id.side_effect = lambda sessao_id: sessoes.get(sessao_id)

    def salvar_sessao(sessao: Sessao) -> None:
        sessoes[sessao.id] = sessao
        sessoes_salvas[sessao.id] = sessao

    uow.sessao.save.side_effect = salvar_sessao
    uow._sessoes = sessoes
    uow._sessoes_salvas = sessoes_salvas
    return uow


def _auditoria() -> Mock:
    return Mock(spec=AuditoriaRegistro)


def _service(uow: Mock, auditoria: Mock | None = None) -> AutenticacaoService:
    return AutenticacaoService(
        lambda: uow,
        auditoria or _auditoria(),
        HmacAccessTokenService(JWT_SECRET),
        refresh_secret_factory=lambda: "refresh-secret",
    )


def _credencial(usuario: Usuario, segredo: str = SEGREDO) -> Credencial:
    return Credencial.definir(usuario_id=usuario.id, segredo=segredo)


def _sessao_por_token(uow: Mock, refresh_token: str) -> Sessao:
    sessao_id_raw, _ = refresh_token.split(".", 1)
    return cast(Sessao, uow._sessoes[uuid.UUID(sessao_id_raw)])


def _assert_auditoria_sem_segredo(auditoria: Mock, segredo: str) -> None:
    for call in auditoria.registrar.call_args_list:
        detalhes = call.kwargs.get("detalhes")
        if detalhes is not None:
            assert segredo not in detalhes


def test_login_valido_emite_access_token_e_refresh_persistido() -> None:
    usuario = _usuario()
    uow = _uow(usuario=usuario, credencial=_credencial(usuario))
    auditoria = _auditoria()
    service = _service(uow, auditoria)

    resultado = service.login(
        identificador_institucional=IDENTIFICADOR,
        email=EMAIL,
        segredo=SEGREDO,
        agora=AGORA,
    )

    assert isinstance(resultado, AutenticacaoResultado)
    assert resultado.usuario_id == usuario.id
    assert resultado.tenant_id == TENANT_ID
    assert resultado.access_token_expira_em == AGORA + timedelta(minutes=ACCESS_TOKEN_MINUTOS)
    assert resultado.refresh_token_expira_em == AGORA + timedelta(days=REFRESH_TOKEN_DIAS)
    sessao = _sessao_por_token(uow, resultado.refresh_token)
    assert sessao.verificar_refresh_token(resultado.refresh_token, AGORA)
    assert SEGREDO not in resultado.access_token
    assert SEGREDO not in resultado.refresh_token
    uow.sessao.save.assert_called_once_with(sessao)
    uow.commit.assert_called_once()
    _assert_auditoria_sem_segredo(auditoria, SEGREDO)


def test_access_token_e_autocontido_e_verificavel_sem_banco() -> None:
    usuario = _usuario(perfil_acesso="Administrador")
    issuer = HmacAccessTokenService(JWT_SECRET)

    token = issuer.emitir(usuario, AGORA)
    claims = issuer.verificar(token.token, AGORA + timedelta(minutes=1))

    assert claims.usuario_id == usuario.id
    assert claims.tenant_id == usuario.tenant_id
    assert claims.perfil_acesso == "Administrador"
    assert claims.expira_em == AGORA + timedelta(minutes=ACCESS_TOKEN_MINUTOS)
    with pytest.raises(AutenticacaoRecusadaError):
        issuer.verificar(token.token, AGORA + timedelta(minutes=ACCESS_TOKEN_MINUTOS))


def test_access_token_malformado_recusa_de_forma_uniforme() -> None:
    issuer = HmacAccessTokenService(JWT_SECRET)

    with pytest.raises(AutenticacaoRecusadaError) as exc_info:
        issuer.verificar("header.payload.%%%%", AGORA)

    assert str(exc_info.value) == "Autenticacao recusada"


@pytest.mark.parametrize(
    ("usuario", "credencial", "segredo"),
    [
        (None, None, SEGREDO),
        (_usuario(estado=UsuarioState.CONVIDADO), None, SEGREDO),
        (_usuario(), _credencial(_usuario()), "senha errada"),
        (_usuario(), None, SEGREDO),
    ],
)
def test_login_recusa_uniforme_sem_revelar_motivo(
    usuario: Usuario | None,
    credencial: Credencial | None,
    segredo: str,
) -> None:
    auditoria = _auditoria()
    uow = _uow(usuario=usuario, credencial=credencial)
    service = _service(uow, auditoria)

    with pytest.raises(AutenticacaoRecusadaError) as exc_info:
        service.login(
            identificador_institucional=IDENTIFICADOR,
            email=EMAIL,
            segredo=segredo,
            agora=AGORA,
        )

    assert str(exc_info.value) == "Autenticacao recusada"
    uow.sessao.save.assert_not_called()
    uow.commit.assert_not_called()
    auditoria.registrar.assert_any_call(
        "autenticacao",
        None,
        "login.recusado",
        "recusado",
        detalhes='{"identificador": "IDENT-AUTH", "erro": "AutenticacaoRecusadaError"}',
    )
    _assert_auditoria_sem_segredo(auditoria, segredo)


def test_login_recusa_tenant_inativo() -> None:
    usuario = _usuario()
    uow = _uow(
        usuario=usuario,
        credencial=_credencial(usuario),
        tenant=_tenant(estado=TenantState.INATIVO),
    )
    service = _service(uow)

    with pytest.raises(AutenticacaoRecusadaError):
        service.login(
            identificador_institucional=IDENTIFICADOR,
            email=EMAIL,
            segredo=SEGREDO,
            agora=AGORA,
        )

    uow.credencial.find_by_usuario_id.assert_not_called()
    uow.sessao.save.assert_not_called()


def test_refresh_valido_emite_novo_access_token_sem_credencial() -> None:
    usuario = _usuario(perfil_acesso="Operador")
    uow = _uow(usuario=usuario, credencial=_credencial(usuario))
    service = _service(uow)
    login = service.login(
        identificador_institucional=IDENTIFICADOR,
        email=EMAIL,
        segredo=SEGREDO,
        agora=AGORA,
    )
    usuario.perfil_acesso = "Administrador"

    renovacao = service.refresh(
        refresh_token=login.refresh_token,
        agora=AGORA + timedelta(minutes=10),
    )

    assert isinstance(renovacao, RenovacaoResultado)
    assert renovacao.usuario_id == usuario.id
    assert renovacao.access_token != login.access_token
    claims = HmacAccessTokenService(JWT_SECRET).verificar(
        renovacao.access_token,
        AGORA + timedelta(minutes=10),
    )
    assert claims.perfil_acesso == "Administrador"
    assert uow.credencial.find_by_usuario_id.call_count == 1


def test_refresh_recusa_tenant_inativo() -> None:
    usuario = _usuario()
    tenant = _tenant()
    uow = _uow(usuario=usuario, credencial=_credencial(usuario), tenant=tenant)
    service = _service(uow)
    login = service.login(
        identificador_institucional=IDENTIFICADOR,
        email=EMAIL,
        segredo=SEGREDO,
        agora=AGORA,
    )
    tenant.inativar()

    with pytest.raises(AutenticacaoRecusadaError):
        service.refresh(
            refresh_token=login.refresh_token,
            agora=AGORA + timedelta(minutes=1),
        )

    assert uow.commit.call_count == 1


def test_refresh_revogado_ou_expirado_recusa() -> None:
    usuario = _usuario()
    uow = _uow(usuario=usuario, credencial=_credencial(usuario))
    service = _service(uow)
    login = service.login(
        identificador_institucional=IDENTIFICADOR,
        email=EMAIL,
        segredo=SEGREDO,
        agora=AGORA,
    )
    sessao = _sessao_por_token(uow, login.refresh_token)
    sessao.revogar(AGORA + timedelta(minutes=1))

    with pytest.raises(AutenticacaoRecusadaError):
        service.refresh(refresh_token=login.refresh_token, agora=AGORA + timedelta(minutes=2))

    sessao.revogado_em = None
    with pytest.raises(AutenticacaoRecusadaError):
        service.refresh(refresh_token=login.refresh_token, agora=AGORA + timedelta(days=8))


def test_logout_revoga_refresh_token_e_e_idempotente() -> None:
    usuario = _usuario()
    uow = _uow(usuario=usuario, credencial=_credencial(usuario))
    service = _service(uow)
    login = service.login(
        identificador_institucional=IDENTIFICADOR,
        email=EMAIL,
        segredo=SEGREDO,
        agora=AGORA,
    )
    sessao = _sessao_por_token(uow, login.refresh_token)

    service.logout(refresh_token=login.refresh_token, agora=AGORA + timedelta(minutes=1))
    primeira_revogacao = sessao.revogado_em
    service.logout(refresh_token=login.refresh_token, agora=AGORA + timedelta(minutes=2))

    assert primeira_revogacao == AGORA + timedelta(minutes=1)
    assert sessao.revogado_em == primeira_revogacao
    assert uow.sessao.save.call_count == 3  # login + dois logouts idempotentes


def test_logout_nao_revoga_outras_sessoes_do_usuario() -> None:
    usuario = _usuario()
    uow = _uow(usuario=usuario, credencial=_credencial(usuario))
    service = _service(uow)
    primeira = service.login(
        identificador_institucional=IDENTIFICADOR,
        email=EMAIL,
        segredo=SEGREDO,
        agora=AGORA,
    )
    segunda = service.login(
        identificador_institucional=IDENTIFICADOR,
        email=EMAIL,
        segredo=SEGREDO,
        agora=AGORA + timedelta(minutes=1),
    )

    service.logout(refresh_token=primeira.refresh_token, agora=AGORA + timedelta(minutes=2))

    assert _sessao_por_token(uow, primeira.refresh_token).revogado_em is not None
    assert _sessao_por_token(uow, segunda.refresh_token).revogado_em is None


def test_refresh_token_malformado_recusa_sem_salvar() -> None:
    uow = _uow(usuario=_usuario())
    service = _service(uow)

    with pytest.raises(AutenticacaoRecusadaError):
        service.refresh(refresh_token="token-malformado", agora=AGORA)

    uow.sessao.save.assert_not_called()
    uow.commit.assert_not_called()
