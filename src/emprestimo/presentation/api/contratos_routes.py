"""Rotas REST do contexto Contratos (EPIC-004/P5)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from emprestimo.application.autorizacao import Principal
from emprestimo.application.contratos import (
    AssinaturaContratoService,
    CancelamentoEncerramentoContratoService,
    ConsultaContratoService,
    ContratoCreditoResultado,
    FormalizacaoContratoService,
    LiberacaoContratoService,
)
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.contrato_credito import ContratoCredito
from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.presentation.api.contratos_schemas import (
    ContratoCreditoCreateRequest,
    ContratoCreditoListagemResponse,
    ContratoCreditoResponse,
    ContratoLiberadoLogicoResponse,
    DecisaoContratoRequest,
    EventoContratoResponse,
)
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_assinatura_contrato_service,
    get_cancelamento_encerramento_contrato_service,
    get_carteira_do_principal,
    get_consulta_contrato_service,
    get_formalizacao_contrato_service,
    get_liberacao_contrato_service,
    get_principal_atual,
)
from emprestimo.presentation.api.openapi import (
    RESPOSTA_CONFLITO_ESTADO,
    RESPOSTAS_PROTEGIDAS_COM_RECURSO,
    combinar_respostas,
)

PERMISSAO_CONTRATO_CRIAR = "contratos.contrato.criar"
PERMISSAO_CONTRATO_LER = "contratos.contrato.ler"
PERMISSAO_CONTRATO_ASSINAR = "contratos.contrato.assinar"
PERMISSAO_CONTRATO_LIBERAR = "contratos.contrato.liberar"
PERMISSAO_CONTRATO_ENCERRAR = "contratos.contrato.encerrar"

router = APIRouter(
    prefix="/credit",
    tags=["contracts"],
    dependencies=[Depends(get_principal_atual)],
    responses=RESPOSTAS_PROTEGIDAS_COM_RECURSO,
)


@router.post(
    "/carteiras/{carteira_id}/contratos",
    status_code=201,
    response_model=ContratoCreditoResponse,
    summary="Criar contrato de credito",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def criar_contrato(
    payload: ContratoCreditoCreateRequest,
    carteira: Carteira = Depends(get_carteira_do_principal),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONTRATO_CRIAR)),
    service: FormalizacaoContratoService = Depends(get_formalizacao_contrato_service),
) -> ContratoCreditoResponse:
    resultado = service.criar_de_proposta(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        proposta_comercial_id=payload.proposta_comercial_id,
        usuario_id=principal.usuario_id,
    )
    return _contrato_response(resultado)


@router.get(
    "/carteiras/{carteira_id}/contratos",
    response_model=ContratoCreditoListagemResponse,
    summary="Listar contratos da carteira",
)
def listar_contratos(
    carteira: Carteira = Depends(get_carteira_do_principal),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONTRATO_LER)),
    service: ConsultaContratoService = Depends(get_consulta_contrato_service),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    devedor_id: uuid.UUID | None = Query(default=None),
    estado: ContratoCreditoState | None = Query(default=None),
) -> ContratoCreditoListagemResponse:
    resultado = service.listar_contratos(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        devedor_id=devedor_id,
        estado=estado,
        pagina=page,
        tamanho=size,
    )
    return ContratoCreditoListagemResponse(
        items=[_contrato_domain_response(contrato) for contrato in resultado.items],
        total=resultado.total,
        page=resultado.pagina,
        size=resultado.tamanho,
        pages=resultado.paginas,
    )


@router.get(
    "/contratos/{contrato_id}",
    response_model=ContratoCreditoResponse,
    summary="Consultar contrato de credito por ID",
)
def consultar_contrato(
    contrato_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONTRATO_LER)),
    service: ConsultaContratoService = Depends(get_consulta_contrato_service),
) -> ContratoCreditoResponse:
    return _contrato_response(
        service.consultar_contrato(contrato_id=contrato_id, tenant_id=principal.tenant_id)
    )


@router.get(
    "/contratos/{contrato_id}/historico",
    response_model=list[EventoContratoResponse],
    summary="Consultar historico contratual",
)
def consultar_historico_contrato(
    contrato_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONTRATO_LER)),
    service: ConsultaContratoService = Depends(get_consulta_contrato_service),
) -> list[EventoContratoResponse]:
    eventos = service.consultar_historico(contrato_id=contrato_id, tenant_id=principal.tenant_id)
    return [
        EventoContratoResponse(
            id=evento.id,
            contrato_id=evento.contrato_id,
            usuario_id=evento.usuario_id,
            tipo=evento.tipo,
            estado_anterior=evento.estado_anterior,
            estado_posterior=evento.estado_posterior,
            motivo=evento.motivo,
            criado_em=evento.criado_em,
        )
        for evento in eventos
    ]


@router.post(
    "/contratos/{contrato_id}/assinar",
    response_model=ContratoCreditoResponse,
    summary="Registrar assinatura contratual",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def assinar_contrato(
    contrato_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONTRATO_ASSINAR)),
    service: AssinaturaContratoService = Depends(get_assinatura_contrato_service),
) -> ContratoCreditoResponse:
    return _contrato_response(
        service.assinar(
            contrato_id=contrato_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
        )
    )


@router.post(
    "/contratos/{contrato_id}/liberar-para-motor",
    response_model=ContratoLiberadoLogicoResponse,
    summary="Liberar contrato para Motor Financeiro futuro",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def liberar_contrato_para_motor(
    contrato_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONTRATO_LIBERAR)),
    service: LiberacaoContratoService = Depends(get_liberacao_contrato_service),
) -> ContratoLiberadoLogicoResponse:
    saida = service.liberar_para_motor(
        contrato_id=contrato_id,
        tenant_id=principal.tenant_id,
        usuario_id=principal.usuario_id,
    )
    return ContratoLiberadoLogicoResponse(**saida.to_dict())


@router.post(
    "/contratos/{contrato_id}/cancelar",
    response_model=ContratoCreditoResponse,
    summary="Cancelar contrato nao liberado",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def cancelar_contrato(
    contrato_id: uuid.UUID,
    payload: DecisaoContratoRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONTRATO_ENCERRAR)),
    service: CancelamentoEncerramentoContratoService = Depends(
        get_cancelamento_encerramento_contrato_service
    ),
) -> ContratoCreditoResponse:
    return _contrato_response(
        service.cancelar(
            contrato_id=contrato_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
        )
    )


@router.post(
    "/contratos/{contrato_id}/encerrar",
    response_model=ContratoCreditoResponse,
    summary="Encerrar contrato sem alterar operacao financeira",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def encerrar_contrato(
    contrato_id: uuid.UUID,
    payload: DecisaoContratoRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONTRATO_ENCERRAR)),
    service: CancelamentoEncerramentoContratoService = Depends(
        get_cancelamento_encerramento_contrato_service
    ),
) -> ContratoCreditoResponse:
    return _contrato_response(
        service.encerrar(
            contrato_id=contrato_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
        )
    )


def _contrato_response(resultado: ContratoCreditoResultado) -> ContratoCreditoResponse:
    return ContratoCreditoResponse(
        id=resultado.contrato_id,
        tenant_id=resultado.tenant_id,
        carteira_id=resultado.carteira_id,
        devedor_id=resultado.devedor_id,
        proposta_comercial_id=resultado.proposta_comercial_id,
        criado_por_usuario_id=resultado.criado_por_usuario_id,
        estado=resultado.estado,
        parametros=resultado.parametros,
        criado_em=resultado.criado_em,
        atualizado_em=resultado.atualizado_em,
        formalizado_por_usuario_id=resultado.formalizado_por_usuario_id,
        formalizado_em=resultado.formalizado_em,
        assinado_por_usuario_id=resultado.assinado_por_usuario_id,
        assinado_em=resultado.assinado_em,
        liberado_por_usuario_id=resultado.liberado_por_usuario_id,
        liberado_em=resultado.liberado_em,
        motivo_encerramento=resultado.motivo_encerramento,
        total_eventos=resultado.total_eventos,
    )


def _contrato_domain_response(contrato: ContratoCredito) -> ContratoCreditoResponse:
    return ContratoCreditoResponse(
        id=contrato.id,
        tenant_id=contrato.tenant_id,
        carteira_id=contrato.carteira_id,
        devedor_id=contrato.devedor_id,
        proposta_comercial_id=contrato.proposta_comercial_id,
        criado_por_usuario_id=contrato.criado_por_usuario_id,
        estado=contrato.estado,
        parametros=contrato.parametros,
        criado_em=contrato.criado_em,
        atualizado_em=contrato.atualizado_em,
        formalizado_por_usuario_id=contrato.formalizado_por_usuario_id,
        formalizado_em=contrato.formalizado_em,
        assinado_por_usuario_id=contrato.assinado_por_usuario_id,
        assinado_em=contrato.assinado_em,
        liberado_por_usuario_id=contrato.liberado_por_usuario_id,
        liberado_em=contrato.liberado_em,
        motivo_encerramento=contrato.motivo_encerramento,
        total_eventos=len(contrato.decisoes),
    )
