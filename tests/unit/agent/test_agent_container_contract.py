from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def _compose_config() -> dict[str, Any]:
    environment = os.environ.copy()
    environment.update(
        {
            "POSTGRES_PASSWORD": "compose-test-password",
            "JWT_SECRET_KEY": "compose-test-jwt",
            "FRONTEND_SESSION_KEY_ID": "compose-test",
            "FRONTEND_SESSION_KEY": "x" * 43,
            "TIANET_AGENT_INTERNAL_SECRET": "s" * 32,
        }
    )
    completed = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    value: object = json.loads(completed.stdout)
    assert isinstance(value, dict)
    return value


def test_agent_fica_em_rede_e_volume_exclusivos_sem_porta_publicada() -> None:
    config = _compose_config()
    agent = config["services"]["agent"]
    assert set(agent["networks"]) == {"agent-egress"}
    # Loopback publicado não é porta pública: só o Caddy do host alcança;
    # qualquer bind fora de 127.0.0.1 continua proibido (ingress WhatsApp).
    for publicada in agent.get("ports", []):
        assert publicada.get("host_ip", "") == "127.0.0.1", publicada
    assert agent["read_only"] is True
    assert agent["cap_drop"] == ["ALL"]
    assert agent["security_opt"] == ["no-new-privileges:true"]
    assert agent["environment"]["TIANET_AGENT_ENABLED"] == "false"
    assert agent["volumes"] == [
        {
            "type": "volume",
            "source": "agent-codex-data",
            "target": "/var/lib/tianet-agent/codex",
            "volume": {},
        },
        {
            "type": "volume",
            "source": "agent-runtime",
            "target": "/run/tianet-agent",
            "volume": {},
        },
    ]
    assert config["services"]["api"]["volumes"] == [
        {
            "type": "volume",
            "source": "agent-runtime",
            "target": "/run/tianet-agent",
            "read_only": True,
            "volume": {},
        }
    ]
    for service_name in ("api", "postgres", "worker", "migrate"):
        assert "agent-egress" not in config["services"][service_name]["networks"]


def test_compose_carrega_com_agent_desligado_e_sem_segredo() -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "POSTGRES_PASSWORD": "compose-test-password",
            "JWT_SECRET_KEY": "compose-test-jwt",
            "FRONTEND_SESSION_KEY_ID": "compose-test",
            "FRONTEND_SESSION_KEY": "x" * 43,
            "TIANET_AGENT_ENABLED": "false",
            "TIANET_AGENT_INTERNAL_SECRET": "",
        }
    )
    completed = subprocess.run(
        ["docker", "compose", "config", "--quiet"],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_imagem_fixa_cli_oficial_e_executa_com_usuario_sem_privilegio() -> None:
    dockerfile = (ROOT / "Dockerfile.agent").read_text(encoding="utf-8")
    assert "ARG CODEX_VERSION=0.146.1" in dockerfile
    assert "ARG CODEX_SHA256=" in dockerfile
    assert "github.com/openai/codex/releases/download/" in dockerfile
    assert "rust-v{version}/codex-x86_64-unknown-linux-musl.tar.gz" in dockerfile
    assert "hashlib.sha256(archive).hexdigest() != expected" in dockerfile
    assert "codex --version" in dockerfile
    assert "USER app" not in dockerfile
    assert "USER agent" in dockerfile
    assert "COPY docs" not in dockerfile
    assert "COPY migrations" not in dockerfile
    assert "COPY src ./src" not in dockerfile
    assert "COPY src/emprestimo/agent ./emprestimo/agent" in dockerfile
    assert "--require-hashes" in dockerfile
    assert "ghcr.io/astral-sh/uv@sha256:" in dockerfile
    assert "generate-json-schema" in dockerfile
    assert 'CMD ["python", "-m", "emprestimo.agent.server", "serve"]' in dockerfile
