"""Testes unitários dos casos de uso de consulta de Tenant (IMP-025, IMP-026).

Usam fakes em memória para UoW e repositório — nenhuma persistência real.
Cobertura: Tenant encontrado, Tenant inexistente, delegação ao Repository.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from emprestimo.application.consulta import TenantConsultaPorIdService, TenantConsultaService
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.platform.tenant import Tenant, TenantState


@dataclass
class _FakeTenantRepo:
    """Fake do TenantRepository."""

    tenants: dict[str, Tenant] = field(default_factory=dict)
    chamadas_find_by_identificador: int = 0
    chamadas_find_by_id: int = 0
    ultimo_identificador_recebido: str | None = None
    ultimo_id_recebido: uuid.UUID | None = None

    def find_by_identificador_institucional(self, identificador: str) -> Tenant | None:
        self.chamadas_find_by_identificador += 1
        self.ultimo_identificador_recebido = identificador
        return self.tenants.get(identificador)

    def find_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        self.chamadas_find_by_id += 1
        self.ultimo_id_recebido = tenant_id
        # Busca por ID na lista de tenants
        for tenant in self.tenants.values():
            if tenant.id == tenant_id:
                return tenant
        return None

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


# --- Testes do TenantConsultaService (IMP-025) ---


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


def test_consulta_delega_ao_repository_sem_transformacao() -> None:
    """O serviço deve delegar a chamada ao Repository sem transformar a entrada."""
    uow = _FakeUoW()
    uow.tenant.save(_make_tenant("IDENT-0001"))
    service = TenantConsultaService(uow_factory=lambda: uow)

    # Chama com identificador que tem espaços - o serviço NÃO deve fazer strip
    service.consultar_por_identificador("  IDENT-0001  ")

    # Verifica que o identificador foi passado EXATAMENTE como recebido
    assert uow.tenant.ultimo_identificador_recebido == "  IDENT-0001  "
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


# --- Testes do TenantConsultaPorIdService (IMP-026) ---


def test_consulta_por_id_tenant_encontrado() -> None:
    """Deve retornar o Aggregate Tenant quando encontrado por ID."""
    tenant = _make_tenant("IDENT-0001", "Financeira ABC")
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service = TenantConsultaPorIdService(uow_factory=lambda: uow)

    resultado = service.consultar_por_id(tenant.id)

    assert resultado is not None
    assert isinstance(resultado, Tenant)
    assert resultado.id == tenant.id
    assert resultado.identificador_institucional == "IDENT-0001"
    assert resultado.nome == "Financeira ABC"
    assert uow.tenant.chamadas_find_by_id == 1


def test_consulta_por_id_tenant_inexistente_retorna_none() -> None:
    """Deve retornar None quando Tenant não existe por ID (sem exceção)."""
    uow = _FakeUoW()
    service = TenantConsultaPorIdService(uow_factory=lambda: uow)

    resultado = service.consultar_por_id(uuid.uuid4())

    assert resultado is None
    assert uow.tenant.chamadas_find_by_id == 1


def test_consulta_por_id_delega_ao_repository_sem_transformacao() -> None:
    """O serviço deve delegar a chamada ao Repository sem transformar a entrada."""
    tenant = _make_tenant("IDENT-0001")
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service = TenantConsultaPorIdService(uow_factory=lambda: uow)

    service.consultar_por_id(tenant.id)

    # Verifica que o ID foi passado EXATAMENTE como recebido
    assert uow.tenant.ultimo_id_recebido == tenant.id
    assert uow.tenant.chamadas_find_by_id == 1


def test_consulta_por_id_multiplas_chamadas_independentes() -> None:
    """Cada chamada deve ser independente e chamar o repo novamente."""
    tenant = _make_tenant("IDENT-0001")
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service = TenantConsultaPorIdService(uow_factory=lambda: uow)

    service.consultar_por_id(tenant.id)
    service.consultar_por_id(tenant.id)
    service.consultar_por_id(tenant.id)

    assert uow.tenant.chamadas_find_by_id == 3
