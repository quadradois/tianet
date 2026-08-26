"""Rotas de autenticacao IAM (IMP-090)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from emprestimo.application.autenticacao import AutenticacaoService
from emprestimo.presentation.api.dependencies import (
    get_autenticacao_service,
)
from emprestimo.presentation.api.openapi import RESPOSTAS_AUTH
from emprestimo.presentation.api.schemas import (
    AuthLoginRequest,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthRefreshRequest,
    AuthRefreshResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"], responses=RESPOSTAS_AUTH)


@router.post(
    "/login",
    response_model=AuthLoginResponse,
    summary="Autenticar usuario e emitir tokens",
)
def login(
    payload: AuthLoginRequest,
    service: AutenticacaoService = Depends(get_autenticacao_service),
) -> AuthLoginResponse:
    """Autentica Usuario ativo no Tenant identificado (FEATURE-009)."""
    resultado = service.login(
        identificador_institucional=payload.identificador_institucional,
        email=payload.email,
        segredo=payload.segredo,
    )
    return AuthLoginResponse(
        usuario_id=resultado.usuario_id,
        tenant_id=resultado.tenant_id,
        access_token=resultado.access_token,
        access_token_expira_em=resultado.access_token_expira_em,
        refresh_token=resultado.refresh_token,
        refresh_token_expira_em=resultado.refresh_token_expira_em,
    )


@router.post(
    "/refresh",
    response_model=AuthRefreshResponse,
    summary="Renovar access token por refresh token",
)
def refresh(
    payload: AuthRefreshRequest,
    service: AutenticacaoService = Depends(get_autenticacao_service),
) -> AuthRefreshResponse:
    """Renova access token sem nova credencial (US-029)."""
    resultado = service.refresh(refresh_token=payload.refresh_token)
    return AuthRefreshResponse(
        usuario_id=resultado.usuario_id,
        tenant_id=resultado.tenant_id,
        access_token=resultado.access_token,
        access_token_expira_em=resultado.access_token_expira_em,
    )


@router.post(
    "/logout",
    response_model=AuthLogoutResponse,
    summary="Encerrar sessao revogando refresh token",
)
def logout(
    payload: AuthRefreshRequest,
    service: AutenticacaoService = Depends(get_autenticacao_service),
) -> AuthLogoutResponse:
    """Revoga refresh token da sessao atual (US-030)."""
    service.logout(refresh_token=payload.refresh_token)
    return AuthLogoutResponse(status="ok")
