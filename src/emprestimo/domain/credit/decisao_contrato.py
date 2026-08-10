"""Decisao contratual registrada no ciclo do EPIC-004."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState


@dataclass(frozen=True)
class DecisaoContrato:
    """Transicao de estado contratual com ator e instante."""

    contrato_id: uuid.UUID
    usuario_id: uuid.UUID
    tipo: str
    estado_anterior: ContratoCreditoState
    estado_posterior: ContratoCreditoState
    motivo: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
