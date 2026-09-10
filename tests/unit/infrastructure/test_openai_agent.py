from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from emprestimo.application.openai_conexao import OpenAIAgentProtocolError
from emprestimo.infrastructure.openai_agent import MAX_RESPONSE_BYTES, OpenAIAgentClient

SECRET = "s" * 32


def test_cliente_valida_dto_fechado_e_envia_segredo() -> None:
    async def scenario() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["X-TiaNet-Agent-Secret"] == SECRET
            assert request.url.path == "/internal/openai/conexao"
            return httpx.Response(
                200,
                json={
                    "enabled": True,
                    "processAvailable": True,
                    "accountConnected": False,
                    "planType": None,
                    "startupError": False,
                    "state": "DESCONECTADO",
                    "usageSummary": None,
                },
            )

        client = OpenAIAgentClient(
            Path("C:/run/tianet-agent/agent.sock"),
            SECRET,
            transport=httpx.MockTransport(handler),
        )
        try:
            result = await client.connection()
            assert result.state == "DESCONECTADO"
            assert result.account_connected is False
        finally:
            await client.close()

    asyncio.run(scenario())


def test_login_recusa_host_fora_da_openai() -> None:
    async def scenario() -> None:
        transport = httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "verificationUrl": "https://example.com/device",
                    "userCode": "ABCD",
                    "expiresAt": "2026-09-10T00:00:00+00:00",
                },
            )
        )
        client = OpenAIAgentClient(
            Path("C:/run/tianet-agent/agent.sock"), SECRET, transport=transport
        )
        try:
            with pytest.raises(OpenAIAgentProtocolError, match="host"):
                await client.begin_login()
        finally:
            await client.close()

    asyncio.run(scenario())


def test_resposta_acima_do_limite_falha_fechada() -> None:
    async def scenario() -> None:
        transport = httpx.MockTransport(
            lambda _: httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))
        )
        client = OpenAIAgentClient(
            Path("C:/run/tianet-agent/agent.sock"), SECRET, transport=transport
        )
        try:
            with pytest.raises(OpenAIAgentProtocolError, match="limite"):
                await client.connection()
        finally:
            await client.close()

    asyncio.run(scenario())
