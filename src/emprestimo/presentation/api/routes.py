"""Rotas da API pública da FEATURE-001 (IMP-017/018), FEATURE-002 (IMP-026/027/028),
FEATURE-003 (IMP-032) e FEATURE-004 (IMP-036).

A camada Presentation apenas: valida entrada (header/body/query), monta DTOs,
chama os casos de uso da Application e converte o resultado em resposta HTTP.
Nenhuma regra de negócio existe aqui — erros de domínio/aplicação são
traduzidos por exception handlers registrados no app (main.py).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Literal, NoReturn, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from emprestimo.application.atualizacao import TenantAtualizacaoService
from emprestimo.application.autorizacao import AutorizacaoService, Principal
from emprestimo.application.consulta import (
    TenantConsultaPorIdService,
    TenantConsultaService,
    TenantListagemService,
)
from emprestimo.application.estado import TenantEstadoService
from emprestimo.application.provisioning import TenantProvisioningService
from emprestimo.domain.platform.ports import TenantFiltro, TenantOrdenacao
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_autorizacao_service,
    get_principal_atual,
    get_tenant_atualizacao_service,
    get_tenant_consulta_por_id_service,
    get_tenant_consulta_service,
    get_tenant_estado_service,
    get_tenant_listagem_service,
    get_tenant_provisioning_service,
)
from emprestimo.presentation.api.openapi import (
    RESPOSTA_RECURSO_NAO_ENCONTRADO,
    RESPOSTAS_PROTEGIDAS,
    combinar_respostas,
)
from emprestimo.presentation.api.schemas import (
    TenantCreateRequest,
    TenantListagemParams,
    TenantListagemResponse,
    TenantProvisioningResponse,
    TenantResponse,
    TenantUpdateRequest,
)

PERMISSAO_TENANT_ATUALIZAR = "tenant.atualizar"
PERMISSAO_TENANT_CRIAR = "tenant.criar"
PERMISSAO_TENANT_INATIVAR = "tenant.inativar"
PERMISSAO_TENANT_LER = "tenant.ler"
PERMISSAO_TENANT_REATIVAR = "tenant.reativar"

router = APIRouter(
    prefix="/platform",
    tags=["platform"],
    dependencies=[Depends(get_principal_atual)],
    responses=RESPOSTAS_PROTEGIDAS,
)


@router.post(
    "/tenants",
    status_code=201,
    response_model=TenantProvisioningResponse,
    summary="Provisionar um novo Tenant",
)
def criar_tenant(
    payload: TenantCreateRequest,
    _: Principal = Depends(exigir_permissao(PERMISSAO_TENANT_CRIAR)),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    service: TenantProvisioningService = Depends(get_tenant_provisioning_service),
) -> TenantProvisioningResponse:
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
    return TenantProvisioningResponse(
        id=resultado.tenant_id,
        identificador_institucional=resultado.identificador_institucional,
        nome=resultado.nome,
        estado=resultado.estado,
        criado_em=resultado.criado_em,
        usuario_administrador_id=resultado.usuario_administrador_id,
        token_ativacao=resultado.token_ativacao,
    )


def _exigir_permissao_tenant(
    operacao: str,
) -> Callable[[uuid.UUID, Principal, AutorizacaoService], Principal]:
    def dependencia(
        tenant_id: uuid.UUID,
        principal: Principal = Depends(get_principal_atual),
        autorizacao: AutorizacaoService = Depends(get_autorizacao_service),
    ) -> Principal:
        if not principal.administrador_plataforma and tenant_id != principal.tenant_id:
            autorizacao.exigir_tenant_do_recurso(
                principal,
                recurso_id=tenant_id,
                recurso_tenant_id=tenant_id,
                recurso_tipo="tenant",
            )
        autorizacao.exigir_permissao(principal, operacao)
        return principal

    return dependencia


@router.get(
    "/tenants",
    response_model=TenantListagemResponse | TenantResponse,
    summary="Consultar por identificador institucional (IMP-026) ou listar (IMP-027)",
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def consultar_ou_listar_tenants(
    principal: Principal = Depends(get_principal_atual),
    identificador_institucional: str | None = Query(
        default=None,
        min_length=1,
        max_length=120,
        description="Consulta exata por identificador institucional (US-010, DA-002)",
    ),
    params: TenantListagemParams = Depends(),
    service_consulta: TenantConsultaService = Depends(get_tenant_consulta_service),
    service_por_id: TenantConsultaPorIdService = Depends(get_tenant_consulta_por_id_service),
    service_listagem: TenantListagemService = Depends(get_tenant_listagem_service),
    autorizacao: AutorizacaoService = Depends(get_autorizacao_service),
) -> TenantListagemResponse | TenantResponse:
    """Consulta exata por identificador (200/404) ou listagem paginada (US-011, DA-003)."""
    if identificador_institucional is not None:
        # Normalização na Presentation (IMP-025 ajuste)
        identificador = identificador_institucional.strip()
        tenant = service_consulta.consultar_por_identificador(identificador)
        if tenant is None:
            _responder_tenant_nao_encontrado()
        if not principal.administrador_plataforma and tenant.id != principal.tenant_id:
            autorizacao.exigir_tenant_do_recurso(
                principal,
                recurso_id=tenant.id,
                recurso_tenant_id=tenant.id,
                recurso_tipo="tenant",
            )
        autorizacao.exigir_permissao(principal, PERMISSAO_TENANT_LER)
        return TenantResponse(
            id=tenant.id,
            identificador_institucional=tenant.identificador_institucional,
            nome=tenant.nome,
            estado=tenant.estado,
            criado_em=tenant.criado_em,
        )

    autorizacao.exigir_permissao(principal, PERMISSAO_TENANT_LER)
    if principal.administrador_plataforma:
        resultado = service_listagem.listar(
            page=params.page,
            size=params.size,
            ordenacao=_parse_ordenacao(params.sort),
            filtro=TenantFiltro(estado=params.estado),
        )
        return TenantListagemResponse(
            items=[
                TenantResponse(
                    id=tenant.id,
                    identificador_institucional=tenant.identificador_institucional,
                    nome=tenant.nome,
                    estado=tenant.estado,
                    criado_em=tenant.criado_em,
                )
                for tenant in resultado.items
            ],
            total=resultado.total,
            page=resultado.page,
            size=resultado.size,
            pages=resultado.pages,
        )

    tenant = service_por_id.consultar_por_id(principal.tenant_id)
    if tenant is None or (params.estado is not None and tenant.estado != params.estado):
        total = 0
        items = []
    else:
        total = 1
        items = [tenant] if params.page == 1 else []
    return TenantListagemResponse(
        items=[
            TenantResponse(
                id=t.id,
                identificador_institucional=t.identificador_institucional,
                nome=t.nome,
                estado=t.estado,
                criado_em=t.criado_em,
            )
            for t in items
        ],
        total=total,
        page=params.page,
        size=params.size,
        pages=total,
    )


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Consultar um Tenant por ID (IMP-026, US-009, DA-001)",
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def obter_tenant_por_id(
    tenant_id: uuid.UUID,
    principal: Principal = Depends(_exigir_permissao_tenant(PERMISSAO_TENANT_LER)),
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
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def atualizar_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdateRequest,
    principal: Principal = Depends(_exigir_permissao_tenant(PERMISSAO_TENANT_ATUALIZAR)),
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
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def inativar_tenant(
    tenant_id: uuid.UUID,
    principal: Principal = Depends(_exigir_permissao_tenant(PERMISSAO_TENANT_INATIVAR)),
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
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def reativar_tenant(
    tenant_id: uuid.UUID,
    principal: Principal = Depends(_exigir_permissao_tenant(PERMISSAO_TENANT_REATIVAR)),
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


def _responder_tenant_nao_encontrado() -> NoReturn:
    raise HTTPException(
        status_code=404,
        detail={"codigo": "tenant_nao_encontrado", "mensagem": "Tenant inexistente"},
    )
