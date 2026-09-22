"""Regua do lembrete de atraso (PLAN-045 D5).

Funcao pura, sem estado: o primeiro lembrete sai um dia depois do acerto em
aberto e os seguintes de tres em tres dias. Quem decide *se* o lembrete sai e
a Credora, autorizando no resumo diario; esta regua decide apenas *quando* ele
entra na lista de candidatos.
"""

from __future__ import annotations

__all__ = ["INTERVALO_DIAS", "elegivel_lembrete"]

INTERVALO_DIAS = 3


def elegivel_lembrete(dias_atraso: int) -> bool:
    """D+1, D+4, D+7, ... Antes do vencimento e no proprio dia, nunca."""
    if dias_atraso < 1:
        return False
    return (dias_atraso - 1) % INTERVALO_DIAS == 0
