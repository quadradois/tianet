"""Rotas REST da Operacao Diaria (EPIC-007/P4)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from emprestimo.application.autorizacao import Principal
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.operacao_diaria import EstadoCobranca, EstadoCompromisso
from emprestimo.presentation.api.automacao_schemas import (
    ConciliacaoLegadaRequest,
    NotificacaoResponse,
)
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_apropriar_pagamento_promessa_service,
    get_carteira_do_principal,
    get_consultar_agenda_operacional_service,
    get_consultar_fila_cobranca_service,
    get_consultar_historico_comunicacao_service,
    get_criar_compromisso_agenda_service,
    get_criar_lembrete_agenda_service,
    get_manter_compromisso_agenda_service,
    get_manter_lembrete_agenda_service,
    get_notification_service,
    get_principal_atual,
    get_registrar_acao_cobranca_service,
    get_registrar_comunicacao_manual_service,
    get_registrar_promessa_service,
    get_relatorios_operacionais_service,
)
from emprestimo.presentation.api.observability import get_correlation_id
from emprestimo.presentation.api.openapi import (
    RESPOSTA_CONFLITO_ESTADO,
    RESPOSTA_PAYLOAD_INVALIDO,
    RESPOSTAS_PROTEGIDAS_COM_RECURSO,
    combinar_respostas,
)
from emprestimo.presentation.api.operacao_diaria_schemas import (
    AcaoCobrancaCreateRequest,
    AcaoCobrancaResponse,
    AgendaItemResponse,
    AgendaOperacionalResponse,
    ApropriacaoPagamentoCreateRequest,
    ApropriacaoPagamentoResponse,
    CobrancaCasoResponse,
    CompromissoAgendaCreateRequest,
    ComunicacaoManualCreateRequest,
    FilaCobrancaResponse,
    FluxoDiaResponse,
    FluxoPrevistoRealizadoResponse,
    HistoricoComunicacaoResponse,
    LembreteAgendaCreateRequest,
    LembreteResponse,
    PagamentoOperacionalResponse,
    PagamentosEncerramentosResponse,
    PromessaPagamentoCreateRequest,
    PromessaPagamentoResponse,
    ReagendarRequest,
    RegistroComunicacaoResponse,
    ResumoCarteiraResponse,
    VencimentoOperacionalResponse,
    VencimentosInadimplenciaResponse,
)

PERMISSAO_COBRANCA_LER = "cobranca.caso.ler"
PERMISSAO_ACAO_REGISTRAR = "cobranca.acao.registrar"
PERMISSAO_PROMESSA_REGISTRAR = "cobranca.promessa.registrar"
PERMISSAO_PROMESSA_APROPRIAR = "cobranca.promessa.apropriar"
PERMISSAO_AGENDA_LER = "agenda.ler"
PERMISSAO_COMPROMISSO_GERIR = "agenda.compromisso.gerir"
PERMISSAO_LEMBRETE_GERIR = "agenda.lembrete.gerir"
PERMISSAO_COMUNICACAO_REGISTRAR = "comunicacao.registrar"
PERMISSAO_COMUNICACAO_LER = "comunicacao.ler"
PERMISSAO_RELATORIOS_LER = "relatorios.operacionais.ler"
PERMISSAO_NOTIFICACAO_CONCILIAR = "notificacao.conciliar"

router = APIRouter(
    prefix="/credit",
    tags=["daily-operations"],
    dependencies=[Depends(get_principal_atual)],
    responses=combinar_respostas(RESPOSTAS_PROTEGIDAS_COM_RECURSO, RESPOSTA_PAYLOAD_INVALIDO),
)


@router.get(
    "/cobrancas/casos",
    response_model=FilaCobrancaResponse,
    summary="Consultar fila de cobranca",
)
def consultar_fila_cobranca(
    principal: Principal = Depends(exigir_permissao(PERMISSAO_COBRANCA_LER)),
    service: Any = Depends(get_consultar_fila_cobranca_service),
    carteira_id: uuid.UUID | None = Query(default=None),
    devedor_id: uuid.UUID | None = Query(default=None),
    estado: EstadoCobranca | None = Query(default=None),
) -> FilaCobrancaResponse:
    resultado = service.listar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira_id,
        devedor_id=devedor_id,
        estado=estado,
    )
    return FilaCobrancaResponse(
        items=[_caso_response(item) for item in resultado.items],
        total=resultado.total,
    )


@router.post(
    "/cobrancas/casos/{cobranca_caso_id}/acoes",
    response_model=AcaoCobrancaResponse,
    summary="Registrar acao de cobranca",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def registrar_acao_cobranca(
    cobranca_caso_id: uuid.UUID,
    payload: AcaoCobrancaCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_ACAO_REGISTRAR)),
    service: Any = Depends(get_registrar_acao_cobranca_service),
) -> AcaoCobrancaResponse:
    resultado = service.registrar(
        tenant_id=principal.tenant_id,
        cobranca_caso_id=cobranca_caso_id,
        usuario_id=principal.usuario_id,
        tipo=payload.tipo,
        resultado=payload.resultado,
        parcela_id=payload.parcela_id,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
    )
    return _acao_response(resultado)


@router.post(
    "/cobrancas/casos/{cobranca_caso_id}/promessas",
    response_model=PromessaPagamentoResponse,
    summary="Registrar promessa de pagamento",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def registrar_promessa(
    cobranca_caso_id: uuid.UUID,
    payload: PromessaPagamentoCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROMESSA_REGISTRAR)),
    service: Any = Depends(get_registrar_promessa_service),
) -> PromessaPagamentoResponse:
    resultado = service.registrar(
        tenant_id=principal.tenant_id,
        cobranca_caso_id=cobranca_caso_id,
        usuario_id=principal.usuario_id,
        valor_declarado=payload.valor_declarado,
        data_promessa=payload.data_promessa,
        parcela_id=payload.parcela_id,
        observacao=payload.observacao,
        pagamento_informado=payload.pagamento_informado,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
    )
    return _promessa_response(resultado)


@router.post(
    "/cobrancas/promessas/{promessa_id}/apropriacoes",
    response_model=ApropriacaoPagamentoResponse,
    summary="Apropriar pagamento oficial em promessa",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def apropriar_promessa(
    promessa_id: uuid.UUID,
    payload: ApropriacaoPagamentoCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PROMESSA_APROPRIAR)),
    service: Any = Depends(get_apropriar_pagamento_promessa_service),
) -> ApropriacaoPagamentoResponse:
    resultado = service.apropriar(
        tenant_id=principal.tenant_id,
        promessa_id=promessa_id,
        pagamento_id=payload.pagamento_id,
        usuario_id=principal.usuario_id,
        parcela_id=payload.parcela_id,
        data_referencia=payload.data_referencia,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
    )
    return _apropriacao_response(resultado)


@router.get(
    "/agenda",
    response_model=AgendaOperacionalResponse,
    summary="Consultar agenda operacional",
)
def consultar_agenda(
    principal: Principal = Depends(exigir_permissao(PERMISSAO_AGENDA_LER)),
    service: Any = Depends(get_consultar_agenda_operacional_service),
    carteira_id: uuid.UUID | None = Query(default=None),
    devedor_id: uuid.UUID | None = Query(default=None),
    emprestimo_id: uuid.UUID | None = Query(default=None),
    estado: EstadoCompromisso | None = Query(default=None),
    janela_inicio: datetime | None = Query(default=None),
    janela_fim: datetime | None = Query(default=None),
    incluir_lembretes: bool = Query(default=True),
) -> AgendaOperacionalResponse:
    resultado = service.listar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira_id,
        devedor_id=devedor_id,
        emprestimo_id=emprestimo_id,
        estado=estado,
        janela_inicio=janela_inicio,
        janela_fim=janela_fim,
        incluir_lembretes=incluir_lembretes,
    )
    return _agenda_response(resultado)


@router.post(
    "/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos",
    response_model=AgendaItemResponse,
    summary="Criar compromisso de agenda",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def criar_compromisso(
    devedor_id: uuid.UUID,
    payload: CompromissoAgendaCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    carteira: Carteira = Depends(get_carteira_do_principal),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_COMPROMISSO_GERIR)),
    service: Any = Depends(get_criar_compromisso_agenda_service),
) -> AgendaItemResponse:
    resultado = service.criar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        devedor_id=devedor_id,
        usuario_id=principal.usuario_id,
        titulo=payload.titulo,
        previsto_para=payload.previsto_para,
        emprestimo_id=payload.emprestimo_id,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
    )
    return _agenda_item_response(resultado)


@router.post(
    "/agenda/compromissos/{agenda_item_id}/lembretes",
    response_model=LembreteResponse,
    summary="Criar lembrete de agenda",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def criar_lembrete(
    request: Request,
    agenda_item_id: uuid.UUID,
    payload: LembreteAgendaCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_LEMBRETE_GERIR)),
    service: Any = Depends(get_criar_lembrete_agenda_service),
) -> LembreteResponse:
    resultado = service.criar(
        tenant_id=principal.tenant_id,
        agenda_item_id=agenda_item_id,
        usuario_id=principal.usuario_id,
        horario=payload.horario,
        mensagem=payload.mensagem,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
        correlation_id=get_correlation_id(request),
    )
    return _lembrete_response(resultado)


@router.post(
    "/agenda/compromissos/{agenda_item_id}/reagendar",
    response_model=AgendaItemResponse,
    summary="Reagendar compromisso",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def reagendar_compromisso(
    agenda_item_id: uuid.UUID,
    payload: ReagendarRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_COMPROMISSO_GERIR)),
    service: Any = Depends(get_manter_compromisso_agenda_service),
) -> AgendaItemResponse:
    return _agenda_item_response(
        service.reagendar(
            tenant_id=principal.tenant_id,
            agenda_item_id=agenda_item_id,
            usuario_id=principal.usuario_id,
            novo_horario=payload.novo_horario,
            idempotency_key=_exigir_idempotency_key(idempotency_key),
        )
    )


@router.post(
    "/agenda/compromissos/{agenda_item_id}/concluir",
    response_model=AgendaItemResponse,
    summary="Concluir compromisso",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def concluir_compromisso(
    agenda_item_id: uuid.UUID,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_COMPROMISSO_GERIR)),
    service: Any = Depends(get_manter_compromisso_agenda_service),
) -> AgendaItemResponse:
    return _agenda_item_response(
        service.concluir(
            tenant_id=principal.tenant_id,
            agenda_item_id=agenda_item_id,
            usuario_id=principal.usuario_id,
            idempotency_key=_exigir_idempotency_key(idempotency_key),
        )
    )


@router.post(
    "/agenda/compromissos/{agenda_item_id}/cancelar",
    response_model=AgendaItemResponse,
    summary="Cancelar compromisso",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def cancelar_compromisso(
    agenda_item_id: uuid.UUID,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_COMPROMISSO_GERIR)),
    service: Any = Depends(get_manter_compromisso_agenda_service),
) -> AgendaItemResponse:
    return _agenda_item_response(
        service.cancelar(
            tenant_id=principal.tenant_id,
            agenda_item_id=agenda_item_id,
            usuario_id=principal.usuario_id,
            idempotency_key=_exigir_idempotency_key(idempotency_key),
        )
    )


@router.post(
    "/agenda/lembretes/{lembrete_id}/reagendar",
    response_model=LembreteResponse,
    summary="Reagendar lembrete",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def reagendar_lembrete(
    lembrete_id: uuid.UUID,
    payload: ReagendarRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_LEMBRETE_GERIR)),
    service: Any = Depends(get_manter_lembrete_agenda_service),
) -> LembreteResponse:
    return _lembrete_response(
        service.reagendar(
            tenant_id=principal.tenant_id,
            lembrete_id=lembrete_id,
            usuario_id=principal.usuario_id,
            novo_horario=payload.novo_horario,
            idempotency_key=_exigir_idempotency_key(idempotency_key),
        )
    )


@router.post(
    "/agenda/lembretes/{lembrete_id}/enviar",
    response_model=NotificacaoResponse,
    summary="Conciliar manualmente envio legado de lembrete",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
    deprecated=True,
)
def enviar_lembrete(
    lembrete_id: uuid.UUID,
    payload: ConciliacaoLegadaRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_NOTIFICACAO_CONCILIAR)),
    service: Any = Depends(get_notification_service),
) -> NotificacaoResponse:
    chave = _exigir_idempotency_key(idempotency_key)
    resultado = service.conciliar(
        tenant_id=principal.tenant_id,
        solicitacao_id=payload.notification_id,
        provider_message_id=payload.provider_message_id,
        usuario_id=principal.usuario_id,
        motivo=payload.motivo,
        idempotency_key=chave,
        lembrete_id_esperado=lembrete_id,
    )
    return NotificacaoResponse(
        id=resultado.id,
        carteira_id=resultado.carteira_id,
        lembrete_id=resultado.lembrete_id,
        job_id=resultado.job_id,
        estado=resultado.estado,
        provider_message_id=resultado.provider_message_id,
        resultado_em=resultado.resultado_em,
        codigo_resultado=resultado.codigo_resultado,
    )


@router.post(
    "/agenda/lembretes/{lembrete_id}/concluir",
    response_model=LembreteResponse,
    summary="Concluir lembrete",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def concluir_lembrete(
    lembrete_id: uuid.UUID,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_LEMBRETE_GERIR)),
    service: Any = Depends(get_manter_lembrete_agenda_service),
) -> LembreteResponse:
    return _lembrete_response(
        service.concluir(
            tenant_id=principal.tenant_id,
            lembrete_id=lembrete_id,
            usuario_id=principal.usuario_id,
            idempotency_key=_exigir_idempotency_key(idempotency_key),
        )
    )


@router.post(
    "/agenda/lembretes/{lembrete_id}/cancelar",
    response_model=LembreteResponse,
    summary="Cancelar lembrete",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def cancelar_lembrete(
    lembrete_id: uuid.UUID,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_LEMBRETE_GERIR)),
    service: Any = Depends(get_manter_lembrete_agenda_service),
) -> LembreteResponse:
    return _lembrete_response(
        service.cancelar(
            tenant_id=principal.tenant_id,
            lembrete_id=lembrete_id,
            usuario_id=principal.usuario_id,
            idempotency_key=_exigir_idempotency_key(idempotency_key),
        )
    )


@router.post(
    "/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes",
    response_model=RegistroComunicacaoResponse,
    summary="Registrar comunicacao manual",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def registrar_comunicacao(
    devedor_id: uuid.UUID,
    payload: ComunicacaoManualCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    carteira: Carteira = Depends(get_carteira_do_principal),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_COMUNICACAO_REGISTRAR)),
    service: Any = Depends(get_registrar_comunicacao_manual_service),
) -> RegistroComunicacaoResponse:
    resultado = service.registrar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        devedor_id=devedor_id,
        usuario_id=principal.usuario_id,
        canal=payload.canal,
        ocorrido_em=payload.ocorrido_em,
        resumo=payload.resumo,
        resultado=payload.resultado,
        emprestimo_id=payload.emprestimo_id,
        parcela_id=payload.parcela_id,
        cobranca_acao_id=payload.cobranca_acao_id,
        agenda_item_id=payload.agenda_item_id,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
    )
    return _registro_response(resultado)


@router.get(
    "/comunicacoes",
    response_model=HistoricoComunicacaoResponse,
    summary="Consultar historico de comunicacao",
)
def consultar_comunicacoes(
    principal: Principal = Depends(exigir_permissao(PERMISSAO_COMUNICACAO_LER)),
    service: Any = Depends(get_consultar_historico_comunicacao_service),
    carteira_id: uuid.UUID | None = Query(default=None),
    devedor_id: uuid.UUID | None = Query(default=None),
    emprestimo_id: uuid.UUID | None = Query(default=None),
    cobranca_acao_id: uuid.UUID | None = Query(default=None),
    agenda_item_id: uuid.UUID | None = Query(default=None),
) -> HistoricoComunicacaoResponse:
    resultado = service.listar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira_id,
        devedor_id=devedor_id,
        emprestimo_id=emprestimo_id,
        cobranca_acao_id=cobranca_acao_id,
        agenda_item_id=agenda_item_id,
    )
    return HistoricoComunicacaoResponse(
        registros=[_registro_response(item) for item in resultado.registros],
        total=resultado.total,
    )


@router.get(
    "/carteiras/{carteira_id}/relatorios/resumo",
    response_model=ResumoCarteiraResponse,
    summary="Consultar resumo operacional da carteira",
)
def relatorio_resumo(
    carteira: Carteira = Depends(get_carteira_do_principal),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_RELATORIOS_LER)),
    service: Any = Depends(get_relatorios_operacionais_service),
    data_referencia: date = Query(...),
) -> ResumoCarteiraResponse:
    resultado = service.resumo_carteira(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        data_referencia=data_referencia,
    )
    return ResumoCarteiraResponse(**resultado.__dict__)


@router.get(
    "/carteiras/{carteira_id}/relatorios/vencimentos",
    response_model=VencimentosInadimplenciaResponse,
    summary="Consultar vencimentos e inadimplencia",
)
def relatorio_vencimentos(
    carteira: Carteira = Depends(get_carteira_do_principal),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_RELATORIOS_LER)),
    service: Any = Depends(get_relatorios_operacionais_service),
    data_referencia: date = Query(...),
) -> VencimentosInadimplenciaResponse:
    resultado = service.vencimentos_inadimplencia(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        data_referencia=data_referencia,
    )
    return VencimentosInadimplenciaResponse(
        tenant_id=resultado.tenant_id,
        carteira_id=resultado.carteira_id,
        data_referencia=resultado.data_referencia,
        itens=[VencimentoOperacionalResponse(**item.__dict__) for item in resultado.itens],
        total=resultado.total,
    )


@router.get(
    "/carteiras/{carteira_id}/relatorios/pagamentos",
    response_model=PagamentosEncerramentosResponse,
    summary="Consultar pagamentos e operacoes encerradas",
)
def relatorio_pagamentos(
    carteira: Carteira = Depends(get_carteira_do_principal),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_RELATORIOS_LER)),
    service: Any = Depends(get_relatorios_operacionais_service),
    inicio: date = Query(...),
    fim: date = Query(...),
) -> PagamentosEncerramentosResponse:
    _validar_periodo_relatorio(inicio, fim)
    resultado = service.pagamentos_encerramentos(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        inicio=inicio,
        fim=fim,
    )
    return PagamentosEncerramentosResponse(
        tenant_id=resultado.tenant_id,
        carteira_id=resultado.carteira_id,
        inicio=resultado.inicio,
        fim=resultado.fim,
        pagamentos=[PagamentoOperacionalResponse(**item.__dict__) for item in resultado.pagamentos],
        operacoes_quitadas=list(resultado.operacoes_quitadas),
        total_realizado=resultado.total_realizado,
    )


@router.get(
    "/carteiras/{carteira_id}/relatorios/fluxo",
    response_model=FluxoPrevistoRealizadoResponse,
    summary="Consultar fluxo previsto e realizado",
)
def relatorio_fluxo(
    carteira: Carteira = Depends(get_carteira_do_principal),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_RELATORIOS_LER)),
    service: Any = Depends(get_relatorios_operacionais_service),
    inicio: date = Query(...),
    fim: date = Query(...),
) -> FluxoPrevistoRealizadoResponse:
    _validar_periodo_relatorio(inicio, fim)
    resultado = service.fluxo_previsto_realizado(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        inicio=inicio,
        fim=fim,
    )
    return FluxoPrevistoRealizadoResponse(
        tenant_id=resultado.tenant_id,
        carteira_id=resultado.carteira_id,
        inicio=resultado.inicio,
        fim=resultado.fim,
        itens=[
            FluxoDiaResponse(
                data=item.data,
                realizado=item.realizado,
                acertos=item.acertos,
                pagamento_ids=list(item.pagamento_ids),
            )
            for item in resultado.itens
        ],
    )


def _exigir_idempotency_key(valor: str | None) -> str:
    if valor is None or not valor.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "codigo": "idempotency_key_ausente",
                "mensagem": "Header Idempotency-Key e obrigatorio",
            },
        )
    return valor.strip()


def _validar_periodo_relatorio(inicio: date, fim: date) -> None:
    if inicio > fim:
        raise HTTPException(
            status_code=400,
            detail={
                "codigo": "payload_invalido",
                "mensagem": "inicio deve ser menor ou igual ao fim",
            },
        )


def _caso_response(resultado: Any) -> CobrancaCasoResponse:
    return CobrancaCasoResponse(**resultado.__dict__)


def _acao_response(resultado: Any) -> AcaoCobrancaResponse:
    return AcaoCobrancaResponse(**resultado.__dict__)


def _promessa_response(resultado: Any) -> PromessaPagamentoResponse:
    return PromessaPagamentoResponse(**resultado.__dict__)


def _apropriacao_response(resultado: Any) -> ApropriacaoPagamentoResponse:
    return ApropriacaoPagamentoResponse(**resultado.__dict__)


def _agenda_item_response(resultado: Any) -> AgendaItemResponse:
    return AgendaItemResponse(**resultado.__dict__)


def _lembrete_response(resultado: Any) -> LembreteResponse:
    return LembreteResponse(**resultado.__dict__)


def _agenda_response(resultado: Any) -> AgendaOperacionalResponse:
    return AgendaOperacionalResponse(
        compromissos=[_agenda_item_response(item) for item in resultado.compromissos],
        lembretes=[_lembrete_response(item) for item in resultado.lembretes],
        total=resultado.total,
    )


def _registro_response(resultado: Any) -> RegistroComunicacaoResponse:
    return RegistroComunicacaoResponse(**resultado.__dict__)
