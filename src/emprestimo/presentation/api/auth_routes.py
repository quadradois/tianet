"""Rotas de autenticacao IAM (IMP-090)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from emprestimo.application.autenticacao import AutenticacaoService
from emprestimo.application.credenciais import CredenciaisService
from emprestimo.application.errors import AutenticacaoRecusadaError
from emprestimo.presentation.api.dependencies import (
    get_autenticacao_service,
    get_credenciais_service,
)
from emprestimo.presentation.api.openapi import RESPOSTAS_AUTH
from emprestimo.presentation.api.schemas import (
    AtivacaoRequest,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthRefreshRequest,
    AuthRefreshResponse,
    CredencialResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"], responses=RESPOSTAS_AUTH)


@router.post("/ativar", response_model=CredencialResponse)
def ativar(
    payload: AtivacaoRequest,
    service: CredenciaisService = Depends(get_credenciais_service),
) -> CredencialResponse:
    resultado = service.ativar_com_token(
        token=payload.token_ativacao,
        segredo=payload.segredo,
    )
    return CredencialResponse(
        usuario_id=resultado.usuario_id,
        tenant_id=resultado.tenant_id,
        estado=resultado.estado,
    )


@router.post(
    "/login",
    response_model=AuthLoginResponse,
    summary="Autenticar usuario e emitir tokens",
)
def login(
    payload: Any = Body(default=None),
    service: AutenticacaoService = Depends(get_autenticacao_service),
) -> AuthLoginResponse:
    """Autentica Usuario ativo no Tenant identificado (FEATURE-009)."""
    request = _parse_login(payload)
    resultado = service.login(
        identificador_institucional=request.identificador_institucional,
        email=request.email,
        segredo=request.segredo,
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
    payload: Any = Body(default=None),
    service: AutenticacaoService = Depends(get_autenticacao_service),
) -> AuthRefreshResponse:
    """Renova access token sem nova credencial (US-029)."""
    request = _parse_refresh(payload)
    resultado = service.refresh(refresh_token=request.refresh_token)
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
    payload: Any = Body(default=None),
    service: AutenticacaoService = Depends(get_autenticacao_service),
) -> AuthLogoutResponse:
    """Revoga refresh token da sessao atual (US-030)."""
    request = _parse_refresh(payload)
    service.logout(refresh_token=request.refresh_token)
    return AuthLogoutResponse(status="ok")


def _parse_login(payload: Any) -> AuthLoginRequest:
    if not isinstance(payload, dict):
        raise AutenticacaoRecusadaError()
    identificador_institucional = payload.get("identificador_institucional")
    email = payload.get("email")
    segredo = payload.get("segredo")
    if (
        not isinstance(identificador_institucional, str)
        or not isinstance(email, str)
        or not isinstance(segredo, str)
    ):
        raise AutenticacaoRecusadaError()
    try:
        return AuthLoginRequest(
            identificador_institucional=identificador_institucional,
            email=email,
            segredo=segredo,
        )
    except ValueError:
        raise AutenticacaoRecusadaError() from None


def _parse_refresh(payload: Any) -> AuthRefreshRequest:
    if not isinstance(payload, dict):
        raise AutenticacaoRecusadaError()
    refresh_token = payload.get("refresh_token")
    if not isinstance(refresh_token, str):
        raise AutenticacaoRecusadaError()
    try:
        return AuthRefreshRequest(refresh_token=refresh_token)
    except ValueError:
        raise AutenticacaoRecusadaError() from None
