"""Rotas administrativas da autenticação OpenAI/Codex (ADR-020)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from emprestimo.application.autorizacao import Principal
from emprestimo.application.openai_conexao import (
    OpenAIConnectionService,
    OpenAIRateLimit,
    OpenAIRateWindow,
)
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_openai_connection_service,
    get_principal_atual,
)
from emprestimo.presentation.api.openai_schemas import (
    OpenAIConnectionResponse,
    OpenAIDeviceChallengeResponse,
    OpenAIDiagnosticResponse,
    OpenAILogoutResponse,
    OpenAIModelResponse,
    OpenAIRateLimitResponse,
    OpenAIRateWindowResponse,
    OpenAIUsageSummaryResponse,
)
from emprestimo.presentation.api.openapi import (
    RESPOSTA_SERVICO_INDISPONIVEL,
    RESPOSTA_UPSTREAM_INVALIDO,
    RESPOSTAS_PROTEGIDAS,
    combinar_respostas,
)

router = APIRouter(
    prefix="/platform/openai",
    tags=["OpenAI"],
    dependencies=[Depends(get_principal_atual)],
    responses=combinar_respostas(
        RESPOSTAS_PROTEGIDAS,
        RESPOSTA_UPSTREAM_INVALIDO,
        RESPOSTA_SERVICO_INDISPONIVEL,
    ),
)


@router.get("/conexao", response_model=OpenAIConnectionResponse)
async def connection(
    _: Principal = Depends(exigir_permissao("openai.conexao.ler")),
    service: OpenAIConnectionService = Depends(get_openai_connection_service),
) -> OpenAIConnectionResponse:
    """Snapshot local; não consulta o App Server nem a rede OpenAI."""
    result = await service.connection()
    return OpenAIConnectionResponse(
        enabled=result.enabled,
        process_available=result.process_available,
        account_connected=result.account_connected,
        plan_type=result.plan_type,
        state=result.state,
        usage_summary=(
            OpenAIUsageSummaryResponse(
                observed_at=result.usage_summary.observed_at,
                rate_limits_status=result.usage_summary.rate_limits_status,
                rate_limits=[_limit(item) for item in result.usage_summary.rate_limits],
            )
            if result.usage_summary is not None
            else None
        ),
    )


@router.get("/diagnostico", response_model=OpenAIDiagnosticResponse)
async def diagnostic(
    _: Principal = Depends(exigir_permissao("openai.conexao.ler")),
    service: OpenAIConnectionService = Depends(get_openai_connection_service),
) -> OpenAIDiagnosticResponse:
    """Atualiza conta, catálogo e limites; o agent compartilha chamadas concorrentes."""
    result = await service.diagnostic()
    return OpenAIDiagnosticResponse(
        state=result.state,
        observed_at=result.observed_at,
        account_status=result.account_status,
        account_connected=result.account_connected,
        plan_type=result.plan_type,
        models_status=result.models_status,
        models=[
            OpenAIModelResponse(id=item.id, display_name=item.display_name, default=item.default)
            for item in result.models
        ],
        rate_limits_status=result.rate_limits_status,
        rate_limits=[_limit(item) for item in result.rate_limits],
    )


@router.post("/conexao/login", response_model=OpenAIDeviceChallengeResponse)
async def begin_login(
    principal: Principal = Depends(exigir_permissao("openai.conexao.gerir")),
    service: OpenAIConnectionService = Depends(get_openai_connection_service),
) -> OpenAIDeviceChallengeResponse:
    """Inicia device code; a isenção de Idempotency-Key é fechada na ADR-020."""
    result = await service.begin_login(principal.tenant_id, principal.usuario_id)
    return OpenAIDeviceChallengeResponse(
        verification_url=result.verification_url,
        user_code=result.user_code,
        expires_at=result.expires_at,
    )


@router.delete("/conexao", response_model=OpenAILogoutResponse)
async def logout(
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao("openai.conexao.gerir")),
    service: OpenAIConnectionService = Depends(get_openai_connection_service),
) -> OpenAILogoutResponse:
    """Remove a sessão local; não promete revogação remota da conta."""
    result = await service.logout(
        principal.tenant_id,
        principal.usuario_id,
        idempotency_key=idempotency_key,
    )
    return OpenAILogoutResponse(
        state=result.state,
        local_logout=result.local_logout,
        remote_revocation_verified=result.remote_revocation_verified,
    )


def _window(value: OpenAIRateWindow | None) -> OpenAIRateWindowResponse | None:
    if value is None:
        return None
    return OpenAIRateWindowResponse(
        used_percent=value.used_percent,
        window_duration_minutes=value.window_duration_minutes,
        resets_at=value.resets_at,
    )


def _limit(value: OpenAIRateLimit) -> OpenAIRateLimitResponse:
    return OpenAIRateLimitResponse(
        limit_id=value.limit_id,
        plan_type=value.plan_type,
        primary=_window(value.primary),
        secondary=_window(value.secondary),
    )
