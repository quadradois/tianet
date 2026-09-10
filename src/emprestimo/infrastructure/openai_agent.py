"""Cliente da API para o serviço agent por HTTP sobre socket Unix."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import httpx

from emprestimo.application.openai_conexao import (
    DiagnosticStatus,
    OpenAIAgentProtocolError,
    OpenAIAgentUnavailableError,
    OpenAIConnectionSnapshot,
    OpenAIDeviceChallenge,
    OpenAIDiagnostic,
    OpenAILogoutResult,
    OpenAIModel,
    OpenAIRateLimit,
    OpenAIRateWindow,
    OpenAIState,
    OpenAIUsageSummary,
)

MAX_RESPONSE_BYTES = 1024 * 1024
ALLOWED_STATES = frozenset(
    {
        "DESABILITADO",
        "INDISPONIVEL",
        "DESCONECTADO",
        "AGUARDANDO_USUARIO",
        "CONECTADO",
        "LIMITE_ATINGIDO",
        "ERRO",
        "ERRO_RESULTADO_DESCONHECIDO",
    }
)


class OpenAIAgentClient:
    def __init__(
        self,
        socket_path: Path,
        internal_secret: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not socket_path.is_absolute():
            raise RuntimeError("socket do agent deve ser absoluto")
        if len(internal_secret) < 32:
            raise RuntimeError("TIANET_AGENT_INTERNAL_SECRET deve ter ao menos 32 caracteres")
        self._client = httpx.AsyncClient(
            transport=transport or httpx.AsyncHTTPTransport(uds=str(socket_path), retries=0),
            base_url="http://agent",
            timeout=httpx.Timeout(15.0),
            limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
            headers={"X-TiaNet-Agent-Secret": internal_secret},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def connection(self) -> OpenAIConnectionSnapshot:
        data = await self._request("GET", "/internal/openai/conexao")
        _exact(
            data,
            {
                "enabled",
                "processAvailable",
                "accountConnected",
                "planType",
                "startupError",
                "state",
                "usageSummary",
            },
        )
        usage_summary = _usage_summary(data.get("usageSummary"))
        return OpenAIConnectionSnapshot(
            enabled=_bool(data.get("enabled"), "enabled"),
            process_available=_bool(data.get("processAvailable"), "processAvailable"),
            account_connected=_bool(data.get("accountConnected"), "accountConnected"),
            plan_type=_nullable_text(data.get("planType"), "planType"),
            state=_state(data.get("state")),
            usage_summary=usage_summary,
        )

    async def diagnostic(self) -> OpenAIDiagnostic:
        data = await self._request("GET", "/internal/openai/diagnostico")
        _exact(data, {"state", "observedAt", "account", "models", "rateLimits"})
        account = _object(data.get("account"), "account")
        account_status = _status(account.get("status"), "account.status")
        _exact(
            account, {"status", "connected", "planType"} if account_status == "ok" else {"status"}
        )
        models = _object(data.get("models"), "models")
        models_status = _status(models.get("status"), "models.status")
        _exact(models, {"status", "items"})
        limits = _object(data.get("rateLimits"), "rateLimits")
        limits_status = _status(limits.get("status"), "rateLimits.status")
        _exact(limits, {"status", "items"})
        return OpenAIDiagnostic(
            state=_state(data.get("state")),
            observed_at=_datetime(data.get("observedAt"), "observedAt"),
            account_status=account_status,
            account_connected=(
                _bool(account.get("connected"), "account.connected")
                if account_status == "ok"
                else None
            ),
            plan_type=(
                _nullable_text(account.get("planType"), "account.planType")
                if account_status == "ok"
                else None
            ),
            models_status=models_status,
            models=tuple(_model(item) for item in _list(models.get("items"), "models.items")),
            rate_limits_status=limits_status,
            rate_limits=tuple(
                _rate_limit(item) for item in _list(limits.get("items"), "rateLimits.items")
            ),
        )

    async def begin_login(self) -> OpenAIDeviceChallenge:
        data = await self._request("POST", "/internal/openai/conexao/login")
        _exact(data, {"verificationUrl", "userCode", "expiresAt"})
        verification_url = _text(data.get("verificationUrl"), "verificationUrl")
        parsed = urlparse(verification_url)
        if parsed.scheme != "https" or parsed.hostname != "auth.openai.com":
            raise OpenAIAgentProtocolError("host de verificacao nao permitido")
        return OpenAIDeviceChallenge(
            verification_url=verification_url,
            user_code=_text(data.get("userCode"), "userCode"),
            expires_at=_datetime(data.get("expiresAt"), "expiresAt"),
        )

    async def logout(self) -> OpenAILogoutResult:
        data = await self._request("DELETE", "/internal/openai/conexao")
        _exact(data, {"state", "localLogout", "remoteRevocationVerified"})
        return OpenAILogoutResult(
            state=_state(data.get("state")),
            local_logout=_bool(data.get("localLogout"), "localLogout"),
            remote_revocation_verified=_bool(
                data.get("remoteRevocationVerified"), "remoteRevocationVerified"
            ),
        )

    async def _request(self, method: str, path: str) -> dict[str, Any]:
        try:
            async with self._client.stream(method, path) as response:
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise OpenAIAgentProtocolError("resposta interna excedeu o limite")
                status_code = response.status_code
        except OpenAIAgentProtocolError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise OpenAIAgentUnavailableError("servico agent indisponivel") from exc
        if status_code == 503:
            raise OpenAIAgentUnavailableError("Codex App Server indisponivel")
        if status_code != 200:
            raise OpenAIAgentProtocolError("servico agent recusou a operacao")
        try:
            decoded = httpx.Response(200, content=bytes(body)).json()
        except ValueError as exc:
            raise OpenAIAgentProtocolError("JSON interno invalido") from exc
        return _object(decoded, "response")


class DisabledOpenAIAgentClient:
    """Estado explícito quando a feature flag está desligada."""

    async def connection(self) -> OpenAIConnectionSnapshot:
        return OpenAIConnectionSnapshot(
            enabled=False,
            process_available=False,
            account_connected=False,
            plan_type=None,
            state="DESABILITADO",
            usage_summary=None,
        )

    async def diagnostic(self) -> OpenAIDiagnostic:
        raise OpenAIAgentUnavailableError("integracao OpenAI desabilitada")

    async def begin_login(self) -> OpenAIDeviceChallenge:
        raise OpenAIAgentUnavailableError("integracao OpenAI desabilitada")

    async def logout(self) -> OpenAILogoutResult:
        raise OpenAIAgentUnavailableError("integracao OpenAI desabilitada")


def _object(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise OpenAIAgentProtocolError(f"{field} invalido")
    return value


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise OpenAIAgentProtocolError(f"{field} invalido")
    return value


def _exact(value: dict[str, Any], allowed: set[str]) -> None:
    if set(value) != allowed:
        raise OpenAIAgentProtocolError("campos internos invalidos")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise OpenAIAgentProtocolError(f"{field} invalido")
    return value


def _nullable_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise OpenAIAgentProtocolError(f"{field} invalido")
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OpenAIAgentProtocolError(f"{field} invalido")
    return value


def _nullable_integer(value: object, field: str) -> int | None:
    if value is None:
        return None
    return _integer(value, field)


def _datetime(value: object, field: str) -> datetime:
    text = _text(value, field)
    try:
        result = datetime.fromisoformat(text)
    except ValueError as exc:
        raise OpenAIAgentProtocolError(f"{field} invalido") from exc
    if result.tzinfo is None:
        raise OpenAIAgentProtocolError(f"{field} sem timezone")
    return result


def _state(value: object) -> OpenAIState:
    state = _text(value, "state")
    if state not in ALLOWED_STATES:
        raise OpenAIAgentProtocolError("state invalido")
    return cast(OpenAIState, state)


def _status(value: object, field: str) -> DiagnosticStatus:
    result = _text(value, field)
    if result not in {"ok", "error"}:
        raise OpenAIAgentProtocolError(f"{field} invalido")
    return cast(DiagnosticStatus, result)


def _model(value: object) -> OpenAIModel:
    data = _object(value, "model")
    _exact(data, {"id", "displayName", "default"})
    return OpenAIModel(
        id=_text(data.get("id"), "model.id"),
        display_name=_text(data.get("displayName"), "model.displayName"),
        default=_bool(data.get("default"), "model.default"),
    )


def _window(value: object, field: str) -> OpenAIRateWindow | None:
    if value is None:
        return None
    data = _object(value, field)
    _exact(data, {"usedPercent", "windowDurationMinutes", "resetsAt"})
    used_percent = _integer(data.get("usedPercent"), f"{field}.usedPercent")
    if not 0 <= used_percent <= 100:
        raise OpenAIAgentProtocolError(f"{field}.usedPercent invalido")
    return OpenAIRateWindow(
        used_percent=used_percent,
        window_duration_minutes=_nullable_integer(
            data.get("windowDurationMinutes"), f"{field}.windowDurationMinutes"
        ),
        resets_at=_nullable_integer(data.get("resetsAt"), f"{field}.resetsAt"),
    )


def _rate_limit(value: object) -> OpenAIRateLimit:
    data = _object(value, "rateLimit")
    _exact(data, {"limitId", "planType", "primary", "secondary"})
    return OpenAIRateLimit(
        limit_id=_nullable_text(data.get("limitId"), "rateLimit.limitId"),
        plan_type=_nullable_text(data.get("planType"), "rateLimit.planType"),
        primary=_window(data.get("primary"), "rateLimit.primary"),
        secondary=_window(data.get("secondary"), "rateLimit.secondary"),
    )


def _usage_summary(value: object) -> OpenAIUsageSummary | None:
    if value is None:
        return None
    data = _object(value, "usageSummary")
    _exact(data, {"observedAt", "rateLimitsStatus", "rateLimits"})
    return OpenAIUsageSummary(
        observed_at=_datetime(data.get("observedAt"), "usageSummary.observedAt"),
        rate_limits_status=_status(data.get("rateLimitsStatus"), "usageSummary.rateLimitsStatus"),
        rate_limits=tuple(
            _rate_limit(item) for item in _list(data.get("rateLimits"), "usageSummary.rateLimits")
        ),
    )
