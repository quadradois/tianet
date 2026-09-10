"""Serviço privado do processo agent, limitado à conexão OpenAI/Codex."""

from __future__ import annotations

import asyncio
import hmac
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol, TypeVar

from fastapi import FastAPI, Header, HTTPException, Response, status

from emprestimo.agent.codex_app_server import (
    AccountInfo,
    CodexAppServerClient,
    CodexRequestTimeoutError,
    DeviceCodeChallenge,
    LoginCompletedNotification,
    ModelInfo,
    RateLimitInfo,
    RateLimitWindow,
)

LOGIN_TTL_SECONDS = 10 * 60
DIAGNOSTIC_TTL_SECONDS = 60
MAX_MODEL_PAGES = 20
MUTATION_BUDGET_SECONDS = 8
DIAGNOSTIC_BUDGET_SECONDS = 12
RECOVERY_BUDGET_SECONDS = 4


class AccountClient(Protocol):
    @property
    def available(self) -> bool: ...

    async def read_account(self) -> AccountInfo: ...

    async def start_device_login(self) -> DeviceCodeChallenge: ...

    async def cancel_login(self, login_id: str) -> bool: ...

    async def list_models(
        self, cursor: str | None = None
    ) -> tuple[tuple[ModelInfo, ...], str | None]: ...

    async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]: ...

    async def logout(self) -> None: ...

    async def next_notification(self, timeout_seconds: float | None = None) -> object: ...

    async def close(self) -> None: ...


ClientStarter = Callable[..., Awaitable[AccountClient]]
MutationResult = TypeVar("MutationResult")


@dataclass(frozen=True)
class AgentSettings:
    enabled: bool
    internal_secret: str
    codex_executable: Path
    codex_home: Path
    runtime_directory: Path
    codex_user_agent_identity: str

    @classmethod
    def from_environment(cls) -> AgentSettings:
        secret = os.environ.get("TIANET_AGENT_INTERNAL_SECRET", "")
        enabled = os.environ.get("TIANET_AGENT_ENABLED", "false").lower() == "true"
        if enabled and len(secret) < 32:
            raise RuntimeError("TIANET_AGENT_INTERNAL_SECRET deve ter ao menos 32 caracteres")
        return cls(
            enabled=enabled,
            internal_secret=secret,
            codex_executable=Path(os.environ.get("CODEX_EXECUTABLE", "/usr/local/bin/codex")),
            codex_home=Path(os.environ.get("CODEX_HOME", "/var/lib/tianet-agent/codex")),
            runtime_directory=Path(os.environ.get("TIANET_AGENT_RUNTIME", "/tmp/tianet-agent")),
            codex_user_agent_identity=os.environ.get(
                "CODEX_USER_AGENT_IDENTITY", "tianet-agent-auth/0.146.1"
            ),
        )


@dataclass(frozen=True)
class _ActiveChallenge:
    challenge: DeviceCodeChallenge
    expires_monotonic: float
    expires_at: datetime
    generation: int


class AgentUnavailableError(RuntimeError):
    """O processo App Server não pode atender a operação."""


class AgentRuntime:
    """Estado local single-tenant; nenhum token sai do cliente App Server."""

    def __init__(self, settings: AgentSettings, client_starter: ClientStarter) -> None:
        self.settings = settings
        self._client_starter = client_starter
        self.client: AccountClient | None = None
        self.process_available = False
        self.account_connected = False
        self.plan_type: str | None = None
        self.startup_error = False
        self.state = "INDISPONIVEL" if settings.enabled else "DESABILITADO"
        self._mutation_lock = asyncio.Lock()
        self._diagnostic_lock = asyncio.Lock()
        self._generation = 0
        self._challenge: _ActiveChallenge | None = None
        self._login_watcher: asyncio.Task[None] | None = None
        self._diagnostic_task: asyncio.Task[dict[str, object]] | None = None
        self._diagnostic_cache: dict[str, object] | None = None
        self._diagnostic_observed_monotonic = 0.0

    async def start(self) -> None:
        if not self.settings.enabled:
            return
        try:
            await self._start_client()
            account = await self._require_client().read_account()
            self._apply_account(account)
        except Exception:
            await self._mark_unavailable()

    async def close(self) -> None:
        self._generation += 1
        if self._login_watcher is not None:
            self._login_watcher.cancel()
            await asyncio.gather(self._login_watcher, return_exceptions=True)
            self._login_watcher = None
        if self.client is not None:
            await self.client.close()
            self.client = None
        self.process_available = False

    def refresh_local_state(self) -> None:
        if self.client is not None and self.process_available and not self.client.available:
            self._advance_generation()
            self.process_available = False
            self.account_connected = False
            self.plan_type = None
            self.startup_error = True
            self.state = "INDISPONIVEL"

    def snapshot(self) -> dict[str, object]:
        self.refresh_local_state()
        usage_summary: dict[str, object] | None = None
        if self._diagnostic_cache is not None:
            limits = self._diagnostic_cache["rateLimits"]
            if isinstance(limits, dict):
                usage_summary = {
                    "observedAt": self._diagnostic_cache["observedAt"],
                    "rateLimitsStatus": limits["status"],
                    "rateLimits": limits["items"],
                }
        return {
            "enabled": self.settings.enabled,
            "processAvailable": self.process_available,
            "accountConnected": self.account_connected,
            "planType": self.plan_type,
            "startupError": self.startup_error,
            "state": self.state,
            "usageSummary": usage_summary,
        }

    async def begin_login(self) -> dict[str, str]:
        return await self._run_mutation(self._begin_login_locked)

    async def _begin_login_locked(self) -> dict[str, str]:
        client = self._require_client()
        now = time.monotonic()
        if self._challenge is not None and self._challenge.expires_monotonic > now:
            return self._challenge_response(self._challenge)
        if self._challenge is not None:
            try:
                await client.cancel_login(self._challenge.challenge.login_id)
            except Exception as exc:
                self.state = "ERRO_RESULTADO_DESCONHECIDO"
                self._clear_challenge()
                await self._reconcile_after_uncertain_result()
                raise AgentUnavailableError(
                    "cancelamento do login expirado nao foi confirmado"
                ) from exc
            self._clear_challenge()

        self._advance_generation()
        generation = self._generation
        try:
            challenge = await client.start_device_login()
        except Exception:
            self.state = "ERRO_RESULTADO_DESCONHECIDO"
            await self._reconcile_after_uncertain_result()
            raise
        active = _ActiveChallenge(
            challenge=challenge,
            expires_monotonic=now + LOGIN_TTL_SECONDS,
            expires_at=datetime.now(UTC) + timedelta(seconds=LOGIN_TTL_SECONDS),
            generation=generation,
        )
        self._challenge = active
        self.state = "AGUARDANDO_USUARIO"
        self._diagnostic_cache = None
        self._login_watcher = asyncio.create_task(self._watch_login(active))
        return self._challenge_response(active)

    async def diagnose(self) -> dict[str, object]:
        deadline = asyncio.get_running_loop().time() + DIAGNOSTIC_BUDGET_SECONDS
        task: asyncio.Task[dict[str, object]] | None = None
        try:
            async with asyncio.timeout_at(deadline):
                async with self._mutation_lock:
                    self._require_client()
                    generation = self._generation
                async with self._diagnostic_lock:
                    age = time.monotonic() - self._diagnostic_observed_monotonic
                    if self._diagnostic_cache is not None and age < DIAGNOSTIC_TTL_SECONDS:
                        return self._diagnostic_cache
                    task = self._diagnostic_task
                    if task is None or task.done():
                        task = asyncio.create_task(self._collect_diagnostic_bounded(generation))
                        task.add_done_callback(self._consume_diagnostic_result)
                        self._diagnostic_task = task
                return await asyncio.shield(task)
        finally:
            if task is not None and task.done():
                async with self._diagnostic_lock:
                    if self._diagnostic_task is task:
                        self._diagnostic_task = None

    async def _collect_diagnostic_bounded(self, generation: int) -> dict[str, object]:
        async with asyncio.timeout(DIAGNOSTIC_BUDGET_SECONDS):
            return await self._collect_diagnostic(generation)

    @staticmethod
    def _consume_diagnostic_result(task: asyncio.Task[dict[str, object]]) -> None:
        if not task.cancelled():
            task.exception()

    async def logout(self) -> dict[str, object]:
        return await self._run_mutation(self._logout_locked)

    async def _logout_locked(self) -> dict[str, object]:
        client = self._require_client()
        self._advance_generation()
        had_challenge = self._challenge is not None
        if self._login_watcher is not None:
            self._login_watcher.cancel()
            await asyncio.gather(self._login_watcher, return_exceptions=True)
            self._login_watcher = None
        if self._challenge is not None:
            with suppress(Exception):
                await client.cancel_login(self._challenge.challenge.login_id)
            self._clear_challenge()
        try:
            if had_challenge:
                await self._restart_client()
                client = self._require_client()
            await client.logout()
            account = await client.read_account()
        except Exception:
            self.state = "ERRO_RESULTADO_DESCONHECIDO"
            await self._reconcile_after_uncertain_result()
            raise
        if account.authenticated:
            self.state = "ERRO_RESULTADO_DESCONHECIDO"
            await self._reconcile_after_uncertain_result()
            raise AgentUnavailableError("logout local nao foi confirmado")
        self._apply_account(account)
        return {
            "state": self.state,
            "localLogout": True,
            "remoteRevocationVerified": False,
        }

    async def _start_client(self) -> None:
        self.client = await self._client_starter(
            (str(self.settings.codex_executable), "app-server"),
            codex_home=self.settings.codex_home,
            working_directory=self.settings.runtime_directory,
            expected_user_agent_identity=self.settings.codex_user_agent_identity,
        )
        self.process_available = True
        self.startup_error = False

    async def _restart_client(self) -> None:
        if self.client is not None:
            await self.client.close()
            self.client = None
        self.process_available = False
        await self._start_client()

    def _require_client(self) -> AccountClient:
        self.refresh_local_state()
        if not self.settings.enabled or not self.process_available or self.client is None:
            raise AgentUnavailableError("Codex App Server indisponivel")
        return self.client

    def _apply_account(self, account: AccountInfo) -> None:
        self.process_available = True
        self.account_connected = account.authenticated
        self.plan_type = account.plan_type
        self.state = "CONECTADO" if account.authenticated else "DESCONECTADO"
        self._diagnostic_cache = None

    def _advance_generation(self) -> None:
        self._generation += 1
        self._diagnostic_cache = None

    async def _mark_unavailable(self) -> None:
        self.startup_error = True
        if self.client is not None:
            await self.client.close()
            self.client = None
        self.process_available = False
        self.account_connected = False
        self.plan_type = None
        self.state = "INDISPONIVEL"

    def _clear_challenge(self) -> None:
        self._challenge = None
        self._login_watcher = None

    @staticmethod
    def _challenge_response(active: _ActiveChallenge) -> dict[str, str]:
        return {
            "verificationUrl": active.challenge.verification_url,
            "userCode": active.challenge.user_code,
            "expiresAt": active.expires_at.isoformat(),
        }

    async def _watch_login(self, active: _ActiveChallenge) -> None:
        try:
            while True:
                remaining = max(0.0, active.expires_monotonic - time.monotonic())
                try:
                    notification = await self._require_client().next_notification(remaining)
                except (TimeoutError, CodexRequestTimeoutError):
                    await self._expire_login(active)
                    return
                if not isinstance(notification, LoginCompletedNotification):
                    continue
                if notification.login_id not in {None, active.challenge.login_id}:
                    continue
                break
            async with self._mutation_lock:
                if self._generation != active.generation or self._challenge is not active:
                    return
                if not notification.success or notification.error_present:
                    self._advance_generation()
                    self.state = "ERRO"
                    self._clear_challenge()
                    return
                try:
                    account = await self._require_client().read_account()
                except Exception:
                    self._advance_generation()
                    self.state = "ERRO_RESULTADO_DESCONHECIDO"
                    self._clear_challenge()
                    await self._reconcile_after_uncertain_result()
                    return
                self._advance_generation()
                self._apply_account(account)
                self._clear_challenge()
        except asyncio.CancelledError:
            raise
        except Exception:
            if self._generation == active.generation and self._challenge is active:
                self._advance_generation()
                self.state = "ERRO"
                self._clear_challenge()

    async def _expire_login(self, active: _ActiveChallenge) -> None:
        async with self._mutation_lock:
            if self._generation != active.generation or self._challenge is not active:
                return
            client = self._require_client()
            self._advance_generation()
            try:
                await client.cancel_login(active.challenge.login_id)
            except Exception:
                self.state = "ERRO_RESULTADO_DESCONHECIDO"
                self._clear_challenge()
                await self._reconcile_after_uncertain_result()
                return
            self._clear_challenge()
            try:
                self._apply_account(await client.read_account())
            except Exception:
                self.state = "ERRO_RESULTADO_DESCONHECIDO"
                await self._reconcile_after_uncertain_result()

    async def _collect_diagnostic(self, generation: int) -> dict[str, object]:
        client = self._require_client()
        observed_at = datetime.now(UTC).isoformat()
        account: AccountInfo | None
        try:
            account = await client.read_account()
            account_section: dict[str, object] = {
                "status": "ok",
                "connected": account.authenticated,
                "planType": account.plan_type,
            }
        except Exception:
            account = None
            account_section = {"status": "error"}

        try:
            models: list[ModelInfo] = []
            cursor: str | None = None
            for _ in range(MAX_MODEL_PAGES):
                page, cursor = await client.list_models(cursor)
                models.extend(page)
                if cursor is None:
                    break
            else:
                raise AgentUnavailableError("paginacao de modelos excedeu o limite")
            models_section: dict[str, object] = {
                "status": "ok",
                "items": [
                    {
                        "id": item.model,
                        "displayName": item.display_name,
                        "default": item.is_default,
                    }
                    for item in models
                    if not item.hidden
                ],
            }
        except Exception:
            models_section = {"status": "error", "items": []}

        try:
            rate_limits = await client.read_rate_limits()
            limits_section: dict[str, object] = {
                "status": "ok",
                "items": [self._rate_limit_json(item) for item in rate_limits],
            }
        except Exception:
            rate_limits = ()
            limits_section = {"status": "error", "items": []}

        result: dict[str, object] = {
            "state": self.state,
            "observedAt": observed_at,
            "account": account_section,
            "models": models_section,
            "rateLimits": limits_section,
        }
        if generation != self._generation:
            raise AgentUnavailableError("diagnostico invalidado por mudanca de estado")
        if account is not None:
            self._apply_account(account)
            if account.authenticated and self._limit_reached(rate_limits):
                self.state = "LIMITE_ATINGIDO"
            result["state"] = self.state
        self._diagnostic_cache = result
        self._diagnostic_observed_monotonic = time.monotonic()
        return result

    @staticmethod
    def _rate_limit_json(item: RateLimitInfo) -> dict[str, object]:
        def window(value: RateLimitWindow | None) -> dict[str, int | None] | None:
            if value is None:
                return None
            return {
                "usedPercent": value.used_percent,
                "windowDurationMinutes": value.window_duration_minutes,
                "resetsAt": value.resets_at,
            }

        return {
            "limitId": item.limit_id,
            "planType": item.plan_type,
            "primary": window(item.primary),
            "secondary": window(item.secondary),
        }

    @staticmethod
    def _limit_reached(items: tuple[RateLimitInfo, ...]) -> bool:
        return any(
            window is not None and window.used_percent >= 100
            for item in items
            for window in (item.primary, item.secondary)
        )

    async def _reconcile_after_uncertain_result(self) -> None:
        try:
            await self._restart_client()
            account = await self._require_client().read_account()
        except Exception:
            await self._mark_unavailable()
            return
        self._apply_account(account)

    async def _run_mutation(
        self, operation: Callable[[], Awaitable[MutationResult]]
    ) -> MutationResult:
        deadline = asyncio.get_running_loop().time() + MUTATION_BUDGET_SECONDS
        try:
            async with asyncio.timeout_at(deadline):
                await self._mutation_lock.acquire()
        except TimeoutError as exc:
            raise AgentUnavailableError("outra mutacao ainda esta em andamento") from exc
        try:
            try:
                async with asyncio.timeout_at(deadline):
                    return await operation()
            except TimeoutError as exc:
                await self._recover_locked()
                raise AgentUnavailableError("mutacao excedeu o tempo limite") from exc
            except asyncio.CancelledError:
                await self._recover_locked()
                raise
        finally:
            self._mutation_lock.release()

    async def _recover_locked(self) -> None:
        self._advance_generation()
        if self._login_watcher is not None:
            self._login_watcher.cancel()
            await asyncio.gather(self._login_watcher, return_exceptions=True)
        self._clear_challenge()
        try:
            async with asyncio.timeout(RECOVERY_BUDGET_SECONDS):
                await self._reconcile_after_uncertain_result()
            return
        except TimeoutError:
            pass
        client = self.client
        if client is not None:
            await client.close()
            if client.available:
                raise AgentUnavailableError("processo Codex nao encerrou")
        self.client = None
        self.process_available = False
        self.account_connected = False
        self.plan_type = None
        self.startup_error = True
        self.state = "INDISPONIVEL"


def create_agent_app(
    settings: AgentSettings | None = None,
    client_starter: ClientStarter = CodexAppServerClient.start,
) -> FastAPI:
    configured = settings or AgentSettings.from_environment()
    runtime = AgentRuntime(configured, client_starter)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await runtime.start()
        yield
        await runtime.close()

    app = FastAPI(
        title="TiaNet Agent interno",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.agent_runtime = runtime

    def authorize(internal_secret: str | None) -> None:
        if (
            len(configured.internal_secret) < 32
            or internal_secret is None
            or not hmac.compare_digest(internal_secret, configured.internal_secret)
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    @app.get("/health")
    async def health(response: Response) -> dict[str, bool | str]:
        runtime.refresh_local_state()
        healthy = not configured.enabled or runtime.process_available
        if not healthy:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "ready" if healthy else "degraded",
            "enabled": configured.enabled,
            "processAvailable": runtime.process_available,
            "accountConnected": runtime.account_connected,
        }

    @app.get("/internal/openai/conexao")
    async def connection_snapshot(
        internal_secret: str | None = Header(default=None, alias="X-TiaNet-Agent-Secret"),
    ) -> dict[str, object]:
        authorize(internal_secret)
        return runtime.snapshot()

    @app.get("/internal/openai/diagnostico")
    async def diagnostic(
        internal_secret: str | None = Header(default=None, alias="X-TiaNet-Agent-Secret"),
    ) -> dict[str, object]:
        authorize(internal_secret)
        try:
            return await runtime.diagnose()
        except TimeoutError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from exc
        except AgentUnavailableError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY) from exc

    @app.post("/internal/openai/conexao/login")
    async def begin_login(
        internal_secret: str | None = Header(default=None, alias="X-TiaNet-Agent-Secret"),
    ) -> dict[str, str]:
        authorize(internal_secret)
        try:
            return await runtime.begin_login()
        except AgentUnavailableError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY) from exc

    @app.delete("/internal/openai/conexao")
    async def logout(
        internal_secret: str | None = Header(default=None, alias="X-TiaNet-Agent-Secret"),
    ) -> dict[str, object]:
        authorize(internal_secret)
        try:
            return await runtime.logout()
        except AgentUnavailableError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE) from exc
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY) from exc

    return app
