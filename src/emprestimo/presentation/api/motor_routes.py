"""Rotas REST do Motor Financeiro (EPIC-005/P5)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from emprestimo.application.autorizacao import Principal
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.emprestimo import EmprestimoState
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_carteira_do_principal,
    get_consulta_emprestimo_service,
    get_consulta_saldo_service,
    get_criacao_emprestimo_service,
    get_pagamento_service,
    get_plano_parcelas_service,
    get_principal_atual,
    get_quitacao_renegociacao_service,
)
from emprestimo.presentation.api.motor_schemas import (
    EmprestimoListagemResponse,
    EmprestimoResponse,
    MemoriaCalculoResponse,
    PagamentoCreateRequest,
    PagamentoResponse,
    ParcelaResponse,
    PassoCalculoResponse,
    PlanoParcelasRequest,
    PlanoParcelasResponse,
    QuitacaoCalculadaResponse,
    QuitacaoRequest,
    QuitacaoResponse,
    RenegociacaoCreateRequest,
    RenegociacaoResponse,
    SaldoResponse,
    ValorQuitacaoResponse,
)
from emprestimo.presentation.api.openapi import (
    RESPOSTA_CONFLITO_ESTADO,
    RESPOSTA_PAYLOAD_INVALIDO,
    RESPOSTAS_PROTEGIDAS_COM_RECURSO,
    combinar_respostas,
)

PERMISSAO_EMPRESTIMO_CRIAR = "motor.emprestimo.criar"
PERMISSAO_EMPRESTIMO_LER = "motor.emprestimo.ler"
PERMISSAO_PARCELA_GERAR = "motor.parcela.gerar"
PERMISSAO_PARCELA_LER = "motor.parcela.ler"
PERMISSAO_PAGAMENTO_REGISTRAR = "motor.pagamento.registrar"
PERMISSAO_SALDO_LER = "motor.saldo.ler"
PERMISSAO_MEMORIA_LER = "motor.memoria.ler"
PERMISSAO_QUITACAO_EXECUTAR = "motor.quitacao.executar"
PERMISSAO_RENEGOCIACAO_CRIAR = "motor.renegociacao.criar"

router = APIRouter(
    prefix="/credit",
    tags=["financial-engine"],
    dependencies=[Depends(get_principal_atual)],
    responses=combinar_respostas(RESPOSTAS_PROTEGIDAS_COM_RECURSO, RESPOSTA_PAYLOAD_INVALIDO),
)


@router.post(
    "/contratos/{contrato_id}/emprestimos",
    status_code=201,
    response_model=EmprestimoResponse,
    summary="Criar emprestimo a partir de contrato liberado",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def criar_emprestimo(
    contrato_id: uuid.UUID,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_EMPRESTIMO_CRIAR)),
    service: Any = Depends(get_criacao_emprestimo_service),
) -> EmprestimoResponse:
    resultado = service.criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=principal.tenant_id,
        usuario_id=principal.usuario_id,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
    )
    return _emprestimo_response(resultado)


@router.get(
    "/emprestimos/{emprestimo_id}",
    response_model=EmprestimoResponse,
    summary="Consultar emprestimo por ID",
)
def consultar_emprestimo(
    emprestimo_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_EMPRESTIMO_LER)),
    service: Any = Depends(get_consulta_emprestimo_service),
) -> EmprestimoResponse:
    return _emprestimo_response(
        service.consultar(emprestimo_id=emprestimo_id, tenant_id=principal.tenant_id)
    )


@router.get(
    "/carteiras/{carteira_id}/emprestimos",
    response_model=EmprestimoListagemResponse,
    summary="Listar emprestimos da carteira",
)
def listar_emprestimos(
    carteira: Carteira = Depends(get_carteira_do_principal),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_EMPRESTIMO_LER)),
    service: Any = Depends(get_consulta_emprestimo_service),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    devedor_id: uuid.UUID | None = Query(default=None),
    estado: EmprestimoState | None = Query(default=None),
) -> EmprestimoListagemResponse:
    resultado = service.listar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        devedor_id=devedor_id,
        estado=estado,
        pagina=page,
        tamanho=size,
    )
    return EmprestimoListagemResponse(
        items=[_emprestimo_response(item) for item in resultado.items],
        total=resultado.total,
        page=resultado.pagina,
        size=resultado.tamanho,
        pages=resultado.paginas,
    )


@router.post(
    "/emprestimos/{emprestimo_id}/parcelas",
    response_model=PlanoParcelasResponse,
    summary="Gerar plano de parcelas do emprestimo",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def criar_plano_parcelas(
    emprestimo_id: uuid.UUID,
    payload: PlanoParcelasRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PARCELA_GERAR)),
    service: Any = Depends(get_plano_parcelas_service),
) -> PlanoParcelasResponse:
    resultado = service.gerar(
        emprestimo_id=emprestimo_id,
        tenant_id=principal.tenant_id,
        data_referencia=payload.data_referencia,
    )
    return _plano_response(resultado)


@router.get(
    "/emprestimos/{emprestimo_id}/parcelas",
    response_model=PlanoParcelasResponse,
    summary="Consultar parcelas do emprestimo",
)
def consultar_parcelas(
    emprestimo_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PARCELA_LER)),
    service: Any = Depends(get_plano_parcelas_service),
) -> PlanoParcelasResponse:
    resultado = service.consultar(emprestimo_id=emprestimo_id, tenant_id=principal.tenant_id)
    return _plano_response(resultado)


@router.post(
    "/emprestimos/{emprestimo_id}/pagamentos",
    response_model=PagamentoResponse,
    summary="Registrar pagamento no Motor Financeiro",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def registrar_pagamento(
    emprestimo_id: uuid.UUID,
    payload: PagamentoCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_PAGAMENTO_REGISTRAR)),
    service: Any = Depends(get_pagamento_service),
) -> PagamentoResponse:
    resultado = service.registrar(
        emprestimo_id=emprestimo_id,
        tenant_id=principal.tenant_id,
        usuario_id=principal.usuario_id,
        valor=payload.valor,
        recebido_em=payload.recebido_em,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
    )
    return _pagamento_response(resultado)


@router.get(
    "/emprestimos/{emprestimo_id}/saldo",
    response_model=SaldoResponse,
    summary="Consultar saldo devedor do emprestimo",
)
def consultar_saldo(
    emprestimo_id: uuid.UUID,
    data_referencia: date = Query(...),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_SALDO_LER)),
    service: Any = Depends(get_consulta_saldo_service),
) -> SaldoResponse:
    resultado = service.consultar(
        emprestimo_id=emprestimo_id,
        tenant_id=principal.tenant_id,
        data_referencia=data_referencia,
    )
    return SaldoResponse(
        emprestimo_id=resultado.emprestimo_id,
        tenant_id=resultado.tenant_id,
        data_referencia=resultado.data_referencia,
        principal=resultado.principal,
        juros=resultado.juros,
        encargos=resultado.encargos,
        total=resultado.total,
        memoria=_memoria_response(resultado.memoria),
    )


@router.get(
    "/emprestimos/{emprestimo_id}/memoria-calculo",
    response_model=list[MemoriaCalculoResponse],
    summary="Consultar memorias de calculo do emprestimo",
)
def consultar_memorias(
    emprestimo_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_MEMORIA_LER)),
    service: Any = Depends(get_consulta_emprestimo_service),
) -> list[MemoriaCalculoResponse]:
    memorias = service.consultar_memorias(
        emprestimo_id=emprestimo_id,
        tenant_id=principal.tenant_id,
    )
    return [_memoria_response(memoria) for memoria in memorias]


@router.get(
    "/emprestimos/{emprestimo_id}/quitacao",
    response_model=QuitacaoCalculadaResponse,
    summary="Consultar valor para quitacao do emprestimo",
)
def consultar_quitacao(
    emprestimo_id: uuid.UUID,
    data_referencia: date = Query(...),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_QUITACAO_EXECUTAR)),
    service: Any = Depends(get_quitacao_renegociacao_service),
) -> QuitacaoCalculadaResponse:
    resultado = service.calcular_valor_quitacao(
        emprestimo_id=emprestimo_id,
        tenant_id=principal.tenant_id,
        data_referencia=data_referencia,
    )
    return QuitacaoCalculadaResponse(
        emprestimo_id=resultado.emprestimo_id,
        tenant_id=resultado.tenant_id,
        valor_quitacao=ValorQuitacaoResponse(
            valor_total=resultado.valor_quitacao.valor_total,
            moeda=resultado.valor_quitacao.moeda,
            data_referencia=resultado.valor_quitacao.data_referencia,
            componentes=dict(resultado.valor_quitacao.componentes),
        ),
        memoria=_memoria_response(resultado.memoria),
    )


@router.post(
    "/emprestimos/{emprestimo_id}/quitacao",
    response_model=QuitacaoResponse,
    summary="Executar quitacao do emprestimo",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def executar_quitacao(
    emprestimo_id: uuid.UUID,
    payload: QuitacaoRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_QUITACAO_EXECUTAR)),
    service: Any = Depends(get_quitacao_renegociacao_service),
) -> QuitacaoResponse:
    resultado = service.quitar(
        emprestimo_id=emprestimo_id,
        tenant_id=principal.tenant_id,
        usuario_id=principal.usuario_id,
        recebido_em=payload.recebido_em,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
    )
    return QuitacaoResponse(
        emprestimo_id=resultado.emprestimo_id,
        tenant_id=resultado.tenant_id,
        estado=resultado.estado,
        pagamento=_pagamento_response(resultado.pagamento),
        memoria_quitacao=_memoria_response(resultado.memoria_quitacao),
    )


@router.post(
    "/emprestimos/{emprestimo_id}/renegociacoes",
    response_model=RenegociacaoResponse,
    summary="Registrar renegociacao financeira",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def registrar_renegociacao(
    emprestimo_id: uuid.UUID,
    payload: RenegociacaoCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO_RENEGOCIACAO_CRIAR)),
    service: Any = Depends(get_quitacao_renegociacao_service),
) -> RenegociacaoResponse:
    resultado = service.renegociar(
        emprestimo_id=emprestimo_id,
        tenant_id=principal.tenant_id,
        usuario_id=principal.usuario_id,
        novos_parametros=payload.novos_parametros,
        renegociado_em=payload.renegociado_em,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
    )
    return RenegociacaoResponse(
        emprestimo_id=resultado.emprestimo_id,
        tenant_id=resultado.tenant_id,
        novos_parametros=resultado.novos_parametros,
        memoria=_memoria_response(resultado.memoria),
    )


def _exigir_idempotency_key(idempotency_key: str | None) -> str:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "codigo": "idempotency_key_ausente",
                "mensagem": "Header Idempotency-Key e obrigatorio",
            },
        )
    return idempotency_key.strip()


def _emprestimo_response(resultado: Any) -> EmprestimoResponse:
    return EmprestimoResponse(
        id=resultado.emprestimo_id,
        contrato_id=resultado.contrato_id,
        tenant_id=resultado.tenant_id,
        carteira_id=resultado.carteira_id,
        devedor_id=resultado.devedor_id,
        estado=resultado.estado,
        principal_original=resultado.principal_original,
        moeda=resultado.moeda,
        parametros_financeiros=resultado.parametros_financeiros,
        criado_em=resultado.criado_em,
        dia_de_acerto=resultado.dia_de_acerto,
        proximo_acerto_em=resultado.proximo_acerto_em,
        acerto_pendente_desde=resultado.acerto_pendente_desde,
    )


def _plano_response(resultado: Any) -> PlanoParcelasResponse:
    return PlanoParcelasResponse(
        emprestimo_id=resultado.emprestimo_id,
        tenant_id=resultado.tenant_id,
        parcelas=[
            ParcelaResponse(
                id=parcela.parcela_id,
                emprestimo_id=parcela.emprestimo_id,
                numero=parcela.numero,
                vencimento=parcela.vencimento,
                valor_previsto=parcela.valor_previsto,
                principal=parcela.principal,
                juros=parcela.juros,
                encargos=parcela.encargos,
                valor_liquidado=parcela.valor_liquidado,
                estado=parcela.estado,
            )
            for parcela in resultado.parcelas
        ],
        memoria=_memoria_response(resultado.memoria) if resultado.memoria else None,
    )


def _pagamento_response(resultado: Any) -> PagamentoResponse:
    return PagamentoResponse(
        id=resultado.pagamento_id,
        emprestimo_id=resultado.emprestimo_id,
        tenant_id=resultado.tenant_id,
        valor_recebido=resultado.valor_recebido,
        recebido_em=resultado.recebido_em,
        valor_juros=resultado.valor_juros,
        valor_amortizacao=resultado.valor_amortizacao,
        valor_encargos=resultado.valor_encargos,
        estado=resultado.estado,
        chave_idempotencia=resultado.chave_idempotencia,
        parcelas_liquidadas=list(resultado.parcelas_liquidadas),
        memoria=_memoria_response(resultado.memoria) if resultado.memoria else None,
    )


def _memoria_response(memoria: Any) -> MemoriaCalculoResponse:
    return MemoriaCalculoResponse(
        id=memoria.id,
        tipo=memoria.tipo,
        entradas=dict(memoria.entradas),
        regra=dict(memoria.regra),
        periodos=[dict(periodo) for periodo in memoria.periodos],
        passos=[_passo_response(passo) for passo in memoria.passos],
        arredondamentos=list(memoria.arredondamentos),
        resultados=dict(memoria.resultados),
        criado_em=memoria.criado_em,
    )


def _passo_response(passo: Any) -> PassoCalculoResponse:
    return PassoCalculoResponse(
        nome=passo.nome,
        entradas=dict(passo.entradas),
        saidas=dict(passo.saidas),
        arredondamento=passo.arredondamento,
    )
