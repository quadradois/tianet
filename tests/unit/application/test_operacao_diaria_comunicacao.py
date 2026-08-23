"""Testes unitarios dos servicos de Comunicacao Manual (IMP-179)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import Mock

import pytest

from emprestimo.application.errors import (
    AgendaItemNaoEncontradoError,
    EmprestimoNaoEncontradoError,
    IdempotenciaConflitoError,
)
from emprestimo.application.operacao_diaria import (
    ConsultarHistoricoComunicacao,
    RegistrarComunicacaoManual,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.credit.operacao_diaria import (
    AcaoCobranca,
    AgendaItem,
    CanalComunicacao,
    RegistroComunicacao,
    TipoAcaoCobranca,
)
from emprestimo.domain.credit.ports import RegistroComunicacaoFiltros

TENANT_ID = uuid.UUID("72000000-0000-0000-0000-000000000001")
CARTEIRA_ID = uuid.UUID("72000000-0000-0000-0000-000000000002")
DEVEDOR_ID = uuid.UUID("72000000-0000-0000-0000-000000000003")
EMPRESTIMO_ID = uuid.UUID("72000000-0000-0000-0000-000000000004")
USUARIO_ID = uuid.UUID("72000000-0000-0000-0000-000000000005")


def test_registrar_comunicacao_manual_idempotente_e_consultar_historico() -> None:
    uow = _FakeUoW()
    service = RegistrarComunicacaoManual(_uow_factory(uow), _auditoria())
    ocorrido_em = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)

    primeiro = service.registrar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_id=USUARIO_ID,
        canal=CanalComunicacao.TELEFONE,
        ocorrido_em=ocorrido_em,
        resumo="Ligacao realizada",
        resultado="Cliente pediu retorno",
        idempotency_key="com-1",
        emprestimo_id=EMPRESTIMO_ID,
    )
    segundo = service.registrar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_id=USUARIO_ID,
        canal=CanalComunicacao.TELEFONE,
        ocorrido_em=ocorrido_em,
        resumo="Ligacao realizada",
        resultado="Cliente pediu retorno",
        idempotency_key="com-1",
        emprestimo_id=EMPRESTIMO_ID,
    )
    historico = ConsultarHistoricoComunicacao(_uow_factory(uow)).listar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
    )

    assert segundo == primeiro
    assert historico.total == 1
    assert historico.registros[0].registro_id == primeiro.registro_id
    assert len(uow.registro_comunicacao.salvos) == 1
    assert uow.commits == 1


def test_registrar_comunicacao_rejeita_payload_divergente() -> None:
    uow = _FakeUoW()
    service = RegistrarComunicacaoManual(_uow_factory(uow), _auditoria())
    ocorrido_em = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    service.registrar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_id=USUARIO_ID,
        canal=CanalComunicacao.EMAIL,
        ocorrido_em=ocorrido_em,
        resumo="Email enviado",
        resultado="Sem retorno",
        idempotency_key="com-div",
    )

    with pytest.raises(IdempotenciaConflitoError, match="payload divergente"):
        service.registrar(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
            usuario_id=USUARIO_ID,
            canal=CanalComunicacao.EMAIL,
            ocorrido_em=ocorrido_em,
            resumo="Email enviado",
            resultado="Retornou depois",
            idempotency_key="com-div",
        )


def test_registrar_comunicacao_rejeita_emprestimo_fora_da_cadeia() -> None:
    uow = _FakeUoW(emprestimo=_Emprestimo(TENANT_ID, CARTEIRA_ID, uuid.uuid4()))

    with pytest.raises(EmprestimoNaoEncontradoError):
        RegistrarComunicacaoManual(_uow_factory(uow), _auditoria()).registrar(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
            usuario_id=USUARIO_ID,
            canal=CanalComunicacao.CHAT,
            ocorrido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            resumo="Chat",
            resultado="Cadeia invalida",
            idempotency_key="com-emp-cross",
            emprestimo_id=EMPRESTIMO_ID,
        )


def test_registrar_comunicacao_rejeita_agenda_cross_tenant() -> None:
    agenda_item = _agenda_item(tenant_id=uuid.uuid4())
    uow = _FakeUoW(agenda_item=agenda_item)

    with pytest.raises(AgendaItemNaoEncontradoError):
        RegistrarComunicacaoManual(_uow_factory(uow), _auditoria()).registrar(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
            usuario_id=USUARIO_ID,
            canal=CanalComunicacao.CHAT,
            ocorrido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            resumo="Chat",
            resultado="Agenda fora do tenant",
            idempotency_key="com-agenda-cross",
            agenda_item_id=agenda_item.id,
        )


def test_consultar_historico_nao_commita() -> None:
    registro = _registro()
    uow = _FakeUoW(registros=[registro])

    historico = ConsultarHistoricoComunicacao(_uow_factory(uow)).listar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
    )

    assert historico.total == 1
    assert historico.registros[0].resultado == registro.resultado
    assert uow.commits == 0


def _auditoria() -> AuditoriaRegistro:
    return cast(AuditoriaRegistro, Mock())


def _uow_factory(uow: _FakeUoW) -> Callable[[], UnitOfWork]:
    return lambda: cast(UnitOfWork, uow)


def _registro() -> RegistroComunicacao:
    return RegistroComunicacao(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        emprestimo_id=EMPRESTIMO_ID,
        responsavel_id=USUARIO_ID,
        canal=CanalComunicacao.TELEFONE,
        ocorrido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        resumo="Ligacao",
        resultado="Sem retorno",
    )


def _agenda_item(*, tenant_id: uuid.UUID = TENANT_ID) -> AgendaItem:
    return AgendaItem(
        tenant_id=tenant_id,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_solicitante_id=USUARIO_ID,
        titulo="Retornar cliente",
        previsto_para=datetime(2026, 12, 10, 12, 0, tzinfo=UTC),
        emprestimo_id=EMPRESTIMO_ID,
    )


@dataclass
class _IdempotenciaFake:
    registros: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)

    def registrar(self, chave: str, escopo: str, solicitacao_hash: str) -> None:
        self.registros[(chave, escopo)] = {
            "estado": "processing",
            "solicitacao_hash": solicitacao_hash,
            "resultado": None,
        }

    def find_by_chave(self, chave: str, escopo: str) -> dict[str, Any] | None:
        return self.registros.get((chave, escopo))

    def concluir(self, chave: str, escopo: str, resultado: str) -> None:
        self.registros[(chave, escopo)]["estado"] = "finished"
        self.registros[(chave, escopo)]["resultado"] = resultado


@dataclass
class _RepoId:
    value: object

    def find_by_id(self, _id: uuid.UUID) -> object:
        return self.value


@dataclass
class _Emprestimo:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID


@dataclass
class _EmprestimoRepo:
    emprestimo: _Emprestimo | None

    def find_by_id(self, emprestimo_id: uuid.UUID) -> _Emprestimo | None:
        if emprestimo_id == EMPRESTIMO_ID:
            return self.emprestimo
        return None


@dataclass
class _AcaoRepo:
    acao: AcaoCobranca | None = None

    def find_by_id(self, acao_id: uuid.UUID) -> AcaoCobranca | None:
        if self.acao is not None and self.acao.id == acao_id:
            return self.acao
        return None


@dataclass
class _AgendaRepo:
    agenda_item: AgendaItem | None = None

    def find_by_id(self, agenda_item_id: uuid.UUID) -> AgendaItem | None:
        if self.agenda_item is not None and self.agenda_item.id == agenda_item_id:
            return self.agenda_item
        return None


@dataclass
class _RegistroRepo:
    existentes: list[RegistroComunicacao]
    salvos: list[RegistroComunicacao] = field(default_factory=list)

    def save(self, registro: RegistroComunicacao) -> None:
        self.salvos.append(registro)
        if registro not in self.existentes:
            self.existentes.append(registro)

    def find_by_id(self, registro_id: uuid.UUID) -> RegistroComunicacao | None:
        return next((registro for registro in self.existentes if registro.id == registro_id), None)

    def listar(self, filtros: RegistroComunicacaoFiltros) -> list[RegistroComunicacao]:
        return [
            registro
            for registro in self.existentes
            if registro.tenant_id == filtros.tenant_id
            and (filtros.carteira_id is None or registro.carteira_id == filtros.carteira_id)
            and (filtros.devedor_id is None or registro.devedor_id == filtros.devedor_id)
            and (filtros.emprestimo_id is None or registro.emprestimo_id == filtros.emprestimo_id)
            and (
                filtros.cobranca_acao_id is None
                or registro.cobranca_acao_id == filtros.cobranca_acao_id
            )
            and (
                filtros.agenda_item_id is None or registro.agenda_item_id == filtros.agenda_item_id
            )
        ]


@dataclass
class _FakeUoW:
    registros: list[RegistroComunicacao] = field(default_factory=list)
    emprestimo: _Emprestimo | None = None
    agenda_item: AgendaItem | None = None
    commits: int = 0
    rollbacks: int = 0
    closed: bool = False
    idempotencia: _IdempotenciaFake = field(default_factory=_IdempotenciaFake)
    carteira: _RepoId = field(init=False)
    devedor: _RepoId = field(init=False)
    usuario: _RepoId = field(init=False)
    emprestimo_repo: _EmprestimoRepo = field(init=False)
    acao_cobranca: _AcaoRepo = field(init=False)
    agenda_repo: _AgendaRepo = field(init=False)
    registro_comunicacao: _RegistroRepo = field(init=False)

    def __post_init__(self) -> None:
        self.carteira = _RepoId(_EntidadeTenant(TENANT_ID))
        self.devedor = _RepoId(_Devedor(CARTEIRA_ID))
        self.usuario = _RepoId(_EntidadeTenant(TENANT_ID))
        self.emprestimo = self.emprestimo or _Emprestimo(TENANT_ID, CARTEIRA_ID, DEVEDOR_ID)
        self.emprestimo_repo = _EmprestimoRepo(self.emprestimo)
        self.acao_cobranca = _AcaoRepo(
            AcaoCobranca(
                tenant_id=TENANT_ID,
                carteira_id=CARTEIRA_ID,
                devedor_id=DEVEDOR_ID,
                cobranca_caso_id=uuid.uuid4(),
                emprestimo_id=EMPRESTIMO_ID,
                criado_por_usuario_id=USUARIO_ID,
                tipo=TipoAcaoCobranca.TELEFONE,
                resultado="Contato",
            )
        )
        self.agenda_repo = _AgendaRepo(self.agenda_item)
        self.registro_comunicacao = _RegistroRepo(self.registros)
        object.__setattr__(self, "emprestimo", self.emprestimo_repo)
        object.__setattr__(self, "agenda_item", self.agenda_repo)

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
    tenant_id: uuid.UUID


@dataclass(frozen=True)
class _Devedor:
    carteira_id: uuid.UUID
