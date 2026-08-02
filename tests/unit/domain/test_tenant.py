"""Testes unitários do Aggregate Tenant (IMP-001)."""

from __future__ import annotations

from datetime import UTC, datetime

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
