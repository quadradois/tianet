"""Cliente HTTP autenticado para a API TiaNet (IMP-356-D, rota A).

Um único `httpx` assíncrono, sem SDK de provedor: fala com a API do produto,
nunca com provedor de IA. Autorização é aplicada pela API via bearer do
Principal copilot — 401/403 viram falha fechada, nunca tentativa
alternativa. Timeout individual por tentativa; deadline global pertence ao
executor (356-F).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol

import httpx


class ApiError(Exception):
    """Falha de transporte, contrato ou autorização — sempre fechada."""


class ApiAutorizacaoError(ApiError):
    """401/403: identidade revogada ou sem permissão. Encerra, sem loop."""


class ApiAusenciaError(ApiError):
    """404 neutro: ausência, nunca saldo zero nem total inferido."""


class ProtocoloClienteApi(Protocol):
    """Borda que o dispatcher enxerga: um GET autenticado, nada mais."""

    async def get(
        self,
        caminho: str,
        params: Mapping[str, str | int] | None = None,
        timeout_segundos: float | None = None,
    ) -> dict[str, Any]: ...


class ClienteApi:
    def __init__(
        self,
        base_url: str,
        provedor_token: Callable[[], str],
        timeout_segundos: float = 5.0,
        transporte: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_segundos),
            transport=transporte,
        )
        self._provedor_token = provedor_token

    async def get(
        self,
        caminho: str,
        params: Mapping[str, str | int] | None = None,
        timeout_segundos: float | None = None,
    ) -> dict[str, Any]:
        if not caminho.startswith("/"):
            raise ApiError("caminho interno deve ser absoluto")
        timeout = httpx.Timeout(timeout_segundos) if timeout_segundos is not None else None
        try:
            resposta = await self._client.get(
                caminho,
                params=dict(params or {}),
                headers={"Authorization": f"Bearer {self._provedor_token()}"},
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise ApiError("tempo esgotado na API") from exc
        except httpx.HTTPError as exc:
            raise ApiError("falha de transporte na API") from exc
        if resposta.status_code in (401, 403):
            raise ApiAutorizacaoError("acesso recusado pela API")
        if resposta.status_code == 404:
            raise ApiAusenciaError("recurso ausente")
        if not 200 <= resposta.status_code < 300:
            raise ApiError(f"API respondeu {resposta.status_code}")
        try:
            corpo = resposta.json()
        except ValueError as exc:
            raise ApiError("resposta invalida da API") from exc
        if not isinstance(corpo, dict):
            raise ApiError("resposta invalida da API")
        return corpo

    async def close(self) -> None:
        await self._client.aclose()
