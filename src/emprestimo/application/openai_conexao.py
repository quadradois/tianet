"""Casos de uso administrativos da conexão OpenAI/Codex."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from emprestimo.application.idempotencia import (
    concluir_idempotencia,
    dataclass_do_resultado,
    iniciar_idempotencia,
    resultado_de_dataclass,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork

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
DiagnosticStatus = Literal["ok", "error"]


class OpenAIAgentUnavailableError(RuntimeError):
    """Canal local ou processo agent indisponível."""


class OpenAIAgentProtocolError(RuntimeError):
    """Resposta interna inválida ou falha upstream sanitizada."""


@dataclass(frozen=True)
class OpenAIConnectionSnapshot:
    enabled: bool
    process_available: bool
    account_connected: bool
    plan_type: str | None
    state: OpenAIState
    usage_summary: OpenAIUsageSummary | None = None


@dataclass(frozen=True)
class OpenAIDeviceChallenge:
    verification_url: str
    user_code: str
    expires_at: datetime


@dataclass(frozen=True)
class OpenAIModel:
    id: str
    display_name: str
    default: bool


@dataclass(frozen=True)
class OpenAIRateWindow:
    used_percent: int
    window_duration_minutes: int | None
    resets_at: int | None


@dataclass(frozen=True)
class OpenAIRateLimit:
    limit_id: str | None
    plan_type: str | None
    primary: OpenAIRateWindow | None
    secondary: OpenAIRateWindow | None


@dataclass(frozen=True)
class OpenAIUsageSummary:
    observed_at: datetime
    rate_limits_status: DiagnosticStatus
    rate_limits: tuple[OpenAIRateLimit, ...]


@dataclass(frozen=True)
class OpenAIDiagnostic:
    state: OpenAIState
    observed_at: datetime
    account_status: DiagnosticStatus
    account_connected: bool | None
    plan_type: str | None
    models_status: DiagnosticStatus
    models: tuple[OpenAIModel, ...]
    rate_limits_status: DiagnosticStatus
    rate_limits: tuple[OpenAIRateLimit, ...]


@dataclass(frozen=True)
class OpenAILogoutResult:
    state: OpenAIState
    local_logout: bool
    remote_revocation_verified: bool


class OpenAIConnectionProvider(Protocol):
    async def connection(self) -> OpenAIConnectionSnapshot: ...

    async def diagnostic(self) -> OpenAIDiagnostic: ...

    async def begin_login(self) -> OpenAIDeviceChallenge: ...

    async def logout(self) -> OpenAILogoutResult: ...


class OpenAIConnectionService:
    def __init__(
        self,
        provider: OpenAIConnectionProvider,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._provider = provider
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    async def connection(self) -> OpenAIConnectionSnapshot:
        return await self._provider.connection()

    async def diagnostic(self) -> OpenAIDiagnostic:
        return await self._provider.diagnostic()

    async def begin_login(
        self, tenant_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> OpenAIDeviceChallenge:
        self._audit("login.inicio", "iniciado", tenant_id, usuario_id)
        try:
            challenge = await self._provider.begin_login()
        except Exception as exc:
            self._audit(
                "login.falha", "falhou", tenant_id, usuario_id, error_type=type(exc).__name__
            )
            raise
        self._audit("login.sucesso", "ok", tenant_id, usuario_id)
        return challenge

    async def logout(
        self,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        *,
        idempotency_key: str,
    ) -> OpenAILogoutResult:
        with self._uow_factory() as uow:
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo="openai-conexao-logout",
                solicitacao={"tenant_id": tenant_id},
            )
            if replay is not None:
                return dataclass_do_resultado(replay, OpenAILogoutResult, chave=idempotency_key)
            self._audit("logout.inicio", "iniciado", tenant_id, usuario_id)
            try:
                result = await self._provider.logout()
                concluir_idempotencia(
                    uow,
                    chave=idempotency_key,
                    escopo="openai-conexao-logout",
                    resultado=resultado_de_dataclass(result),
                )
                uow.commit()
            except Exception as exc:
                self._audit(
                    "logout.falha",
                    "falhou",
                    tenant_id,
                    usuario_id,
                    error_type=type(exc).__name__,
                )
                raise
            self._audit("logout.sucesso", "ok", tenant_id, usuario_id)
            return result

    def _audit(
        self,
        action: str,
        status: str,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        *,
        error_type: str | None = None,
    ) -> None:
        details = {"tenant_id": str(tenant_id), "usuario_id": str(usuario_id)}
        if error_type is not None:
            details["erro_tipo"] = error_type
        self._auditoria.registrar(
            "openai_conexao",
            tenant_id,
            action,
            status,
            detalhes=json.dumps(details, sort_keys=True),
        )
