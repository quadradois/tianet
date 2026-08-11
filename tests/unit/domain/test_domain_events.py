"""Contratos de eventos internos e projections reconstruiveis (IMP-197/198)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from emprestimo.domain.common.events import DomainEventEnvelope, ProjectionMetadata

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000123")
EVENT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def test_event_envelope_expoe_campos_obrigatorios_e_payload_isolado() -> None:
    payload = {"entidade_id": "abc", "status": "ok"}
    event = DomainEventEnvelope(
        event_id=EVENT_ID,
        event_type="ContratoLiberadoLogico",
        event_version=1,
        occurred_at=datetime(2026, 8, 11, tzinfo=UTC),
        tenant_id=TENANT_ID,
        correlation_id="corr-123",
        payload=payload,
    )

    payload["status"] = "alterado"
    serialized = event.to_dict()

    assert serialized == {
        "event_id": str(EVENT_ID),
        "event_type": "ContratoLiberadoLogico",
        "event_version": 1,
        "occurred_at": "2026-08-11T00:00:00+00:00",
        "tenant_id": str(TENANT_ID),
        "correlation_id": "corr-123",
        "payload": {"entidade_id": "abc", "status": "ok"},
    }


def test_event_envelope_rejeita_campos_semanticos_invalidos() -> None:
    with pytest.raises(ValueError, match="event_type"):
        DomainEventEnvelope(
            event_id=EVENT_ID,
            event_type=" ",
            event_version=1,
            occurred_at=datetime.now(UTC),
            tenant_id=TENANT_ID,
            correlation_id="corr",
            payload={},
        )

    with pytest.raises(ValueError, match="event_version"):
        DomainEventEnvelope(
            event_id=EVENT_ID,
            event_type="Teste",
            event_version=0,
            occurred_at=datetime.now(UTC),
            tenant_id=TENANT_ID,
            correlation_id="corr",
            payload={},
        )

    with pytest.raises(ValueError, match="timezone"):
        DomainEventEnvelope(
            event_id=EVENT_ID,
            event_type="Teste",
            event_version=1,
            occurred_at=datetime(2026, 8, 11),
            tenant_id=TENANT_ID,
            correlation_id="corr",
            payload={},
        )


def test_projection_metadata_declara_origem_versao_e_data_referencia() -> None:
    metadata = ProjectionMetadata(
        origem="SituacaoParcelaNaDataV1",
        versao=1,
        tenant_id=TENANT_ID,
        correlation_id="corr-456",
        event_id=EVENT_ID,
        data_referencia=date(2026, 8, 11),
    )

    assert metadata.origem == "SituacaoParcelaNaDataV1"
    assert metadata.versao == 1
    assert metadata.data_referencia == date(2026, 8, 11)


def test_projection_metadata_rejeita_origem_ou_versao_invalidas() -> None:
    with pytest.raises(ValueError, match="origem"):
        ProjectionMetadata(
            origem=" ",
            versao=1,
            tenant_id=TENANT_ID,
            correlation_id="corr",
            event_id=EVENT_ID,
        )

    with pytest.raises(ValueError, match="versao"):
        ProjectionMetadata(
            origem="EventoV1",
            versao=0,
            tenant_id=TENANT_ID,
            correlation_id="corr",
            event_id=EVENT_ID,
        )
