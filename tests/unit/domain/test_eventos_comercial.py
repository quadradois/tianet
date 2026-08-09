"""Testes unitarios dos eventos comerciais (IMP-108, EPIC-003)."""

from __future__ import annotations

import uuid

from emprestimo.domain.credit.eventos_comercial import (
    PropostaAprovada,
    PropostaCancelada,
    PropostaEnviadaParaAnalise,
    PropostaExpirada,
    PropostaRecusada,
)
from emprestimo.domain.credit.proposta_comercial import (
    PropostaComercial,
    PropostaComercialState,
)

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CARTEIRA_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEVEDOR_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
USUARIO_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
DECISOR_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _parametros() -> dict[str, object]:
    return {
        "valor_solicitado": "10000.00",
        "modalidade": "prazo_fixo",
        "prazo_meses": 12,
    }


def _proposta() -> PropostaComercial:
    return PropostaComercial.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        criada_por_usuario_id=USUARIO_ID,
        parametros=_parametros(),
    )


def test_enviar_para_analise_gera_evento_com_dados_da_decisao() -> None:
    proposta = _proposta()

    proposta.enviar_para_analise(usuario_id=USUARIO_ID)

    evento = proposta.eventos[-1]
    assert isinstance(evento, PropostaEnviadaParaAnalise)
    assert evento.proposta_id == proposta.id
    assert evento.tenant_id == TENANT_ID
    assert evento.carteira_id == CARTEIRA_ID
    assert evento.devedor_id == DEVEDOR_ID
    assert evento.usuario_id == USUARIO_ID
    assert evento.estado_anterior == PropostaComercialState.RASCUNHO
    assert evento.estado_posterior == PropostaComercialState.EM_ANALISE
    assert evento.ocorrido_em == proposta.decisoes[-1].criado_em


def test_aprovar_gera_evento_de_proposta_aprovada() -> None:
    proposta = _proposta()
    proposta.enviar_para_analise(usuario_id=USUARIO_ID)

    proposta.aprovar(usuario_id=DECISOR_ID)

    assert isinstance(proposta.eventos[-1], PropostaAprovada)
    assert proposta.eventos[-1].estado_posterior == PropostaComercialState.APROVADA


def test_recusar_cancelar_e_expirar_geram_eventos_especificos() -> None:
    recusada = _proposta()
    recusada.enviar_para_analise(usuario_id=USUARIO_ID)
    recusada.recusar(usuario_id=DECISOR_ID, motivo="politica comercial")

    cancelada = _proposta()
    cancelada.cancelar(usuario_id=DECISOR_ID, motivo="cliente desistiu")

    expirada = _proposta()
    expirada.enviar_para_analise(usuario_id=USUARIO_ID)
    expirada.expirar(usuario_id=DECISOR_ID)

    assert isinstance(recusada.eventos[-1], PropostaRecusada)
    assert recusada.eventos[-1].motivo == "politica comercial"
    assert isinstance(cancelada.eventos[-1], PropostaCancelada)
    assert cancelada.eventos[-1].motivo == "cliente desistiu"
    assert isinstance(expirada.eventos[-1], PropostaExpirada)


def test_evento_serializa_para_auditoria() -> None:
    proposta = _proposta()

    proposta.cancelar(usuario_id=DECISOR_ID, motivo="cliente desistiu")
    audit = proposta.eventos[-1].to_audit_dict()

    assert audit["evento"] == "PropostaCancelada"
    assert audit["proposta_id"] == str(proposta.id)
    assert audit["tenant_id"] == str(TENANT_ID)
    assert audit["carteira_id"] == str(CARTEIRA_ID)
    assert audit["devedor_id"] == str(DEVEDOR_ID)
    assert audit["usuario_id"] == str(DECISOR_ID)
    assert audit["estado_anterior"] == "rascunho"
    assert audit["estado_posterior"] == "cancelada"
    assert audit["motivo"] == "cliente desistiu"
    assert isinstance(audit["ocorrido_em"], str)


def test_eventos_expostos_nao_permitem_mutacao_da_trilha_interna() -> None:
    proposta = _proposta()
    proposta.cancelar(usuario_id=DECISOR_ID)
    eventos = proposta.eventos

    eventos += eventos

    assert len(proposta.eventos) == 1
