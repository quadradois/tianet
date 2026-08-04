"""Testes unitários do Aggregate Tenant (IMP-001)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.tenant import Tenant, TenantState


def test_criacao_tenant_gera_identidade() -> None:
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")

    assert tenant.id is not None
    assert tenant.identificador_institucional == "IDENT-0001"
    assert tenant.nome == "Financeira ABC"


def test_estado_inicial_do_tenant_e_provisao() -> None:
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")

    assert tenant.estado == TenantState.PROVISAO


def test_timestamp_de_criacao_preenchido() -> None:
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")

    assert isinstance(tenant.criado_em, datetime)
    assert tenant.criado_em.tzinfo is not None


def test_identificadores_distintos_geram_tenants_distintos() -> None:
    a = Tenant(identificador_institucional="IDENT-A", nome="A")
    b = Tenant(identificador_institucional="IDENT-A", nome="A")

    assert a.id != b.id


def test_estado_aceita_ativos_e_inativos() -> None:
    ativo = Tenant(identificador_institucional="IDENT-A", nome="A", estado=TenantState.ATIVO)
    inativo = Tenant(identificador_institucional="IDENT-B", nome="B", estado=TenantState.INATIVO)

    assert ativo.estado == TenantState.ATIVO
    assert inativo.estado == TenantState.INATIVO


def test_timestamp_pode_ser_fornecido() -> None:
    criado = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="A", criado_em=criado)

    assert tenant.criado_em == criado


# --------------------------------------------------------------------------- #
# Atualização cadastral (IMP-029)
# --------------------------------------------------------------------------- #


def test_atualizar_nome_altera_nome_e_preserva_demais_campos() -> None:
    tenant = Tenant(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        estado=TenantState.ATIVO,
    )
    id_original = tenant.id
    identificador_original = tenant.identificador_institucional
    criado_em_original = tenant.criado_em
    estado_original = tenant.estado

    tenant.atualizar_nome("Financeira ABC Atualizada")

    assert tenant.nome == "Financeira ABC Atualizada"
    assert tenant.id == id_original
    assert tenant.identificador_institucional == identificador_original
    assert tenant.criado_em == criado_em_original
    assert tenant.estado == estado_original


def test_atualizar_nome_vazio_lanca_violacao() -> None:
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.atualizar_nome("")

    assert excinfo.value.codigo == "DOMAIN-017"
    assert "vazio" in excinfo.value.mensagem.lower()
    assert tenant.nome == "Financeira ABC"


def test_atualizar_nome_espacos_lanca_violacao() -> None:
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.atualizar_nome("   ")

    assert excinfo.value.codigo == "DOMAIN-017"
    assert tenant.nome == "Financeira ABC"


def test_atualizar_nome_maior_que_200_lanca_violacao() -> None:
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.atualizar_nome("A" * 201)

    assert excinfo.value.codigo == "DOMAIN-017"
    assert "200" in excinfo.value.mensagem
    assert tenant.nome == "Financeira ABC"


def test_atualizar_nome_limite_200_caracteres_aceito() -> None:
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")
    nome_200 = "A" * 200

    tenant.atualizar_nome(nome_200)

    assert tenant.nome == nome_200


def test_atualizar_nome_identificador_institucional_permance_imutavel() -> None:
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")

    tenant.atualizar_nome("Outro Nome")

    assert tenant.identificador_institucional == "IDENT-0001"


# --------------------------------------------------------------------------- #
# Transições de estado operacional — inativação (IMP-033)
# --------------------------------------------------------------------------- #


def test_inativar_tenant_ativo_transiciona_para_inativo() -> None:
    tenant = Tenant(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        estado=TenantState.ATIVO,
    )

    tenant.inativar()

    assert tenant.estado == TenantState.INATIVO


def test_inativar_tenant_ja_inativo_lanca_violacao() -> None:
    tenant = Tenant(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        estado=TenantState.INATIVO,
    )

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.inativar()

    assert excinfo.value.codigo == "DOMAIN-017"
    assert "inativados" in excinfo.value.mensagem.lower()
    assert tenant.estado == TenantState.INATIVO


def test_inativar_tenant_em_provisao_lanca_violacao() -> None:
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")

    assert tenant.estado == TenantState.PROVISAO

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.inativar()

    assert excinfo.value.codigo == "DOMAIN-017"
    assert "inativados" in excinfo.value.mensagem.lower()
    assert tenant.estado == TenantState.PROVISAO


def test_inativar_preserva_atributos_cadastrais() -> None:
    tenant = Tenant(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        estado=TenantState.ATIVO,
    )
    id_original = tenant.id
    identificador_original = tenant.identificador_institucional
    nome_original = tenant.nome
    criado_em_original = tenant.criado_em

    tenant.inativar()

    assert tenant.id == id_original
    assert tenant.identificador_institucional == identificador_original
    assert tenant.nome == nome_original
    assert tenant.criado_em == criado_em_original


def test_inativar_preserva_identidade_e_vinculos() -> None:
    tenant = Tenant(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        estado=TenantState.ATIVO,
    )
    id_original = tenant.id

    tenant.inativar()

    assert tenant.id == id_original
    assert tenant.identificador_institucional == "IDENT-0001"


# --------------------------------------------------------------------------- #
# Transições de estado operacional — reativação (IMP-033)
# --------------------------------------------------------------------------- #


def test_reativar_tenant_inativo_transiciona_para_ativo() -> None:
    tenant = Tenant(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        estado=TenantState.INATIVO,
    )

    tenant.reativar()

    assert tenant.estado == TenantState.ATIVO


def test_reativar_tenant_ja_ativo_lanca_violacao() -> None:
    tenant = Tenant(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        estado=TenantState.ATIVO,
    )

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.reativar()

    assert excinfo.value.codigo == "DOMAIN-017"
    assert "reativados" in excinfo.value.mensagem.lower()
    assert tenant.estado == TenantState.ATIVO


def test_reativar_tenant_em_provisao_lanca_violacao() -> None:
    tenant = Tenant(identificador_institucional="IDENT-0001", nome="Financeira ABC")

    assert tenant.estado == TenantState.PROVISAO

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        tenant.reativar()

    assert excinfo.value.codigo == "DOMAIN-017"
    assert "reativados" in excinfo.value.mensagem.lower()
    assert tenant.estado == TenantState.PROVISAO


def test_reativar_preserva_atributos_cadastrais() -> None:
    tenant = Tenant(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        estado=TenantState.INATIVO,
    )
    id_original = tenant.id
    identificador_original = tenant.identificador_institucional
    nome_original = tenant.nome
    criado_em_original = tenant.criado_em

    tenant.reativar()

    assert tenant.id == id_original
    assert tenant.identificador_institucional == identificador_original
    assert tenant.nome == nome_original
    assert tenant.criado_em == criado_em_original


def test_reativar_preserva_identidade() -> None:
    tenant = Tenant(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        estado=TenantState.INATIVO,
    )
    id_original = tenant.id

    tenant.reativar()

    assert tenant.id == id_original
    assert tenant.identificador_institucional == "IDENT-0001"


def test_ciclo_inativar_reativar_retorna_ao_estado_ativo() -> None:
    """US-013 + US-014: inativar seguido de reativar restaura Ativo."""
    tenant = Tenant(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        estado=TenantState.ATIVO,
    )

    tenant.inativar()
    assert tenant.estado == TenantState.INATIVO

    tenant.reativar()
    assert tenant.estado == TenantState.ATIVO
