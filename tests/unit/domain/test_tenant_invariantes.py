"""Testes unitários das invariantes do Aggregate Tenant (IMP-009..IMP-012)."""

from __future__ import annotations

import uuid

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.tenant import (
    CONFIGURACOES_PADRAO,
    PERFIL_ADMINISTRADOR,
    Tenant,
)
from emprestimo.domain.platform.usuario import Usuario, UsuarioState


def _tenant() -> Tenant:
    return Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")


def test_usuario_do_mesmo_tenant_e_aceito() -> None:
    tenant = _tenant()
    usuario = Usuario(tenant_id=tenant.id, nome="Maria", email="maria@exemplo.com")

    tenant.adicionar_usuario(usuario)

    assert tenant.usuarios == (usuario,)


def test_usuario_de_outro_tenant_viola_inv_001() -> None:
    tenant = _tenant()
    estranho = Usuario(tenant_id=uuid.uuid4(), nome="X", email="x@exemplo.com")

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.adicionar_usuario(estranho)

    assert excinfo.value.codigo == "INV-001"
    assert tenant.usuarios == ()


def test_usuario_duplicado_viola_inv_001() -> None:
    tenant = _tenant()
    usuario = Usuario(tenant_id=tenant.id, nome="Maria", email="maria@exemplo.com")
    tenant.adicionar_usuario(usuario)

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.adicionar_usuario(usuario)

    assert excinfo.value.codigo == "INV-001"
    assert len(tenant.usuarios) == 1


def test_carteira_do_mesmo_tenant_e_aceita() -> None:
    tenant = _tenant()
    carteira = Carteira(tenant_id=tenant.id, nome="Carteira Principal")

    tenant.adicionar_carteira(carteira)

    assert tenant.carteiras == (carteira,)


def test_carteira_de_outro_tenant_viola_inv_002() -> None:
    tenant = _tenant()
    estranha = Carteira(tenant_id=uuid.uuid4(), nome="Carteira Estranha")

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.adicionar_carteira(estranha)

    assert excinfo.value.codigo == "INV-002"
    assert tenant.carteiras == ()


def test_segunda_carteira_viola_inv_005() -> None:
    tenant = _tenant()
    tenant.adicionar_carteira(Carteira(tenant_id=tenant.id, nome="Carteira Principal"))

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.adicionar_carteira(Carteira(tenant_id=tenant.id, nome="Carteira Extra"))

    assert excinfo.value.codigo == "INV-005"
    assert len(tenant.carteiras) == 1


def test_configuracao_de_outro_tenant_e_rejeitada() -> None:
    tenant = _tenant()
    estranha = Configuracao(tenant_id=uuid.uuid4(), chave="moeda", valor="USD")

    with pytest.raises(ViolacaoInvarianteError):
        tenant.adicionar_configuracao(estranha)


def test_configuracao_com_chave_duplicada_e_rejeitada() -> None:
    tenant = _tenant()
    tenant.adicionar_configuracao(Configuracao(tenant_id=tenant.id, chave="moeda", valor="BRL"))

    with pytest.raises(ViolacaoInvarianteError):
        tenant.adicionar_configuracao(Configuracao(tenant_id=tenant.id, chave="moeda", valor="USD"))


def test_criar_carteira_padrao_vincula_ao_tenant() -> None:
    tenant = _tenant()

    carteira = tenant.criar_carteira_padrao()

    assert carteira.tenant_id == tenant.id
    assert carteira.nome == "Carteira Principal"
    assert tenant.carteiras == (carteira,)


def test_criar_usuario_administrador_com_perfil() -> None:
    tenant = _tenant()

    admin = tenant.criar_usuario_administrador("Maria", "maria@exemplo.com")

    assert admin.tenant_id == tenant.id
    assert admin.nome == "Maria"
    assert admin.email == "maria@exemplo.com"
    assert admin.perfil_acesso == PERFIL_ADMINISTRADOR
    assert admin.estado == UsuarioState.CONVIDADO
    assert tenant.usuarios == (admin,)


def test_inicializar_configuracoes_padrao() -> None:
    tenant = _tenant()

    criadas = tenant.inicializar_configuracoes()

    assert {config.chave for config in criadas} == {chave for chave, _ in CONFIGURACOES_PADRAO}
    assert all(config.tenant_id == tenant.id for config in criadas)
    assert {config.chave for config in tenant.configuracoes} == {
        chave for chave, _ in CONFIGURACOES_PADRAO
    }


def test_inicializar_configuracoes_e_idempotente() -> None:
    tenant = _tenant()
    tenant.inicializar_configuracoes()

    segundas = tenant.inicializar_configuracoes()

    assert segundas == ()
    assert len(tenant.configuracoes) == len(CONFIGURACOES_PADRAO)


def test_provisionamento_completo_via_aggregate() -> None:
    """UC-003 + UC-004 + UC-005 executados através do Aggregate Tenant."""
    tenant = _tenant()

    carteira = tenant.criar_carteira_padrao()
    admin = tenant.criar_usuario_administrador("Maria", "maria@exemplo.com")
    configs = tenant.inicializar_configuracoes()

    assert carteira.tenant_id == tenant.id
    assert admin.tenant_id == tenant.id
    assert len(configs) == len(CONFIGURACOES_PADRAO)
    assert all(config.tenant_id == tenant.id for config in configs)
