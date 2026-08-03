"""Testes unitários do TenantConsultaService (IMP-025).

Usam fakes em memória para UoW e repositório — nenhuma persistência real.
Cobertura: Tenant encontrado, Tenant inexistente, repository chamado uma vez.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from emprestimo.application.consulta import TenantConsultaService
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.platform.tenant import Tenant, TenantState


@dataclass
class _FakeTenantRepo:
    """Fake do TenantRepository."""

    tenants: dict[str, Tenant] = field(default_factory=dict)
    chamadas_find_by_identificador: int = 0

    def find_by_identificador_institucional(self, identificador: str) -> Tenant | None:
        self.chamadas_find_by_identificador += 1
        return self.tenants.get(identificador)

    def save(self, tenant: Tenant) -> None:
        self.tenants[tenant.identificador_institucional] = tenant


@dataclass
class _FakeUoW(UnitOfWork):
    """Fake do UnitOfWork."""

    tenant: _FakeTenantRepo = field(default_factory=_FakeTenantRepo)
    commit_count: int = 0
    rollback_count: int = 0

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        pass


def _make_tenant(identificador: str = "IDENT-0001", nome: str = "Financeira ABC") -> Tenant:
    """Cria um Tenant de teste."""
    return Tenant(
        id=uuid.uuid4(),
        identificador_institucional=identificador,
        nome=nome,
        estado=TenantState.ATIVO,
        criado_em=datetime.now(UTC),
    )


def test_consulta_tenant_encontrado() -> None:
    """Deve retornar o Aggregate Tenant quando encontrado."""
    uow = _FakeUoW()
    uow.tenant.save(_make_tenant("IDENT-0001", "Financeira ABC"))
    service = TenantConsultaService(uow_factory=lambda: uow)

    resultado = service.consultar_por_identificador("IDENT-0001")

    assert resultado is not None
    assert isinstance(resultado, Tenant)
    assert resultado.identificador_institucional == "IDENT-0001"
    assert resultado.nome == "Financeira ABC"
    assert uow.tenant.chamadas_find_by_identificador == 1


def test_consulta_tenant_inexistente_retorna_none() -> None:
    """Deve retornar None quando Tenant não existe (sem exceção)."""
    uow = _FakeUoW()
    service = TenantConsultaService(uow_factory=lambda: uow)

    resultado = service.consultar_por_identificador("IDENT-INEXISTENTE")

    assert resultado is None
    assert uow.tenant.chamadas_find_by_identificador == 1


def test_consulta_repository_chamado_exatamente_uma_vez() -> None:
    """Repository deve ser chamado exatamente uma vez por consulta."""
    uow = _FakeUoW()
    uow.tenant.save(_make_tenant("IDENT-0001"))
    service = TenantConsultaService(uow_factory=lambda: uow)

    service.consultar_por_identificador("IDENT-0001")

    assert uow.tenant.chamadas_find_by_identificador == 1


def test_consulta_sem_logica_adicional_alem_da_orquestracao() -> None:
    """O caso de uso não deve conter lógica além da orquestração (strip + repo call)."""
    uow = _FakeUoW()
    uow.tenant.save(_make_tenant("IDENT-0001"))
    service = TenantConsultaService(uow_factory=lambda: uow)

    # Testa que apenas faz strip e delega ao repo
    resultado = service.consultar_por_identificador("  IDENT-0001  ")

    assert resultado is not None
    assert resultado.identificador_institucional == "IDENT-0001"
    assert uow.tenant.chamadas_find_by_identificador == 1


def test_consulta_multiplas_chamadas_independentes() -> None:
    """Cada chamada deve ser independente e chamar o repo novamente."""
    uow = _FakeUoW()
    uow.tenant.save(_make_tenant("IDENT-0001"))
    service = TenantConsultaService(uow_factory=lambda: uow)

    service.consultar_por_identificador("IDENT-0001")
    service.consultar_por_identificador("IDENT-0001")
    service.consultar_por_identificador("IDENT-0001")

    assert uow.tenant.chamadas_find_by_identificador == 3
