"""Cliente LLM BYOK — rota A (IMP-356-D lote 2, slice 1).

Fala `POST {base_url}/chat/completions` com `httpx`, sem SDK. Módulo
separado do `api_client.py` de propósito: bearer do provedor nunca cruza
com bearer copilot, e cada base tem seu timeout e seus erros fechados.
Sem retry de inferência (`LLM_MAX_RETRIES=0`): erro degrada, nunca
re-cobra. Segredo nunca aparece em exceção, log ou teste.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from emprestimo.agent.catalogo import CATALOGO, CATALOGO_VERSAO

TIMEOUT_PADRAO_SEGUNDOS = 15.0
MAX_TOKENS_SAIDA_PADRAO = 1000

# Famílias que rejeitam `max_tokens` e exigem `max_completion_tokens`.
MODELOS_TETO_COMPLETION = ("gpt-5", "o1", "o3")


def parametro_teto_saida(modelo: str) -> str:
    """Nome do parâmetro de teto de saída aceito pelo modelo."""
    if modelo.startswith(MODELOS_TETO_COMPLETION):
        return "max_completion_tokens"
    return "max_tokens"


class LlmError(Exception):
    """Falha fechada do provedor — degrada, nunca tenta outro modelo/rota."""


class LlmIndisponivelError(LlmError):
    """Transporte, timeout, HTTP não-2xx: provedor indisponível."""


class LlmLimiteError(LlmIndisponivelError):
    """429: a chamada não executou (sem cobrança, sem incerteza).

    Distinta para o harness poder espacar e continuar; no produto,
    degrada como indisponibilidade — nunca retry automático de
    inferência incerta.
    """


class LlmRespostaInvalidaError(LlmError):
    """200 com corpo fora do schema: resposta inutilizável."""


@dataclass(frozen=True)
class Mensagem:
    papel: str
    conteudo: str


@dataclass(frozen=True)
class Uso:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ChamadaFerramenta:
    id: str
    nome: str
    argumentos: str  # JSON cru; parse/validação pertencem ao slice 2


@dataclass(frozen=True)
class RespostaChat:
    texto: str | None
    chamadas: tuple[ChamadaFerramenta, ...]
    uso: Uso | None


@dataclass(frozen=True)
class PedidoChat:
    mensagens: tuple[Mensagem, ...]
    ferramentas: tuple[dict[str, Any], ...]
    max_tokens_saida: int = MAX_TOKENS_SAIDA_PADRAO


def montar_tools() -> list[dict[str, Any]]:
    """Gera `tools[]` do function calling a partir do catálogo frozen.

    Nomes, descrições e schemas vêm de literais revisados — o modelo nunca
    define ferramenta. Dinheiro e data trafegam como string.
    """
    ferramentas: list[dict[str, Any]] = []
    for ferramenta in CATALOGO.values():
        propriedades: dict[str, Any] = {}
        obrigatorios: list[str] = []
        for nome, restricao in ferramenta.argumentos.items():
            if restricao.tipo == "texto":
                propriedades[nome] = {
                    "type": "string",
                    "minLength": restricao.minimo,
                    "maxLength": restricao.maximo,
                }
            elif restricao.tipo == "data":
                propriedades[nome] = {"type": "string", "format": "date"}
            else:  # pragma: no cover - catálogo fechado, tipo sempre conhecido
                raise LlmError("tipo de argumento desconhecido no catalogo")
            if restricao.obrigatorio:
                obrigatorios.append(nome)
        ferramentas.append(
            {
                "type": "function",
                "function": {
                    "name": ferramenta.nome,
                    "description": ferramenta.descricao,
                    "parameters": {
                        "type": "object",
                        "properties": propriedades,
                        "required": obrigatorios,
                        "additionalProperties": False,
                    },
                },
            }
        )
    return ferramentas


def _uso_de(corpo: Mapping[str, Any]) -> Uso | None:
    uso = corpo.get("usage")
    if uso is None:
        return None
    if not isinstance(uso, Mapping):
        raise LlmRespostaInvalidaError("usage invalido")
    try:
        return Uso(
            prompt_tokens=int(uso["prompt_tokens"]),
            completion_tokens=int(uso["completion_tokens"]),
            total_tokens=int(uso["total_tokens"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LlmRespostaInvalidaError("usage invalido") from exc


def _resposta_de(corpo: Mapping[str, Any]) -> RespostaChat:
    escolhas = corpo.get("choices")
    if not isinstance(escolhas, list) or not escolhas:
        raise LlmRespostaInvalidaError("sem choices")
    primeira = escolhas[0]
    if not isinstance(primeira, Mapping):
        raise LlmRespostaInvalidaError("choice invalido")
    mensagem = primeira.get("message")
    if not isinstance(mensagem, Mapping):
        raise LlmRespostaInvalidaError("message invalida")
    texto = mensagem.get("content")
    if texto is not None and not isinstance(texto, str):
        raise LlmRespostaInvalidaError("content invalido")
    brutas = mensagem.get("tool_calls") or []
    if not isinstance(brutas, list):
        raise LlmRespostaInvalidaError("tool_calls invalido")
    chamadas: list[ChamadaFerramenta] = []
    for bruta in brutas:
        if not isinstance(bruta, Mapping):
            raise LlmRespostaInvalidaError("tool_call invalido")
        funcao = bruta.get("function")
        if not isinstance(funcao, Mapping):
            raise LlmRespostaInvalidaError("function invalida")
        nome = funcao.get("name")
        argumentos = funcao.get("arguments")
        if not isinstance(nome, str) or not nome or not isinstance(argumentos, str):
            raise LlmRespostaInvalidaError("function invalida")
        chamadas.append(
            ChamadaFerramenta(id=str(bruta.get("id", "")), nome=nome, argumentos=argumentos)
        )
    return RespostaChat(texto=texto, chamadas=tuple(chamadas), uso=_uso_de(corpo))


class LlmClient:
    def __init__(
        self,
        base_url: str,
        modelo: str,
        provedor_chave: Callable[[], str],
        timeout_segundos: float = TIMEOUT_PADRAO_SEGUNDOS,
        transporte: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if timeout_segundos <= 0:
            raise LlmError("timeout deve ser positivo")
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_segundos),
            transport=transporte,
        )
        self._modelo = modelo
        self._provedor_chave = provedor_chave

    async def chat(self, pedido: PedidoChat, timeout_segundos: float | None = None) -> RespostaChat:
        corpo_pedido = {
            "model": self._modelo,
            "messages": [
                {"role": mensagem.papel, "content": mensagem.conteudo}
                for mensagem in pedido.mensagens
            ],
            "tools": list(pedido.ferramentas),
            "tool_choice": "auto",
            parametro_teto_saida(self._modelo): pedido.max_tokens_saida,
        }
        timeout = httpx.Timeout(timeout_segundos) if timeout_segundos is not None else None
        try:
            resposta = await self._client.post(
                "/chat/completions",
                json=corpo_pedido,
                headers={"Authorization": f"Bearer {self._provedor_chave()}"},
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise LlmIndisponivelError("tempo esgotado no provedor") from exc
        except httpx.HTTPError as exc:
            raise LlmIndisponivelError("falha de transporte no provedor") from exc
        if resposta.status_code in (401, 403):
            raise LlmIndisponivelError("credencial do provedor recusada")
        if resposta.status_code == 429:
            raise LlmLimiteError("cota do provedor esgotada")
        if not 200 <= resposta.status_code < 300:
            raise LlmIndisponivelError("provedor indisponivel")
        try:
            corpo = resposta.json()
        except ValueError as exc:
            raise LlmRespostaInvalidaError("corpo ilegivel") from exc
        if not isinstance(corpo, dict):
            raise LlmRespostaInvalidaError("corpo invalido")
        return _resposta_de(corpo)

    async def close(self) -> None:
        await self._client.aclose()


__all__ = [
    "CATALOGO_VERSAO",
    "ChamadaFerramenta",
    "LlmClient",
    "LlmError",
    "LlmIndisponivelError",
    "LlmLimiteError",
    "LlmRespostaInvalidaError",
    "MAX_TOKENS_SAIDA_PADRAO",
    "Mensagem",
    "PedidoChat",
    "RespostaChat",
    "TIMEOUT_PADRAO_SEGUNDOS",
    "Uso",
    "montar_tools",
    "parametro_teto_saida",
]
