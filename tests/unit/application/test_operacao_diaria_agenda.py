"""Testes unitarios dos servicos de Agenda Operacional (IMP-178)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from emprestimo.application.errors import (
    AgendaItemNaoEncontradoError,
    EmprestimoNaoEncontradoError,
    IdempotenciaConflitoError,
    TransicaoEstadoInvalidaError,
)
from emprestimo.application.operacao_diaria import (
    ConsultarAgendaOperacional,
    CriarCompromissoAgenda,
    CriarLembreteAgenda,
    ManterCompromissoAgenda,
    ManterLembreteAgenda,
)
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.credit.operacao_diaria import (
    AgendaItem,
    EstadoCompromisso,
    EstadoLembrete,
    Lembrete,
)
from emprestimo.domain.credit.ports import AgendaItemFiltros

TENANT_ID = uuid.UUID("71000000-0000-0000-0000-000000000001")
CARTEIRA_ID = uuid.UUID("71000000-0000-0000-0000-000000000002")
DEVEDOR_ID = uuid.UUID("71000000-0000-0000-0000-000000000003")
EMPRESTIMO_ID = uuid.UUID("71000000-0000-0000-0000-000000000004")
USUARIO_ID = uuid.UUID("71000000-0000-0000-0000-000000000005")


def test_consultar_agenda_filtra_janela_estado_e_nao_commita() -> None:
    futuro = datetime.now(UTC) + timedelta(days=2)
    item_aberto = _agenda_item(previsto_para=futuro)
    item_cancelado = _agenda_item(
        previsto_para=futuro + timedelta(days=1),
        estado=EstadoCompromisso.CANCELADO,
    )
    lembrete = _lembrete(agenda_item_id=item_aberto.id, horario=futuro + timedelta(hours=1))
    uow = _FakeUoW(agenda_items=[item_aberto, item_cancelado], lembretes=[lembrete])

    resultado = ConsultarAgendaOperacional(_uow_factory(uow)).listar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        estado=EstadoCompromisso.ABERTO,
        janela_inicio=futuro - timedelta(hours=1),
        janela_fim=futuro + timedelta(hours=2),
    )

    assert resultado.total == 2
    assert [item.agenda_item_id for item in resultado.compromissos] == [item_aberto.id]
    assert [item.lembrete_id for item in resultado.lembretes] == [lembrete.id]
    assert uow.commits == 0


def test_criar_compromisso_idempotente_nao_duplica() -> None:
    uow = _FakeUoW()
    service = CriarCompromissoAgenda(_uow_factory(uow))
    previsto_para = datetime.now(UTC) + timedelta(days=1)

    primeiro = service.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_id=USUARIO_ID,
        titulo="Retornar cliente",
        previsto_para=previsto_para,
        idempotency_key="agenda-1",
        emprestimo_id=EMPRESTIMO_ID,
    )
    segundo = service.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_id=USUARIO_ID,
        titulo="Retornar cliente",
        previsto_para=previsto_para,
        idempotency_key="agenda-1",
        emprestimo_id=EMPRESTIMO_ID,
    )

    assert segundo == primeiro
    assert len(uow.agenda_item.salvos) == 1
    assert uow.commits == 1


def test_replay_criacao_agenda_retorna_snapshot_original_apos_mutacao() -> None:
    uow = _FakeUoW()
    criar = CriarCompromissoAgenda(_uow_factory(uow))
    manter = ManterCompromissoAgenda(_uow_factory(uow))
    previsto_para = datetime.now(UTC) + timedelta(days=1)
    original = criar.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_id=USUARIO_ID,
        titulo="Retornar cliente",
        previsto_para=previsto_para,
        idempotency_key="agenda-snapshot",
        emprestimo_id=EMPRESTIMO_ID,
    )
    manter.concluir(
        tenant_id=TENANT_ID,
        agenda_item_id=original.agenda_item_id,
        usuario_id=USUARIO_ID,
        idempotency_key="agenda-snapshot-concluir",
    )

    replay = criar.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_id=USUARIO_ID,
        titulo="Retornar cliente",
        previsto_para=previsto_para,
        idempotency_key="agenda-snapshot",
        emprestimo_id=EMPRESTIMO_ID,
    )

    assert replay == original
    assert replay.estado is EstadoCompromisso.ABERTO


def test_criar_compromisso_rejeita_emprestimo_fora_da_cadeia() -> None:
    uow = _FakeUoW(
        emprestimo=_Emprestimo(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=uuid.uuid4(),
        )
    )

    with pytest.raises(EmprestimoNaoEncontradoError):
        CriarCompromissoAgenda(_uow_factory(uow)).criar(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
            usuario_id=USUARIO_ID,
            titulo="Retornar cliente",
            previsto_para=datetime.now(UTC) + timedelta(days=1),
            idempotency_key="agenda-emprestimo-cross",
            emprestimo_id=EMPRESTIMO_ID,
        )


def test_criar_compromisso_rejeita_payload_divergente() -> None:
    uow = _FakeUoW()
    service = CriarCompromissoAgenda(_uow_factory(uow))
    previsto_para = datetime.now(UTC) + timedelta(days=1)
    service.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_id=USUARIO_ID,
        titulo="Retornar cliente",
        previsto_para=previsto_para,
        idempotency_key="agenda-div",
    )

    with pytest.raises(IdempotenciaConflitoError, match="payload divergente"):
        service.criar(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
            usuario_id=USUARIO_ID,
            titulo="Outro retorno",
            previsto_para=previsto_para,
            idempotency_key="agenda-div",
        )


def test_criar_lembrete_e_cancelar_com_replay() -> None:
    item = _agenda_item()
    uow = _FakeUoW(agenda_items=[item])
    lembretes = CriarLembreteAgenda(_uow_factory(uow))
    manter = ManterLembreteAgenda(_uow_factory(uow))
    horario = item.previsto_para - timedelta(hours=1)

    criado = lembretes.criar(
        tenant_id=TENANT_ID,
        agenda_item_id=item.id,
        usuario_id=USUARIO_ID,
        horario=horario,
        mensagem="Confirmar agenda",
        idempotency_key="lembrete-1",
    )
    cancelado = manter.cancelar(
        tenant_id=TENANT_ID,
        lembrete_id=criado.lembrete_id,
        usuario_id=USUARIO_ID,
        idempotency_key="lembrete-cancelar-1",
    )
    replay = manter.cancelar(
        tenant_id=TENANT_ID,
        lembrete_id=criado.lembrete_id,
        usuario_id=USUARIO_ID,
        idempotency_key="lembrete-cancelar-1",
    )

    assert cancelado.estado is EstadoLembrete.CANCELADO
    assert replay == cancelado
    assert len(uow.lembrete.salvos) == 2


def test_reagendar_e_concluir_lembrete() -> None:
    item = _agenda_item()
    lembrete = _lembrete(
        agenda_item_id=item.id,
        horario=item.previsto_para - timedelta(hours=1),
    )
    uow = _FakeUoW(agenda_items=[item], lembretes=[lembrete])
    manter = ManterLembreteAgenda(_uow_factory(uow))

    reagendado = manter.reagendar(
        tenant_id=TENANT_ID,
        lembrete_id=lembrete.id,
        usuario_id=USUARIO_ID,
        novo_horario=item.previsto_para - timedelta(hours=2),
        idempotency_key="lembrete-reagendar-1",
    )
    concluido = manter.concluir(
        tenant_id=TENANT_ID,
        lembrete_id=lembrete.id,
        usuario_id=USUARIO_ID,
        idempotency_key="lembrete-concluir-1",
    )

    assert reagendado.horario == item.previsto_para - timedelta(hours=2)
    assert concluido.estado is EstadoLembrete.CONCLUIDO


def test_lembrete_concluido_rejeita_envio_e_cancelamento() -> None:
    item = _agenda_item()
    lembrete = _lembrete(
        agenda_item_id=item.id,
        horario=item.previsto_para - timedelta(hours=1),
    )
    uow = _FakeUoW(agenda_items=[item], lembretes=[lembrete])
    manter = ManterLembreteAgenda(_uow_factory(uow))

    concluido = manter.concluir(
        tenant_id=TENANT_ID,
        lembrete_id=lembrete.id,
        usuario_id=USUARIO_ID,
        idempotency_key="lembrete-concluir-terminal",
    )

    assert concluido.estado is EstadoLembrete.CONCLUIDO
    with pytest.raises(TransicaoEstadoInvalidaError):
        manter.enviar(
            tenant_id=TENANT_ID,
            lembrete_id=lembrete.id,
            usuario_id=USUARIO_ID,
            idempotency_key="lembrete-enviar-concluido",
        )
    with pytest.raises(TransicaoEstadoInvalidaError):
        manter.cancelar(
            tenant_id=TENANT_ID,
            lembrete_id=lembrete.id,
            usuario_id=USUARIO_ID,
            idempotency_key="lembrete-cancelar-concluido",
        )


def test_lembrete_enviado_rejeita_conclusao() -> None:
    item = _agenda_item()
    lembrete = _lembrete(
        agenda_item_id=item.id,
        horario=item.previsto_para - timedelta(hours=1),
    )
    uow = _FakeUoW(agenda_items=[item], lembretes=[lembrete])
    manter = ManterLembreteAgenda(_uow_factory(uow))

    enviado = manter.enviar(
        tenant_id=TENANT_ID,
        lembrete_id=lembrete.id,
        usuario_id=USUARIO_ID,
        idempotency_key="lembrete-enviar-terminal",
    )

    assert enviado.estado is EstadoLembrete.ENVIADO
    with pytest.raises(TransicaoEstadoInvalidaError):
        manter.concluir(
            tenant_id=TENANT_ID,
            lembrete_id=lembrete.id,
            usuario_id=USUARIO_ID,
            idempotency_key="lembrete-concluir-enviado",
        )


def test_reagendar_concluir_e_rejeitar_cancelamento_de_concluido() -> None:
    item = _agenda_item()
    uow = _FakeUoW(agenda_items=[item])
    manter = ManterCompromissoAgenda(_uow_factory(uow))

    reagendado = manter.reagendar(
        tenant_id=TENANT_ID,
        agenda_item_id=item.id,
        usuario_id=USUARIO_ID,
        novo_horario=datetime.now(UTC) + timedelta(days=3),
        idempotency_key="agenda-reagendar-1",
    )
    concluido = manter.concluir(
        tenant_id=TENANT_ID,
        agenda_item_id=item.id,
        usuario_id=USUARIO_ID,
        idempotency_key="agenda-concluir-1",
    )

    assert reagendado.estado is EstadoCompromisso.REAGENDADO
    assert concluido.estado is EstadoCompromisso.CONCLUIDO
    with pytest.raises(TransicaoEstadoInvalidaError):
        manter.cancelar(
            tenant_id=TENANT_ID,
            agenda_item_id=item.id,
            usuario_id=USUARIO_ID,
            idempotency_key="agenda-cancelar-invalido",
        )


def test_agenda_cross_tenant_responde_404_logico() -> None:
    item = _agenda_item(tenant_id=uuid.uuid4())
    uow = _FakeUoW(agenda_items=[item])

    with pytest.raises(AgendaItemNaoEncontradoError):
        ManterCompromissoAgenda(_uow_factory(uow)).concluir(
            tenant_id=TENANT_ID,
            agenda_item_id=item.id,
            usuario_id=USUARIO_ID,
            idempotency_key="agenda-cross",
        )

    assert uow.agenda_item.salvos == []
    assert uow.rollbacks == 1


def _uow_factory(uow: _FakeUoW) -> Callable[[], UnitOfWork]:
    return lambda: cast(UnitOfWork, uow)


def _agenda_item(
    *,
    tenant_id: uuid.UUID = TENANT_ID,
    previsto_para: datetime | None = None,
    estado: EstadoCompromisso = EstadoCompromisso.ABERTO,
) -> AgendaItem:
    item = AgendaItem(
        tenant_id=tenant_id,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_solicitante_id=USUARIO_ID,
        titulo="Retornar cliente",
        previsto_para=previsto_para or datetime.now(UTC) + timedelta(days=1),
        emprestimo_id=EMPRESTIMO_ID,
    )
    item.estado = estado
    return item


def _lembrete(
    *,
    agenda_item_id: uuid.UUID,
    horario: datetime,
) -> Lembrete:
    return Lembrete(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        agenda_item_id=agenda_item_id,
        horario=horario,
        enviado_por_usuario_id=USUARIO_ID,
        mensagem="Confirmar agenda",
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
class _EmprestimoRepo:
    emprestimo: _Emprestimo | None

    def find_by_id(self, emprestimo_id: uuid.UUID) -> _Emprestimo | None:
        if self.emprestimo is not None and emprestimo_id == EMPRESTIMO_ID:
            return self.emprestimo
        return None


@dataclass
class _AgendaItemRepo:
    existentes: list[AgendaItem]
    salvos: list[AgendaItem] = field(default_factory=list)

    def save(self, agenda_item: AgendaItem) -> None:
        self.salvos.append(agenda_item)
        if agenda_item not in self.existentes:
            self.existentes.append(agenda_item)

    def find_by_id(self, agenda_item_id: uuid.UUID) -> AgendaItem | None:
        return next((item for item in self.existentes if item.id == agenda_item_id), None)

    def listar(self, filtros: AgendaItemFiltros) -> list[AgendaItem]:
        return [
            item
            for item in self.existentes
            if item.tenant_id == filtros.tenant_id
            and (filtros.carteira_id is None or item.carteira_id == filtros.carteira_id)
            and (filtros.devedor_id is None or item.devedor_id == filtros.devedor_id)
            and (filtros.emprestimo_id is None or item.emprestimo_id == filtros.emprestimo_id)
            and (filtros.estado is None or item.estado == filtros.estado)
            and (filtros.janela_inicio is None or item.previsto_para >= filtros.janela_inicio)
            and (filtros.janela_fim is None or item.previsto_para <= filtros.janela_fim)
        ]


@dataclass
class _LembreteRepo:
    existentes: list[Lembrete]
    salvos: list[Lembrete] = field(default_factory=list)

    def save(self, lembrete: Lembrete) -> None:
        self.salvos.append(lembrete)
        if lembrete not in self.existentes:
            self.existentes.append(lembrete)

    def find_by_id(self, lembrete_id: uuid.UUID) -> Lembrete | None:
        return next((lembrete for lembrete in self.existentes if lembrete.id == lembrete_id), None)

    def find_by_agenda_item_id(self, agenda_item_id: uuid.UUID) -> list[Lembrete]:
        return [
            lembrete for lembrete in self.existentes if lembrete.agenda_item_id == agenda_item_id
        ]


@dataclass
class _FakeUoW:
    agenda_items: list[AgendaItem] = field(default_factory=list)
    lembretes: list[Lembrete] = field(default_factory=list)
    emprestimo: _Emprestimo | None = None
    commits: int = 0
    rollbacks: int = 0
    closed: bool = False
    idempotencia: _IdempotenciaFake = field(default_factory=_IdempotenciaFake)
    agenda_item: _AgendaItemRepo = field(init=False)
    lembrete: _LembreteRepo = field(init=False)
    carteira: _RepoId = field(init=False)
    devedor: _RepoId = field(init=False)
    usuario: _RepoId = field(init=False)
    emprestimo_repo: _EmprestimoRepo = field(init=False)

    def __post_init__(self) -> None:
        self.agenda_item = _AgendaItemRepo(self.agenda_items)
        self.lembrete = _LembreteRepo(self.lembretes)
        self.carteira = _RepoId(_EntidadeTenant(id=CARTEIRA_ID, tenant_id=TENANT_ID))
        self.devedor = _RepoId(_Devedor(carteira_id=CARTEIRA_ID))
        self.usuario = _RepoId(_EntidadeTenant(id=USUARIO_ID, tenant_id=TENANT_ID))
        self.emprestimo = self.emprestimo or _Emprestimo(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
        )
        self.emprestimo_repo = _EmprestimoRepo(self.emprestimo)
        object.__setattr__(self, "emprestimo", self.emprestimo_repo)

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


@dataclass(frozen=True)
class _Emprestimo:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
