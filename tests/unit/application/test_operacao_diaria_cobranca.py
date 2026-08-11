"""Testes unitarios dos servicos de Cobranca Manual (IMP-177)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import pytest

from emprestimo.application.errors import (
    CobrancaCasoNaoEncontradoError,
    IdempotenciaConflitoError,
)
from emprestimo.application.operacao_diaria import (
    ESCOPO_IDEMPOTENCIA_ACAO_COBRANCA,
    ApropriarPagamentoPromessa,
    ConsultarFilaCobranca,
    RegistrarAcaoCobranca,
    RegistrarPromessa,
)
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.credit.operacao_diaria import (
    AcaoCobranca,
    CobrancaCaso,
    EstadoCobranca,
    TipoAcaoCobranca,
)
from emprestimo.domain.credit.pagamento import Pagamento
from emprestimo.domain.credit.ports import (
    ApropriacaoPagamentoFiltros,
    CobrancaCasoFiltros,
)
from emprestimo.domain.credit.promessa import (
    ApropriacaoPagamento,
    PromessaPagamento,
    PromessaPagamentoState,
)

TENANT_ID = uuid.UUID("70000000-0000-0000-0000-000000000001")
CARTEIRA_ID = uuid.UUID("70000000-0000-0000-0000-000000000002")
DEVEDOR_ID = uuid.UUID("70000000-0000-0000-0000-000000000003")
EMPRESTIMO_ID = uuid.UUID("70000000-0000-0000-0000-000000000004")
USUARIO_ID = uuid.UUID("70000000-0000-0000-0000-000000000005")
PARCELA_ID = uuid.UUID("70000000-0000-0000-0000-000000000006")
PAGAMENTO_ID = uuid.UUID("70000000-0000-0000-0000-000000000007")


def test_consultar_fila_retorna_apenas_casos_abertos() -> None:
    aberto = _caso()
    encerrado = _caso(estado=EstadoCobranca.ENCERRADO)
    uow = _FakeUoW(casos=[aberto, encerrado])

    resultado = ConsultarFilaCobranca(_uow_factory(uow)).listar(tenant_id=TENANT_ID)

    assert resultado.total == 1
    assert resultado.items[0].caso_id == aberto.id
    assert uow.commits == 0


def test_registrar_acao_cobranca_persiste_com_idempotencia_e_replay() -> None:
    uow = _FakeUoW(casos=[_caso()])
    service = RegistrarAcaoCobranca(_uow_factory(uow))

    primeiro = service.registrar(
        tenant_id=TENANT_ID,
        cobranca_caso_id=uow.cobranca_caso.casos[0].id,
        usuario_id=USUARIO_ID,
        tipo=TipoAcaoCobranca.TELEFONE,
        resultado="cliente prometeu retorno",
        idempotency_key="acao-1",
        parcela_id=PARCELA_ID,
    )
    segundo = service.registrar(
        tenant_id=TENANT_ID,
        cobranca_caso_id=uow.cobranca_caso.casos[0].id,
        usuario_id=USUARIO_ID,
        tipo=TipoAcaoCobranca.TELEFONE,
        resultado="cliente prometeu retorno",
        idempotency_key="acao-1",
        parcela_id=PARCELA_ID,
    )

    assert segundo == primeiro
    assert len(uow.acao_cobranca.salvas) == 1
    assert uow.commits == 1
    assert (
        uow.idempotencia.registros[("acao-1", ESCOPO_IDEMPOTENCIA_ACAO_COBRANCA)]["estado"]
        == "finished"
    )


def test_registrar_acao_cobranca_rejeita_payload_divergente() -> None:
    uow = _FakeUoW(casos=[_caso()])
    service = RegistrarAcaoCobranca(_uow_factory(uow))
    service.registrar(
        tenant_id=TENANT_ID,
        cobranca_caso_id=uow.cobranca_caso.casos[0].id,
        usuario_id=USUARIO_ID,
        tipo=TipoAcaoCobranca.EMAIL,
        resultado="email enviado",
        idempotency_key="acao-div",
    )

    with pytest.raises(IdempotenciaConflitoError, match="payload divergente"):
        service.registrar(
            tenant_id=TENANT_ID,
            cobranca_caso_id=uow.cobranca_caso.casos[0].id,
            usuario_id=USUARIO_ID,
            tipo=TipoAcaoCobranca.EMAIL,
            resultado="email com outro resultado",
            idempotency_key="acao-div",
        )


def test_registrar_acao_cross_tenant_responde_404_logico() -> None:
    uow = _FakeUoW(casos=[_caso(tenant_id=uuid.uuid4())])

    with pytest.raises(CobrancaCasoNaoEncontradoError):
        RegistrarAcaoCobranca(_uow_factory(uow)).registrar(
            tenant_id=TENANT_ID,
            cobranca_caso_id=uow.cobranca_caso.casos[0].id,
            usuario_id=USUARIO_ID,
            tipo=TipoAcaoCobranca.TELEFONE,
            resultado="tentativa",
            idempotency_key="acao-cross",
        )

    assert uow.acao_cobranca.salvas == []
    assert uow.rollbacks == 1


def test_registrar_promessa_cria_estado_pagamento_informado() -> None:
    uow = _FakeUoW(casos=[_caso()])

    resultado = RegistrarPromessa(_uow_factory(uow)).registrar(
        tenant_id=TENANT_ID,
        cobranca_caso_id=uow.cobranca_caso.casos[0].id,
        usuario_id=USUARIO_ID,
        valor_declarado=Decimal("100.00"),
        data_promessa=date(2026, 9, 10),
        idempotency_key="promessa-1",
        parcela_id=PARCELA_ID,
        pagamento_informado=True,
    )

    assert resultado.estado is PromessaPagamentoState.PAGAMENTO_INFORMADO
    assert uow.promessa_pagamento.salvas[0].parcela_id == PARCELA_ID
    assert uow.commits == 1


def test_apropriar_pagamento_promessa_usa_pagamento_oficial_e_cumpre_promessa() -> None:
    pagamento = _pagamento(valor=Decimal("120.00"))
    promessa = PromessaPagamento.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        emprestimo_id=EMPRESTIMO_ID,
        criado_por_usuario_id=USUARIO_ID,
        valor_declarado=Decimal("100.00"),
        data_promessa=date(2026, 9, 10),
        parcela_id=PARCELA_ID,
    )
    uow = _FakeUoW(casos=[_caso()], promessas=[promessa], pagamentos=[pagamento])

    resultado = ApropriarPagamentoPromessa(_uow_factory(uow)).apropriar(
        tenant_id=TENANT_ID,
        promessa_id=promessa.id,
        pagamento_id=pagamento.id,
        usuario_id=USUARIO_ID,
        idempotency_key="apropriar-1",
    )

    assert resultado.valor == pagamento.valor_recebido
    assert resultado.parcela_id == PARCELA_ID
    assert resultado.estado_promessa is PromessaPagamentoState.CUMPRIDA
    assert len(uow.apropriacao_pagamento.salvas) == 1
    assert uow.promessa_pagamento.salvas[-1].estado is PromessaPagamentoState.CUMPRIDA


def _uow_factory(uow: _FakeUoW) -> Callable[[], UnitOfWork]:
    return lambda: cast(UnitOfWork, uow)


def _caso(
    *,
    tenant_id: uuid.UUID = TENANT_ID,
    estado: EstadoCobranca = EstadoCobranca.PENDENTE,
) -> CobrancaCaso:
    return CobrancaCaso(
        tenant_id=tenant_id,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        emprestimo_id=EMPRESTIMO_ID,
        titulo="Cobranca manual",
        origem="teste",
        estado=estado,
    )


def _pagamento(*, valor: Decimal) -> Pagamento:
    return Pagamento(
        id=PAGAMENTO_ID,
        emprestimo_id=EMPRESTIMO_ID,
        valor_recebido=valor,
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        valor_juros=Decimal("0.00"),
        valor_amortizacao=valor,
        parcelas_liquidadas=(PARCELA_ID,),
        usuario_id=USUARIO_ID,
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
class _CobrancaCasoRepo:
    casos: list[CobrancaCaso]

    def find_by_id(self, caso_id: uuid.UUID) -> CobrancaCaso | None:
        return next((caso for caso in self.casos if caso.id == caso_id), None)

    def listar(self, filtros: CobrancaCasoFiltros) -> list[CobrancaCaso]:
        return [
            caso
            for caso in self.casos
            if caso.tenant_id == filtros.tenant_id
            and (filtros.carteira_id is None or caso.carteira_id == filtros.carteira_id)
            and (filtros.devedor_id is None or caso.devedor_id == filtros.devedor_id)
            and (filtros.estado is None or caso.estado == filtros.estado)
        ]


@dataclass
class _AcaoCobrancaRepo:
    salvas: list[AcaoCobranca] = field(default_factory=list)

    def save(self, acao: AcaoCobranca) -> None:
        self.salvas.append(acao)

    def find_by_id(self, acao_id: uuid.UUID) -> AcaoCobranca | None:
        return next((acao for acao in self.salvas if acao.id == acao_id), None)


@dataclass
class _PromessaPagamentoRepo:
    existentes: list[PromessaPagamento]
    salvas: list[PromessaPagamento] = field(default_factory=list)

    def save(self, promessa: PromessaPagamento) -> None:
        self.salvas.append(promessa)
        if promessa not in self.existentes:
            self.existentes.append(promessa)

    def find_by_id(self, promessa_id: uuid.UUID) -> PromessaPagamento | None:
        return next((promessa for promessa in self.existentes if promessa.id == promessa_id), None)


@dataclass
class _ApropriacaoPagamentoRepo:
    salvas: list[ApropriacaoPagamento] = field(default_factory=list)

    def save(self, apropriacao: ApropriacaoPagamento) -> None:
        self.salvas.append(apropriacao)

    def find_by_id(self, apropriacao_id: uuid.UUID) -> ApropriacaoPagamento | None:
        return next((item for item in self.salvas if item.id == apropriacao_id), None)

    def listar(self, filtros: ApropriacaoPagamentoFiltros) -> list[ApropriacaoPagamento]:
        return [
            item
            for item in self.salvas
            if (filtros.promessa_id is None or item.promessa_id == filtros.promessa_id)
            and (filtros.pagamento_id is None or item.pagamento_id == filtros.pagamento_id)
        ]


@dataclass
class _PagamentoRepo:
    pagamentos: list[Pagamento]

    def find_by_id(self, pagamento_id: uuid.UUID) -> Pagamento | None:
        return next(
            (pagamento for pagamento in self.pagamentos if pagamento.id == pagamento_id),
            None,
        )


@dataclass
class _FakeUoW:
    casos: list[CobrancaCaso]
    promessas: list[PromessaPagamento] = field(default_factory=list)
    pagamentos: list[Pagamento] = field(default_factory=list)
    commits: int = 0
    rollbacks: int = 0
    closed: bool = False
    idempotencia: _IdempotenciaFake = field(default_factory=_IdempotenciaFake)
    cobranca_caso: _CobrancaCasoRepo = field(init=False)
    acao_cobranca: _AcaoCobrancaRepo = field(default_factory=_AcaoCobrancaRepo)
    promessa_pagamento: _PromessaPagamentoRepo = field(init=False)
    apropriacao_pagamento: _ApropriacaoPagamentoRepo = field(
        default_factory=_ApropriacaoPagamentoRepo
    )
    pagamento: _PagamentoRepo = field(init=False)
    carteira: _RepoId = field(init=False)
    devedor: _RepoId = field(init=False)
    usuario: _RepoId = field(init=False)

    def __post_init__(self) -> None:
        self.cobranca_caso = _CobrancaCasoRepo(self.casos)
        self.promessa_pagamento = _PromessaPagamentoRepo(self.promessas)
        self.pagamento = _PagamentoRepo(self.pagamentos)
        self.carteira = _RepoId(_EntidadeTenant(id=CARTEIRA_ID, tenant_id=TENANT_ID))
        self.devedor = _RepoId(_Devedor(carteira_id=CARTEIRA_ID))
        self.usuario = _RepoId(_EntidadeTenant(id=USUARIO_ID, tenant_id=TENANT_ID))

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
