"""Testes unitários do TenantProvisioningService (IMP-013..IMP-016).

Usam fakes em memória para UoW, idempotência, unicidade e auditoria —
nenhuma persistência real. Cobertura: fluxo completo, transação única
(commit no fim / rollback em falha), replay da Idempotency-Key, conflito
divergente, trilha de auditoria.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import pytest

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import (
    AuditoriaRegistro,
    IdempotenciaRegistro,
    UnitOfWork,
)
from emprestimo.application.provisioning import (
    ESCOPO_IDEMPOTENCIA,
    TenantProvisionado,
    TenantProvisioningService,
)
from emprestimo.domain.common.errors import TenantJaExisteError
from emprestimo.domain.platform.tenant import TenantState


@dataclass
class _FakeIdempotencia(IdempotenciaRegistro):
    registros: dict[str, dict] = field(default_factory=dict)

    def registrar(self, chave: str, escopo: str, solicitacao_hash: str) -> None:
        self.registros[chave] = {
            "escopo": escopo,
            "solicitacao_hash": solicitacao_hash,
            "estado": "running",
            "resultado": None,
        }

    def find_by_chave(self, chave: str) -> dict | None:
        return self.registros.get(chave)

    def concluir(self, chave: str, resultado: str) -> None:
        self.registros[chave]["estado"] = "finished"
        self.registros[chave]["resultado"] = resultado


@dataclass
class _FakeAuditoria(AuditoriaRegistro):
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
class _FakeRepo:
    salvos: list = field(default_factory=list)

    def save(self, entidade: object) -> None:
        self.salvos.append(entidade)


@dataclass
class _FakeUoW(UnitOfWork):
    idempotencia: _FakeIdempotencia
    tenant: _FakeRepo = field(default_factory=_FakeRepo)
    usuario: _FakeRepo = field(default_factory=_FakeRepo)
    configuracao: _FakeRepo = field(default_factory=_FakeRepo)
    carteira: _FakeRepo = field(default_factory=_FakeRepo)
    commit_count: int = 0
    rollback_count: int = 0
    fail_on_commit: bool = False

    def commit(self) -> None:
        if self.fail_on_commit:
            raise RuntimeError("falha no commit")
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        return None


class _UnicidadeFake:
    """Fake do UnicidadeTenantService: conflito se o identificador já existir."""

    def __init__(self) -> None:
        self.existentes: set[str] = set()
        self.chamadas: int = 0

    def verificar(self, identificador: str) -> None:
        self.chamadas += 1
        if identificador in self.existentes:
            raise TenantJaExisteError(identificador)


@dataclass
class _Contexto:
    uow: _FakeUoW
    unicidade: _UnicidadeFake
    auditoria: _FakeAuditoria
    service: TenantProvisioningService


def _contexto() -> _Contexto:
    uow = _FakeUoW(idempotencia=_FakeIdempotencia())
    unicidade = _UnicidadeFake()
    auditoria = _FakeAuditoria()
    service = TenantProvisioningService(
        uow_factory=lambda: uow,
        unicidade=unicidade,
        auditoria=auditoria,
    )
    return _Contexto(uow, unicidade, auditoria, service)


def _provisionar(service: TenantProvisioningService, chave: str = "chave-1") -> TenantProvisionado:
    return service.provisionar(
        identificador_institucional="IDENT-0001",
        nome="Financeira ABC",
        nome_administrador="Maria",
        email_administrador="maria@exemplo.com",
        idempotency_key=chave,
    )


def test_provisionamento_completo() -> None:
    ctx = _contexto()

    resultado = _provisionar(ctx.service)

    assert resultado.estado == TenantState.ATIVO
    assert ctx.unicidade.chamadas == 1
    assert len(ctx.uow.tenant.salvos) == 2  # Tenant em Provisão + confirmação (Ativo)
    assert ctx.uow.tenant.salvos[-1].estado == TenantState.ATIVO
    assert len(ctx.uow.carteira.salvos) == 1
    assert len(ctx.uow.usuario.salvos) == 1
    assert len(ctx.uow.configuracao.salvos) == len(("moeda",))  # CONFIGURACOES_PADRAO
    assert ctx.uow.commit_count == 1
    assert ctx.uow.rollback_count == 0
    chave = ctx.uow.idempotencia.registros["chave-1"]
    assert chave["estado"] == "finished"
    assert chave["escopo"] == ESCOPO_IDEMPOTENCIA


def test_trilha_de_auditoria_registrada_no_sucesso() -> None:
    ctx = _contexto()

    _provisionar(ctx.service)

    acoes = [evento[2] for evento in ctx.auditoria.eventos]
    assert "provisionar.inicio" in acoes
    assert "provisionar.dados_validados" in acoes
    assert "provisionar.carteira_criada" in acoes
    assert "provisionar.usuario_administrador_criado" in acoes
    assert "provisionar.configuracoes_aplicadas" in acoes
    assert "provisionar.confirmado" in acoes
    assert "provisionar.sucesso" in acoes
    assert "provisionar.falha" not in acoes


def test_replay_com_mesma_chave_retorna_mesmo_resultado() -> None:
    ctx = _contexto()

    primeiro = _provisionar(ctx.service, chave="chave-replay")
    segundo = _provisionar(ctx.service, chave="chave-replay")

    assert segundo.tenant_id == primeiro.tenant_id
    assert segundo.identificador_institucional == primeiro.identificador_institucional
    assert ctx.unicidade.chamadas == 1  # não reprovisiona
    assert len(ctx.uow.tenant.salvos) == 2  # nenhuma duplicação
    assert ctx.uow.commit_count == 2
    assert "provisionar.replay" in [e[2] for e in ctx.auditoria.eventos]


def test_replay_com_payload_divergente_gera_conflito() -> None:
    ctx = _contexto()
    _provisionar(ctx.service, chave="chave-divergente")

    with pytest.raises(IdempotenciaConflitoError):
        ctx.service.provisionar(
            identificador_institucional="OUTRO-IDENT",
            nome="Outra Financeira",
            nome_administrador="João",
            email_administrador="joao@exemplo.com",
            idempotency_key="chave-divergente",
        )


def test_unicidade_falha_dispara_rollback_e_auditoria_de_falha() -> None:
    ctx = _contexto()
    ctx.unicidade.existentes.add("IDENT-0001")

    with pytest.raises(TenantJaExisteError):
        _provisionar(ctx.service)

    assert ctx.uow.rollback_count == 1
    assert ctx.uow.commit_count == 0
    assert ctx.uow.tenant.salvos == []
    acoes = [evento[2] for evento in ctx.auditoria.eventos]
    assert "provisionar.falha" in acoes
    assert "provisionar.rollback" in acoes


def test_falha_no_commit_dispara_rollback() -> None:
    ctx = _contexto()
    ctx.uow.fail_on_commit = True

    with pytest.raises(RuntimeError):
        _provisionar(ctx.service)

    assert ctx.uow.rollback_count == 1
