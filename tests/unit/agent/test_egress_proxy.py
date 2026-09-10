from __future__ import annotations

import asyncio

import pytest

from emprestimo.agent import egress_proxy
from emprestimo.agent.egress_proxy import parse_connect_request, resolve_public_addresses


def test_proxy_aceita_somente_connect_https_para_allowlist() -> None:
    assert (
        parse_connect_request(
            b"CONNECT auth.openai.com:443 HTTP/1.1\r\nHost: auth.openai.com\r\n\r\n"
        )
        == "auth.openai.com"
    )
    for request in (
        b"CONNECT host.docker.internal:8000 HTTP/1.1\r\n\r\n",
        b"CONNECT api:8000 HTTP/1.1\r\n\r\n",
        b"GET https://auth.openai.com/ HTTP/1.1\r\n\r\n",
        b"CONNECT evil-openai.com:443 HTTP/1.1\r\n\r\n",
    ):
        with pytest.raises(PermissionError):
            parse_connect_request(request)


def test_proxy_recusa_resolucao_para_endereco_privado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_getaddrinfo(*args: object, **kwargs: object) -> list[tuple[object, ...]]:
        return [(2, 1, 6, "", ("127.0.0.1", 443))]

    async def scenario() -> None:
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(PermissionError, match="nao publico"):
            await resolve_public_addresses("auth.openai.com")

    asyncio.run(scenario())


def test_proxy_recusa_conexao_quando_teto_esta_ocupado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        semaphore = asyncio.Semaphore(1)
        await semaphore.acquire()
        monkeypatch.setattr(egress_proxy, "_ACTIVE_TUNNELS", semaphore)
        monkeypatch.setattr(egress_proxy, "ADMISSION_TIMEOUT_SECONDS", 0.01)
        server = await asyncio.start_server(egress_proxy.handle_client, "127.0.0.1", 0)
        try:
            port = server.sockets[0].getsockname()[1]
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"CONNECT auth.openai.com:443 HTTP/1.1\r\n\r\n")
            await writer.drain()
            response = await reader.read(100)
            assert response.startswith(b"HTTP/1.1 503")
            writer.close()
            await writer.wait_closed()
        finally:
            semaphore.release()
            server.close()
            await server.wait_closed()

    asyncio.run(scenario())
