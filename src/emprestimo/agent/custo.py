"""Estimativa de custo de inferência (IMP-356-D lote 2, slice 3).

DR-005 §3: sem teto em moeda — o sistema observa e alerta, nunca bloqueia.
Tabela versionada por modelo; modelo desconhecido custa desconhecido
(`None`), nunca zero. Aritmética em Decimal; preço nunca vai para log
junto de prompt — aqui só entram contagens.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

TABELA_PRECOS_VERSAO = "precos_openai_2026_09"

TOKENS_POR_MILHAO = Decimal(1_000_000)


@dataclass(frozen=True)
class PrecoModelo:
    entrada_usd_por_milhao: Decimal
    saida_usd_por_milhao: Decimal


TABELA_PRECOS: dict[str, PrecoModelo] = {
    "gpt-4o-mini": PrecoModelo(
        entrada_usd_por_milhao=Decimal("0.15"),
        saida_usd_por_milhao=Decimal("0.60"),
    ),
    "gpt-4.1-mini": PrecoModelo(
        entrada_usd_por_milhao=Decimal("0.40"),
        saida_usd_por_milhao=Decimal("1.60"),
    ),
    "gpt-4.1-mini-2025-04-14": PrecoModelo(
        entrada_usd_por_milhao=Decimal("0.40"),
        saida_usd_por_milhao=Decimal("1.60"),
    ),
    "gpt-5-mini": PrecoModelo(
        entrada_usd_por_milhao=Decimal("0.25"),
        saida_usd_por_milhao=Decimal("2.00"),
    ),
    "gpt-5-mini-2025-08-07": PrecoModelo(
        entrada_usd_por_milhao=Decimal("0.25"),
        saida_usd_por_milhao=Decimal("2.00"),
    ),
}


def estimar_custo_usd(modelo: str, prompt_tokens: int, completion_tokens: int) -> Decimal | None:
    """Custo estimado em USD; `None` se o modelo não está tabelado."""
    if prompt_tokens < 0 or completion_tokens < 0:
        raise ValueError("contagem de tokens negativa")
    preco = TABELA_PRECOS.get(modelo)
    if preco is None:
        return None
    return (
        Decimal(prompt_tokens) * preco.entrada_usd_por_milhao
        + Decimal(completion_tokens) * preco.saida_usd_por_milhao
    ) / TOKENS_POR_MILHAO
