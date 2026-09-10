from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from emprestimo.agent.codex_app_server import (
    AccountInfo,
    CodexAppServerClient,
    CodexFrameTooLargeError,
    CodexInvalidMessageError,
    CodexMethodDeniedError,
    CodexProcessExitedError,
    CodexRemoteError,
    CodexRequestTimeoutError,
    DeviceCodeChallenge,
    LoginCompletedNotification,
    ModelInfo,
)

FAKE_SERVER = r"""
import json, os, sys, time
mode = sys.argv[1]

def receive():
    line = sys.stdin.buffer.readline()
    if not line:
        raise SystemExit(0)
    return json.loads(line)

def send(message):
    print(json.dumps(message, separators=(",", ":")), flush=True)

request = receive()
if os.environ.get("TIANET_SHOULD_NOT_LEAK"):
    raise SystemExit(21)
send({"id": request["id"], "result": {
    "codexHome": os.environ["CODEX_HOME"], "platformFamily": "test",
    "platformOs": "test", "userAgent": "fake/1"}})
assert receive() == {"method": "initialized"}
send({"method": "configWarning", "params": {
    "summary": "Codex could not find bubblewrap on PATH. fixture", "details": None},
    "emittedAtMs": 1})
send({"method": "remoteControl/status/changed", "params": {"status": "disabled"},
    "emittedAtMs": 1})
if mode == "eof":
    raise SystemExit(0)
if mode == "malformed-notification":
    send({"method": "account/login/completed", "params": {
        "loginId": "login-1", "success": "yes", "unexpected": True}})
if mode == "notification-flood":
    for _ in range(33):
        send({"method": "account/updated", "params": {
            "authMode": None, "planType": None}})
if mode == "out-of-order":
    first, second = receive(), receive()
    responses = {
        "account/read": {"account": {"type": "chatgpt", "planType": "free"},
            "requiresOpenaiAuth": True},
        "model/list": {"data": [{"model": "gpt-test", "displayName": "GPT Test",
            "isDefault": True, "hidden": False}], "nextCursor": None},
    }
    send({"id": second["id"], "result": responses[second["method"]]})
    send({"id": first["id"], "result": responses[first["method"]]})
    raise SystemExit(0)

while True:
    request = receive()
    method, request_id = request["method"], request["id"]
    if mode == "timeout":
        time.sleep(2)
    elif mode == "oversized":
        print("{" + "x" * 4096 + "}", flush=True)
    elif mode == "invalid":
        print("not-json", flush=True)
    elif mode == "server-request":
        send({"id": 999, "method": "item/commandExecution/requestApproval", "params": {}})
    elif mode == "remote-error":
        send({"id": request_id, "error": {"code": -32000, "message": "secret"}})
    elif mode == "extra-field":
        send({"id": request_id, "result": {"account": None,
            "requiresOpenaiAuth": True}, "unexpected": True})
    elif mode == "invalid-result":
        send({"id": request_id, "result": []})
    elif mode == "unexpected-config-warning":
        send({"method": "configWarning", "params": {
            "summary": "outro aviso", "details": None}})
    elif method == "account/login/start":
        send({"method": "account/login/completed", "params": {
            "loginId": "login-1", "success": True, "error": None}})
        send({"id": request_id, "result": {"type": "chatgptDeviceCode",
            "loginId": "login-1", "verificationUrl":
            "https://auth.openai.com/codex/device", "userCode": "ABCD-EFGH"}})
    elif method == "account/login/cancel":
        send({"id": request_id, "result": {"status": "canceled"}})
    elif method == "account/read":
        send({"id": request_id, "result": {"account": {"type": "chatgpt",
            "email": "not-forwarded@example.test", "planType": "free"},
            "requiresOpenaiAuth": True}})
    elif method == "model/list":
        send({"id": request_id, "result": {"data": [{"id": "m1",
            "model": "gpt-test", "displayName": "GPT Test", "description": "fixture",
            "isDefault": True, "hidden": False, "defaultReasoningEffort": "low",
            "supportedReasoningEfforts": []}], "nextCursor": None}})
    elif method == "account/rateLimits/read":
        send({"id": request_id, "result": {"rateLimits": {"limitId": "codex",
            "planType": "free", "primary": {"usedPercent": 7,
            "windowDurationMins": 300, "resetsAt": 1234}, "secondary": None},
            "rateLimitsByLimitId": None, "rateLimitResetCredits": None}})
    elif method == "account/logout":
        send({"id": request_id, "result": {}})
"""


async def _client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str = "success",
    *,
    timeout: float = 1.0,
    frame_limit: int = 1024 * 1024,
    expected_user_agent_identity: str | None = None,
) -> CodexAppServerClient:
    tmp_path.mkdir(parents=True, exist_ok=True)
    script = tmp_path / "fake_codex_server.py"
    script.write_text(FAKE_SERVER, encoding="utf-8")
    monkeypatch.setenv("TIANET_SHOULD_NOT_LEAK", "must-not-reach-child")
    return await CodexAppServerClient.start(
        (sys.executable, str(script), mode),
        codex_home=(tmp_path / "codex-home").resolve(),
        working_directory=(tmp_path / "runtime").resolve(),
        timeout_seconds=timeout,
        max_frame_bytes=frame_limit,
        expected_user_agent_identity=expected_user_agent_identity,
    )


def test_fluxo_administrativo_tipado_e_ambiente_sanitizado(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        async with await _client(tmp_path, monkeypatch) as client:
            assert await client.start_device_login() == DeviceCodeChallenge(
                "login-1", "https://auth.openai.com/codex/device", "ABCD-EFGH"
            )
            assert await client.next_notification() == LoginCompletedNotification(
                login_id="login-1", success=True, error_present=False
            )
            assert await client.cancel_login("login-1") is True
            assert await client.read_account() == AccountInfo(True, "free")
            models, cursor = await client.list_models()
            assert models == (ModelInfo("gpt-test", "GPT Test", True, False),)
            assert cursor is None
            limits = await client.read_rate_limits()
            assert limits[0].primary is not None
            assert limits[0].primary.used_percent == 7
            await client.logout()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("mode", "error", "frame_limit"),
    [
        ("invalid", CodexInvalidMessageError, 1024 * 1024),
        ("server-request", CodexMethodDeniedError, 1024 * 1024),
        ("oversized", CodexFrameTooLargeError, 1024),
        ("remote-error", CodexRemoteError, 1024 * 1024),
        ("extra-field", CodexInvalidMessageError, 1024 * 1024),
        ("unexpected-config-warning", CodexInvalidMessageError, 1024 * 1024),
    ],
)
def test_respostas_perigosas_falham_fechadas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    error: type[Exception],
    frame_limit: int,
) -> None:
    async def scenario() -> None:
        async with await _client(tmp_path, monkeypatch, mode, frame_limit=frame_limit) as client:
            with pytest.raises(error):
                await client.read_account()

    asyncio.run(scenario())


def test_timeout_e_eof_sao_diferenciados(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        async with await _client(
            tmp_path / "timeout", monkeypatch, "timeout", timeout=0.5
        ) as client:
            with pytest.raises(CodexRequestTimeoutError):
                await client.read_account()
        async with await _client(tmp_path / "eof", monkeypatch, "eof") as client:
            await asyncio.sleep(0.05)
            with pytest.raises(CodexProcessExitedError):
                await client.read_account()

    asyncio.run(scenario())


@pytest.mark.skipif(sys.platform == "win32", reason="SIGTERM ignorável exige POSIX")
def test_close_cancelado_mata_e_recolhe_filho_que_ignora_sigterm() -> None:
    async def scenario() -> None:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        client = CodexAppServerClient(
            process,
            timeout_seconds=1,
            max_frame_bytes=1024,
            expected_user_agent_identity=None,
        )
        closing = asyncio.create_task(client.close())
        await asyncio.sleep(0.05)
        closing.cancel()
        with pytest.raises(asyncio.CancelledError):
            await closing
        assert process.returncode is not None
        assert not client.available

    asyncio.run(scenario())


def test_respostas_concorrentes_podem_chegar_fora_de_ordem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        async with await _client(tmp_path, monkeypatch, "out-of-order") as client:
            account, model_page = await asyncio.gather(client.read_account(), client.list_models())
            assert account == AccountInfo(True, "free")
            assert model_page == (
                (ModelInfo("gpt-test", "GPT Test", True, False),),
                None,
            )

    asyncio.run(scenario())


@pytest.mark.parametrize("expected_identity", ["codex_cli_rs/0.146.1", "fake/1-extra"])
def test_user_agent_fixado_rejeita_identidade_incompativel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, expected_identity: str
) -> None:
    async def scenario() -> None:
        with pytest.raises(CodexInvalidMessageError, match="versao"):
            await _client(
                tmp_path,
                monkeypatch,
                expected_user_agent_identity=expected_identity,
            )

    asyncio.run(scenario())


def test_resposta_invalida_com_id_conhecido_falha_imediatamente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        async with await _client(tmp_path, monkeypatch, "invalid-result") as client:
            with pytest.raises(CodexInvalidMessageError, match="response.result"):
                await client.read_account()

    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["malformed-notification", "notification-flood"])
def test_notificacao_malformada_ou_fila_saturada_falha_fechada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    async def scenario() -> None:
        async with await _client(tmp_path, monkeypatch, mode) as client:
            if mode == "notification-flood":
                await asyncio.sleep(0.05)
            with pytest.raises(CodexInvalidMessageError):
                await client.next_notification(timeout_seconds=0.5)

    asyncio.run(scenario())


def test_timeout_inclui_espera_pelo_lock_e_backpressure_de_escrita(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        async with await _client(tmp_path, monkeypatch) as client:
            client._timeout_seconds = 0.05
            await client._write_lock.acquire()
            try:
                with pytest.raises(CodexRequestTimeoutError) as lock_timeout:
                    await client.read_account()
                assert lock_timeout.value.may_have_been_sent is False
            finally:
                client._write_lock.release()

            async def slow_write(message: dict[str, object]) -> None:
                await asyncio.sleep(0.2)

            monkeypatch.setattr(client, "_write", slow_write)
            with pytest.raises(CodexRequestTimeoutError) as write_timeout:
                await client.read_account()
            assert write_timeout.value.may_have_been_sent is True
            assert client._pending == {}

    asyncio.run(scenario())


def test_cancelamento_remove_requisicao_pendente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        async with await _client(tmp_path, monkeypatch, "timeout") as client:
            request = asyncio.create_task(client.read_account())
            await asyncio.sleep(0.05)
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
            assert client._pending == {}

    asyncio.run(scenario())


def test_metodo_fora_da_allowlist_nunca_e_enviado(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        async with await _client(tmp_path, monkeypatch) as client:
            with pytest.raises(CodexMethodDeniedError):
                await client._request("thread/start", {})

    asyncio.run(scenario())
