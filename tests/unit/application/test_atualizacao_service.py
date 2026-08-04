"""Testes unitários do caso de uso de atualização de Tenant (IMP-030).

Usam fakes em memória para UoW e repositório — nenhuma persistência real.
Cobertura: Tenant encontrado, Tenant inexistente, delegação ao Aggregate,
persistência via Repository, commit da UoW, nenhuma lógica adicional.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from emprestimo.application.atualizacao import TenantAtualizacaoService
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.platform.tenant import Tenant, TenantState


@dataclass
class _FakeTenantRepo:
    """Fake do TenantRepository."""

    tenants: dict[uuid.UUID, Tenant] = field(default_factory=dict)
    chamadas_find_by_id: int = 0
    chamadas_save: int = 0
    ultimo_id_recebido: uuid.UUID | None = None
    ultimo_tenant_salvo: Tenant | None = None

    def find_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        self.chamadas_find_by_id += 1
        self.ultimo_id_recebido = tenant_id
        return self.tenants.get(tenant_id)

    def save(self, tenant: Tenant) -> None:
        self.chamadas_save += 1
        self.ultimo_tenant_salvo = tenant
        self.tenants[tenant.id] = tenant


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


def _make_tenant(
    tenant_id: uuid.UUID | None = None,
    identificador: str = "IDENT-0001",
    nome: str = "Financeira ABC",
    estado: TenantState = TenantState.ATIVO,
) -> Tenant:
    """Cria um Tenant de teste."""
    return Tenant(
        id=tenant_id or uuid.uuid4(),
        identificador_institucional=identificador,
        nome=nome,
        estado=estado,
        criado_em=datetime.now(UTC),
    )


# --- Testes do TenantAtualizacaoService (IMP-030) ---


def test_atualizacao_com_sucesso() -> None:
    """Deve atualizar o nome e retornar o Tenant atualizado."""
    tenant = _make_tenant(nome="Nome Original")
    uow = _FakeUoW()
    uow.tenant.save(tenant)  # Setup: 1 save
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    resultado = service.atualizar_nome(tenant.id, "Nome Atualizado")

    assert resultado is not None
    assert isinstance(resultado, Tenant)
    assert resultado.id == tenant.id
    assert resultado.identificador_institucional == "IDENT-0001"
    assert resultado.nome == "Nome Atualizado"
    assert resultado.estado == TenantState.ATIVO
    assert resultado.criado_em == tenant.criado_em
    assert uow.tenant.chamadas_find_by_id == 1
    assert uow.tenant.chamadas_save == 2  # 1 setup + 1 service
    assert uow.commit_count == 1


def test_atualizacao_tenant_inexistente_retorna_none() -> None:
    """Deve retornar None quando Tenant não existe (sem exceção)."""
    uow = _FakeUoW()
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    resultado = service.atualizar_nome(uuid.uuid4(), "Qualquer Nome")

    assert resultado is None
    assert uow.tenant.chamadas_find_by_id == 1
    assert uow.tenant.chamadas_save == 0
    assert uow.commit_count == 0


def test_atualizacao_delega_ao_aggregate() -> None:
    """Deve delegar a validação e atualização ao Aggregate Tenant."""
    tenant = _make_tenant(nome="Nome Original")
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    service.atualizar_nome(tenant.id, "Novo Nome")

    # Verifica que o Aggregate foi chamado (nome alterado)
    assert tenant.nome == "Novo Nome"
    # Verifica que os demais campos permanecem inalterados
    assert tenant.identificador_institucional == "IDENT-0001"
    assert tenant.estado == TenantState.ATIVO


def test_atualizacao_persiste_via_repository() -> None:
    """Deve chamar Repository.save com o Tenant atualizado."""
    tenant = _make_tenant(nome="Nome Original")
    uow = _FakeUoW()
    uow.tenant.save(tenant)  # Setup: 1 save
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    resultado = service.atualizar_nome(tenant.id, "Nome Atualizado")

    assert uow.tenant.chamadas_save == 2  # 1 setup + 1 service
    assert uow.tenant.ultimo_tenant_salvo is resultado
    assert uow.tenant.ultimo_tenant_salvo.nome == "Nome Atualizado"


def test_atualizacao_commit_da_uow() -> None:
    """Deve chamar commit na UnitOfWork após persistência."""
    tenant = _make_tenant(nome="Nome Original")
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    service.atualizar_nome(tenant.id, "Nome Atualizado")

    assert uow.commit_count == 1


def test_atualizacao_sem_rollback_quando_sucesso() -> None:
    """Não deve chamar rollback quando a atualização é bem-sucedida."""
    tenant = _make_tenant(nome="Nome Original")
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    service.atualizar_nome(tenant.id, "Nome Atualizado")

    assert uow.rollback_count == 0


def test_atualizacao_nao_altera_estado_nem_identificador() -> None:
    """Deve preservar estado, identificador_institucional, id e criado_em."""
    tenant = _make_tenant(
        nome="Nome Original",
        estado=TenantState.ATIVO,
        identificador="IDENT-ORIGINAL",
    )
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    resultado = service.atualizar_nome(tenant.id, "Novo Nome")

    assert resultado.identificador_institucional == "IDENT-ORIGINAL"
    assert resultado.estado == TenantState.ATIVO
    assert resultado.id == tenant.id
    assert resultado.criado_em == tenant.criado_em


def test_atualizacao_propaga_violacao_invariante_do_aggregate() -> None:
    """Deve propagar ViolacaoInvarianteError do Aggregate (nome vazio)."""
    from emprestimo.domain.common.errors import ViolacaoInvarianteError

    tenant = _make_tenant(nome="Nome Original")
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    try:
        service.atualizar_nome(tenant.id, "")
        pytest.fail("Deveria ter lançado ViolacaoInvarianteError")
    except ViolacaoInvarianteError as exc:
        assert exc.codigo == "DOMAIN-017"
        assert "vazio" in exc.mensagem.lower()

    # Verifica que rollback foi chamado após exceção
    assert uow.rollback_count == 1
    assert uow.commit_count == 0


def test_atualizacao_propaga_violacao_nome_longo_do_aggregate() -> None:
    """Deve propagar ViolacaoInvarianteError do Aggregate (nome > 200)."""
    from emprestimo.domain.common.errors import ViolacaoInvarianteError

    tenant = _make_tenant(nome="Nome Original")
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    try:
        service.atualizar_nome(tenant.id, "A" * 201)
        pytest.fail("Deveria ter lançado ViolacaoInvarianteError")
    except ViolacaoInvarianteError as exc:
        assert exc.codigo == "DOMAIN-017"
        assert "200" in exc.mensagem

    assert uow.rollback_count == 1
    assert uow.commit_count == 0


def test_atualizacao_multiplas_chamadas_independentes() -> None:
    """Cada chamada deve ser independente (novo UoW a cada chamada)."""
    tenant = _make_tenant(nome="Nome Original")
    uow = _FakeUoW()
    uow.tenant.save(tenant)  # Setup: 1 save
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    service.atualizar_nome(tenant.id, "Nome 1")
    service.atualizar_nome(tenant.id, "Nome 2")
    service.atualizar_nome(tenant.id, "Nome 3")

    assert uow.tenant.chamadas_find_by_id == 3
    assert uow.tenant.chamadas_save == 4  # 1 setup + 3 service
    assert uow.commit_count == 3


def test_atualizacao_sem_logica_adicional_alem_delegacao() -> None:
    """Serviço não deve ter lógica além de: buscar → delegar → salvar → commit."""
    tenant = _make_tenant(nome="Nome Original")
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service = TenantAtualizacaoService(uow_factory=lambda: uow)

    # Passa nome já formatado - serviço não deve fazer strip, normalização, etc.
    resultado = service.atualizar_nome(tenant.id, "  Nome com Espaços  ")

    # O Aggregate Tenant.atualizar_nome faz strip e validação
    # O serviço apenas delega
    assert resultado.nome == "Nome com Espaços"  # Aggregate fez strip
