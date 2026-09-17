from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from emprestimo.agent import service as agent_service
from emprestimo.agent.codex_app_server import (
    AccountInfo,
    CodexRequestTimeoutError,
    DeviceCodeChallenge,
    ModelInfo,
    RateLimitInfo,
    RateLimitWindow,
)
from emprestimo.agent.service import (
    AgentRuntime,
    AgentSettings,
    AgentUnavailableError,
    create_agent_app,
)

SECRET = "s" * 32


def _settings(*, enabled: bool, executable: Path) -> AgentSettings:
    return AgentSettings(
        enabled=enabled,
        internal_secret=SECRET,
        codex_executable=executable,
        codex_home=Path("C:/tianet-test/codex-home"),
        runtime_directory=Path("C:/tianet-test/runtime"),
        codex_user_agent_identity="tianet-agent-auth/0.146.1",
    )


def test_feature_flag_desligada_e_snapshot_protegido() -> None:
    app = create_agent_app(_settings(enabled=False, executable=Path("C:/missing.exe")))
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {
            "status": "ready",
            "enabled": False,
            "processAvailable": False,
            "accountConnected": False,
        }
        assert client.get("/internal/openai/conexao").status_code == 401
        assert (
            client.get(
                "/internal/openai/conexao",
                headers={"X-TiaNet-Agent-Secret": "wrong"},
            ).status_code
            == 401
        )
        snapshot = client.get(
            "/internal/openai/conexao",
            headers={"X-TiaNet-Agent-Secret": SECRET},
        )
        assert snapshot.status_code == 200
        assert snapshot.json() == {
            "enabled": False,
            "processAvailable": False,
            "accountConnected": False,
            "planType": None,
            "startupError": False,
            "state": "DESABILITADO",
            "usageSummary": None,
        }
        assert SECRET not in snapshot.text


def test_health_distingue_processo_indisponivel_de_conta_desconectada(
    tmp_path: Path,
) -> None:
    missing = (tmp_path / "missing-codex").resolve()
    app = create_agent_app(_settings(enabled=True, executable=missing))
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 503
        assert health.json() == {
            "status": "degraded",
            "enabled": True,
            "processAvailable": False,
            "accountConnected": False,
        }
        snapshot = client.get(
            "/internal/openai/conexao",
            headers={"X-TiaNet-Agent-Secret": SECRET},
        )
        assert snapshot.json()["startupError"] is True


def test_configuracao_recusa_segredo_curto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TIANET_AGENT_ENABLED", "true")
    monkeypatch.setenv("TIANET_AGENT_INTERNAL_SECRET", "curto")
    with pytest.raises(RuntimeError, match="32 caracteres"):
        AgentSettings.from_environment()


def test_configuracao_desligada_nao_exige_segredo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TIANET_AGENT_ENABLED", "false")
    monkeypatch.delenv("TIANET_AGENT_INTERNAL_SECRET", raising=False)
    assert AgentSettings.from_environment().internal_secret == ""


def test_health_observa_morte_do_filho_sem_consulta_externa() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.available = True
            self.read_count = 0

        async def read_account(self) -> AccountInfo:
            self.read_count += 1
            return AccountInfo(authenticated=False, plan_type=None)

        async def start_device_login(self) -> DeviceCodeChallenge:
            raise AssertionError("nao chamado")

        async def cancel_login(self, login_id: str) -> bool:
            raise AssertionError(login_id)

        async def list_models(
            self, cursor: str | None = None
        ) -> tuple[tuple[ModelInfo, ...], str | None]:
            raise AssertionError(cursor)

        async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]:
            raise AssertionError("nao chamado")

        async def logout(self) -> None:
            raise AssertionError("nao chamado")

        async def next_notification(self, timeout_seconds: float | None = None) -> object:
            raise AssertionError(timeout_seconds)

        async def close(self) -> None:
            self.available = False

    fake = FakeClient()

    async def start_fake(*args: object, **kwargs: object) -> FakeClient:
        return fake

    app = create_agent_app(
        _settings(enabled=True, executable=Path("C:/fake-codex.exe")),
        client_starter=start_fake,
    )
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert fake.read_count == 1
        fake.available = False
        health = client.get("/health")
        assert health.status_code == 503
        assert health.json()["processAvailable"] is False
        assert fake.read_count == 1


def test_servico_nao_expoe_rotas_de_inferencia() -> None:
    app = create_agent_app(_settings(enabled=False, executable=Path("C:/missing.exe")))
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    assert paths == {
        "/health",
        "/internal/openai/conexao",
        "/internal/openai/conexao/login",
        "/internal/openai/diagnostico",
    }


def test_login_repetido_reusa_desafio_sem_expor_login_id() -> None:
    class FakeClient:
        available = True

        def __init__(self) -> None:
            self.login_count = 0

        async def read_account(self) -> AccountInfo:
            return AccountInfo(authenticated=False, plan_type=None)

        async def start_device_login(self) -> DeviceCodeChallenge:
            self.login_count += 1
            return DeviceCodeChallenge(
                login_id="interno",
                verification_url="https://auth.openai.com/codex/device",
                user_code="ABCD-EFGH",
            )

        async def cancel_login(self, login_id: str) -> bool:
            return login_id == "interno"

        async def list_models(
            self, cursor: str | None = None
        ) -> tuple[tuple[ModelInfo, ...], str | None]:
            return (), None

        async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]:
            return ()

        async def logout(self) -> None:
            return None

        async def next_notification(self, timeout_seconds: float | None = None) -> object:
            await asyncio.sleep(timeout_seconds or 600)
            raise AssertionError("watcher nao deveria expirar durante o teste")

        async def close(self) -> None:
            self.available = False

    fake = FakeClient()

    async def start_fake(*args: object, **kwargs: object) -> FakeClient:
        return fake

    app = create_agent_app(
        _settings(enabled=True, executable=Path("C:/fake-codex.exe")),
        client_starter=start_fake,
    )
    headers = {"X-TiaNet-Agent-Secret": SECRET}
    with TestClient(app) as client:
        first = client.post("/internal/openai/conexao/login", headers=headers)
        second = client.post("/internal/openai/conexao/login", headers=headers)
        assert first.status_code == 200
        assert second.json() == first.json()
        assert fake.login_count == 1
        assert set(first.json()) == {"verificationUrl", "userCode", "expiresAt"}
        assert "interno" not in first.text
        assert client.get("/internal/openai/conexao", headers=headers).json()["state"] == (
            "AGUARDANDO_USUARIO"
        )


def test_diagnostico_compartilha_cache_e_filtra_modelo_oculto() -> None:
    class FakeClient:
        available = True

        def __init__(self) -> None:
            self.account_reads = 0
            self.model_reads = 0
            self.limit_reads = 0

        async def read_account(self) -> AccountInfo:
            self.account_reads += 1
            return AccountInfo(authenticated=True, plan_type="free")

        async def start_device_login(self) -> DeviceCodeChallenge:
            raise AssertionError("nao chamado")

        async def cancel_login(self, login_id: str) -> bool:
            raise AssertionError(login_id)

        async def list_models(
            self, cursor: str | None = None
        ) -> tuple[tuple[ModelInfo, ...], str | None]:
            self.model_reads += 1
            return (
                (
                    ModelInfo("visible", "Visible", True, False),
                    ModelInfo("hidden", "Hidden", False, True),
                ),
                None,
            )

        async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]:
            self.limit_reads += 1
            return (
                RateLimitInfo(
                    limit_id="codex",
                    plan_type="free",
                    primary=RateLimitWindow(50, 300, 123),
                    secondary=None,
                ),
            )

        async def logout(self) -> None:
            raise AssertionError("nao chamado")

        async def next_notification(self, timeout_seconds: float | None = None) -> object:
            raise AssertionError(timeout_seconds)

        async def close(self) -> None:
            self.available = False

    fake = FakeClient()

    async def start_fake(*args: object, **kwargs: object) -> FakeClient:
        return fake

    app = create_agent_app(
        _settings(enabled=True, executable=Path("C:/fake-codex.exe")),
        client_starter=start_fake,
    )
    headers = {"X-TiaNet-Agent-Secret": SECRET}
    with TestClient(app) as client:
        first = client.get("/internal/openai/diagnostico", headers=headers)
        second = client.get("/internal/openai/diagnostico", headers=headers)
        assert first.status_code == 200
        assert second.json() == first.json()
        assert first.json()["models"]["items"] == [
            {"id": "visible", "displayName": "Visible", "default": True}
        ]
        assert fake.account_reads == 2  # startup + primeiro diagnostico
        assert fake.model_reads == 1
        assert fake.limit_reads == 1
        snapshot = client.get("/internal/openai/conexao", headers=headers).json()
        assert snapshot["usageSummary"]["rateLimits"][0]["primary"]["usedPercent"] == 50
        assert fake.account_reads == 2
        assert fake.model_reads == 1
        assert fake.limit_reads == 1
        fake.available = False
        unavailable = client.get("/internal/openai/conexao", headers=headers).json()
        assert unavailable["state"] == "INDISPONIVEL"
        assert unavailable["usageSummary"] is None
        assert fake.account_reads == 2
        assert fake.model_reads == 1
        assert fake.limit_reads == 1


def test_device_code_expirado_e_cancelado_e_volta_a_desconectado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        available = True

        def __init__(self) -> None:
            self.cancelled: list[str] = []

        async def read_account(self) -> AccountInfo:
            return AccountInfo(authenticated=False, plan_type=None)

        async def start_device_login(self) -> DeviceCodeChallenge:
            return DeviceCodeChallenge("login-expira", "https://auth.openai.com", "ABCD")

        async def cancel_login(self, login_id: str) -> bool:
            self.cancelled.append(login_id)
            return True

        async def list_models(
            self, cursor: str | None = None
        ) -> tuple[tuple[ModelInfo, ...], str | None]:
            return (), None

        async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]:
            return ()

        async def logout(self) -> None:
            return None

        async def next_notification(self, timeout_seconds: float | None = None) -> object:
            await asyncio.sleep(timeout_seconds or 0)
            raise CodexRequestTimeoutError("account/login/completed", may_have_been_sent=False)

        async def close(self) -> None:
            self.available = False

    fake = FakeClient()

    async def start_fake(*args: object, **kwargs: object) -> FakeClient:
        return fake

    monkeypatch.setattr(agent_service, "LOGIN_TTL_SECONDS", 0.01)
    app = create_agent_app(
        _settings(enabled=True, executable=Path("C:/fake-codex.exe")),
        client_starter=start_fake,
    )
    headers = {"X-TiaNet-Agent-Secret": SECRET}
    with TestClient(app) as client:
        assert client.post("/internal/openai/conexao/login", headers=headers).status_code == 200
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            snapshot = client.get("/internal/openai/conexao", headers=headers).json()
            if snapshot["state"] == "DESCONECTADO":
                break
            time.sleep(0.01)
        assert snapshot["state"] == "DESCONECTADO"
        assert fake.cancelled == ["login-expira"]


def test_diagnostico_anterior_a_mutacao_nao_publica_resultado() -> None:
    async def scenario() -> None:
        models_started = asyncio.Event()
        release_models = asyncio.Event()

        class FakeClient:
            available = True

            async def read_account(self) -> AccountInfo:
                return AccountInfo(authenticated=False, plan_type=None)

            async def start_device_login(self) -> DeviceCodeChallenge:
                return DeviceCodeChallenge("novo-login", "https://auth.openai.com", "EFGH")

            async def cancel_login(self, login_id: str) -> bool:
                return True

            async def list_models(
                self, cursor: str | None = None
            ) -> tuple[tuple[ModelInfo, ...], str | None]:
                models_started.set()
                await release_models.wait()
                return ((ModelInfo("antigo", "Antigo", True, False),), None)

            async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]:
                return ()

            async def logout(self) -> None:
                return None

            async def next_notification(self, timeout_seconds: float | None = None) -> object:
                await asyncio.Event().wait()
                raise AssertionError("inalcancavel")

            async def close(self) -> None:
                self.available = False

        fake = FakeClient()

        async def start_fake(*args: object, **kwargs: object) -> FakeClient:
            return fake

        runtime = AgentRuntime(
            _settings(enabled=True, executable=Path("C:/fake-codex.exe")), start_fake
        )
        await runtime.start()
        diagnostic = asyncio.create_task(runtime.diagnose())
        await models_started.wait()
        await runtime.begin_login()
        release_models.set()
        with pytest.raises(AgentUnavailableError, match="invalidado"):
            await diagnostic
        assert runtime._diagnostic_cache is None
        await runtime.close()

    asyncio.run(scenario())


def test_timeout_global_do_login_reinicia_e_reconcilia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        available = True

        def __init__(self, *, block_login: bool) -> None:
            self.block_login = block_login

        async def read_account(self) -> AccountInfo:
            return AccountInfo(authenticated=False, plan_type=None)

        async def start_device_login(self) -> DeviceCodeChallenge:
            if self.block_login:
                await asyncio.Event().wait()
            raise AssertionError("login nao deveria ser repetido na reconciliacao")

        async def cancel_login(self, login_id: str) -> bool:
            return True

        async def list_models(
            self, cursor: str | None = None
        ) -> tuple[tuple[ModelInfo, ...], str | None]:
            return (), None

        async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]:
            return ()

        async def logout(self) -> None:
            return None

        async def next_notification(self, timeout_seconds: float | None = None) -> object:
            await asyncio.Event().wait()
            raise AssertionError("inalcancavel")

        async def close(self) -> None:
            self.available = False

    starts: list[FakeClient] = []

    async def start_fake(*args: object, **kwargs: object) -> FakeClient:
        client = FakeClient(block_login=not starts)
        starts.append(client)
        return client

    monkeypatch.setattr(agent_service, "MUTATION_BUDGET_SECONDS", 0.01)
    monkeypatch.setattr(agent_service, "RECOVERY_BUDGET_SECONDS", 0.5)
    app = create_agent_app(
        _settings(enabled=True, executable=Path("C:/fake-codex.exe")),
        client_starter=start_fake,
    )
    headers = {"X-TiaNet-Agent-Secret": SECRET}
    with TestClient(app) as client:
        response = client.post("/internal/openai/conexao/login", headers=headers)
        assert response.status_code == 503
        assert len(starts) == 2
        snapshot = client.get("/internal/openai/conexao", headers=headers).json()
        assert snapshot["state"] == "DESCONECTADO"


def test_diagnostico_iniciado_durante_logout_respeita_deadline_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        logout_started = asyncio.Event()
        release_logout = asyncio.Event()

        class FakeClient:
            available = True
            model_reads = 0

            async def read_account(self) -> AccountInfo:
                return AccountInfo(authenticated=False, plan_type=None)

            async def start_device_login(self) -> DeviceCodeChallenge:
                raise AssertionError("nao chamado")

            async def cancel_login(self, login_id: str) -> bool:
                return True

            async def list_models(
                self, cursor: str | None = None
            ) -> tuple[tuple[ModelInfo, ...], str | None]:
                self.model_reads += 1
                return (), None

            async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]:
                return ()

            async def logout(self) -> None:
                logout_started.set()
                await release_logout.wait()

            async def next_notification(self, timeout_seconds: float | None = None) -> object:
                await asyncio.Event().wait()
                raise AssertionError("inalcancavel")

            async def close(self) -> None:
                self.available = False

        fake = FakeClient()

        async def start_fake(*args: object, **kwargs: object) -> FakeClient:
            return fake

        runtime = AgentRuntime(
            _settings(enabled=True, executable=Path("C:/fake-codex.exe")), start_fake
        )
        monkeypatch.setattr(agent_service, "DIAGNOSTIC_BUDGET_SECONDS", 0.01)
        await runtime.start()
        logout_task = asyncio.create_task(runtime.logout())
        await logout_started.wait()
        diagnostic_task = asyncio.create_task(runtime.diagnose())
        await asyncio.sleep(0)
        assert fake.model_reads == 0
        with pytest.raises(TimeoutError):
            await diagnostic_task
        release_logout.set()
        await logout_task
        monkeypatch.setattr(agent_service, "DIAGNOSTIC_BUDGET_SECONDS", 1)
        result = await runtime.diagnose()
        assert result["state"] == "DESCONECTADO"
        assert fake.model_reads == 1
        await runtime.close()

    asyncio.run(scenario())


def test_cancelamento_de_mutacao_admitida_recupera_antes_da_proxima(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        events: list[str] = []

        class FakeClient:
            available = True

            def __init__(self, number: int) -> None:
                self.number = number

            async def read_account(self) -> AccountInfo:
                events.append(f"read-{self.number}")
                return AccountInfo(authenticated=False, plan_type=None)

            async def start_device_login(self) -> DeviceCodeChallenge:
                events.append(f"login-{self.number}")
                if self.number == 1:
                    await asyncio.Event().wait()
                return DeviceCodeChallenge("login-2", "https://auth.openai.com", "IJKL")

            async def cancel_login(self, login_id: str) -> bool:
                return True

            async def list_models(
                self, cursor: str | None = None
            ) -> tuple[tuple[ModelInfo, ...], str | None]:
                return (), None

            async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]:
                return ()

            async def logout(self) -> None:
                return None

            async def next_notification(self, timeout_seconds: float | None = None) -> object:
                await asyncio.Event().wait()
                raise AssertionError("inalcancavel")

            async def close(self) -> None:
                events.append(f"close-{self.number}")
                self.available = False

        clients: list[FakeClient] = []

        async def start_fake(*args: object, **kwargs: object) -> FakeClient:
            client = FakeClient(len(clients) + 1)
            clients.append(client)
            events.append(f"start-{client.number}")
            return client

        monkeypatch.setattr(agent_service, "MUTATION_BUDGET_SECONDS", 1)
        monkeypatch.setattr(agent_service, "RECOVERY_BUDGET_SECONDS", 0.2)
        runtime = AgentRuntime(
            _settings(enabled=True, executable=Path("C:/fake-codex.exe")), start_fake
        )
        await runtime.start()
        first = asyncio.create_task(runtime.begin_login())
        while "login-1" not in events:
            await asyncio.sleep(0)
        second = asyncio.create_task(runtime.begin_login())
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        second_result = (await asyncio.gather(second, return_exceptions=True))[0]
        assert isinstance(second_result, dict)
        assert events.index("login-2") > events.index("read-2")
        assert events.index("close-1") < events.index("start-2")
        await runtime.close()

    asyncio.run(scenario())


def test_cancelamento_de_um_consumidor_nao_cancela_diagnostico_compartilhado() -> None:
    async def scenario() -> None:
        models_started = asyncio.Event()
        release_models = asyncio.Event()

        class FakeClient:
            available = True

            async def read_account(self) -> AccountInfo:
                return AccountInfo(authenticated=True, plan_type="free")

            async def start_device_login(self) -> DeviceCodeChallenge:
                raise AssertionError("nao chamado")

            async def cancel_login(self, login_id: str) -> bool:
                return True

            async def list_models(
                self, cursor: str | None = None
            ) -> tuple[tuple[ModelInfo, ...], str | None]:
                models_started.set()
                await release_models.wait()
                return (), None

            async def read_rate_limits(self) -> tuple[RateLimitInfo, ...]:
                return ()

            async def logout(self) -> None:
                return None

            async def next_notification(self, timeout_seconds: float | None = None) -> object:
                await asyncio.Event().wait()
                raise AssertionError("inalcancavel")

            async def close(self) -> None:
                self.available = False

        fake = FakeClient()

        async def start_fake(*args: object, **kwargs: object) -> FakeClient:
            return fake

        runtime = AgentRuntime(
            _settings(enabled=True, executable=Path("C:/fake-codex.exe")), start_fake
        )
        await runtime.start()
        first = asyncio.create_task(runtime.diagnose())
        second = asyncio.create_task(runtime.diagnose())
        await models_started.wait()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert not second.done()
        release_models.set()
        assert (await second)["state"] == "CONECTADO"
        await runtime.close()

    asyncio.run(scenario())


def _rotas(app: FastAPI) -> set[str]:
    return {getattr(r, "path", "") for r in app.routes}


def test_ingress_ausente_sem_configuracao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_TENANT_ID", raising=False)
    monkeypatch.delenv("AGENT_INSTANCIA_ID", raising=False)
    app = create_agent_app(_settings(enabled=False, executable=Path("C:/missing.exe")))
    assert "/whatsapp/webhook" not in _rotas(app)


def test_ingress_montado_com_configuracao(monkeypatch: pytest.MonkeyPatch) -> None:
    import uuid

    monkeypatch.setenv("AGENT_TENANT_ID", str(uuid.uuid4()))
    monkeypatch.setenv("AGENT_INSTANCIA_ID", "inst-evolution-1")
    monkeypatch.setenv("COPILOT_OPERATOR_ALLOWLIST", "5511999999999")
    app = create_agent_app(_settings(enabled=False, executable=Path("C:/missing.exe")))
    with TestClient(app) as client:
        resposta = client.post("/whatsapp/webhook", content=b"nao-json")
        assert resposta.status_code == 400


def test_ingress_recusa_tenant_invalido(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_TENANT_ID", "nao-uuid")
    monkeypatch.setenv("AGENT_INSTANCIA_ID", "inst-evolution-1")
    with pytest.raises(RuntimeError):
        create_agent_app(_settings(enabled=False, executable=Path("C:/missing.exe")))


def test_porta_http_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    from emprestimo.agent.server import porta_http

    monkeypatch.delenv("TIANET_AGENT_HTTP_PORT", raising=False)
    assert porta_http() is None
    monkeypatch.setenv("TIANET_AGENT_HTTP_PORT", "8010")
    assert porta_http() == 8010
    monkeypatch.setenv("TIANET_AGENT_HTTP_PORT", "0")
    with pytest.raises(RuntimeError):
        porta_http()
    monkeypatch.setenv("TIANET_AGENT_HTTP_PORT", "abc")
    with pytest.raises(RuntimeError):
        porta_http()
