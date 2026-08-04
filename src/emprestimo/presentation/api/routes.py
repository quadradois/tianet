"""Rotas da API pública da FEATURE-001 (IMP-017/018), FEATURE-002 (IMP-026/027/028),
FEATURE-003 (IMP-032) e FEATURE-004 (IMP-036).

A camada Presentation apenas: valida entrada (header/body/query), monta DTOs,
chama os casos de uso da Application e converte o resultado em resposta HTTP.
Nenhuma regra de negócio existe aqui — erros de domínio/aplicação são
traduzidos por exception handlers registrados no app (main.py).
"""

from __future__ import annotations

import uuid
from typing import Literal, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from emprestimo.application.atualizacao import TenantAtualizacaoService
from emprestimo.application.consulta import (
    TenantConsultaPorIdService,
    TenantConsultaService,
    TenantListagemService,
)
from emprestimo.application.estado import TenantEstadoService
from emprestimo.application.provisioning import TenantProvisioningService
from emprestimo.domain.platform.ports import TenantFiltro, TenantOrdenacao
from emprestimo.presentation.api.dependencies import (
    get_tenant_atualizacao_service,
    get_tenant_consulta_por_id_service,
    get_tenant_consulta_service,
    get_tenant_estado_service,
    get_tenant_listagem_service,
    get_tenant_provisioning_service,
)
from emprestimo.presentation.api.schemas import (
    TenantCreateRequest,
    TenantListagemParams,
    TenantListagemResponse,
    TenantResponse,
    TenantUpdateRequest,
)

router = APIRouter(prefix="/platform", tags=["platform"])


@router.post(
    "/tenants",
    status_code=201,
    response_model=TenantResponse,
    summary="Provisionar um novo Tenant",
)
def criar_tenant(
    payload: TenantCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: TenantProvisioningService = Depends(get_tenant_provisioning_service),
) -> TenantResponse:
    """Provisiona uma nova organização (UC-001..UC-007, AD-002)."""
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "codigo": "idempotency_key_ausente",
                "mensagem": "Header Idempotency-Key é obrigatório",
            },
        )

    resultado = service.provisionar(
        identificador_institucional=payload.identificador_institucional,
        nome=payload.nome,
        nome_administrador=payload.nome_administrador,
        email_administrador=payload.email_administrador,
        idempotency_key=idempotency_key.strip(),
    )
    return TenantResponse(
        id=resultado.tenant_id,
        identificador_institucional=resultado.identificador_institucional,
        nome=resultado.nome,
        estado=resultado.estado,
        criado_em=resultado.criado_em,
    )


@router.get(
    "/tenants",
    response_model=TenantListagemResponse | TenantResponse,
    summary="Consultar por identificador institucional (IMP-026) ou listar (IMP-027)",
)
def consultar_ou_listar_tenants(
    identificador_institucional: str | None = Query(
        default=None,
        min_length=1,
        max_length=120,
        description="Consulta exata por identificador institucional (US-010, DA-002)",
    ),
    params: TenantListagemParams = Depends(),
    service_consulta: TenantConsultaService = Depends(get_tenant_consulta_service),
    service_listagem: TenantListagemService = Depends(get_tenant_listagem_service),
) -> TenantListagemResponse | TenantResponse:
    """Consulta exata por identificador (200/404) ou listagem paginada (US-011, DA-003)."""
    if identificador_institucional is not None:
        # Normalização na Presentation (IMP-025 ajuste)
        identificador = identificador_institucional.strip()
        tenant = service_consulta.consultar_por_identificador(identificador)
        if tenant is None:
            raise HTTPException(
                status_code=404,
                detail={"codigo": "tenant_nao_encontrado", "mensagem": "Tenant inexistente"},
            )
        return TenantResponse(
            id=tenant.id,
            identificador_institucional=tenant.identificador_institucional,
            nome=tenant.nome,
            estado=tenant.estado,
            criado_em=tenant.criado_em,
        )

    # Listagem paginada (IMP-027)
    ordenacao = _parse_ordenacao(params.sort)
    filtro = TenantFiltro(estado=params.estado) if params.estado else None

    resultado = service_listagem.listar(
        page=params.page,
        size=params.size,
        ordenacao=ordenacao,
        filtro=filtro,
    )
    return TenantListagemResponse(
        items=[
            TenantResponse(
                id=t.id,
                identificador_institucional=t.identificador_institucional,
                nome=t.nome,
                estado=t.estado,
                criado_em=t.criado_em,
            )
            for t in resultado.items
        ],
        total=resultado.total,
        page=resultado.page,
        size=resultado.size,
        pages=resultado.pages,
    )


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Consultar um Tenant por ID (IMP-026, US-009, DA-001)",
)
def obter_tenant_por_id(
    tenant_id: uuid.UUID,
    service: TenantConsultaPorIdService = Depends(get_tenant_consulta_por_id_service),
) -> TenantResponse:
    """Retorna o Tenant e seu estado operacional (UC-007 — confirmação)."""
    tenant = service.consultar_por_id(tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=404,
            detail={"codigo": "tenant_nao_encontrado", "mensagem": "Tenant inexistente"},
        )
    return TenantResponse(
        id=tenant.id,
        identificador_institucional=tenant.identificador_institucional,
        nome=tenant.nome,
        estado=tenant.estado,
        criado_em=tenant.criado_em,
    )


@router.patch(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Atualizar nome do Tenant (IMP-032, US-012, DA-205)",
)
def atualizar_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdateRequest,
    service: TenantAtualizacaoService = Depends(get_tenant_atualizacao_service),
) -> TenantResponse:
    """Atualização parcial (PATCH) do nome institucional (FEATURE-003).

    A normalização (strip) acontece no DTO; a validação de domínio
    (não vazio, <= 200) permanece no Aggregate — a violação responde
    422 ``regra_violada`` (handler do main.py).
    """
    tenant = service.atualizar_nome(tenant_id, payload.nome)
    if tenant is None:
        raise HTTPException(
            status_code=404,
            detail={"codigo": "tenant_nao_encontrado", "mensagem": "Tenant inexistente"},
        )
    return TenantResponse(
        id=tenant.id,
        identificador_institucional=tenant.identificador_institucional,
        nome=tenant.nome,
        estado=tenant.estado,
        criado_em=tenant.criado_em,
    )


@router.post(
    "/tenants/{tenant_id}/inativar",
    response_model=TenantResponse,
    summary="Inativar um Tenant (IMP-036, US-013, DA-205)",
)
def inativar_tenant(
    tenant_id: uuid.UUID,
    service: TenantEstadoService = Depends(get_tenant_estado_service),
) -> TenantResponse:
    """Transição Ativo → Inativo (FEATURE-004).

    Sem corpo de request. Estado divergente responde 409 ``conflito_estado``
    (traduzido de ``TransicaoEstadoInvalidaError`` no main.py); a regra de
    transição permanece no Aggregate (DOMAIN-017).
    """
    tenant = service.inativar(tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=404,
            detail={"codigo": "tenant_nao_encontrado", "mensagem": "Tenant inexistente"},
        )
    return TenantResponse(
        id=tenant.id,
        identificador_institucional=tenant.identificador_institucional,
        nome=tenant.nome,
        estado=tenant.estado,
        criado_em=tenant.criado_em,
    )


@router.post(
    "/tenants/{tenant_id}/reativar",
    response_model=TenantResponse,
    summary="Reativar um Tenant (IMP-036, US-014, DA-205)",
)
def reativar_tenant(
    tenant_id: uuid.UUID,
    service: TenantEstadoService = Depends(get_tenant_estado_service),
) -> TenantResponse:
    """Transição Inativo → Ativo (FEATURE-004).

    Sem corpo de request. Estado divergente responde 409 ``conflito_estado``
    (traduzido de ``TransicaoEstadoInvalidaError`` no main.py); a regra de
    transição permanece no Aggregate (DOMAIN-017).
    """
    tenant = service.reativar(tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=404,
            detail={"codigo": "tenant_nao_encontrado", "mensagem": "Tenant inexistente"},
        )
    return TenantResponse(
        id=tenant.id,
        identificador_institucional=tenant.identificador_institucional,
        nome=tenant.nome,
        estado=tenant.estado,
        criado_em=tenant.criado_em,
    )


CampoOrdenacao = Literal["criado_em", "identificador_institucional", "nome", "estado"]
DirecaoOrdenacao = Literal["asc", "desc"]


def _parse_ordenacao(sort: str) -> TenantOrdenacao:
    """Converte ``campo:direcao`` (já validado pelo pattern do schema) em port.

    O cast é seguro: TenantListagemParams.sort valida o pattern na Presentation.
    """
    campo, direcao = sort.split(":")
    return TenantOrdenacao(
        campo=cast(CampoOrdenacao, campo),
        direcao=cast(DirecaoOrdenacao, direcao),
    )
