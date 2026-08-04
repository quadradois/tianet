"""Testes unitários do caso de uso de transições de estado (IMP-034/035).

Usam fakes em memória para UoW, repositório e auditoria — nenhuma
persistência real. Cobertura: inativação/reativação com sucesso, Tenant
inexistente, delegação ao Aggregate, persistência via Repository, commit da
UoW, tradução de violação em TransicaoEstadoInvalidaError e trilha de
auditoria (inicio/sucesso/falha).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from emprestimo.application.errors import TransicaoEstadoInvalidaError
from emprestimo.application.estado import TenantEstadoService
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
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
class _FakeAuditoria(AuditoriaRegistro):
    """Fake da AuditoriaRegistro — captura os eventos registrados."""

    eventos: list[tuple[str, uuid.UUID | None, str, str]] = field(default_factory=list)

    def registrar(
        self,
        entidade: str,
        entidade_id: uuid.UUID | None,
        acao: str,
        status: str,
        detalhes: str | None = None,
    ) -> None:
        del detalhes
        self.eventos.append((entidade, entidade_id, acao, status))


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


def _fazer_servico(uow: _FakeUoW) -> tuple[TenantEstadoService, _FakeAuditoria]:
    """Cria o serviço de estado com UoW e auditoria fakes."""
    auditoria = _FakeAuditoria()
    service = TenantEstadoService(
        uow_factory=lambda: uow,
        auditoria=auditoria,
    )
    return service, auditoria


# --- Testes de inativação (US-013, IMP-034) ---


def test_inativacao_com_sucesso() -> None:
    """Deve inativar o Tenant e retorná-lo com estado Inativo."""
    tenant = _make_tenant(estado=TenantState.ATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)  # Setup: 1 save
    service, _ = _fazer_servico(uow)

    resultado = service.inativar(tenant.id)

    assert resultado is not None
    assert isinstance(resultado, Tenant)
    assert resultado.id == tenant.id
    assert resultado.estado == TenantState.INATIVO
    assert resultado.identificador_institucional == "IDENT-0001"
    assert resultado.nome == "Financeira ABC"
    assert resultado.criado_em == tenant.criado_em
    assert uow.tenant.chamadas_find_by_id == 1
    assert uow.tenant.chamadas_save == 2  # 1 setup + 1 service
    assert uow.commit_count == 1


def test_inativacao_tenant_inexistente_retorna_none() -> None:
    """Deve retornar None quando Tenant não existe (sem exceção)."""
    uow = _FakeUoW()
    service, _ = _fazer_servico(uow)

    resultado = service.inativar(uuid.uuid4())

    assert resultado is None
    assert uow.tenant.chamadas_find_by_id == 1
    assert uow.tenant.chamadas_save == 0
    assert uow.commit_count == 0


def test_inativacao_delega_ao_aggregate() -> None:
    """Deve delegar a transição ao Aggregate Tenant."""
    tenant = _make_tenant(estado=TenantState.ATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, _ = _fazer_servico(uow)

    service.inativar(tenant.id)

    assert tenant.estado == TenantState.INATIVO
    assert tenant.identificador_institucional == "IDENT-0001"
    assert tenant.nome == "Financeira ABC"


def test_inativacao_persiste_via_repository() -> None:
    """Deve chamar Repository.save com o Tenant transicionado."""
    tenant = _make_tenant(estado=TenantState.ATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)  # Setup: 1 save
    service, _ = _fazer_servico(uow)

    resultado = service.inativar(tenant.id)

    assert uow.tenant.chamadas_save == 2  # 1 setup + 1 service
    assert uow.tenant.ultimo_tenant_salvo is resultado
    assert uow.tenant.ultimo_tenant_salvo.estado == TenantState.INATIVO


def test_inativacao_commit_da_uow() -> None:
    """Deve chamar commit na UnitOfWork após persistência."""
    tenant = _make_tenant(estado=TenantState.ATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, _ = _fazer_servico(uow)

    service.inativar(tenant.id)

    assert uow.commit_count == 1
    assert uow.rollback_count == 0


def test_inativacao_estado_divergente_traduz_para_conflito() -> None:
    """Violação do Aggregate (ex.: já Inativo) vira TransicaoEstadoInvalidaError."""
    tenant = _make_tenant(estado=TenantState.INATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, _ = _fazer_servico(uow)

    with pytest.raises(TransicaoEstadoInvalidaError) as excinfo:
        service.inativar(tenant.id)

    assert excinfo.value.acao == "inativar"
    assert excinfo.value.tenant_id == tenant.id
    assert "inativados" in excinfo.value.motivo.lower()
    assert tenant.estado == TenantState.INATIVO
    assert uow.rollback_count == 1
    assert uow.commit_count == 0


def test_inativacao_provisao_traduz_para_conflito() -> None:
    """Tenant em Provisão não pode ser inativado — conflito traduzido."""
    tenant = _make_tenant(estado=TenantState.PROVISAO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, _ = _fazer_servico(uow)

    with pytest.raises(TransicaoEstadoInvalidaError):
        service.inativar(tenant.id)

    assert tenant.estado == TenantState.PROVISAO
    assert uow.rollback_count == 1


def test_inativacao_nao_altera_dados_cadastrais() -> None:
    """Inativação altera apenas o estado; demais campos permanecem."""
    tenant = _make_tenant(estado=TenantState.ATIVO, identificador="IDENT-ORIGINAL")
    id_original = tenant.id
    criado_em = tenant.criado_em
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, _ = _fazer_servico(uow)

    resultado = service.inativar(tenant.id)

    assert resultado.identificador_institucional == "IDENT-ORIGINAL"
    assert resultado.nome == "Financeira ABC"
    assert resultado.id == id_original
    assert resultado.criado_em == criado_em


# --- Testes de reativação (US-014, IMP-034) ---


def test_reativacao_com_sucesso() -> None:
    """Deve reativar o Tenant e retorná-lo com estado Ativo."""
    tenant = _make_tenant(estado=TenantState.INATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)  # Setup: 1 save
    service, _ = _fazer_servico(uow)

    resultado = service.reativar(tenant.id)

    assert resultado is not None
    assert isinstance(resultado, Tenant)
    assert resultado.id == tenant.id
    assert resultado.estado == TenantState.ATIVO
    assert resultado.identificador_institucional == "IDENT-0001"
    assert resultado.nome == "Financeira ABC"
    assert resultado.criado_em == tenant.criado_em
    assert uow.tenant.chamadas_find_by_id == 1
    assert uow.tenant.chamadas_save == 2  # 1 setup + 1 service
    assert uow.commit_count == 1


def test_reativacao_tenant_inexistente_retorna_none() -> None:
    """Deve retornar None quando Tenant não existe (sem exceção)."""
    uow = _FakeUoW()
    service, _ = _fazer_servico(uow)

    resultado = service.reativar(uuid.uuid4())

    assert resultado is None
    assert uow.tenant.chamadas_find_by_id == 1
    assert uow.tenant.chamadas_save == 0
    assert uow.commit_count == 0


def test_reativacao_estado_divergente_traduz_para_conflito() -> None:
    """Violação do Aggregate (ex.: já Ativo) vira TransicaoEstadoInvalidaError."""
    tenant = _make_tenant(estado=TenantState.ATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, _ = _fazer_servico(uow)

    with pytest.raises(TransicaoEstadoInvalidaError) as excinfo:
        service.reativar(tenant.id)

    assert excinfo.value.acao == "reativar"
    assert excinfo.value.tenant_id == tenant.id
    assert "reativados" in excinfo.value.motivo.lower()
    assert tenant.estado == TenantState.ATIVO
    assert uow.rollback_count == 1
    assert uow.commit_count == 0


def test_reativacao_nao_recria_dados() -> None:
    """Reativação altera apenas o estado; nada é recriado."""
    tenant = _make_tenant(estado=TenantState.INATIVO, identificador="IDENT-ORIGINAL")
    id_original = tenant.id
    criado_em = tenant.criado_em
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, _ = _fazer_servico(uow)

    resultado = service.reativar(tenant.id)

    assert resultado.identificador_institucional == "IDENT-ORIGINAL"
    assert resultado.nome == "Financeira ABC"
    assert resultado.id == id_original
    assert resultado.criado_em == criado_em


# --- Testes de auditoria das transições (IMP-035) ---


def test_auditoria_inativacao_sucesso() -> None:
    """Deve registrar inativar.inicio e inativar.sucesso, sem falha."""
    tenant = _make_tenant(estado=TenantState.ATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, auditoria = _fazer_servico(uow)

    service.inativar(tenant.id)

    acoes = [evento[2] for evento in auditoria.eventos]
    assert acoes == ["inativar.inicio", "inativar.sucesso"]
    assert all(evento[0] == "tenant" for evento in auditoria.eventos)
    assert all(evento[1] == tenant.id for evento in auditoria.eventos)


def test_auditoria_reativacao_sucesso() -> None:
    """Deve registrar reativar.inicio e reativar.sucesso, sem falha."""
    tenant = _make_tenant(estado=TenantState.INATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, auditoria = _fazer_servico(uow)

    service.reativar(tenant.id)

    acoes = [evento[2] for evento in auditoria.eventos]
    assert acoes == ["reativar.inicio", "reativar.sucesso"]
    assert all(evento[0] == "tenant" for evento in auditoria.eventos)
    assert all(evento[1] == tenant.id for evento in auditoria.eventos)


def test_auditoria_ausente_quando_tenant_inexistente() -> None:
    """Não deve registrar nenhum evento quando o Tenant não existe."""
    uow = _FakeUoW()
    service, auditoria = _fazer_servico(uow)

    resultado = service.inativar(uuid.uuid4())

    assert resultado is None
    assert auditoria.eventos == []


def test_auditoria_falha_em_transicao_invalida() -> None:
    """Deve registrar inativar.falha quando o Aggregate rejeita a transição."""
    tenant = _make_tenant(estado=TenantState.INATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, auditoria = _fazer_servico(uow)

    with pytest.raises(TransicaoEstadoInvalidaError):
        service.inativar(tenant.id)

    acoes = [evento[2] for evento in auditoria.eventos]
    assert acoes == ["inativar.inicio", "inativar.falha"]
    assert "inativar.sucesso" not in acoes


def test_auditoria_ordem_dos_eventos_reativacao() -> None:
    """A sequência deve respeitar: inicio → ... → sucesso."""
    tenant = _make_tenant(estado=TenantState.INATIVO)
    uow = _FakeUoW()
    uow.tenant.save(tenant)
    service, auditoria = _fazer_servico(uow)

    service.reativar(tenant.id)

    eventos = [evento[2] for evento in auditoria.eventos]
    assert eventos[0] == "reativar.inicio"
    assert eventos[-1] == "reativar.sucesso"


def test_falha_nao_invariante_tambem_registra_auditoria() -> None:
    """Erro inesperado (ex.: persistência) registra falha e propaga sem traduzir."""

    class _RepoQueFalha(_FakeTenantRepo):
        def save(self, tenant: Tenant) -> None:
            raise RuntimeError("falha no banco")

    tenant = _make_tenant(estado=TenantState.ATIVO)
    uow = _FakeUoW()
    uow.tenant = _RepoQueFalha(tenants={tenant.id: tenant})
    service, auditoria = _fazer_servico(uow)

    with pytest.raises(RuntimeError, match="falha no banco"):
        service.inativar(tenant.id)

    acoes = [evento[2] for evento in auditoria.eventos]
    assert acoes == ["inativar.inicio", "inativar.falha"]
    assert "inativar.sucesso" not in acoes
