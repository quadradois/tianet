"""Rotas do interruptor do Mercado Pago (IMP-388, PLAN-045 §3.12).

Cinco operacoes sobre um recurso unico por Tenant. Todas exigem
`mercadopago.configurar` — permissao de administrador, porque ligar a
integracao escolhe pagar taxa por recebimento: e decisao economica do
proprietario, nao de operacao.

`GET` nao devolve segredo em nenhuma hipotese; as escritas exigem
`Idempotency-Key` como todo POST/PUT do sistema.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from emprestimo.application.autorizacao import Principal
from emprestimo.application.configuracao_mercadopago import ConfiguracaoMercadoPagoService
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_configuracao_mercadopago_service,
)
from emprestimo.presentation.api.mercadopago_schemas import (
    ConfiguracaoMercadoPagoResponse,
    CredenciaisMercadoPagoRequest,
)
from emprestimo.presentation.api.openapi import RESPOSTAS_PROTEGIDAS

PERMISSAO = "mercadopago.configurar"

router = APIRouter(
    prefix="/platform/mercadopago",
    tags=["platform"],
    responses=RESPOSTAS_PROTEGIDAS,
)


@router.get("/configuracao", response_model=ConfiguracaoMercadoPagoResponse)
def consultar_configuracao(
    principal: Principal = Depends(exigir_permissao(PERMISSAO)),
    service: ConfiguracaoMercadoPagoService = Depends(get_configuracao_mercadopago_service),
) -> ConfiguracaoMercadoPagoResponse:
    """Tenant que nunca configurou responde desligado — ausencia nao e 404."""
    return ConfiguracaoMercadoPagoResponse.de(service.consultar(tenant_id=principal.tenant_id))


@router.put("/configuracao", response_model=ConfiguracaoMercadoPagoResponse)
def definir_credenciais(
    payload: CredenciaisMercadoPagoRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO)),
    service: ConfiguracaoMercadoPagoService = Depends(get_configuracao_mercadopago_service),
) -> ConfiguracaoMercadoPagoResponse:
    """Grava cifrado e **invalida o teste anterior**: credencial nova nao herda aval."""
    return ConfiguracaoMercadoPagoResponse.de(
        service.definir_credenciais(
            tenant_id=principal.tenant_id,
            access_token=payload.access_token,
            webhook_secret=payload.webhook_secret,
            usuario_id=principal.usuario_id,
            idempotency_key=idempotency_key.strip(),
        )
    )


@router.post("/configuracao/testar", response_model=ConfiguracaoMercadoPagoResponse)
def testar_credencial(
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO)),
    service: ConfiguracaoMercadoPagoService = Depends(get_configuracao_mercadopago_service),
) -> ConfiguracaoMercadoPagoResponse:
    """Leitura autenticada no provedor, sem criar cobranca."""
    del idempotency_key
    return ConfiguracaoMercadoPagoResponse.de(
        service.testar(tenant_id=principal.tenant_id, usuario_id=principal.usuario_id)
    )


@router.post("/configuracao/habilitar", response_model=ConfiguracaoMercadoPagoResponse)
def habilitar(
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO)),
    service: ConfiguracaoMercadoPagoService = Depends(get_configuracao_mercadopago_service),
) -> ConfiguracaoMercadoPagoResponse:
    """Exige as duas credenciais e teste bem-sucedido."""
    return ConfiguracaoMercadoPagoResponse.de(
        service.habilitar(
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
            idempotency_key=idempotency_key.strip(),
        )
    )


@router.post("/configuracao/desabilitar", response_model=ConfiguracaoMercadoPagoResponse)
def desabilitar(
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao(PERMISSAO)),
    service: ConfiguracaoMercadoPagoService = Depends(get_configuracao_mercadopago_service),
) -> ConfiguracaoMercadoPagoResponse:
    """Impede emissao nova; Pix pendente segue valido e conciliavel."""
    return ConfiguracaoMercadoPagoResponse.de(
        service.desabilitar(
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
            idempotency_key=idempotency_key.strip(),
        )
    )
