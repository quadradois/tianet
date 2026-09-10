"""Schemas públicos da conexão administrativa OpenAI/Codex."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OpenAIState = Literal[
    "DESABILITADO",
    "INDISPONIVEL",
    "DESCONECTADO",
    "AGUARDANDO_USUARIO",
    "CONECTADO",
    "LIMITE_ATINGIDO",
    "ERRO",
    "ERRO_RESULTADO_DESCONHECIDO",
]


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class OpenAIDeviceChallengeResponse(_ClosedModel):
    verification_url: str = Field(alias="verificationUrl")
    user_code: str = Field(alias="userCode")
    expires_at: datetime = Field(alias="expiresAt")


class OpenAIModelResponse(_ClosedModel):
    id: str
    display_name: str = Field(alias="displayName")
    default: bool


class OpenAIRateWindowResponse(_ClosedModel):
    used_percent: int = Field(alias="usedPercent", ge=0, le=100)
    window_duration_minutes: int | None = Field(alias="windowDurationMinutes")
    resets_at: int | None = Field(alias="resetsAt")


class OpenAIRateLimitResponse(_ClosedModel):
    limit_id: str | None = Field(alias="limitId")
    plan_type: str | None = Field(alias="planType")
    primary: OpenAIRateWindowResponse | None
    secondary: OpenAIRateWindowResponse | None


class OpenAIUsageSummaryResponse(_ClosedModel):
    observed_at: datetime = Field(alias="observedAt")
    rate_limits_status: Literal["ok", "error"] = Field(alias="rateLimitsStatus")
    rate_limits: list[OpenAIRateLimitResponse] = Field(alias="rateLimits")


class OpenAIConnectionResponse(_ClosedModel):
    enabled: bool
    process_available: bool = Field(alias="processAvailable")
    account_connected: bool = Field(alias="accountConnected")
    plan_type: str | None = Field(alias="planType")
    state: OpenAIState
    usage_summary: OpenAIUsageSummaryResponse | None = Field(alias="usageSummary")


class OpenAIDiagnosticResponse(_ClosedModel):
    state: OpenAIState
    observed_at: datetime = Field(alias="observedAt")
    account_status: Literal["ok", "error"] = Field(alias="accountStatus")
    account_connected: bool | None = Field(alias="accountConnected")
    plan_type: str | None = Field(alias="planType")
    models_status: Literal["ok", "error"] = Field(alias="modelsStatus")
    models: list[OpenAIModelResponse]
    rate_limits_status: Literal["ok", "error"] = Field(alias="rateLimitsStatus")
    rate_limits: list[OpenAIRateLimitResponse] = Field(alias="rateLimits")


class OpenAILogoutResponse(_ClosedModel):
    state: OpenAIState
    local_logout: bool = Field(alias="localLogout")
    remote_revocation_verified: bool = Field(alias="remoteRevocationVerified")
