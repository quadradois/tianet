"""Proxy CONNECT mínimo que limita o egress do processo Codex à OpenAI."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import sys
from collections.abc import Iterable
from contextlib import suppress

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8080
HEADER_LIMIT = 8 * 1024
CONNECT_TIMEOUT_SECONDS = 10
WRITE_TIMEOUT_SECONDS = 5
IDLE_TIMEOUT_SECONDS = 60
MAX_TUNNEL_BYTES = 8 * 1024 * 1024
MAX_ACTIVE_TUNNELS = 16
ADMISSION_TIMEOUT_SECONDS = 0.1
ALLOWED_HOSTS = frozenset(
    {
        "auth.openai.com",
        "api.openai.com",
        "chatgpt.com",
    }
)
_ACTIVE_TUNNELS = asyncio.Semaphore(MAX_ACTIVE_TUNNELS)


def parse_connect_request(header: bytes) -> str:
    if len(header) > HEADER_LIMIT or not header.endswith(b"\r\n\r\n"):
        raise ValueError("cabecalho invalido")
    try:
        request_line = header.split(b"\r\n", 1)[0].decode("ascii")
        method, authority, version = request_line.split(" ")
        host, port = authority.rsplit(":", 1)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("requisicao invalida") from exc
    normalized_host = host.lower().rstrip(".")
    if (
        method != "CONNECT"
        or version not in {"HTTP/1.0", "HTTP/1.1"}
        or port != "443"
        or normalized_host not in ALLOWED_HOSTS
    ):
        raise PermissionError("destino nao permitido")
    return normalized_host


async def resolve_public_addresses(host: str) -> tuple[tuple[int, str], ...]:
    loop = asyncio.get_running_loop()
    records = await loop.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    addresses: list[tuple[int, str]] = []
    for family, _, _, _, sockaddr in records:
        address = str(sockaddr[0])
        if not ipaddress.ip_address(address).is_global:
            raise PermissionError("resolucao retornou endereco nao publico")
        item = (family, address)
        if item not in addresses:
            addresses.append(item)
    if not addresses:
        raise OSError("destino sem endereco")
    return tuple(addresses)


async def open_allowed_upstream(host: str) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    last_error: OSError | None = None
    addresses = await asyncio.wait_for(
        resolve_public_addresses(host), timeout=CONNECT_TIMEOUT_SECONDS
    )
    for family, address in addresses:
        try:
            return await asyncio.wait_for(
                asyncio.open_connection(address, 443, family=family),
                timeout=CONNECT_TIMEOUT_SECONDS,
            )
        except OSError as exc:
            last_error = exc
    raise last_error or OSError("nao foi possivel conectar")


async def relay(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    transferred = 0
    while True:
        chunk = await asyncio.wait_for(
            reader.read(min(64 * 1024, MAX_TUNNEL_BYTES - transferred + 1)),
            timeout=IDLE_TIMEOUT_SECONDS,
        )
        if not chunk:
            return
        transferred += len(chunk)
        if transferred > MAX_TUNNEL_BYTES:
            raise ValueError("tunel excedeu o limite")
        writer.write(chunk)
        await asyncio.wait_for(writer.drain(), timeout=WRITE_TIMEOUT_SECONDS)


async def close_writers(writers: Iterable[asyncio.StreamWriter]) -> None:
    materialized = tuple(writers)
    for writer in materialized:
        writer.close()
    await asyncio.gather(
        *(
            asyncio.wait_for(writer.wait_closed(), timeout=WRITE_TIMEOUT_SECONDS)
            for writer in materialized
        ),
        return_exceptions=True,
    )


async def respond(writer: asyncio.StreamWriter, response: bytes) -> None:
    with suppress(OSError, TimeoutError):
        writer.write(response)
        await asyncio.wait_for(writer.drain(), timeout=WRITE_TIMEOUT_SECONDS)


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    try:
        await asyncio.wait_for(_ACTIVE_TUNNELS.acquire(), timeout=ADMISSION_TIMEOUT_SECONDS)
    except TimeoutError:
        await respond(
            writer,
            b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\n\r\n",
        )
        await close_writers((writer,))
        return
    try:
        await _handle_admitted_client(reader, writer)
    finally:
        _ACTIVE_TUNNELS.release()


async def _handle_admitted_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    upstream_writer: asyncio.StreamWriter | None = None
    try:
        header = await asyncio.wait_for(
            reader.readuntil(b"\r\n\r\n"), timeout=CONNECT_TIMEOUT_SECONDS
        )
        host = parse_connect_request(header)
        upstream_reader, upstream_writer = await open_allowed_upstream(host)
        await respond(writer, b"HTTP/1.1 200 Connection Established\r\n\r\n")
        client_to_upstream = asyncio.create_task(relay(reader, upstream_writer))
        upstream_to_client = asyncio.create_task(relay(upstream_reader, writer))
        done, pending = await asyncio.wait(
            {client_to_upstream, upstream_to_client},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*done, *pending, return_exceptions=True)
    except PermissionError:
        await respond(writer, b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
    except asyncio.IncompleteReadError:
        return
    except (TimeoutError, OSError, ValueError, asyncio.LimitOverrunError):
        await respond(writer, b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
    finally:
        await close_writers(item for item in (writer, upstream_writer) if item is not None)


async def serve() -> None:
    server = await asyncio.start_server(
        handle_client,
        LISTEN_HOST,
        LISTEN_PORT,
        backlog=32,
        limit=HEADER_LIMIT,
    )
    async with server:
        await server.serve_forever()


async def health() -> None:
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection("127.0.0.1", LISTEN_PORT),
        timeout=2,
    )
    writer.write(b"CONNECT health.invalid:443 HTTP/1.1\r\n\r\n")
    await asyncio.wait_for(writer.drain(), timeout=WRITE_TIMEOUT_SECONDS)
    response = await asyncio.wait_for(reader.read(80), timeout=2)
    await close_writers((writer,))
    if not response.startswith(b"HTTP/1.1 403"):
        raise SystemExit(1)


if __name__ == "__main__":
    command = sys.argv[1:] or ["serve"]
    if command == ["serve"]:
        asyncio.run(serve())
    elif command == ["health"]:
        asyncio.run(health())
    else:
        raise SystemExit("uso: python -m emprestimo.agent.egress_proxy [serve|health]")
