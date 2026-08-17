"""Endpoint do lancamento composto de emprestimo (IMP-306, PLAN-027)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from emprestimo.application.autorizacao import AutorizacaoService, Principal
from emprestimo.application.lancamento import (
    CondicoesLancamento,
    DevedorNovo,
    LancamentoService,
)
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.presentation.api.dependencies import (
    get_autorizacao_service,
    get_carteira_do_principal,
    get_lancamento_service,
    get_principal_atual,
)
from emprestimo.presentation.api.lancamento_schemas import (
    LancamentoCreateRequest,
    LancamentoResponse,
)
from emprestimo.presentation.api.openapi import (
    RESPOSTA_CONFLITO_ESTADO,
    RESPOSTA_PAYLOAD_INVALIDO,
    RESPOSTAS_PROTEGIDAS_COM_RECURSO,
    combinar_respostas,
)

# O lancamento atravessa quatro contextos numa transacao so, entao exige as
# quatro permissoes. Nao existe permissao propria de "lancamento": conceder uma
# criaria um atalho para quem nao pode executar as etapas separadamente.
PERMISSOES_LANCAMENTO = (
    "devedor.criar",
    "comercial.proposta.criar",
    "contratos.contrato.criar",
    "motor.emprestimo.criar",
)

router = APIRouter(
    prefix="/credit",
    tags=["launch"],
    dependencies=[Depends(get_principal_atual)],
    responses=combinar_respostas(RESPOSTAS_PROTEGIDAS_COM_RECURSO, RESPOSTA_PAYLOAD_INVALIDO),
)


def _exigir_idempotency_key(idempotency_key: str | None) -> str:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "codigo": "idempotency_key_ausente",
                "mensagem": "Header Idempotency-Key e obrigatorio.",
            },
        )
    return idempotency_key.strip()


@router.post(
    "/carteiras/{carteira_id}/lancamentos",
    status_code=201,
    response_model=LancamentoResponse,
    summary="Lancar emprestimo em uma unica operacao",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def lancar_emprestimo(
    payload: LancamentoCreateRequest,
    carteira: Carteira = Depends(get_carteira_do_principal),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(get_principal_atual),
    autorizacao: AutorizacaoService = Depends(get_autorizacao_service),
    service: LancamentoService = Depends(get_lancamento_service),
) -> LancamentoResponse:
    for operacao in PERMISSOES_LANCAMENTO:
        autorizacao.exigir_permissao(principal, operacao)

    resultado = service.lancar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira.id,
        usuario_id=principal.usuario_id,
        condicoes=CondicoesLancamento(
            valor_contratado=payload.condicoes.valor_contratado,
            taxa_juros_mensal=payload.condicoes.taxa_juros_mensal,
            quantidade_parcelas=payload.condicoes.quantidade_parcelas,
            primeiro_vencimento=payload.condicoes.primeiro_vencimento,
            moeda=payload.condicoes.moeda,
        ),
        data_referencia=payload.data_referencia,
        idempotency_key=_exigir_idempotency_key(idempotency_key),
        devedor_id=payload.devedor_id,
        devedor_novo=(
            None
            if payload.devedor_novo is None
            else DevedorNovo(
                documento=payload.devedor_novo.documento,
                nome=payload.devedor_novo.nome,
                contato_whatsapp=payload.devedor_novo.contato_whatsapp,
            )
        ),
    )
    return LancamentoResponse(
        devedor_id=resultado.devedor_id,
        proposta_id=resultado.proposta_id,
        contrato_id=resultado.contrato_id,
        emprestimo_id=resultado.emprestimo_id,
        quantidade_parcelas=resultado.quantidade_parcelas,
    )
