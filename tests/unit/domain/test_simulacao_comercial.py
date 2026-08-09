"""Testes unitarios da SimulacaoComercial (IMP-104, FEATURE-013)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.simulacao_comercial import SimulacaoComercial

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CARTEIRA_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEVEDOR_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
USUARIO_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _parametros() -> dict[str, object]:
    return {
        "valor_solicitado": "10000.00",
        "modalidade": "prazo_fixo",
        "prazo_meses": 12,
        "observacao": "cenario comercial inicial",
    }


def _simulacao() -> Any:
    return SimulacaoComercial.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        criada_por_usuario_id=USUARIO_ID,
        parametros=_parametros(),
    )


def test_cria_simulacao_comercial_nao_vinculante() -> None:
    simulacao = _simulacao()

    assert simulacao.id is not None
    assert simulacao.tenant_id == TENANT_ID
    assert simulacao.carteira_id == CARTEIRA_ID
    assert simulacao.devedor_id == DEVEDOR_ID
    assert simulacao.criada_por_usuario_id == USUARIO_ID
    assert simulacao.parametros["modalidade"] == "prazo_fixo"


def test_cria_simulacao_com_timestamp() -> None:
    simulacao = _simulacao()

    assert simulacao.criado_em is not None


def test_rejeita_carteira_id_invalido() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        SimulacaoComercial.criar(
            tenant_id=TENANT_ID,
            carteira_id="nao-uuid",  # type: ignore[arg-type]
            devedor_id=DEVEDOR_ID,
            criada_por_usuario_id=USUARIO_ID,
            parametros=_parametros(),
        )

    assert exc.value.codigo == "EPIC-003"


def test_rejeita_devedor_id_invalido() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        SimulacaoComercial.criar(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=None,  # type: ignore[arg-type]
            criada_por_usuario_id=USUARIO_ID,
            parametros=_parametros(),
        )

    assert exc.value.codigo == "EPIC-003"


def test_rejeita_parametros_vazios() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        SimulacaoComercial.criar(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
            criada_por_usuario_id=USUARIO_ID,
            parametros={},
        )

    assert exc.value.codigo == "EPIC-003"


def test_rejeita_parametros_nao_mapeaveis() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        SimulacaoComercial.criar(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            devedor_id=DEVEDOR_ID,
            criada_por_usuario_id=USUARIO_ID,
            parametros=["valor_solicitado", "10000.00"],  # type: ignore[arg-type]
        )

    assert exc.value.codigo == "EPIC-003"


def test_parametros_sao_copiados_defensivamente_na_criacao() -> None:
    parametros = _parametros()

    simulacao = SimulacaoComercial.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        criada_por_usuario_id=USUARIO_ID,
        parametros=parametros,
    )
    parametros["valor_solicitado"] = "999999.00"

    assert simulacao.parametros["valor_solicitado"] == "10000.00"


def test_parametros_expostos_nao_permitam_mutacao_externa() -> None:
    simulacao = _simulacao()
    parametros_expostos = simulacao.parametros

    parametros_expostos["valor_solicitado"] = "999999.00"

    assert simulacao.parametros["valor_solicitado"] == "10000.00"
