"""Decisao Comercial (IMP-108, EPIC-003)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState


@dataclass(frozen=True)
class DecisaoComercial:
    """Registro imutavel de uma transicao comercial."""

    proposta_id: uuid.UUID
    usuario_id: uuid.UUID
    estado_anterior: PropostaComercialState
    estado_posterior: PropostaComercialState
    motivo: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_audit_dict(self) -> dict[str, object]:
        """Serializa a decisao para trilha de auditoria."""

        return {
            "id": str(self.id),
            "proposta_id": str(self.proposta_id),
            "usuario_id": str(self.usuario_id),
            "estado_anterior": self.estado_anterior.value,
            "estado_posterior": self.estado_posterior.value,
            "motivo": self.motivo,
            "criado_em": self.criado_em.isoformat(),
        }
