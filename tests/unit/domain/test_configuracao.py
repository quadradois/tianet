"""Testes unitários da Entity Configuração (IMP-003)."""

from __future__ import annotations

import uuid

from emprestimo.domain.platform.configuracao import Configuracao


def test_criacao_configuracao_exige_tenant_chave_e_valor() -> None:
    tenant_id = uuid.uuid4()
    config = Configuracao(tenant_id=tenant_id, chave="moeda", valor="BRL")

    assert config.tenant_id == tenant_id
    assert config.chave == "moeda"
    assert config.valor == "BRL"
    assert config.id is not None


def test_configuracoes_com_mesma_chave_em_tenants_distintos_sao_entidades_distintas() -> None:
    a = Configuracao(tenant_id=uuid.uuid4(), chave="moeda", valor="BRL")
    b = Configuracao(tenant_id=uuid.uuid4(), chave="moeda", valor="USD")

    assert a.id != b.id
