"""Testes dos services de Configuracoes Financeiras (EPIC-009/P3)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest

from emprestimo.application.configuracoes_financeiras import (
    CalendarioFinanceiroService,
    CapturaSnapshotConfiguracaoService,
    ConfiguracaoFinanceiraService,
    ConsultaConfiguracaoVigenteService,
    IntegracaoConfiguracaoContratoService,
    ParametroFinanceiroInput,
    TaxaFinanceiraInput,
)
from emprestimo.application.errors import TransicaoEstadoInvalidaError
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.credit.configuracoes_financeiras import (
    CalendarioFinanceiro,
    ConfiguracaoFinanceira,
    PoliticaArredondamento,
    SnapshotConfiguracaoContratualV1,
)
from emprestimo.domain.credit.ports import ConfiguracaoFinanceiraFiltros

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CARTEIRA_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
USUARIO_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _uow_factory(uow: _FakeUoW) -> Callable[[], UnitOfWork]:
    return lambda: cast(UnitOfWork, uow)


def test_services_configuracoes_financeiras_executam_fluxo_operacional() -> None:
    uow = _FakeUoW()
    calendario = CalendarioFinanceiroService(_uow_factory(uow)).criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        usuario_id=USUARIO_ID,
        codigo="br_padrao",
        nome="Brasil padrao",
        feriados=(date(2026, 9, 7),),
    )

    service = ConfiguracaoFinanceiraService(_uow_factory(uow))
    configuracao = service.criar_rascunho(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        usuario_id=USUARIO_ID,
        calendario_id=calendario.id,
        modalidade="prazo-fixo",
        vigencia_inicio=date(2026, 9, 1),
        taxas=(
            TaxaFinanceiraInput(
                nome="taxa_juros_mensal",
                valor=Decimal("0.0200"),
                periodicidade="mensal",
            ),
        ),
        parametros=(
            ParametroFinanceiroInput("valor_minimo", Decimal("100.00")),
            ParametroFinanceiroInput("moeda", "BRL"),
        ),
        politica_arredondamento=PoliticaArredondamento("half_up", 2),
    )

    service.aprovar(
        configuracao_id=configuracao.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
    )
    service.ativar(
        configuracao_id=configuracao.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
    )

    vigente = ConsultaConfiguracaoVigenteService(_uow_factory(uow)).consultar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        modalidade="prazo_fixo",
        data_referencia=date(2026, 9, 10),
    )
    snapshot = CapturaSnapshotConfiguracaoService(_uow_factory(uow)).capturar(
        configuracao_id=configuracao.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        motivo="contrato formalizado",
    )
    parametros = IntegracaoConfiguracaoContratoService().montar_parametros_contratuais(
        snapshot=snapshot,
        parametros_operacionais={"valor_contratado": "1000.00"},
    )

    assert vigente.configuracao_id == configuracao.id
    assert snapshot.hash_parametros
    assert parametros["configuracao_financeira_id"] == str(configuracao.id)
    assert "snapshot_configuracao_contratual" in parametros
    assert uow.commit_count == 5


def test_service_traduz_transicao_invalida_para_conflito() -> None:
    uow = _FakeUoW()
    calendario = CalendarioFinanceiro(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        codigo="br_padrao",
        nome="Brasil padrao",
    )
    uow.calendario_financeiro.save(calendario)
    configuracao = ConfiguracaoFinanceiraService(_uow_factory(uow)).criar_rascunho(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        usuario_id=USUARIO_ID,
        calendario_id=calendario.id,
        modalidade="prazo-fixo",
        vigencia_inicio=date(2026, 9, 1),
        taxas=(
            TaxaFinanceiraInput(
                nome="taxa_juros_mensal",
                valor=Decimal("0.0200"),
                periodicidade="mensal",
            ),
        ),
        parametros=(ParametroFinanceiroInput("moeda", "BRL"),),
        politica_arredondamento=PoliticaArredondamento("half_up", 2),
    )

    with pytest.raises(TransicaoEstadoInvalidaError):
        ConfiguracaoFinanceiraService(_uow_factory(uow)).ativar(
            configuracao_id=configuracao.id,
            tenant_id=TENANT_ID,
            usuario_id=USUARIO_ID,
        )


@dataclass
class _FakeUoW:
    modalidade_financeira: _ModalidadeRepo = field(default_factory=lambda: _ModalidadeRepo())
    calendario_financeiro: _CalendarioRepo = field(default_factory=lambda: _CalendarioRepo())
    configuracao_financeira: _ConfiguracaoRepo = field(default_factory=lambda: _ConfiguracaoRepo())
    usuario: _UsuarioRepo = field(default_factory=lambda: _UsuarioRepo())
    carteira: _CarteiraRepo = field(default_factory=lambda: _CarteiraRepo())
    commit_count: int = 0

    def __enter__(self) -> _FakeUoW:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            self.rollback()
        self.close()

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


class _ModalidadeRepo:
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, Any] = {}

    def save(self, modalidade: Any) -> None:
        self.items[modalidade.id] = modalidade

    def find_by_id(self, modalidade_id: uuid.UUID) -> Any | None:
        return self.items.get(modalidade_id)

    def listar(self, tenant_id: uuid.UUID) -> list[Any]:
        return [item for item in self.items.values() if item.tenant_id == tenant_id]


class _CalendarioRepo:
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, CalendarioFinanceiro] = {}

    def save(self, calendario: CalendarioFinanceiro) -> None:
        self.items[calendario.id] = calendario

    def find_by_id(self, calendario_id: uuid.UUID) -> CalendarioFinanceiro | None:
        return self.items.get(calendario_id)

    def listar(self, tenant_id: uuid.UUID) -> list[CalendarioFinanceiro]:
        return [item for item in self.items.values() if item.tenant_id == tenant_id]


class _ConfiguracaoRepo:
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, ConfiguracaoFinanceira] = {}
        self.snapshots: list[SnapshotConfiguracaoContratualV1] = []

    def save(self, configuracao: ConfiguracaoFinanceira) -> None:
        self.items[configuracao.id] = configuracao

    def save_snapshot(self, snapshot: SnapshotConfiguracaoContratualV1) -> None:
        self.snapshots.append(snapshot)

    def find_by_id(self, configuracao_id: uuid.UUID) -> ConfiguracaoFinanceira | None:
        return self.items.get(configuracao_id)

    def listar(self, filtros: ConfiguracaoFinanceiraFiltros) -> list[ConfiguracaoFinanceira]:
        encontrados = [
            item
            for item in self.items.values()
            if item.tenant_id == filtros.tenant_id
            and item.carteira_id == filtros.carteira_id
            and (filtros.modalidade is None or item.modalidade.valor == filtros.modalidade)
            and (filtros.estado is None or item.estado is filtros.estado)
        ]
        if filtros.data_referencia is not None:
            encontrados = [
                item for item in encontrados if item.vigencia.contem(filtros.data_referencia)
            ]
        return encontrados


class _UsuarioRepo:
    def find_by_id(self, usuario_id: uuid.UUID) -> Any:
        return SimpleNamespace(id=usuario_id, tenant_id=TENANT_ID)


class _CarteiraRepo:
    def find_by_id(self, carteira_id: uuid.UUID) -> Any:
        return SimpleNamespace(id=carteira_id, tenant_id=TENANT_ID)
