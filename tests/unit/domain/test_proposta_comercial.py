"""Testes unitarios da PropostaComercial (IMP-104, FEATURE-014..017)."""

from __future__ import annotations

import uuid
from collections.abc import MutableMapping
from typing import Any, cast

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.proposta_aprovada import PropostaAprovadaLogica
from emprestimo.domain.credit.proposta_comercial import (
    PropostaComercial,
    PropostaComercialState,
)

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CARTEIRA_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEVEDOR_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
SIMULACAO_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
USUARIO_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
OUTRO_USUARIO_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")


def _parametros() -> dict[str, object]:
    return {
        "valor_solicitado": "10000.00",
        "modalidade": "prazo_fixo",
        "prazo_meses": 12,
        "validade_dias": 7,
    }


def _proposta() -> Any:
    return PropostaComercial.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        criada_por_usuario_id=USUARIO_ID,
        parametros=_parametros(),
        simulacao_id=SIMULACAO_ID,
    )


def test_cria_proposta_comercial_em_rascunho() -> None:
    proposta = _proposta()

    assert proposta.id is not None
    assert proposta.tenant_id == TENANT_ID
    assert proposta.carteira_id == CARTEIRA_ID
    assert proposta.devedor_id == DEVEDOR_ID
    assert proposta.simulacao_id == SIMULACAO_ID
    assert proposta.estado == PropostaComercialState.RASCUNHO


def test_proposta_sem_simulacao_previa_e_permitida() -> None:
    proposta = PropostaComercial.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        criada_por_usuario_id=USUARIO_ID,
        parametros=_parametros(),
    )

    assert proposta.simulacao_id is None
    assert proposta.estado == PropostaComercialState.RASCUNHO


def test_enviar_para_analise_transiciona_rascunho() -> None:
    proposta = _proposta()

    proposta.enviar_para_analise(usuario_id=USUARIO_ID)

    assert proposta.estado == PropostaComercialState.EM_ANALISE


def test_aprovar_proposta_em_analise() -> None:
    proposta = _proposta()
    proposta.enviar_para_analise(usuario_id=USUARIO_ID)

    proposta.aprovar(usuario_id=OUTRO_USUARIO_ID)

    assert proposta.estado == PropostaComercialState.APROVADA
    assert proposta.aprovada_por_usuario_id == OUTRO_USUARIO_ID
    assert proposta.aprovada_em is not None


def test_recusar_proposta_em_analise() -> None:
    proposta = _proposta()
    proposta.enviar_para_analise(usuario_id=USUARIO_ID)

    proposta.recusar(usuario_id=OUTRO_USUARIO_ID, motivo="politica comercial")

    assert proposta.estado == PropostaComercialState.RECUSADA


def test_cancelar_proposta_em_rascunho() -> None:
    proposta = _proposta()

    proposta.cancelar(usuario_id=USUARIO_ID, motivo="cliente desistiu")

    assert proposta.estado == PropostaComercialState.CANCELADA


def test_expirar_proposta_em_analise() -> None:
    proposta = _proposta()
    proposta.enviar_para_analise(usuario_id=USUARIO_ID)

    proposta.expirar(usuario_id=USUARIO_ID)

    assert proposta.estado == PropostaComercialState.EXPIRADA


def test_rejeita_aprovar_proposta_terminal() -> None:
    proposta = _proposta()
    proposta.cancelar(usuario_id=USUARIO_ID, motivo="cliente desistiu")

    with pytest.raises(ViolacaoInvarianteError) as exc:
        proposta.aprovar(usuario_id=USUARIO_ID)

    assert exc.value.codigo == "EPIC-003"


def test_rejeita_reabrir_proposta_terminal() -> None:
    proposta = _proposta()
    proposta.cancelar(usuario_id=USUARIO_ID, motivo="cliente desistiu")

    with pytest.raises(ViolacaoInvarianteError) as exc:
        proposta.enviar_para_analise(usuario_id=USUARIO_ID)

    assert exc.value.codigo == "EPIC-003"


def test_proposta_aprovada_nao_permite_alterar_parametros() -> None:
    proposta = _proposta()
    proposta.enviar_para_analise(usuario_id=USUARIO_ID)
    proposta.aprovar(usuario_id=USUARIO_ID)

    with pytest.raises(ViolacaoInvarianteError) as exc:
        proposta.atualizar_parametros({"valor_solicitado": "5000.00"})

    assert exc.value.codigo == "EPIC-003"


def test_decisao_registra_estado_anterior_posterior_usuario_e_instante() -> None:
    proposta = _proposta()

    proposta.enviar_para_analise(usuario_id=USUARIO_ID)

    assert proposta.decisoes[-1].usuario_id == USUARIO_ID
    assert proposta.decisoes[-1].estado_anterior == PropostaComercialState.RASCUNHO
    assert proposta.decisoes[-1].estado_posterior == PropostaComercialState.EM_ANALISE
    assert proposta.decisoes[-1].criado_em is not None


def test_contrato_logico_exige_proposta_aprovada() -> None:
    proposta = _proposta()

    with pytest.raises(ViolacaoInvarianteError) as exc:
        proposta.gerar_contrato_logico()

    assert exc.value.codigo == "EPIC-003"


def test_contrato_logico_de_proposta_aprovada_preserva_parametros() -> None:
    proposta = _proposta()
    proposta.enviar_para_analise(usuario_id=USUARIO_ID)
    proposta.aprovar(usuario_id=OUTRO_USUARIO_ID)

    contrato_logico = proposta.gerar_contrato_logico()

    assert contrato_logico.proposta_id == proposta.id
    assert contrato_logico.tenant_id == TENANT_ID
    assert contrato_logico.carteira_id == CARTEIRA_ID
    assert contrato_logico.devedor_id == DEVEDOR_ID
    assert contrato_logico.parametros_aprovados["valor_solicitado"] == "10000.00"


def test_contrato_logico_e_saida_formal_de_proposta_aprovada() -> None:
    proposta = _proposta()
    proposta.enviar_para_analise(usuario_id=USUARIO_ID)
    proposta.aprovar(usuario_id=OUTRO_USUARIO_ID)

    contrato_logico = proposta.gerar_contrato_logico()

    assert isinstance(contrato_logico, PropostaAprovadaLogica)
    assert contrato_logico.aprovada_por_usuario_id == OUTRO_USUARIO_ID
    assert contrato_logico.aprovada_em == proposta.aprovada_em


def test_parametros_aprovados_sao_imutaveis() -> None:
    proposta = _proposta()
    proposta.enviar_para_analise(usuario_id=USUARIO_ID)
    proposta.aprovar(usuario_id=OUTRO_USUARIO_ID)
    contrato_logico = proposta.gerar_contrato_logico()

    with pytest.raises(TypeError):
        cast(MutableMapping[str, object], contrato_logico.parametros_aprovados)[
            "valor_solicitado"
        ] = "5000.00"

    assert contrato_logico.parametros_aprovados["valor_solicitado"] == "10000.00"


def test_contrato_logico_nao_vaza_mutacao_posterior_dos_parametros() -> None:
    parametros = _parametros()
    proposta = PropostaComercial.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        criada_por_usuario_id=USUARIO_ID,
        parametros=parametros,
    )
    proposta.enviar_para_analise(usuario_id=USUARIO_ID)
    proposta.aprovar(usuario_id=OUTRO_USUARIO_ID)

    contrato_logico = proposta.gerar_contrato_logico()
    parametros["valor_solicitado"] = "5000.00"

    assert contrato_logico.parametros_aprovados["valor_solicitado"] == "10000.00"


def test_contrato_logico_serializa_dados_de_integracao() -> None:
    proposta = _proposta()
    proposta.enviar_para_analise(usuario_id=USUARIO_ID)
    proposta.aprovar(usuario_id=OUTRO_USUARIO_ID)

    contrato_logico = proposta.gerar_contrato_logico()
    dados = contrato_logico.to_dict()

    assert dados["proposta_id"] == str(proposta.id)
    assert dados["tenant_id"] == str(TENANT_ID)
    assert dados["carteira_id"] == str(CARTEIRA_ID)
    assert dados["devedor_id"] == str(DEVEDOR_ID)
    assert dados["aprovada_por_usuario_id"] == str(OUTRO_USUARIO_ID)
    assert dados["aprovada_em"] == contrato_logico.aprovada_em.isoformat()
    assert cast(dict[str, object], dados["parametros_aprovados"])["valor_solicitado"] == "10000.00"
