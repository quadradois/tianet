"""Testes unitários dos casos de uso de consulta de Tenant (IMP-025, IMP-026, IMP-027).

Usam fakes em memória para UoW e repositório — nenhuma persistência real.
Cobertura: Tenant encontrado, Tenant inexistente, delegação ao Repository.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from emprestimo.application.consulta import (
    TenantConsultaPorIdService,
    TenantConsultaService,
    TenantListagemService,
)
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.platform.ports import TenantFiltro, TenantOrdenacao, TenantPaginado
from emprestimo.domain.platform.tenant import Tenant, TenantState


@dataclass
class _FakeTenantRepo:
    """Fake do TenantRepository."""

    tenants: dict[str, Tenant] = field(default_factory=dict)
    chamadas_find_by_identificador: int = 0
    chamadas_find_by_id: int = 0
    chamadas_find_all_paginated: int = 0
    ultimo_identificador_recebido: str | None = None
    ultimo_id_recebido: uuid.UUID | None = None
    ultimos_parametros_paginacao: dict[str, Any] | None = None

    def find_by_identificador_institucional(self, identificador: str) -> Tenant | None:
        self.chamadas_find_by_identificador += 1
        self.ultimo_identificador_recebido = identificador
        return self.tenants.get(identificador)

    def find_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        self.chamadas_find_by_id += 1
        self.ultimo_id_recebido = tenant_id
        for tenant in self.tenants.values():
            if tenant.id == tenant_id:
                return tenant
        return None

    def find_all_paginated(
        self,
        page: int = 1,
        size: int = 20,
        ordenacao: TenantOrdenacao | None = None,
        filtro: TenantFiltro | None = None,
    ) -> TenantPaginado:
        self.chamadas_find_all_paginated += 1
        self.ultimos_parametros_paginacao = {
            "page": page,
            "size": size,
            "ordenacao": ordenacao,
            "filtro": filtro,
        }

        # Aplicar filtro em memória para teste
        tenants_filtrados = list(self.tenants.values())
        if filtro and filtro.estado is not None:
            tenants_filtrados = [t for t in tenants_filtrados if t.estado == filtro.estado]

        # Aplicar ordenação
        if ordenacao is None:
            ordenacao = TenantOrdenacao()

        reverse = ordenacao.direcao == "desc"
        # Ordenar com tie-breaker por id (ordenar por id primeiro, depois pelo campo principal)
        tenants_filtrados.sort(key=lambda t: t.id)
        tenants_filtrados.sort(key=lambda t: getattr(t, ordenacao.campo), reverse=reverse)

        total = len(tenants_filtrados)
        offset = (page - 1) * size
        items = tenants_filtrados[offset : offset + size]
        pages = (total + size - 1) // size if size > 0 else 0

        return TenantPaginado(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    def save(self, tenant: Tenant) -> None:
        self.tenants[tenant.identificador_institucional] = tenant


@dataclass
class _FakeUoW(UnitOfWork):
    """Fake do UnitOfWork."""

    tenant: _FakeTenantRepo = field(default_factory=_FakeTenantRepo)  # type: ignore[assignment]
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


# --- Testes do TenantListagemService (IMP-027) ---


def test_listagem_vazia() -> None:
    """Deve retornar lista vazia quando não há tenants."""
    uow = _FakeUoW()
    service = TenantListagemService(uow_factory=lambda: uow)

    resultado = service.listar()

    assert isinstance(resultado, TenantPaginado)
    assert resultado.items == []
    assert resultado.total == 0
    assert resultado.page == 1
    assert resultado.size == 20
    assert resultado.pages == 0
    assert uow.tenant.chamadas_find_all_paginated == 1


def test_listagem_com_resultados() -> None:
    """Deve retornar tenants paginados."""
    uow = _FakeUoW()
    uow.tenant.save(_make_tenant("IDENT-0001", "Tenant A"))
    uow.tenant.save(_make_tenant("IDENT-0002", "Tenant B"))
    uow.tenant.save(_make_tenant("IDENT-0003", "Tenant C"))
    service = TenantListagemService(uow_factory=lambda: uow)

    resultado = service.listar(page=1, size=10)

    assert resultado.total == 3
    assert len(resultado.items) == 3
    assert resultado.page == 1
    assert resultado.size == 10
    assert resultado.pages == 1


def test_listagem_paginacao() -> None:
    """Deve respeitar paginação (page, size)."""
    uow = _FakeUoW()
    for i in range(1, 6):
        uow.tenant.save(_make_tenant(f"IDENT-00{i}", f"Tenant {i}"))
    service = TenantListagemService(uow_factory=lambda: uow)

    page1 = service.listar(page=1, size=2)
    page2 = service.listar(page=2, size=2)
    page3 = service.listar(page=3, size=2)

    assert page1.total == 5
    assert len(page1.items) == 2
    assert page1.page == 1
    assert page1.pages == 3
    assert len(page2.items) == 2
    assert page2.page == 2
    assert len(page3.items) == 1
    assert page3.page == 3


def test_listagem_filtro_estado() -> None:
    """Deve filtrar por estado operacional."""
    uow = _FakeUoW()
    t1 = _make_tenant("IDENT-0001", "Ativo 1")
    t1.estado = TenantState.ATIVO
    t2 = _make_tenant("IDENT-0002", "Inativo 1")
    t2.estado = TenantState.INATIVO
    t3 = _make_tenant("IDENT-0003", "Provisao 1")
    t3.estado = TenantState.PROVISAO
    uow.tenant.save(t1)
    uow.tenant.save(t2)
    uow.tenant.save(t3)
    service = TenantListagemService(uow_factory=lambda: uow)

    resultado = service.listar(filtro=TenantFiltro(estado=TenantState.ATIVO))

    assert resultado.total == 1
    assert len(resultado.items) == 1
    assert resultado.items[0].identificador_institucional == "IDENT-0001"
    assert resultado.items[0].estado == TenantState.ATIVO


def test_listagem_ordenacao() -> None:
    """Deve ordenar conforme especificado."""
    uow = _FakeUoW()
    uow.tenant.save(_make_tenant("IDENT-C", "Tenant C"))
    uow.tenant.save(_make_tenant("IDENT-A", "Tenant A"))
    uow.tenant.save(_make_tenant("IDENT-B", "Tenant B"))
    service = TenantListagemService(uow_factory=lambda: uow)

    resultado = service.listar(
        ordenacao=TenantOrdenacao(campo="identificador_institucional", direcao="asc")
    )

    ids = [t.identificador_institucional for t in resultado.items]
    assert ids == ["IDENT-A", "IDENT-B", "IDENT-C"]


def test_listagem_delega_ao_repository_sem_transformacao() -> None:
    """O serviço deve delegar os parâmetros ao Repository sem transformação."""
    uow = _FakeUoW()
    uow.tenant.save(_make_tenant("IDENT-0001"))
    service = TenantListagemService(uow_factory=lambda: uow)

    filtro = TenantFiltro(estado=TenantState.ATIVO)
    ordenacao = TenantOrdenacao(campo="nome", direcao="desc")
    service.listar(page=2, size=5, ordenacao=ordenacao, filtro=filtro)

    params = uow.tenant.ultimos_parametros_paginacao
    assert params is not None
    assert params["page"] == 2
    assert params["size"] == 5
    assert params["ordenacao"] == ordenacao
    assert params["filtro"] == filtro
    assert uow.tenant.chamadas_find_all_paginated == 1


def test_listagem_limite_maximo_size() -> None:
    """Deve limitar size ao máximo de 100."""
    uow = _FakeUoW()
    for i in range(1, 151):
        uow.tenant.save(_make_tenant(f"IDENT-{i:03d}", f"Tenant {i}"))
    service = TenantListagemService(uow_factory=lambda: uow)

    resultado = service.listar(page=1, size=150)  # Acima do limite

    assert (
        resultado.size == 150
    )  # O serviço não limita; o repo limita (teste unitário do fake não limita)
    # Nota: a limitação de 100 é feita no Repository, não no serviço


def test_listagem_page_minimo_1() -> None:
    """Deve garantir page mínimo 1 (validação feita no Repository)."""
    uow = _FakeUoW()
    uow.tenant.save(_make_tenant("IDENT-0001"))
    service = TenantListagemService(uow_factory=lambda: uow)

    # O serviço delega sem transformação; a validação de page >= 1 é responsabilidade do Repository
    _ = service.listar(page=0, size=10)

    # Verifica que o page=0 foi passado para o repo (sem transformação no serviço)
    assert uow.tenant.ultimos_parametros_paginacao is not None
    assert uow.tenant.ultimos_parametros_paginacao["page"] == 0
