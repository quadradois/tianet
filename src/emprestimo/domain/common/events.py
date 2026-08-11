"""Contratos internos de eventos e projections reconstruiveis (EPIC-008)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True, kw_only=True)
class DomainEventEnvelope:
    """Envelope minimo para eventos internos sem infraestrutura distribuida."""

    event_id: uuid.UUID
    event_type: str
    event_version: int
    occurred_at: datetime
    tenant_id: uuid.UUID
    correlation_id: str
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.event_type.strip():
            raise ValueError("event_type obrigatorio")
        if self.event_version < 1:
            raise ValueError("event_version deve ser positivo")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at deve possuir timezone")
        if not self.correlation_id.strip():
            raise ValueError("correlation_id obrigatorio")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        event_version: int,
        tenant_id: uuid.UUID,
        correlation_id: str,
        payload: Mapping[str, Any],
    ) -> DomainEventEnvelope:
        return cls(
            event_id=uuid.uuid4(),
            event_type=event_type,
            event_version=event_version,
            occurred_at=datetime.now(UTC),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            payload=payload,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "event_version": self.event_version,
            "occurred_at": self.occurred_at.isoformat(),
            "tenant_id": str(self.tenant_id),
            "correlation_id": self.correlation_id,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, kw_only=True)
class ProjectionMetadata:
    """Metadados obrigatorios para read models reconstruiveis."""

    origem: str
    versao: int
    tenant_id: uuid.UUID
    correlation_id: str
    event_id: uuid.UUID
    data_referencia: date | None = None

    def __post_init__(self) -> None:
        if not self.origem.strip():
            raise ValueError("origem obrigatoria")
        if self.versao < 1:
            raise ValueError("versao deve ser positiva")
        if not self.correlation_id.strip():
            raise ValueError("correlation_id obrigatorio")
