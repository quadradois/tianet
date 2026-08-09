"""Estados da Proposta Comercial (EPIC-003)."""

from __future__ import annotations

from enum import StrEnum


class PropostaComercialState(StrEnum):
    """Estados operacionais da PropostaComercial."""

    RASCUNHO = "rascunho"
    EM_ANALISE = "em_analise"
    APROVADA = "aprovada"
    RECUSADA = "recusada"
    CANCELADA = "cancelada"
    EXPIRADA = "expirada"
