"""Rotas REST do contexto Comercial (EPIC-003/P5)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from emprestimo.application.autorizacao import Principal
from emprestimo.application.comercial import (
    ConsultaComercialService,
    DecisaoComercialService,
    IntegracaoPropostaAprovadaService,
    PropostaComercialResultado,
    PropostaComercialService,
    SimulacaoComercialResultado,
    SimulacaoComercialService,
)
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.proposta_comercial import PropostaComercial
from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState
from emprestimo.presentation.api.comercial_schemas import (
    DecisaoComercialRequest,
    PropostaAprovadaLogicaResponse,
    PropostaComercialCreateRequest,
    PropostaComercialListagemResponse,
    PropostaComercialResponse,
    PropostaComercialUpdateRequest,
    SimulacaoComercialCreateRequest,
    SimulacaoComercialResponse,
)
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_carteira_do_principal,
    get_consulta_comercial_service,
    get_decisao_comercial_service,
    get_devedor_da_carteira,
    get_integracao_proposta_aprovada_service,
    get_principal_atual,
    get_proposta_comercial_service,
    get_simulacao_comercial_service,
)
from emprestimo.presentation.api.openapi import (
    RESPOSTA_CONFLITO_ESTADO,
    RESPOSTAS_PROTEGIDAS_COM_RECURSO,
    combinar_respostas,
)

PERMISSAO_SIMULACAO_CRIAR = "comercial.simulacao.criar"
PERMISSAO_PROPOSTA_CRIAR = "comercial.proposta.criar"
PERMISSAO_PROPOSTA_LER = "comercial.proposta.ler"
PERMISSAO_PROPOSTA_DECIDIR = "comercial.proposta.decidir"
PERMISSAO_PROPOSTA_INTEGRAR = "comercial.proposta.integrar"

router = APIRouter(
    prefix="/credit",
    tags=["commercial"],
    dependencies=[Depends(get_principal_atual)],
    responses=RESPOSTAS_PROTEGIDAS_COM_RECURSO,
)


@router.post(
    "/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais",
    status_code=201,
    response_model=SimulacaoComercialResponse,
    summary="Criar simulacao comercial nao vinculante",
)
def criar_simulacao_comercial(
    payload: SimulacaoComercialCreateRequest,
    carteira: Carteira = Depends(get_carteira_do_principal),
    devedor: Devedor = Depends(get_devedor_da_carteira),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_SIMULACAO_CRIAR)),
    service: SimulacaoComercialService = Depends(get_simulacao_comercial_service),
) -> SimulacaoComercialResponse:
    resultado = service.criar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        devedor_id=devedor.id,
        usuario_id=principal.usuario_id,
        parametros=payload.parametros,
    )
    return _simulacao_response(resultado)


@router.get(
    "/simulacoes-comerciais/{simulacao_id}",
    response_model=SimulacaoComercialResponse,
    summary="Consultar simulacao comercial por ID",
)
def consultar_simulacao_comercial(
    simulacao_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_LER)),
    service: ConsultaComercialService = Depends(get_consulta_comercial_service),
) -> SimulacaoComercialResponse:
    return _simulacao_response(
        service.consultar_simulacao(
            simulacao_id=simulacao_id,
            tenant_id=principal.tenant_id,
        )
    )


@router.post(
    "/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
    status_code=201,
    response_model=PropostaComercialResponse,
    summary="Criar proposta comercial",
)
def criar_proposta_comercial(
    payload: PropostaComercialCreateRequest,
    carteira: Carteira = Depends(get_carteira_do_principal),
    devedor: Devedor = Depends(get_devedor_da_carteira),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_CRIAR)),
    service: PropostaComercialService = Depends(get_proposta_comercial_service),
) -> PropostaComercialResponse:
    resultado = service.criar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        devedor_id=devedor.id,
        usuario_id=principal.usuario_id,
        parametros=payload.parametros,
        simulacao_id=payload.simulacao_id,
    )
    return _proposta_response(resultado)


@router.get(
    "/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
    response_model=PropostaComercialListagemResponse,
    summary="Listar propostas comerciais do devedor",
)
def listar_propostas_comerciais(
    carteira: Carteira = Depends(get_carteira_do_principal),
    devedor: Devedor = Depends(get_devedor_da_carteira),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_LER)),
    service: ConsultaComercialService = Depends(get_consulta_comercial_service),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    estado: PropostaComercialState | None = Query(default=None),
) -> PropostaComercialListagemResponse:
    resultado = service.listar_propostas(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        devedor_id=devedor.id,
        estado=estado,
        pagina=page,
        tamanho=size,
    )
    return PropostaComercialListagemResponse(
        items=[_proposta_domain_response(proposta) for proposta in resultado.items],
        total=resultado.total,
        page=resultado.pagina,
        size=resultado.tamanho,
        pages=resultado.paginas,
    )


@router.get(
    "/propostas-comerciais/{proposta_id}",
    response_model=PropostaComercialResponse,
    summary="Consultar proposta comercial por ID",
)
def consultar_proposta_comercial(
    proposta_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_LER)),
    service: ConsultaComercialService = Depends(get_consulta_comercial_service),
) -> PropostaComercialResponse:
    return _proposta_response(
        service.consultar_proposta(proposta_id=proposta_id, tenant_id=principal.tenant_id)
    )


@router.patch(
    "/propostas-comerciais/{proposta_id}",
    response_model=PropostaComercialResponse,
    summary="Atualizar parametros de proposta comercial",
)
def atualizar_proposta_comercial(
    proposta_id: uuid.UUID,
    payload: PropostaComercialUpdateRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_CRIAR)),
    service: PropostaComercialService = Depends(get_proposta_comercial_service),
) -> PropostaComercialResponse:
    return _proposta_response(
        service.atualizar_parametros(
            proposta_id=proposta_id,
            tenant_id=principal.tenant_id,
            parametros=payload.parametros,
        )
    )


@router.post(
    "/propostas-comerciais/{proposta_id}/enviar-para-analise",
    response_model=PropostaComercialResponse,
    summary="Enviar proposta comercial para analise",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def enviar_proposta_para_analise(
    proposta_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_DECIDIR)),
    service: DecisaoComercialService = Depends(get_decisao_comercial_service),
) -> PropostaComercialResponse:
    return _proposta_response(
        service.enviar_para_analise(
            proposta_id=proposta_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
        )
    )


@router.post(
    "/propostas-comerciais/{proposta_id}/aprovar",
    response_model=PropostaComercialResponse,
    summary="Aprovar proposta comercial",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def aprovar_proposta_comercial(
    proposta_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_DECIDIR)),
    service: DecisaoComercialService = Depends(get_decisao_comercial_service),
) -> PropostaComercialResponse:
    return _proposta_response(
        service.aprovar(
            proposta_id=proposta_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
        )
    )


@router.post(
    "/propostas-comerciais/{proposta_id}/recusar",
    response_model=PropostaComercialResponse,
    summary="Recusar proposta comercial",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def recusar_proposta_comercial(
    proposta_id: uuid.UUID,
    payload: DecisaoComercialRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_DECIDIR)),
    service: DecisaoComercialService = Depends(get_decisao_comercial_service),
) -> PropostaComercialResponse:
    return _proposta_response(
        service.recusar(
            proposta_id=proposta_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
        )
    )


@router.post(
    "/propostas-comerciais/{proposta_id}/cancelar",
    response_model=PropostaComercialResponse,
    summary="Cancelar proposta comercial",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def cancelar_proposta_comercial(
    proposta_id: uuid.UUID,
    payload: DecisaoComercialRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_DECIDIR)),
    service: DecisaoComercialService = Depends(get_decisao_comercial_service),
) -> PropostaComercialResponse:
    return _proposta_response(
        service.cancelar(
            proposta_id=proposta_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
        )
    )


@router.post(
    "/propostas-comerciais/{proposta_id}/expirar",
    response_model=PropostaComercialResponse,
    summary="Expirar proposta comercial",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def expirar_proposta_comercial(
    proposta_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_DECIDIR)),
    service: DecisaoComercialService = Depends(get_decisao_comercial_service),
) -> PropostaComercialResponse:
    return _proposta_response(
        service.expirar(
            proposta_id=proposta_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
        )
    )


@router.get(
    "/propostas-comerciais/{proposta_id}/contrato-logico",
    response_model=PropostaAprovadaLogicaResponse,
    summary="Gerar contrato logico de proposta aprovada",
)
def gerar_contrato_logico(
    proposta_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROPOSTA_INTEGRAR)),
    service: IntegracaoPropostaAprovadaService = Depends(get_integracao_proposta_aprovada_service),
) -> PropostaAprovadaLogicaResponse:
    contrato = service.gerar_contrato_logico(
        proposta_id=proposta_id,
        tenant_id=principal.tenant_id,
    )
    return PropostaAprovadaLogicaResponse(**contrato.to_dict())


def _simulacao_response(resultado: SimulacaoComercialResultado) -> SimulacaoComercialResponse:
    return SimulacaoComercialResponse(
        id=resultado.simulacao_id,
        tenant_id=resultado.tenant_id,
        carteira_id=resultado.carteira_id,
        devedor_id=resultado.devedor_id,
        criada_por_usuario_id=resultado.criada_por_usuario_id,
        parametros=resultado.parametros,
        criado_em=resultado.criado_em,
    )


def _proposta_response(resultado: PropostaComercialResultado) -> PropostaComercialResponse:
    return PropostaComercialResponse(
        id=resultado.proposta_id,
        tenant_id=resultado.tenant_id,
        carteira_id=resultado.carteira_id,
        devedor_id=resultado.devedor_id,
        criada_por_usuario_id=resultado.criada_por_usuario_id,
        simulacao_id=resultado.simulacao_id,
        estado=resultado.estado,
        parametros=resultado.parametros,
        criado_em=resultado.criado_em,
        atualizado_em=resultado.atualizado_em,
        aprovada_por_usuario_id=resultado.aprovada_por_usuario_id,
        aprovada_em=resultado.aprovada_em,
        total_decisoes=resultado.total_decisoes,
    )


def _proposta_domain_response(proposta: PropostaComercial) -> PropostaComercialResponse:
    return PropostaComercialResponse(
        id=proposta.id,
        tenant_id=proposta.tenant_id,
        carteira_id=proposta.carteira_id,
        devedor_id=proposta.devedor_id,
        criada_por_usuario_id=proposta.criada_por_usuario_id,
        simulacao_id=proposta.simulacao_id,
        estado=proposta.estado,
        parametros=proposta.parametros,
        criado_em=proposta.criado_em,
        atualizado_em=proposta.atualizado_em,
        aprovada_por_usuario_id=proposta.aprovada_por_usuario_id,
        aprovada_em=proposta.aprovada_em,
        total_decisoes=len(proposta.decisoes),
    )
