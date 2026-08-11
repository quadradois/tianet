"""Testes unitarios do ContratoCredito (IMP-125, EPIC-004)."""

from __future__ import annotations

import uuid
from collections.abc import MutableMapping
from datetime import UTC, datetime
from typing import cast

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contrato_credito import (
    ContratoCredito,
    ContratoCreditoState,
    ContratoLiberadoLogico,
)
from emprestimo.domain.credit.proposta_aprovada import PropostaAprovadaLogica

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CARTEIRA_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEVEDOR_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
PROPOSTA_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
USUARIO_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
OUTRO_USUARIO_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")


def _parametros() -> dict[str, object]:
    return {
        "valor_contratado": "10000.00",
        "modalidade": "prazo_fixo",
        "prazo_meses": 12,
        "primeiro_vencimento": "2026-09-10",
    }


def _proposta_aprovada() -> PropostaAprovadaLogica:
    return PropostaAprovadaLogica(
        proposta_id=PROPOSTA_ID,
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        parametros_aprovados=_parametros(),
        aprovada_por_usuario_id=OUTRO_USUARIO_ID,
        aprovada_em=datetime.now(UTC),
    )


def _contrato() -> ContratoCredito:
    return ContratoCredito.criar_de_proposta_aprovada(
        proposta=_proposta_aprovada(),
        criado_por_usuario_id=USUARIO_ID,
    )


def test_cria_contrato_de_proposta_aprovada_em_rascunho() -> None:
    contrato = _contrato()

    assert contrato.id is not None
    assert contrato.tenant_id == TENANT_ID
    assert contrato.carteira_id == CARTEIRA_ID
    assert contrato.devedor_id == DEVEDOR_ID
    assert contrato.proposta_comercial_id == PROPOSTA_ID
    assert contrato.estado == ContratoCreditoState.RASCUNHO
    assert contrato.decisoes[0].tipo == "criado"
    assert contrato.decisoes[0].estado_anterior == ContratoCreditoState.RASCUNHO
    assert contrato.decisoes[0].estado_posterior == ContratoCreditoState.RASCUNHO


def test_snapshot_contratual_nao_vaza_mutacao_externa() -> None:
    parametros = _parametros()
    proposta = PropostaAprovadaLogica(
        proposta_id=PROPOSTA_ID,
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        parametros_aprovados=parametros,
        aprovada_por_usuario_id=OUTRO_USUARIO_ID,
        aprovada_em=datetime.now(UTC),
    )
    contrato = ContratoCredito.criar_de_proposta_aprovada(
        proposta=proposta,
        criado_por_usuario_id=USUARIO_ID,
    )
    parametros["valor_contratado"] = "5000.00"

    assert contrato.parametros["valor_contratado"] == "10000.00"


def test_formalizar_contrato_rascunho() -> None:
    contrato = _contrato()

    contrato.formalizar(usuario_id=USUARIO_ID)

    assert contrato.estado == ContratoCreditoState.FORMALIZADO
    assert contrato.formalizado_por_usuario_id == USUARIO_ID
    assert contrato.formalizado_em is not None


def test_assinar_contrato_formalizado() -> None:
    contrato = _contrato()
    contrato.formalizar(usuario_id=USUARIO_ID)

    contrato.assinar(usuario_id=OUTRO_USUARIO_ID)

    assert contrato.estado == ContratoCreditoState.ASSINADO
    assert contrato.assinado_por_usuario_id == OUTRO_USUARIO_ID
    assert contrato.assinado_em is not None


def test_liberar_contrato_assinado_gera_saida_logica() -> None:
    contrato = _contrato()
    contrato.formalizar(usuario_id=USUARIO_ID)
    contrato.assinar(usuario_id=USUARIO_ID)

    saida = contrato.liberar_para_motor(usuario_id=OUTRO_USUARIO_ID)

    assert contrato.estado == ContratoCreditoState.LIBERADO_PARA_MOTOR
    assert isinstance(saida, ContratoLiberadoLogico)
    assert saida.contrato_id == contrato.id
    assert saida.proposta_comercial_id == PROPOSTA_ID


def test_liberacao_sem_assinatura_e_rejeitada() -> None:
    contrato = _contrato()

    with pytest.raises(ViolacaoInvarianteError) as exc:
        contrato.liberar_para_motor(usuario_id=USUARIO_ID)

    assert exc.value.codigo == "EPIC-004"


def test_cancelar_contrato_nao_liberado() -> None:
    contrato = _contrato()

    contrato.cancelar(usuario_id=USUARIO_ID, motivo="cliente desistiu")

    assert contrato.estado == ContratoCreditoState.CANCELADO
    assert contrato.motivo_encerramento == "cliente desistiu"


def test_encerrar_contrato_liberado_sem_alterar_operacao_financeira() -> None:
    contrato = _contrato()
    contrato.formalizar(usuario_id=USUARIO_ID)
    contrato.assinar(usuario_id=USUARIO_ID)
    contrato.liberar_para_motor(usuario_id=USUARIO_ID)

    contrato.encerrar(usuario_id=OUTRO_USUARIO_ID, motivo="encerramento administrativo")

    assert contrato.estado == ContratoCreditoState.ENCERRADO
    assert contrato.motivo_encerramento == "encerramento administrativo"


def test_contrato_formalizado_nao_permite_alterar_parametros() -> None:
    contrato = _contrato()
    contrato.formalizar(usuario_id=USUARIO_ID)

    with pytest.raises(ViolacaoInvarianteError) as exc:
        contrato.atualizar_parametros({"valor_contratado": "5000.00"})

    assert exc.value.codigo == "EPIC-004"


def test_decisoes_registram_estado_anterior_posterior_usuario_e_instante() -> None:
    contrato = _contrato()

    contrato.formalizar(usuario_id=USUARIO_ID)

    assert contrato.decisoes[-1].usuario_id == USUARIO_ID
    assert contrato.decisoes[-1].estado_anterior == ContratoCreditoState.RASCUNHO
    assert contrato.decisoes[-1].estado_posterior == ContratoCreditoState.FORMALIZADO
    assert contrato.decisoes[-1].criado_em is not None


def test_saida_logica_exige_contrato_liberado() -> None:
    contrato = _contrato()

    with pytest.raises(ViolacaoInvarianteError) as exc:
        contrato.gerar_saida_logica()

    assert exc.value.codigo == "EPIC-004"


def test_saida_logica_e_imutavel() -> None:
    contrato = _contrato()
    contrato.formalizar(usuario_id=USUARIO_ID)
    contrato.assinar(usuario_id=USUARIO_ID)
    saida = contrato.liberar_para_motor(usuario_id=OUTRO_USUARIO_ID)

    with pytest.raises(TypeError):
        cast(MutableMapping[str, object], saida.parametros_contratados)[
            "valor_contratado"
        ] = "5000.00"

    assert saida.parametros_contratados["valor_contratado"] == "10000.00"


def test_saida_logica_serializa_dados_para_motor_futuro() -> None:
    contrato = _contrato()
    contrato.formalizar(usuario_id=USUARIO_ID)
    contrato.assinar(usuario_id=USUARIO_ID)
    saida = contrato.liberar_para_motor(usuario_id=OUTRO_USUARIO_ID)

    dados = saida.to_dict()

    assert dados["contrato_id"] == str(contrato.id)
    assert dados["proposta_comercial_id"] == str(PROPOSTA_ID)
    assert dados["tenant_id"] == str(TENANT_ID)
    assert dados["carteira_id"] == str(CARTEIRA_ID)
    assert dados["devedor_id"] == str(DEVEDOR_ID)
    assert dados["liberado_por_usuario_id"] == str(OUTRO_USUARIO_ID)
    assert (
        cast(dict[str, object], dados["parametros_contratados"])["valor_contratado"] == "10000.00"
    )
