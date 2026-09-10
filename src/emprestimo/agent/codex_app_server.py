"""Cliente mínimo e fechado para autenticação no Codex App Server.

O módulo não oferece um método JSON-RPC público genérico. A allowlist contém
apenas conta, catálogo e limites; conversa, shell, filesystem, MCP e tools não
são alcançáveis por esta API (ADR-020, Slice A).
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

MAX_FRAME_BYTES: Final = 1024 * 1024
DEFAULT_TIMEOUT_SECONDS: Final = 15.0
PROCESS_TERMINATE_GRACE_SECONDS: Final = 0.5
PROCESS_KILL_WAIT_SECONDS: Final = 0.5
MAX_NOTIFICATION_QUEUE: Final = 32
CLIENT_NAME: Final = "tianet-agent-auth"
CLIENT_VERSION: Final = "0.1.0"

_ALLOWED_METHODS: Final = frozenset(
    {
        "initialize",
        "account/login/start",
        "account/login/cancel",
        "account/read",
        "model/list",
        "account/rateLimits/read",
        "account/logout",
    }
)
_ALLOWED_NOTIFICATIONS: Final = frozenset(
    {"account/login/completed", "account/rateLimits/updated", "account/updated"}
)
_IGNORED_NOTIFICATIONS: Final = frozenset({"configWarning", "remoteControl/status/changed"})
_BUNDLED_BWRAP_WARNING_PREFIX: Final = "Codex could not find bubblewrap on PATH."
_CHATGPT_PLAN_TYPES: Final = frozenset(
    {
        "free",
        "go",
        "plus",
        "pro",
        "prolite",
        "team",
        "self_serve_business_usage_based",
        "business",
        "ent26",
        "enterprise_cbp_usage_based",
        "enterprise",
        "edu",
        "unknown",
    }
)
_SAFE_ENV_NAMES: Final = (
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
)


class CodexAppServerError(RuntimeError):
    """Falha fechada do protocolo ou processo App Server."""


class CodexMethodDeniedError(CodexAppServerError):
    """Método fora da allowlist administrativa."""


class CodexInvalidMessageError(CodexAppServerError):
    """Mensagem que não satisfaz o contrato JSON-RPC esperado."""


class CodexFrameTooLargeError(CodexAppServerError):
    """Frame excedeu o limite aprovado."""


class CodexProcessExitedError(CodexAppServerError):
    """Processo terminou antes de responder."""


class CodexRequestTimeoutError(CodexAppServerError):
    """Operação não concluiu dentro do orçamento."""

    def __init__(self, operation: str, *, may_have_been_sent: bool) -> None:
        self.operation = operation
        self.may_have_been_sent = may_have_been_sent
        suffix = "resultado incerto" if may_have_been_sent else "nao enviado"
        super().__init__(f"timeout em {operation} ({suffix})")


class CodexRemoteError(CodexAppServerError):
    """App Server devolveu erro JSON-RPC sanitizado."""

    def __init__(self, code: int | None) -> None:
        self.code = code
        super().__init__(f"Codex App Server recusou a operacao (code={code!r})")


@dataclass(frozen=True)
class DeviceCodeChallenge:
    login_id: str
    verification_url: str
    user_code: str


@dataclass(frozen=True)
class AccountInfo:
    authenticated: bool
    plan_type: str | None


@dataclass(frozen=True)
class ModelInfo:
    model: str
    display_name: str
    is_default: bool
    hidden: bool


@dataclass(frozen=True)
class RateLimitWindow:
    used_percent: int
    window_duration_minutes: int | None
    resets_at: int | None


@dataclass(frozen=True)
class RateLimitInfo:
    limit_id: str | None
    plan_type: str | None
    primary: RateLimitWindow | None
    secondary: RateLimitWindow | None


@dataclass(frozen=True)
class LoginCompletedNotification:
    login_id: str | None
    success: bool
    error_present: bool


@dataclass(frozen=True)
class AccountUpdatedNotification:
    authenticated: bool
    plan_type: str | None


@dataclass(frozen=True)
class RateLimitsUpdatedNotification:
    rate_limits: RateLimitInfo


AccountNotification = (
    LoginCompletedNotification | AccountUpdatedNotification | RateLimitsUpdatedNotification
)


JsonObject = dict[str, Any]


def _object(value: object, context: str) -> JsonObject:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise CodexInvalidMessageError(f"{context}: objeto invalido")
    return value


def _string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise CodexInvalidMessageError(f"{context}: texto obrigatorio ausente")
    return value


def _nullable_string(value: object, context: str) -> str | None:
    if value is None:
        return None
    return _string(value, context)


def _boolean(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise CodexInvalidMessageError(f"{context}: booleano invalido")
    return value


def _integer(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CodexInvalidMessageError(f"{context}: inteiro invalido")
    return value


def _exact_keys(value: Mapping[str, object], allowed: set[str], context: str) -> None:
    if set(value) - allowed:
        raise CodexInvalidMessageError(f"{context}: campos nao permitidos")


class CodexAppServerClient:
    """Sessão assíncrona JSON-lines com dispatch concorrente por request id."""

    def __init__(
        self,
        process: asyncio.subprocess.Process,
        *,
        timeout_seconds: float,
        max_frame_bytes: int,
        expected_user_agent_identity: str | None,
    ) -> None:
        if process.stdin is None or process.stdout is None or process.stderr is None:
            raise CodexAppServerError("pipes do processo nao foram criados")
        self._process = process
        self._stdin = process.stdin
        self._stdout = process.stdout
        self._stderr = process.stderr
        self._timeout_seconds = timeout_seconds
        self._max_frame_bytes = max_frame_bytes
        self._expected_user_agent_identity = expected_user_agent_identity
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[JsonObject]] = {}
        self._notifications: asyncio.Queue[AccountNotification | CodexAppServerError]
        self._notifications = asyncio.Queue(maxsize=MAX_NOTIFICATION_QUEUE)
        self._write_lock = asyncio.Lock()
        self._closed = False
        self._close_task: asyncio.Task[None] | None = None
        self._terminal_error: CodexAppServerError | None = None
        self._reader_task = asyncio.create_task(self._read_loop())
        self._stderr_task = asyncio.create_task(self._discard_stderr())

    @classmethod
    async def start(
        cls,
        command: Sequence[str],
        *,
        codex_home: Path,
        working_directory: Path,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_frame_bytes: int = MAX_FRAME_BYTES,
        expected_user_agent_identity: str | None = None,
    ) -> CodexAppServerClient:
        if not command or not Path(command[0]).is_absolute():
            raise CodexAppServerError("executavel do App Server deve ter caminho absoluto")
        if not codex_home.is_absolute() or not working_directory.is_absolute():
            raise CodexAppServerError("diretorios do App Server devem ser absolutos")
        if timeout_seconds <= 0 or max_frame_bytes <= 0:
            raise CodexAppServerError("limites do protocolo devem ser positivos")

        codex_home.mkdir(parents=True, exist_ok=True)
        working_directory.mkdir(parents=True, exist_ok=True)
        environment = {name: os.environ[name] for name in _SAFE_ENV_NAMES if name in os.environ}
        environment["CODEX_HOME"] = str(codex_home)
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=working_directory,
            env=environment,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=max_frame_bytes + 1,
        )
        client = cls(
            process,
            timeout_seconds=timeout_seconds,
            max_frame_bytes=max_frame_bytes,
            expected_user_agent_identity=expected_user_agent_identity,
        )
        try:
            await client.initialize()
        except BaseException:
            await client.close()
            raise
        return client

    async def initialize(self) -> None:
        result = await self._request(
            "initialize",
            {
                "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
                "capabilities": {"experimentalApi": False},
            },
        )
        _exact_keys(
            result,
            {"codexHome", "platformFamily", "platformOs", "userAgent"},
            "initialize",
        )
        user_agent = _string(result.get("userAgent"), "initialize.userAgent")
        user_agent_identity = user_agent.split(" ", maxsplit=1)[0]
        if (
            self._expected_user_agent_identity is not None
            and user_agent_identity != self._expected_user_agent_identity
        ):
            raise CodexInvalidMessageError("initialize: versao do App Server incompatível")
        await self._notify("initialized", None)

    @property
    def available(self) -> bool:
        """Indica apenas o estado local do filho e do reader, sem I/O externo."""
        return (
            not self._closed
            and self._terminal_error is None
            and self._process.returncode is None
            and not self._reader_task.done()
        )

    async def start_device_login(self) -> DeviceCodeChallenge:
        result = await self._request("account/login/start", {"type": "chatgptDeviceCode"})
        _exact_keys(
            result,
            {"type", "loginId", "verificationUrl", "userCode"},
            "account/login/start",
        )
        if result.get("type") != "chatgptDeviceCode":
            raise CodexInvalidMessageError("account/login/start: tipo inesperado")
        return DeviceCodeChallenge(
            login_id=_string(result.get("loginId"), "loginId"),
            verification_url=_string(result.get("verificationUrl"), "verificationUrl"),
            user_code=_string(result.get("userCode"), "userCode"),
        )

    async def cancel_login(self, login_id: str) -> bool:
        result = await self._request("account/login/cancel", {"loginId": login_id})
        _exact_keys(result, {"status"}, "account/login/cancel")
        status = _string(result.get("status"), "cancel.status")
        if status not in {"canceled", "notFound"}:
            raise CodexInvalidMessageError("account/login/cancel: status inesperado")
        return status == "canceled"

    async def read_account(self) -> AccountInfo:
        result = await self._request("account/read", {"refreshToken": False})
        _exact_keys(result, {"account", "requiresOpenaiAuth"}, "account/read")
        _boolean(result.get("requiresOpenaiAuth"), "requiresOpenaiAuth")
        account_value = result.get("account")
        if account_value is None:
            return AccountInfo(authenticated=False, plan_type=None)
        account = _object(account_value, "account")
        account_type = _string(account.get("type"), "account.type")
        if account_type != "chatgpt":
            raise CodexInvalidMessageError("account/read: conta nao e ChatGPT")
        return AccountInfo(
            authenticated=True,
            plan_type=_string(account.get("planType"), "account.planType"),
        )

    async def list_models(
        self, cursor: str | None = None
    ) -> tuple[tuple[ModelInfo, ...], str | None]:
        params: JsonObject = {}
        if cursor is not None:
            params["cursor"] = cursor
        result = await self._request("model/list", params)
        _exact_keys(result, {"data", "nextCursor"}, "model/list")
        data = result.get("data")
        if not isinstance(data, list):
            raise CodexInvalidMessageError("model/list.data: lista invalida")
        models: list[ModelInfo] = []
        for value in data:
            model = _object(value, "model")
            models.append(
                ModelInfo(
                    model=_string(model.get("model"), "model.model"),
                    display_name=_string(model.get("displayName"), "model.displayName"),
                    is_default=_boolean(model.get("isDefault"), "model.isDefault"),
                    hidden=_boolean(model.get("hidden"), "model.hidden"),
                )
            )
        return tuple(models), _nullable_string(result.get("nextCursor"), "nextCursor")

    async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]:
        result = await self._request("account/rateLimits/read", {})
        buckets_value = result.get("rateLimitsByLimitId")
        if buckets_value is None:
            buckets = [_object(result.get("rateLimits"), "rateLimits")]
        else:
            bucket_map = _object(buckets_value, "rateLimitsByLimitId")
            buckets = [_object(value, "rateLimit") for value in bucket_map.values()]
        return tuple(self._rate_limit(bucket) for bucket in buckets)

    async def logout(self) -> None:
        result = await self._request("account/logout", {})
        _exact_keys(result, set(), "account/logout")

    async def next_notification(self, timeout_seconds: float | None = None) -> AccountNotification:
        if self._terminal_error is not None:
            raise self._terminal_error
        timeout = self._timeout_seconds if timeout_seconds is None else timeout_seconds
        try:
            notification = await asyncio.wait_for(self._notifications.get(), timeout)
        except TimeoutError as exc:
            raise CodexRequestTimeoutError(
                "aguardar notificacao", may_have_been_sent=False
            ) from exc
        if isinstance(notification, CodexAppServerError):
            raise notification
        return notification

    async def close(self) -> None:
        if self._close_task is None:
            self._closed = True
            self._close_task = asyncio.create_task(self._close_impl())
        try:
            await asyncio.shield(self._close_task)
        except asyncio.CancelledError:
            if self._process.returncode is None:
                with suppress(ProcessLookupError):
                    self._process.kill()
            while not self._close_task.done():
                try:
                    await asyncio.shield(self._close_task)
                except asyncio.CancelledError:
                    continue
            raise

    async def _close_impl(self) -> None:
        self._fail_pending(CodexProcessExitedError("sessao encerrada"))
        if self._process.returncode is None:
            with suppress(ProcessLookupError):
                self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), PROCESS_TERMINATE_GRACE_SECONDS)
            except TimeoutError:
                with suppress(ProcessLookupError):
                    self._process.kill()
                await asyncio.wait_for(self._process.wait(), PROCESS_KILL_WAIT_SECONDS)
        for task in (self._reader_task, self._stderr_task):
            task.cancel()
        await asyncio.gather(self._reader_task, self._stderr_task, return_exceptions=True)

    async def __aenter__(self) -> CodexAppServerClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def _request(self, method: str, params: JsonObject) -> JsonObject:
        if method not in _ALLOWED_METHODS:
            raise CodexMethodDeniedError("metodo Codex nao permitido")
        if self._terminal_error is not None:
            raise self._terminal_error
        if self._closed or self._process.returncode is not None:
            raise CodexProcessExitedError("Codex App Server indisponivel")

        request_id: int | None = None
        future: asyncio.Future[JsonObject] | None = None
        may_have_been_sent = False
        try:
            async with asyncio.timeout(self._timeout_seconds):
                async with self._write_lock:
                    if self._terminal_error is not None:
                        raise self._terminal_error
                    request_id = self._next_id
                    self._next_id += 1
                    future = asyncio.get_running_loop().create_future()
                    self._pending[request_id] = future
                    may_have_been_sent = True
                    await self._write({"id": request_id, "method": method, "params": params})
                return await asyncio.shield(future)
        except TimeoutError as exc:
            self._discard_pending(request_id, future)
            raise CodexRequestTimeoutError(method, may_have_been_sent=may_have_been_sent) from exc
        except asyncio.CancelledError:
            self._discard_pending(request_id, future)
            raise
        except BaseException:
            self._discard_pending(request_id, future)
            raise

    async def _notify(self, method: str, params: JsonObject | None) -> None:
        message: JsonObject = {"method": method}
        if params is not None:
            message["params"] = params
        await self._write(message)

    async def _write(self, message: JsonObject) -> None:
        payload = json.dumps(message, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        if len(payload) + 1 > self._max_frame_bytes:
            raise CodexFrameTooLargeError("frame de saida excede 1 MiB")
        self._stdin.write(payload + b"\n")
        try:
            await self._stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as exc:
            raise CodexProcessExitedError("pipe do App Server foi encerrado") from exc

    async def _read_loop(self) -> None:
        try:
            while True:
                try:
                    line = await self._stdout.readline()
                except ValueError as exc:
                    raise CodexFrameTooLargeError("frame de entrada excede 1 MiB") from exc
                if not line:
                    raise CodexProcessExitedError("App Server encerrou stdout")
                if len(line) > self._max_frame_bytes:
                    raise CodexFrameTooLargeError("frame de entrada excede 1 MiB")
                self._dispatch(self._decode(line))
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            error = (
                exc
                if isinstance(exc, CodexAppServerError)
                else CodexInvalidMessageError("falha no reader")
            )
            self._terminal_error = error
            self._fail_pending(error)
            self._publish_notification_error(error)

    def _dispatch(self, message: JsonObject) -> None:
        if "id" in message and "method" in message:
            raise CodexMethodDeniedError("request iniciado pelo App Server nao permitido")
        if "id" in message:
            _exact_keys(message, {"id", "result", "error"}, "response")
            if ("result" in message) == ("error" in message):
                raise CodexInvalidMessageError("response deve conter result ou error")
            request_id = _integer(message.get("id"), "response.id")
            future = self._pending.get(request_id)
            if future is None:
                raise CodexInvalidMessageError("response.id desconhecido")
            try:
                if "error" in message:
                    error = _object(message.get("error"), "response.error")
                    code_value = error.get("code")
                    code = None if code_value is None else _integer(code_value, "error.code")
                    response_error: CodexAppServerError | None = CodexRemoteError(code)
                    result: JsonObject | None = None
                else:
                    response_error = None
                    result = _object(message.get("result"), "response.result")
            except CodexAppServerError as exc:
                self._pending.pop(request_id, None)
                future.set_exception(exc)
                raise
            self._pending.pop(request_id, None)
            if response_error is not None:
                future.set_exception(response_error)
                return
            assert result is not None
            future.set_result(result)
            return

        _exact_keys(message, {"method", "params", "emittedAtMs"}, "notification")
        method = _string(message.get("method"), "notification.method")
        emitted_at = message.get("emittedAtMs")
        if emitted_at is not None:
            _integer(emitted_at, "notification.emittedAtMs")
        if method in _IGNORED_NOTIFICATIONS:
            self._validate_ignored_notification(method, message.get("params"))
            return
        if method not in _ALLOWED_NOTIFICATIONS:
            raise CodexMethodDeniedError("notificacao Codex nao permitida")
        params = _object(message.get("params"), "notification.params")
        notification = self._account_notification(method, params)
        try:
            self._notifications.put_nowait(notification)
        except asyncio.QueueFull as exc:
            raise CodexInvalidMessageError("fila de notificacoes excedida") from exc

    def _decode(self, line: bytes) -> JsonObject:
        try:
            value = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CodexInvalidMessageError("JSON invalido do App Server") from exc
        return _object(value, "mensagem")

    async def _discard_stderr(self) -> None:
        while await self._stderr.read(8192):
            pass

    def _fail_pending(self, error: BaseException) -> None:
        pending = tuple(self._pending.values())
        self._pending.clear()
        for future in pending:
            if not future.done():
                future.set_exception(error)

    def _discard_pending(
        self,
        request_id: int | None,
        future: asyncio.Future[JsonObject] | None,
    ) -> None:
        if request_id is not None:
            self._pending.pop(request_id, None)
        if future is not None and not future.done():
            future.cancel()

    def _publish_notification_error(self, error: CodexAppServerError) -> None:
        while not self._notifications.empty():
            self._notifications.get_nowait()
        self._notifications.put_nowait(error)

    @staticmethod
    def _account_notification(method: str, params: JsonObject) -> AccountNotification:
        if method == "account/login/completed":
            _exact_keys(params, {"loginId", "success", "error"}, method)
            error = _nullable_string(params.get("error"), f"{method}.error")
            return LoginCompletedNotification(
                login_id=_nullable_string(params.get("loginId"), f"{method}.loginId"),
                success=_boolean(params.get("success"), f"{method}.success"),
                error_present=error is not None,
            )
        if method == "account/updated":
            _exact_keys(params, {"authMode", "planType"}, method)
            auth_mode = _nullable_string(params.get("authMode"), f"{method}.authMode")
            if auth_mode not in {None, "chatgpt"}:
                raise CodexInvalidMessageError(f"{method}: modo de conta inesperado")
            plan_type = _nullable_string(params.get("planType"), f"{method}.planType")
            if plan_type is not None and plan_type not in _CHATGPT_PLAN_TYPES:
                raise CodexInvalidMessageError(f"{method}: plano inesperado")
            return AccountUpdatedNotification(
                authenticated=auth_mode == "chatgpt",
                plan_type=plan_type,
            )
        if method == "account/rateLimits/updated":
            _exact_keys(params, {"rateLimits"}, method)
            rate_limits = _object(params.get("rateLimits"), f"{method}.rateLimits")
            return RateLimitsUpdatedNotification(
                rate_limits=CodexAppServerClient._rate_limit(rate_limits)
            )
        raise CodexMethodDeniedError("notificacao Codex nao permitida")

    @staticmethod
    def _validate_ignored_notification(method: str, value: object) -> None:
        params = _object(value, f"{method}.params")
        if method == "configWarning":
            _exact_keys(params, {"summary", "details", "path", "range"}, method)
            summary = _string(params.get("summary"), f"{method}.summary")
            if not summary.startswith(_BUNDLED_BWRAP_WARNING_PREFIX):
                raise CodexInvalidMessageError("configWarning inesperado")
            _nullable_string(params.get("details"), f"{method}.details")
            _nullable_string(params.get("path"), f"{method}.path")

    @staticmethod
    def _rate_limit(bucket: JsonObject) -> RateLimitInfo:
        return RateLimitInfo(
            limit_id=_nullable_string(bucket.get("limitId"), "rateLimit.limitId"),
            plan_type=_nullable_string(bucket.get("planType"), "rateLimit.planType"),
            primary=CodexAppServerClient._rate_window(bucket.get("primary")),
            secondary=CodexAppServerClient._rate_window(bucket.get("secondary")),
        )

    @staticmethod
    def _rate_window(value: object) -> RateLimitWindow | None:
        if value is None:
            return None
        window = _object(value, "rateLimit.window")
        duration = window.get("windowDurationMins")
        resets_at = window.get("resetsAt")
        return RateLimitWindow(
            used_percent=_integer(window.get("usedPercent"), "window.usedPercent"),
            window_duration_minutes=(
                None if duration is None else _integer(duration, "window.windowDurationMins")
            ),
            resets_at=None if resets_at is None else _integer(resets_at, "window.resetsAt"),
        )
