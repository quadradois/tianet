"""Testes unitarios dos servicos de Contratos (IMP-133..IMP-137)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

import pytest

from emprestimo.application.contratos import FormalizacaoContratoService
from emprestimo.application.errors import TransicaoEstadoInvalidaError
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contrato_credito import ContratoCredito
from emprestimo.domain.credit.devedor import DevedorState
from emprestimo.domain.credit.proposta_aprovada import PropostaAprovadaLogica

TENANT_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
CARTEIRA_ID = uuid.UUID("10000000-0000-0000-0000-000000000002")
DEVEDOR_ID = uuid.UUID("10000000-0000-0000-0000-000000000003")
PROPOSTA_ID = uuid.UUID("10000000-0000-0000-0000-000000000004")
USUARIO_ID = uuid.UUID("10000000-0000-0000-0000-000000000005")


def test_formalizacao_cria_contrato_com_trilha_inicial_auditavel() -> None:
    uow = _FakeUoW(proposta=_PropostaAprovada())
    service = FormalizacaoContratoService(_uow_factory(uow))

    resultado = service.criar_de_proposta(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        proposta_comercial_id=PROPOSTA_ID,
        usuario_id=USUARIO_ID,
    )

    contrato = uow.contrato_credito.salvo
    assert contrato is not None
    assert resultado.total_eventos == 1
    assert contrato.decisoes[0].tipo == "criado"
    assert contrato.decisoes[0].usuario_id == USUARIO_ID
    assert uow.commits == 1


def test_formalizacao_rejeita_proposta_nao_aprovada_sem_commit() -> None:
    uow = _FakeUoW(proposta=_PropostaNaoAprovada())
    service = FormalizacaoContratoService(_uow_factory(uow))

    with pytest.raises(TransicaoEstadoInvalidaError):
        service.criar_de_proposta(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            proposta_comercial_id=PROPOSTA_ID,
            usuario_id=USUARIO_ID,
        )

    assert uow.contrato_credito.salvo is None
    assert uow.commits == 0
    assert uow.rollbacks == 1


def _uow_factory(uow: _FakeUoW) -> Callable[[], UnitOfWork]:
    return lambda: cast(UnitOfWork, uow)


@dataclass
class _RepoId:
    value: object

    def find_by_id(self, _id: uuid.UUID) -> object:
        return self.value


@dataclass
class _ContratoRepo:
    salvo: ContratoCredito | None = None

    def find_by_proposta_id(self, _proposta_id: uuid.UUID) -> None:
        return None

    def save(self, contrato: ContratoCredito) -> None:
        self.salvo = contrato


@dataclass
class _FakeUoW:
    proposta: object
    commits: int = 0
    rollbacks: int = 0
    closed: bool = False
    carteira: _RepoId = field(init=False)
    usuario: _RepoId = field(init=False)
    devedor: _RepoId = field(init=False)
    proposta_comercial: _RepoId = field(init=False)
    contrato_credito: _ContratoRepo = field(default_factory=_ContratoRepo)

    def __post_init__(self) -> None:
        self.carteira = _RepoId(_EntidadeTenant(id=CARTEIRA_ID, tenant_id=TENANT_ID))
        self.usuario = _RepoId(_EntidadeTenant(id=USUARIO_ID, tenant_id=TENANT_ID))
        self.devedor = _RepoId(_Devedor(carteira_id=CARTEIRA_ID))
        self.proposta_comercial = _RepoId(self.proposta)

    def __enter__(self) -> _FakeUoW:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            self.rollback()
        self.close()

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


@dataclass(frozen=True)
class _EntidadeTenant:
    id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass(frozen=True)
class _Devedor:
    carteira_id: uuid.UUID
    estado: DevedorState = DevedorState.ATIVO


class _PropostaAprovada:
    tenant_id = TENANT_ID
    carteira_id = CARTEIRA_ID
    devedor_id = DEVEDOR_ID

    def gerar_contrato_logico(self) -> PropostaAprovadaLogica:
        return PropostaAprovadaLogica(
            proposta_id=PROPOSTA_ID,
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
            parametros_aprovados={"valor": 1000},
            aprovada_por_usuario_id=USUARIO_ID,
            aprovada_em=datetime.now(UTC),
        )


class _PropostaNaoAprovada(_PropostaAprovada):
    def gerar_contrato_logico(self) -> PropostaAprovadaLogica:
        raise ViolacaoInvarianteError("EPIC-003", "proposta nao aprovada")
