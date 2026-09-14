"""Métricas do ingress (IMP-356-B) e de inferência (IMP-356-D lote 2).

Só contagens e motivos — nunca texto, mídia, prompt, resposta, chave ou
custo detalhado por conteúdo. Processo-local e reiniciável para testes; a
persistência e o alarme vivem no Slice F com o restante da
observabilidade.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from emprestimo.agent.llm_client import Uso


@dataclass
class MetricasIngress:
    bytes_recebidos: int = 0
    aceitas: int = 0
    duplicadas: int = 0
    descartes_por_motivo: Counter[str] = field(default_factory=Counter)
    recusas_por_motivo: Counter[str] = field(default_factory=Counter)

    def registrar_entrada(self, tamanho_bytes: int) -> None:
        self.bytes_recebidos += tamanho_bytes

    def registrar_aceita(self, *, duplicada: bool) -> None:
        self.aceitas += 1
        if duplicada:
            self.duplicadas += 1

    def registrar_descarte(self, motivo: str) -> None:
        self.descartes_por_motivo[motivo] += 1

    def registrar_recusa(self, motivo: str) -> None:
        self.recusas_por_motivo[motivo] += 1

    def retrato(self) -> dict[str, Any]:
        return {
            "bytes_recebidos": self.bytes_recebidos,
            "aceitas": self.aceitas,
            "duplicadas": self.duplicadas,
            "descartes_por_motivo": dict(self.descartes_por_motivo),
            "recusas_por_motivo": dict(self.recusas_por_motivo),
        }


METRICAS = MetricasIngress()


@dataclass
class MetricasLlm:
    """Consumo de inferência: chamadas, tokens, custo estimado, falhas."""

    chamadas: int = 0
    chamadas_sem_medicao: int = 0
    tokens_entrada: int = 0
    tokens_saida: int = 0
    custo_estimado_usd: Decimal = field(default_factory=lambda: Decimal("0"))
    falhas_por_motivo: Counter[str] = field(default_factory=Counter)
    ultimo_alerta_usd: Decimal | None = None

    def registrar_chamada(
        self, uso: Uso | None, custo_usd: Decimal | None, falha: str | None = None
    ) -> None:
        self.chamadas += 1
        if uso is None:
            self.chamadas_sem_medicao += 1
        else:
            self.tokens_entrada += uso.prompt_tokens
            self.tokens_saida += uso.completion_tokens
        if custo_usd is not None:
            self.custo_estimado_usd += custo_usd
        if falha is not None:
            self.falhas_por_motivo[falha] += 1

    def deve_alertar(self, limite_usd: Decimal) -> bool:
        """Um disparo por patamar: alerta de novo só acima do último."""
        if self.custo_estimado_usd < limite_usd:
            return False
        return self.ultimo_alerta_usd is None or self.ultimo_alerta_usd < limite_usd

    def marcar_alerta(self, limite_usd: Decimal) -> None:
        self.ultimo_alerta_usd = limite_usd

    def retrato(self) -> dict[str, Any]:
        return {
            "chamadas": self.chamadas,
            "chamadas_sem_medicao": self.chamadas_sem_medicao,
            "tokens_entrada": self.tokens_entrada,
            "tokens_saida": self.tokens_saida,
            "custo_estimado_usd": str(self.custo_estimado_usd),
            "falhas_por_motivo": dict(self.falhas_por_motivo),
            "ultimo_alerta_usd": (
                str(self.ultimo_alerta_usd) if self.ultimo_alerta_usd is not None else None
            ),
        }


METRICAS_LLM = MetricasLlm()
