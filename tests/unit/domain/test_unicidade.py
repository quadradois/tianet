"""Testes unitários do UnicidadeTenantService (IMP-008, UC-002)."""

from __future__ import annotations

import uuid

import pytest

from emprestimo.domain.common.errors import TenantJaExisteError
from emprestimo.domain.platform.ports import TenantRepository
from emprestimo.domain.platform.tenant import Tenant
from emprestimo.domain.platform.unicidade import UnicidadeTenantService


class _TenantRepositoryFake(TenantRepository):
    """Fake do contrato — permite testar o service sem persistência."""

    def __init__(self) -> None:
        self._por_identificador: dict[str, Tenant] = {}

    def save(self, tenant: Tenant) -> None:
        self._por_identificador[tenant.identificador_institucional] = tenant

    def find_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        return next((t for t in self._por_identificador.values() if t.id == tenant_id), None)

    def find_by_identificador_institucional(self, identificador: str) -> Tenant | None:
        return self._por_identificador.get(identificador)

    def find_all(self) -> list[Tenant]:
        return list(self._por_identificador.values())


def test_unicidade_aceita_organizacao_inexistente() -> None:
    service = UnicidadeTenantService(_TenantRepositoryFake())

    service.verificar("IDENT-NOVA")

    assert True  # nenhuma exceção é levantada


def test_unicidade_rejeita_organizacao_existente() -> None:
    repo = _TenantRepositoryFake()
    repo.save(Tenant(identificador_institucional="IDENT-EXISTENTE", nome="Financeira ABC"))
    service = UnicidadeTenantService(repo)

    with pytest.raises(TenantJaExisteError) as excinfo:
        service.verificar("IDENT-EXISTENTE")

    assert excinfo.value.identificador_institucional == "IDENT-EXISTENTE"


def test_unicidade_normaliza_espacos_ao_redor() -> None:
    repo = _TenantRepositoryFake()
    repo.save(Tenant(identificador_institucional="IDENT-EXISTENTE", nome="Financeira ABC"))
    service = UnicidadeTenantService(repo)

    with pytest.raises(TenantJaExisteError):
        service.verificar("  IDENT-EXISTENTE  ")


def test_unicidade_aceita_identificadores_distintos() -> None:
    repo = _TenantRepositoryFake()
    repo.save(Tenant(identificador_institucional="IDENT-A", nome="Financeira A"))
    service = UnicidadeTenantService(repo)

    service.verificar("IDENT-B")

    assert True  # nenhuma exceção é levantada
