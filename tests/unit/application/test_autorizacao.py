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
from emprestimo.application.iam_catalogo import (
    CATALOGO_POR_CODIGO,
    PERMISSOES_ADMIN_TENANT,
    PERMISSOES_PLATAFORMA,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp
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
PERMISSOES_MOTOR_ESPERADAS = {
    "motor.emprestimo.criar",
    "motor.emprestimo.ler",
    "motor.pagamento.registrar",
    "motor.saldo.ler",
    "motor.memoria.ler",
    "motor.quitacao.executar",
    "motor.renegociacao.criar",
}


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


CARTEIRA_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
QUEDA_EM = datetime(2026, 9, 8, 10, 30, tzinfo=UTC)


def _carteira() -> Carteira:
    return Carteira(
        id=CARTEIRA_ID,
        tenant_id=TENANT_ID,
        nome="Carteira Principal",
    )


def _conexao(
    *,
    tenant_id: uuid.UUID = TENANT_ID,
    numero: str | None = None,
    queda_em: datetime | None = None,
) -> ConexaoWhatsApp:
    base = ConexaoWhatsApp.criar(
        tenant_id=tenant_id,
        instancia_id="8a8c901f-16f9-4431-b19d-ed69cccc46c0",
        instancia_nome="adm_tianet",
    )
    if numero is not None:
        base = base.parear(numero, agora=AGORA)
    if queda_em is not None:
        base = base.registrar_queda(agora=queda_em)
    return base


def _principal() -> Principal:
    return Principal(USUARIO_ID, TENANT_ID, "Operador", AGORA + timedelta(minutes=15))


def _uow(
    *,
    usuario: Usuario | None = None,
    perfil: PerfilAcesso | None = None,
    tenant: Tenant | None = None,
    carteiras: list[Carteira] | None = None,
    conexao: ConexaoWhatsApp | None = None,
) -> Mock:
    uow = Mock(spec=UnitOfWork)
    uow.usuario = Mock()
    uow.tenant = Mock()
    uow.perfil_acesso = Mock()
    uow.carteira = Mock()
    uow.conexao_whatsapp = Mock()
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
    resolvidas = (
        carteiras if carteiras is not None else ([_carteira()] if usuario is not None else [])
    )
    uow.carteira.find_by_tenant_id.side_effect = lambda tenant_id: (
        [carteira for carteira in resolvidas if carteira.tenant_id == tenant_id]
    )
    uow.conexao_whatsapp.find_by_tenant_id.side_effect = lambda tenant_id: (
        conexao if conexao is not None and conexao.tenant_id == tenant_id else None
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


def test_catalogo_iam_registra_permissoes_financeiras_como_permissoes_de_tenant() -> None:
    catalogo = set(CATALOGO_POR_CODIGO)
    permissoes_admin = {permissao.codigo for permissao in PERMISSOES_ADMIN_TENANT}
    permissoes_plataforma = {permissao.codigo for permissao in PERMISSOES_PLATAFORMA}

    assert catalogo >= PERMISSOES_MOTOR_ESPERADAS
    assert permissoes_admin >= PERMISSOES_MOTOR_ESPERADAS
    assert PERMISSOES_MOTOR_ESPERADAS.isdisjoint(permissoes_plataforma)


@pytest.mark.parametrize("operacao", sorted(PERMISSOES_MOTOR_ESPERADAS))
def test_exigir_permissao_financeira_segue_rbac_por_perfil_normalizado(operacao: str) -> None:
    principal = Principal(
        USUARIO_ID, TENANT_ID, "Operador Financeiro", AGORA + timedelta(minutes=15)
    )
    service = _service(_uow(perfil=_perfil(nome="Operador Financeiro", permissoes=(operacao,))))

    service.exigir_permissao(principal, operacao)


@pytest.mark.parametrize("operacao", sorted(PERMISSOES_MOTOR_ESPERADAS))
def test_exigir_permissao_financeira_recusa_perfil_sem_operacao(operacao: str) -> None:
    principal = Principal(
        USUARIO_ID, TENANT_ID, "Operador Financeiro", AGORA + timedelta(minutes=15)
    )
    service = _service(
        _uow(perfil=_perfil(nome="Operador Financeiro", permissoes=("devedor.ler",)))
    )

    with pytest.raises(AcessoNegadoError):
        service.exigir_permissao(principal, operacao)


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


def test_consultar_contexto_sem_conexao_nao_tem_alerta() -> None:
    uow = _uow(usuario=_usuario(), perfil=_perfil(), conexao=None)
    service = _service(uow)

    resultado = service.consultar_contexto(_principal())

    assert resultado.whatsapp_pareada is False
    assert resultado.whatsapp_numero is None
    assert resultado.whatsapp_alerta_queda_ativa is False
    assert resultado.whatsapp_queda_detectada_em is None
    uow.conexao_whatsapp.find_by_tenant_id.assert_called_once_with(TENANT_ID)


def test_consultar_contexto_pareada_sem_queda_nao_tem_alerta() -> None:
    conexao = _conexao(numero="5511999990001")
    uow = _uow(usuario=_usuario(), perfil=_perfil(), conexao=conexao)
    service = _service(uow)

    resultado = service.consultar_contexto(_principal())

    assert resultado.whatsapp_pareada is True
    assert resultado.whatsapp_numero == "5511999990001"
    assert resultado.whatsapp_alerta_queda_ativa is False
    assert resultado.whatsapp_queda_detectada_em is None


def test_consultar_contexto_queda_ativa_deriva_do_estado_persistido() -> None:
    conexao = _conexao(queda_em=QUEDA_EM)
    uow = _uow(usuario=_usuario(), perfil=_perfil(), conexao=conexao)
    service = _service(uow)

    resultado = service.consultar_contexto(_principal())

    assert resultado.whatsapp_pareada is False
    assert resultado.whatsapp_numero is None
    assert resultado.whatsapp_alerta_queda_ativa is True
    assert resultado.whatsapp_queda_detectada_em == QUEDA_EM
    assert resultado.whatsapp_queda_detectada_em is not None
    assert resultado.whatsapp_queda_detectada_em.tzinfo is not None
    uow.conexao_whatsapp.find_by_tenant_id.assert_called_once_with(TENANT_ID)


def test_consultar_contexto_isola_queda_por_tenant() -> None:
    conexao_outro_tenant = _conexao(tenant_id=OUTRO_TENANT_ID, queda_em=QUEDA_EM)
    uow = _uow(usuario=_usuario(), perfil=_perfil(), conexao=conexao_outro_tenant)
    service = _service(uow)

    resultado = service.consultar_contexto(_principal())

    assert resultado.whatsapp_alerta_queda_ativa is False
    assert resultado.whatsapp_queda_detectada_em is None
    uow.conexao_whatsapp.find_by_tenant_id.assert_called_once_with(TENANT_ID)


def test_consultar_contexto_nao_carrega_token_nem_qr() -> None:
    from dataclasses import fields as _campos

    from emprestimo.application.autorizacao import ContextoOperacionalResultado

    nomes = {campo.name for campo in _campos(ContextoOperacionalResultado)}
    assert nomes == {
        "usuario_id",
        "usuario_nome",
        "usuario_email",
        "tenant_id",
        "tenant_nome",
        "tenant_identificador_institucional",
        "carteira_id",
        "carteira_nome",
        "perfil_id",
        "perfil_nome",
        "permissoes",
        "whatsapp_pareada",
        "whatsapp_numero",
        "whatsapp_alerta_queda_ativa",
        "whatsapp_queda_detectada_em",
    }
