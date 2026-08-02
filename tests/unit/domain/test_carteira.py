"""Testes unitários do Aggregate Carteira — estrutura mínima (IMP-007)."""

from __future__ import annotations

import uuid

from emprestimo.domain.credit.carteira import Carteira


def test_criacao_carteira_exige_tenant() -> None:
    tenant_id = uuid.uuid4()
    carteira = Carteira(tenant_id=tenant_id, nome="Carteira Principal")

    assert carteira.tenant_id == tenant_id
    assert carteira.nome == "Carteira Principal"
    assert carteira.id is not None
