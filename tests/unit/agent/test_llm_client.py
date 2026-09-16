"""Cliente LLM BYOK (IMP-356-D lote 2, slice 1).

Tudo contra `httpx.MockTransport`: nenhuma chamada real sai daqui. As
provas miram os riscos do slice — bearer, erros fechados sem segredo,
schema estrito e `tools[]` espelhando o catálogo frozen.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from emprestimo.agent.catalogo import CATALOGO
from emprestimo.agent.llm_client import (
    LlmClient,
    LlmError,
    LlmIndisponivelError,
    LlmRespostaInvalidaError,
    Mensagem,
    PedidoChat,
    montar_tools,
    parametro_teto_saida,
)
from emprestimo.agent.service import LlmSettings

CHAVE = "sk-projeto-de-teste-com-mais-de-32-caracteres"


def _cliente(respostas: Any, timeout_segundos: float = 15.0) -> LlmClient:
    if not isinstance(respostas, list):
        respostas = [respostas]

    def _handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {CHAVE}"
        assert str(request.url).endswith("/chat/completions")
        item = respostas.pop(0)
        if isinstance(item, Exception):
            raise item
        status, corpo = item
        return httpx.Response(status, json=corpo)

    return LlmClient(
        "https://api.exemplo/v1",
        "modelo-teste",
        lambda: CHAVE,
        timeout_segundos=timeout_segundos,
        transporte=httpx.MockTransport(_handler),
    )


def _pedido() -> PedidoChat:
    return PedidoChat(
        mensagens=(Mensagem(papel="user", conteudo="quanto devo?"),),
        ferramentas=tuple(montar_tools()),
    )


def _ok(tool_calls: Any = None, sem_uso: bool = False) -> tuple[int, dict[str, Any]]:
    mensagem: dict[str, Any] = {"role": "assistant", "content": None}
    if tool_calls is not None:
        mensagem["tool_calls"] = tool_calls
    corpo: dict[str, Any] = {"choices": [{"message": mensagem}]}
    if not sem_uso:
        corpo["usage"] = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }
    return 200, corpo


def test_tools_espelha_catalogo_frozen() -> None:
    ferramentas = montar_tools()
    assert [f["function"]["name"] for f in ferramentas] == list(CATALOGO)
    for ferramenta in ferramentas:
        assert ferramenta["type"] == "function"
        parametros = ferramenta["function"]["parameters"]
        assert parametros["additionalProperties"] is False
        for esquema in parametros["properties"].values():
            assert esquema["type"] == "string"
    assert ferramentas


def test_parametro_de_teto_por_familia_de_modelo() -> None:
    assert parametro_teto_saida("gpt-4o-mini") == "max_tokens"
    assert parametro_teto_saida("gpt-4.1-mini-2025-04-14") == "max_tokens"
    assert parametro_teto_saida("gpt-5-mini") == "max_completion_tokens"
    assert parametro_teto_saida("gpt-5-mini-2025-08-07") == "max_completion_tokens"
    assert parametro_teto_saida("o3-mini") == "max_completion_tokens"


def test_cliente_5_mini_envia_max_completion_tokens() -> None:
    vistos: dict[str, Any] = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        import json

        vistos.update(json.loads(request.content.decode()))
        status, corpo = _ok()
        return httpx.Response(status, json=corpo)

    cliente = LlmClient(
        "https://api.exemplo/v1",
        "gpt-5-mini-2025-08-07",
        lambda: CHAVE,
        transporte=httpx.MockTransport(_handler),
    )

    async def _cenario() -> None:
        await cliente.chat(_pedido())
        await cliente.close()

    asyncio.run(_cenario())
    assert "max_tokens" not in vistos
    assert vistos["max_completion_tokens"] == 1000


def test_pedido_envia_modelo_tools_e_teto() -> None:
    vistos: dict[str, Any] = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        import json

        vistos.update(json.loads(request.content.decode()))
        status, corpo = _ok()
        return httpx.Response(status, json=corpo)

    cliente = LlmClient(
        "https://api.exemplo/v1",
        "modelo-teste",
        lambda: CHAVE,
        transporte=httpx.MockTransport(_handler),
    )

    async def _cenario() -> None:
        await cliente.chat(_pedido())
        await cliente.close()

    asyncio.run(_cenario())
    assert vistos["model"] == "modelo-teste"
    assert vistos["tool_choice"] == "auto"
    assert vistos["max_tokens"] == 1000
    assert len(vistos["tools"]) == len(CATALOGO)


def test_chat_com_tool_call_parseia_nome_argumentos_e_uso() -> None:
    chamada = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "localizar_devedor", "arguments": '{"nome": "ana"}'},
    }
    cliente = _cliente(_ok([chamada]))

    async def _cenario() -> Any:
        try:
            return await cliente.chat(_pedido())
        finally:
            await cliente.close()

    resposta = asyncio.run(_cenario())
    assert resposta.texto is None
    assert len(resposta.chamadas) == 1
    assert resposta.chamadas[0].nome == "localizar_devedor"
    assert resposta.chamadas[0].argumentos == '{"nome": "ana"}'
    assert resposta.uso is not None and resposta.uso.total_tokens == 15


def test_chat_texto_puro_sem_chamadas() -> None:
    cliente = _cliente((200, {"choices": [{"message": {"role": "assistant", "content": "oi"}}]}))

    async def _cenario() -> Any:
        try:
            return await cliente.chat(_pedido())
        finally:
            await cliente.close()

    resposta = asyncio.run(_cenario())
    assert resposta.texto == "oi"
    assert resposta.chamadas == ()
    assert resposta.uso is None


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_http_nao_2xx_vira_indisponivel_sem_vazar(status: int) -> None:
    cliente = _cliente((status, {"error": "detalhe interno"}))

    async def _cenario() -> None:
        with pytest.raises(LlmIndisponivelError) as ctx:
            await cliente.chat(_pedido())
        await cliente.close()
        assert CHAVE not in str(ctx.value)
        assert "detalhe interno" not in str(ctx.value)

    asyncio.run(_cenario())


def test_timeout_vira_indisponivel() -> None:
    cliente = _cliente(httpx.ConnectTimeout("lento"))

    async def _cenario() -> None:
        with pytest.raises(LlmIndisponivelError):
            await cliente.chat(_pedido())
        await cliente.close()

    asyncio.run(_cenario())


def test_429_vira_limite_distinto_sem_conteudo() -> None:
    from emprestimo.agent.llm_client import LlmLimiteError

    cliente = _cliente((429, {"error": {"message": "quota", "code": "rate_limit"}}))

    async def _cenario() -> None:
        with pytest.raises(LlmLimiteError) as ctx:
            await cliente.chat(_pedido())
        await cliente.close()
        assert isinstance(ctx.value, LlmIndisponivelError)
        assert "quota" not in str(ctx.value)


@pytest.mark.parametrize(
    "corpo",
    [
        {"sem": "choices"},
        {"choices": []},
        {"choices": [{"message": {"role": "assistant", "content": 123}}]},
        {"choices": [{"message": {"role": "assistant", "tool_calls": [{"id": "x"}]}}]},
        {"choices": [{"message": {"role": "assistant", "tool_calls": "nao-lista"}}]},
    ],
)
def test_corpo_fora_do_schema_vira_resposta_invalida(corpo: dict[str, Any]) -> None:
    cliente = _cliente((200, corpo))

    async def _cenario() -> None:
        with pytest.raises(LlmRespostaInvalidaError):
            await cliente.chat(_pedido())
        await cliente.close()

    asyncio.run(_cenario())


def test_timeout_invalido_recusado_na_construcao() -> None:
    with pytest.raises(LlmError):
        LlmClient("https://api.exemplo/v1", "m", lambda: CHAVE, timeout_segundos=0)


def test_settings_padrao_desligado_e_validacao_fechada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variavel in (
        "LLM_ENABLED",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "LLM_API_KEY",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_RETRIES",
        "LLM_MAX_TOKENS_SAIDA",
    ):
        monkeypatch.delenv(variavel, raising=False)
    padrao = LlmSettings.from_environment()
    assert padrao.enabled is False
    assert padrao.base_url == "https://api.openai.com/v1"
    assert padrao.model == "gpt-4o-mini"
    assert padrao.timeout_seconds == 15.0
    assert padrao.max_retries == 0

    monkeypatch.setenv("LLM_ENABLED", "true")
    with pytest.raises(RuntimeError):
        LlmSettings.from_environment()
    monkeypatch.setenv("LLM_API_KEY", CHAVE)
    ligado = LlmSettings.from_environment()
    assert ligado.enabled is True and ligado.api_key == CHAVE

    for variavel, valor in (
        ("LLM_TIMEOUT_SECONDS", "0"),
        ("LLM_TIMEOUT_SECONDS", "quinze"),
        ("LLM_MAX_RETRIES", "1"),
        ("LLM_MAX_RETRIES", "-1"),
        ("LLM_MAX_TOKENS_SAIDA", "0"),
    ):
        monkeypatch.setenv(variavel, valor)
        with pytest.raises(RuntimeError):
            LlmSettings.from_environment()
        monkeypatch.delenv(variavel, raising=False)
