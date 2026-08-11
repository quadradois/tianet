"""Testes unitarios do dominio Configuracoes Financeiras (EPIC-009/P1)."""

from __future__ import annotations

import uuid
from collections.abc import MutableMapping
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.configuracoes_financeiras import (
    CalendarioFinanceiro,
    CodigoModalidadeFinanceira,
    ConfiguracaoFinanceira,
    ConfiguracaoFinanceiraState,
    JanelaVigencia,
    ModalidadeFinanceira,
    ParametroFinanceiroConfigurado,
    PoliticaArredondamento,
    SnapshotConfiguracaoContratualV1,
    TaxaFinanceiraConfigurada,
)

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CARTEIRA_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
USUARIO_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
CALENDARIO_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _configuracao() -> ConfiguracaoFinanceira:
    return ConfiguracaoFinanceira.criar_rascunho(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        modalidade=CodigoModalidadeFinanceira("prazo-fixo"),
        calendario_id=CALENDARIO_ID,
        vigencia=JanelaVigencia(date(2026, 9, 1)),
        taxas=(
            TaxaFinanceiraConfigurada(
                nome="taxa_juros_mensal",
                valor=Decimal("0.0200"),
                periodicidade="mensal",
            ),
        ),
        parametros=(
            ParametroFinanceiroConfigurado("valor_minimo", Decimal("100.00")),
            ParametroFinanceiroConfigurado("moeda", "BRL"),
        ),
        politica_arredondamento=PoliticaArredondamento("half_up", 2),
        criada_por_usuario_id=USUARIO_ID,
        correlation_id="cid-123",
    )


def test_modalidade_canoniza_codigo_e_valida_escopo() -> None:
    modalidade = ModalidadeFinanceira(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        codigo=CodigoModalidadeFinanceira("Prazo-Fixo"),
        nome="Prazo fixo",
    )

    assert modalidade.codigo.valor == "prazo_fixo"
    assert modalidade.ativa is True


def test_value_objects_rejeitam_float_e_vigencia_invalida() -> None:
    with pytest.raises(ViolacaoInvarianteError):
        ParametroFinanceiroConfigurado("taxa", 0.1)

    with pytest.raises(ViolacaoInvarianteError):
        JanelaVigencia(date(2026, 9, 1), date(2026, 9, 1))


def test_calendario_resolve_periodo_operacional_sem_calculo_definitivo() -> None:
    calendario = CalendarioFinanceiro(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        codigo="br_padrao",
        nome="Brasil padrao",
        feriados=(date(2026, 9, 7),),
    )

    periodo = calendario.resolver_periodo(date(2026, 9, 7))

    assert periodo["data_referencia"] == "2026-09-07"
    assert periodo["eh_feriado"] is True


def test_configuracao_transiciona_aprovar_programar_ativar_substituir() -> None:
    configuracao = _configuracao()

    configuracao.aprovar(usuario_id=USUARIO_ID, motivo="dupla aprovacao")
    configuracao.programar(usuario_id=USUARIO_ID, data_ativacao=date(2026, 9, 1))
    configuracao.ativar(usuario_id=USUARIO_ID)
    configuracao.substituir(usuario_id=USUARIO_ID, motivo="nova versao")

    assert configuracao.estado is ConfiguracaoFinanceiraState.SUBSTITUIDA
    assert [evento.tipo for evento in configuracao.eventos] == [
        "configuracao_financeira.criada",
        "configuracao_financeira.aprovada",
        "configuracao_financeira.programada",
        "configuracao_financeira.ativada",
        "configuracao_financeira.substituida",
    ]


def test_transicao_invalida_retorna_violacao_de_invariante() -> None:
    configuracao = _configuracao()

    with pytest.raises(ViolacaoInvarianteError) as exc_info:
        configuracao.ativar(usuario_id=USUARIO_ID)

    assert exc_info.value.codigo == "EPIC-009"


def test_configuracao_ativa_gera_contrato_vigente_e_snapshot_imutavel() -> None:
    configuracao = _configuracao()
    configuracao.aprovar(usuario_id=USUARIO_ID)
    configuracao.ativar(usuario_id=USUARIO_ID)

    vigente = configuracao.gerar_vigente(consultada_em=datetime(2026, 9, 1, 12, 0, tzinfo=UTC))
    snapshot = configuracao.capturar_snapshot(
        usuario_id=USUARIO_ID,
        motivo="contrato formalizado",
        capturado_em=datetime(2026, 9, 1, 12, 5, tzinfo=UTC),
    )

    assert vigente.modalidade == "prazo_fixo"
    assert isinstance(snapshot, SnapshotConfiguracaoContratualV1)
    assert snapshot.hash_parametros
    assert snapshot.to_dict()["capturado_por_usuario_id"] == str(USUARIO_ID)
    with pytest.raises(TypeError):
        cast(MutableMapping[str, object], snapshot.parametros)["moeda"] = "USD"


def test_snapshot_rejeita_hash_incompativel() -> None:
    configuracao = _configuracao()
    configuracao.aprovar(usuario_id=USUARIO_ID)
    configuracao.ativar(usuario_id=USUARIO_ID)

    with pytest.raises(ViolacaoInvarianteError):
        SnapshotConfiguracaoContratualV1(
            configuracao_id=configuracao.id,
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            modalidade="prazo_fixo",
            versao=1,
            parametros=configuracao.parametros_normalizados,
            hash_parametros="hash-invalido",
            capturado_em=datetime.now(UTC),
            capturado_por_usuario_id=USUARIO_ID,
        )
