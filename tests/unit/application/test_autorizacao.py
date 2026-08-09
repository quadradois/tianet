"""Testes unitarios do AutorizacaoService (IMP-089)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.application.autorizacao import (
    AutorizacaoService,
    Principal,
    RecursoDeOutroTenantError,
)
from emprestimo.application.errors import AcessoNegadoError, AutenticacaoRecusadaError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState

TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OUTRO_TENANT_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USUARIO_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
RECURSO_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
AGORA = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
JWT_SECRET = "segredo-local-de-teste"
OPERACAO = "devedor.criar"


def _usuario(
    *,
    tenant_id: uuid.UUID = TENANT_ID,
    estado: UsuarioState = UsuarioState.ATIVO,
    perfil_acesso: str | None = "Operador",
) -> Usuario:
    return Usuario(
        id=USUARIO_ID,
        tenant_id=tenant_id,
        nome="Maria",
        email="maria@exemplo.com",
        estado=estado,
        perfil_acesso=perfil_acesso,
    )


def _perfil(
    *,
    tenant_id: uuid.UUID = TENANT_ID,
    nome: str = "Operador",
    permissoes: tuple[str, ...] = (OPERACAO,),
) -> PerfilAcesso:
    perfil = PerfilAcesso(tenant_id=tenant_id, nome=nome)
    for permissao in permissoes:
        perfil.adicionar_permissao(Permissao(codigo=permissao, descricao=permissao))
    return perfil


def _tenant(*, estado: TenantState = TenantState.ATIVO) -> Tenant:
    return Tenant(
        id=TENANT_ID,
        identificador_institucional="IDENT-AUTHZ",
        nome="Tenant Authz",
        estado=estado,
    )


def _uow(
    *,
    usuario: Usuario | None = None,
    perfil: PerfilAcesso | None = None,
    tenant: Tenant | None = None,
) -> Mock:
    uow = Mock(spec=UnitOfWork)
    uow.usuario = Mock()
    uow.tenant = Mock()
    uow.perfil_acesso = Mock()
    uow.commit = Mock()
    uow.rollback = Mock()
    uow.close = Mock()
    uow.__enter__ = Mock(return_value=uow)
    uow.__exit__ = Mock(return_value=None)
    uow.usuario.find_by_id.side_effect = lambda usuario_id: (
        usuario if usuario is not None and usuario_id == usuario.id else None
    )
    tenant = tenant or (_tenant() if usuario is not None else None)
    uow.tenant.find_by_id.side_effect = lambda tenant_id: (
        tenant if tenant is not None and tenant_id == tenant.id else None
    )
    uow.perfil_acesso.find_by_usuario_id.side_effect = lambda usuario_id: (
        perfil if perfil is not None and usuario_id == USUARIO_ID else None
    )
    return uow


def _auditoria() -> Mock:
    return Mock(spec=AuditoriaRegistro)


def _issuer() -> HmacAccessTokenService:
    return HmacAccessTokenService(JWT_SECRET)


def _token(usuario: Usuario, *, agora: datetime = AGORA) -> str:
    return _issuer().emitir(usuario, agora).token


def _adulterar_assinatura(token: str) -> str:
    header, payload, _ = token.split(".", 2)
    return f"{header}.{payload}.assinatura-invalida"


def _service(uow: Mock, auditoria: Mock | None = None) -> AutorizacaoService:
    return AutorizacaoService(lambda: uow, auditoria or _auditoria(), _issuer())


def test_resolver_principal_com_token_valido() -> None:
    usuario = _usuario(perfil_acesso="Operador")
    uow = _uow(usuario=usuario, perfil=_perfil())
    service = _service(uow)

    principal = service.resolver_principal(_token(usuario), agora=AGORA + timedelta(minutes=1))

    assert principal == Principal(
        usuario_id=usuario.id,
        tenant_id=usuario.tenant_id,
        perfil_acesso="Operador",
        access_token_expira_em=AGORA + timedelta(minutes=15),
    )
    uow.usuario.find_by_id.assert_called_once_with(usuario.id)
    uow.perfil_acesso.find_by_usuario_id.assert_called_once_with(usuario.id)
    uow.commit.assert_called_once()


@pytest.mark.parametrize(
    "token",
    [
        "token-malformado",
        _token(_usuario(), agora=AGORA - timedelta(minutes=20)),
    ],
)
def test_resolver_principal_recusa_token_invalido_com_401_uniforme(token: str) -> None:
    auditoria = _auditoria()
    uow = _uow(usuario=_usuario())
    service = _service(uow, auditoria)

    with pytest.raises(AutenticacaoRecusadaError) as exc_info:
        service.resolver_principal(token, agora=AGORA)

    assert str(exc_info.value) == "Autenticacao recusada"
    auditoria.registrar.assert_any_call(
        "autorizacao",
        None,
        "principal.recusado",
        "recusado",
        detalhes='{"erro": "AutenticacaoRecusadaError"}',
    )


def test_resolver_principal_recusa_assinatura_invalida_sem_consultar_banco() -> None:
    auditoria = _auditoria()
    uow = _uow(usuario=_usuario())
    service = _service(uow, auditoria)
    token = _adulterar_assinatura(_token(_usuario()))

    with pytest.raises(AutenticacaoRecusadaError):
        service.resolver_principal(token, agora=AGORA + timedelta(minutes=1))

    uow.usuario.find_by_id.assert_not_called()
    uow.commit.assert_not_called()
    auditoria.registrar.assert_any_call(
        "autorizacao",
        None,
        "principal.recusado",
        "recusado",
        detalhes='{"erro": "AutenticacaoRecusadaError"}',
    )


@pytest.mark.parametrize(
    "usuario",
    [
        None,
        _usuario(estado=UsuarioState.CONVIDADO),
        _usuario(estado=UsuarioState.INATIVO),
        _usuario(estado=UsuarioState.REMOVIDO),
        _usuario(tenant_id=OUTRO_TENANT_ID),
    ],
)
def test_resolver_principal_recusa_usuario_inexistente_inativo_ou_tenant_divergente(
    usuario: Usuario | None,
) -> None:
    token = _token(_usuario())
    uow = _uow(usuario=usuario)
    service = _service(uow)

    with pytest.raises(AutenticacaoRecusadaError):
        service.resolver_principal(token, agora=AGORA + timedelta(minutes=1))

    uow.commit.assert_not_called()


def test_resolver_principal_recusa_tenant_inativo() -> None:
    usuario = _usuario()
    uow = _uow(usuario=usuario, tenant=_tenant(estado=TenantState.INATIVO))
    service = _service(uow)

    with pytest.raises(AutenticacaoRecusadaError):
        service.resolver_principal(_token(usuario), agora=AGORA + timedelta(minutes=1))

    uow.perfil_acesso.find_by_usuario_id.assert_not_called()
    uow.commit.assert_not_called()


def test_resolver_principal_recusa_perfil_normalizado_de_outro_tenant() -> None:
    usuario = _usuario()
    uow = _uow(
        usuario=usuario,
        perfil=_perfil(tenant_id=OUTRO_TENANT_ID),
    )
    service = _service(uow)

    with pytest.raises(AutenticacaoRecusadaError):
        service.resolver_principal(_token(usuario), agora=AGORA + timedelta(minutes=1))

    uow.commit.assert_not_called()


def test_exigir_permissao_autoriza_quando_perfil_possui_operacao() -> None:
    principal = Principal(USUARIO_ID, TENANT_ID, "Operador", AGORA + timedelta(minutes=15))
    uow = _uow(perfil=_perfil())
    service = _service(uow)

    service.exigir_permissao(principal, OPERACAO)

    uow.perfil_acesso.find_by_usuario_id.assert_called_once_with(USUARIO_ID)
    uow.commit.assert_called_once()


@pytest.mark.parametrize(
    ("perfil_nome", "perfil"),
    [
        (None, None),
        ("Operador", None),
        ("Operador", _perfil(permissoes=("devedor.ler",))),
        ("Operador", _perfil(tenant_id=OUTRO_TENANT_ID)),
    ],
)
def test_exigir_permissao_recusa_sem_perfil_ou_sem_permissao(
    perfil_nome: str | None,
    perfil: PerfilAcesso | None,
) -> None:
    principal = Principal(USUARIO_ID, TENANT_ID, perfil_nome, AGORA + timedelta(minutes=15))
    auditoria = _auditoria()
    uow = _uow(perfil=perfil)
    service = _service(uow, auditoria)

    with pytest.raises(AcessoNegadoError) as exc_info:
        service.exigir_permissao(principal, OPERACAO)

    assert str(exc_info.value) == f"Acesso negado para operacao: {OPERACAO}"
    uow.commit.assert_not_called()
    auditoria.registrar.assert_any_call(
        "autorizacao",
        principal.usuario_id,
        "operacao.negada",
        "negado",
        detalhes=(
            '{"tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", '
            '"operacao": "devedor.criar", "erro": "AcessoNegadoError"}'
        ),
    )


def test_autorizar_operacao_valida_tenant_antes_da_permissao() -> None:
    principal = Principal(USUARIO_ID, TENANT_ID, "Operador", AGORA + timedelta(minutes=15))
    auditoria = _auditoria()
    uow = _uow(perfil=_perfil())
    service = _service(uow, auditoria)

    with pytest.raises(RecursoDeOutroTenantError) as exc_info:
        service.autorizar_operacao(
            principal,
            operacao=OPERACAO,
            recurso_id=RECURSO_ID,
            recurso_tenant_id=OUTRO_TENANT_ID,
            recurso_tipo="devedor",
        )

    assert str(exc_info.value) == "Recurso nao encontrado"
    uow.perfil_acesso.find_by_usuario_id.assert_not_called()
    auditoria.registrar.assert_any_call(
        "autorizacao",
        principal.usuario_id,
        "cross_tenant.negado",
        "negado",
        detalhes=(
            '{"tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", '
            '"recurso_tipo": "devedor", '
            '"recurso_id": "dddddddd-dddd-dddd-dddd-dddddddddddd"}'
        ),
    )


def test_autorizar_operacao_do_mesmo_tenant_exige_permissao() -> None:
    principal = Principal(USUARIO_ID, TENANT_ID, "Operador", AGORA + timedelta(minutes=15))
    uow = _uow(perfil=_perfil())
    service = _service(uow)

    service.autorizar_operacao(
        principal,
        operacao=OPERACAO,
        recurso_id=RECURSO_ID,
        recurso_tenant_id=TENANT_ID,
        recurso_tipo="devedor",
    )

    uow.perfil_acesso.find_by_usuario_id.assert_called_once_with(USUARIO_ID)


def test_exigir_permissao_nao_usa_perfil_textual_sem_vinculo_normalizado() -> None:
    principal = Principal(USUARIO_ID, TENANT_ID, "Operador", AGORA + timedelta(minutes=15))
    uow = _uow(perfil=None)
    service = _service(uow)

    with pytest.raises(AcessoNegadoError):
        service.exigir_permissao(principal, OPERACAO)

    uow.perfil_acesso.find_by_usuario_id.assert_called_once_with(USUARIO_ID)
    uow.perfil_acesso.find_by_tenant_nome.assert_not_called()
