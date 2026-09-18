"""Inicialização e healthcheck do listener HTTP sobre socket Unix."""

from __future__ import annotations

import os
import socket
import stat
import sys
from pathlib import Path
from typing import Any

import uvicorn

DEFAULT_SOCKET_PATH = Path("/run/tianet-agent/agent.sock")
MAX_HEALTH_RESPONSE = 16 * 1024
UNIX_SOCKET_FAMILY: Any = getattr(
    socket, "AF_UNIX", None
)  # noqa: B009 -- ausente nos stubs Windows
# Dentro do container, 127.0.0.1 alcançaria só o próprio loopback e o
# publish do compose (mesmo em 127.0.0.1 do host) nunca chegaria: o DNAT
# entrega no IP do container, que o socket de loopback recusa. Por isso o
# bind é 0.0.0.0 AQUI e o perímetro fica no compose, que publica só em
# 127.0.0.1 do host — exposição pública continua papel do proxy.
BIND_HOST = "0.0.0.0"


def socket_path() -> Path:
    path = Path(os.environ.get("TIANET_AGENT_SOCKET", str(DEFAULT_SOCKET_PATH)))
    if not path.is_absolute():
        raise RuntimeError("TIANET_AGENT_SOCKET deve ser absoluto")
    return path


def prepare_socket(path: Path) -> None:
    """Remove somente um socket residual comprovadamente sem listener."""
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    path.parent.chmod(0o750)
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISSOCK(metadata.st_mode):
        raise RuntimeError("caminho do socket ocupado por entrada insegura")
    probe = socket.socket(UNIX_SOCKET_FAMILY, socket.SOCK_STREAM)
    probe.settimeout(0.5)
    try:
        probe.connect(str(path))
    except (ConnectionRefusedError, FileNotFoundError):
        current = path.lstat()
        if current.st_ino != metadata.st_ino or not stat.S_ISSOCK(current.st_mode):
            raise RuntimeError("socket mudou durante a verificacao") from None
        path.unlink()
    else:
        raise RuntimeError("ja existe um listener ativo no socket")
    finally:
        probe.close()


def porta_http() -> int | None:
    """Porta TCP do ingress, ou None para socket Unix exclusivo.

    Ausente = comportamento atual preservado (só socket). Quando definida,
    o bind é 0.0.0.0 no container e o perímetro fica no compose, que publica
    só em 127.0.0.1 do host — exposição pública é papel do proxy.
    """
    bruto = os.environ.get("TIANET_AGENT_HTTP_PORT", "").strip()
    if not bruto:
        return None
    try:
        porta = int(bruto)
    except ValueError as exc:
        raise RuntimeError("TIANET_AGENT_HTTP_PORT deve ser inteiro") from exc
    if not 1 <= porta <= 65535:
        raise RuntimeError("TIANET_AGENT_HTTP_PORT fora do intervalo")
    return porta


def serve() -> None:
    porta = porta_http()
    if porta is not None:
        uvicorn.run(
            "emprestimo.agent.service:create_agent_app",
            factory=True,
            host=BIND_HOST,
            port=porta,
            limit_concurrency=16,
            timeout_keep_alive=5,
            h11_max_incomplete_event_size=1024 * 1024,
        )
        return
    path = socket_path()
    prepare_socket(path)
    os.umask(0o007)
    listener = socket.socket(UNIX_SOCKET_FAMILY, socket.SOCK_STREAM)
    try:
        listener.bind(str(path))
        path.chmod(0o660)
        listener.listen(32)
        uvicorn.run(
            "emprestimo.agent.service:create_agent_app",
            factory=True,
            fd=listener.fileno(),
            limit_concurrency=16,
            timeout_keep_alive=5,
            h11_max_incomplete_event_size=1024 * 1024,
        )
    finally:
        listener.close()


def health() -> None:
    client = socket.socket(UNIX_SOCKET_FAMILY, socket.SOCK_STREAM)
    client.settimeout(2)
    try:
        client.connect(str(socket_path()))
        client.sendall(b"GET /health HTTP/1.1\r\nHost: agent\r\nConnection: close\r\n\r\n")
        response = client.recv(MAX_HEALTH_RESPONSE)
    finally:
        client.close()
    if not response.startswith(b"HTTP/1.1 200"):
        raise SystemExit(1)


if __name__ == "__main__":
    command = sys.argv[1:] or ["serve"]
    if command == ["serve"]:
        serve()
    elif command == ["health"]:
        health()
    else:
        raise SystemExit("uso: python -m emprestimo.agent.server [serve|health]")
