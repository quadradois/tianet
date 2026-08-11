"""Rotas operacionais publicas de observabilidade (EPIC-008)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Response

from emprestimo.application.health import HealthService
from emprestimo.presentation.api.dependencies import get_health_service
from emprestimo.presentation.api.observability import CORRELATION_ID_HEADER
from emprestimo.presentation.api.schemas import HealthResponse

router = APIRouter(tags=["operations"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Consultar saude operacional da API",
    responses={
        503: {
            "model": HealthResponse,
            "description": "Dependencia tecnica essencial indisponivel.",
        }
    },
)
def health_operacional(
    response: Response,
    x_correlation_id: str | None = Header(default=None, alias=CORRELATION_ID_HEADER),
    service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    """Healthcheck publico, real e sem dados sensiveis."""
    del x_correlation_id
    report = service.verificar()
    response.status_code = report.http_status
    return HealthResponse(status=report.status, service="api", checks=report.checks)
