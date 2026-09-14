"""Métricas do ingress (IMP-356-B): contagens sem conteúdo.

Só bytes e motivos — nunca texto, mídia, prompt ou corpo. Processo-local e
reiniciável para testes; a persistência e o alarme vivem no Slice F com o
restante da observabilidade.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class MetricasIngress:
    bytes_recebidos: int = 0
    aceitas: int = 0
    duplicadas: int = 0
    descartes_por_motivo: Counter[str] = field(default_factory=Counter)

    def registrar_entrada(self, tamanho_bytes: int) -> None:
        self.bytes_recebidos += tamanho_bytes

    def registrar_aceita(self, *, duplicada: bool) -> None:
        self.aceitas += 1
        if duplicada:
            self.duplicadas += 1

    def registrar_descarte(self, motivo: str) -> None:
        self.descartes_por_motivo[motivo] += 1

    def retrato(self) -> dict[str, object]:
        return {
            "bytes_recebidos": self.bytes_recebidos,
            "aceitas": self.aceitas,
            "duplicadas": self.duplicadas,
            "descartes_por_motivo": dict(self.descartes_por_motivo),
        }


METRICAS = MetricasIngress()
