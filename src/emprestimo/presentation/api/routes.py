"""Rotas da API pública da FEATURE-001 (IMP-017/018).

A camada Presentation apenas: valida entrada (header/body), monta DTOs,
chama o TenantProvisioningService e converte o resultado em resposta HTTP.
Nenhuma regra de negócio existe aqui — erros de domínio/aplicação são
traduzidos por exception handlers registrados no app (main.py).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException

from emprestimo.application.provisioning import TenantProvisioningService
from emprestimo.domain.platform.ports import TenantRepository
from emprestimo.presentation.api.dependencies import (
    get_tenant_provisioning_service,
    get_tenant_repository,
)
from emprestimo.presentation.api.schemas import TenantCreateRequest, TenantResponse

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
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Consultar um Tenant",
)
def obter_tenant(
    tenant_id: uuid.UUID,
    repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantResponse:
    """Retorna o Tenant e seu estado operacional (UC-007 — confirmação)."""
    tenant = repository.find_by_id(tenant_id)
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
