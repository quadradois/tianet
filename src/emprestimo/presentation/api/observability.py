"""Observabilidade HTTP: correlation ID, logs estruturados e mascaramento."""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

CORRELATION_ID_HEADER = "X-Correlation-ID"
CORRELATION_ID_STATE_KEY = "correlation_id"
_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/=@+-]{0,127}$")
_MASK = "***"
_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "database_url",
    "documento",
    "dsn",
    "jwt",
    "password",
    "secret",
    "senha",
    "token",
}


def install_observability(app: FastAPI) -> None:
    """Instala middleware transversal de correlation ID e erro tecnico seguro."""

    logger = logging.getLogger("emprestimo.observability")

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next: Any) -> Any:
        correlation_id = resolve_correlation_id(request.headers.get(CORRELATION_ID_HEADER))
        request.state.correlation_id = correlation_id
        try:
            response = await call_next(request)
        except Exception as exc:
            registrar_erro_tecnico(logger, request, exc)
            response = JSONResponse(
                status_code=500,
                content={"codigo": "erro_interno", "mensagem": "erro inesperado no servidor"},
            )
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        logger.info(
            "http_request_completed",
            extra={
                "correlation_id": correlation_id,
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
            },
        )
        return response


def resolve_correlation_id(value: str | None) -> str:
    """Aceita correlation ID valido ou gera UUID quando ausente/invalido."""
    if value is not None and _CORRELATION_ID_PATTERN.fullmatch(value.strip()):
        return value.strip()
    return str(uuid.uuid4())


def get_correlation_id(request: Request) -> str:
    value = getattr(request.state, CORRELATION_ID_STATE_KEY, None)
    return value if isinstance(value, str) else resolve_correlation_id(None)


def mask_sensitive(value: Any) -> Any:
    """Mascara campos sensiveis em estruturas de log."""
    if isinstance(value, Mapping):
        return {
            key: _MASK if _is_sensitive_key(str(key)) else mask_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(mask_sensitive(item) for item in value)
    return value


def registrar_erro_tecnico(logger: logging.Logger, request: Request, exc: Exception) -> None:
    """Registra erro inesperado sem serializar payload, token, stack trace ou DSN."""
    logger.error(
        "http_unexpected_error",
        extra={
            "correlation_id": get_correlation_id(request),
            "http_method": request.method,
            "http_path": request.url.path,
            "error_type": type(exc).__name__,
        },
    )


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEYS)
