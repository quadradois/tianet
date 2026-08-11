"""Contratos operacionais HTTP do EPIC-008."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from emprestimo.application.health import HealthReport
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app
from emprestimo.presentation.api.observability import CORRELATION_ID_HEADER

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class _HealthServiceStub:
    def __init__(self, report: HealthReport) -> None:
        self._report = report

    def verificar(self) -> HealthReport:
        return self._report


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_healthcheck_publico_retorna_saude_minima_sem_dados_sensiveis(
    client: TestClient,
) -> None:
    resp = client.get("/health", headers={CORRELATION_ID_HEADER: "trace-health-1"})

    assert resp.status_code == 200
    assert resp.headers[CORRELATION_ID_HEADER] == "trace-health-1"
    assert resp.json() == {
        "status": "healthy",
        "service": "api",
        "checks": {"database": "healthy"},
    }
    conteudo = resp.text.lower()
    for proibido in ["postgresql://", "tenant", "usuario", "token", "secret", "stack"]:
        assert proibido not in conteudo


def test_healthcheck_indisponivel_retorna_503_sem_vazar_detalhe() -> None:
    app = create_app()
    app.dependency_overrides[dependencies.get_health_service] = lambda: _HealthServiceStub(
        HealthReport(status="unhealthy", checks={"database": "unhealthy"})
    )

    with TestClient(app) as client:
        resp = client.get("/health")

    assert resp.status_code == 503
    assert UUID_PATTERN.fullmatch(resp.headers[CORRELATION_ID_HEADER])
    assert resp.json() == {
        "status": "unhealthy",
        "service": "api",
        "checks": {"database": "unhealthy"},
    }


def test_correlation_id_e_devolvido_em_2xx_4xx_e_5xx(
    client: TestClient,
) -> None:
    ok = client.get("/health", headers={CORRELATION_ID_HEADER: "trace-ok"})
    app = create_app()

    @app.get("/bad", include_in_schema=False)
    def bad_request() -> None:
        raise HTTPException(status_code=400, detail={"codigo": "bad", "mensagem": "bad"})

    @app.get("/boom", include_in_schema=False)
    def boom() -> None:
        raise RuntimeError("token=segredo; postgresql://user:pass@host/db")

    with TestClient(app, raise_server_exceptions=False) as failing_client:
        bad = failing_client.get("/bad", headers={CORRELATION_ID_HEADER: "trace-bad"})
        fail = failing_client.get("/boom", headers={CORRELATION_ID_HEADER: "trace-fail"})

    assert ok.status_code == 200
    assert ok.headers[CORRELATION_ID_HEADER] == "trace-ok"
    assert bad.status_code == 400
    assert bad.headers[CORRELATION_ID_HEADER] == "trace-bad"
    assert fail.status_code == 500
    assert fail.headers[CORRELATION_ID_HEADER] == "trace-fail"
    assert fail.json() == {"codigo": "erro_interno", "mensagem": "erro inesperado no servidor"}
    assert "token=segredo" not in fail.text
    assert "postgresql://" not in fail.text


def test_correlation_id_invalido_e_regenerado(client: TestClient) -> None:
    resp = client.get("/health", headers={CORRELATION_ID_HEADER: "valor invalido"})

    assert resp.status_code == 200
    assert UUID_PATTERN.fullmatch(resp.headers[CORRELATION_ID_HEADER])


def test_erro_tecnico_loga_contexto_sem_payload_sensivel(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app()

    @app.get("/boom", include_in_schema=False)
    def boom() -> None:
        raise RuntimeError("senha=supersecreta")

    caplog.set_level(logging.ERROR, logger="emprestimo.observability")
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/boom", headers={CORRELATION_ID_HEADER: "trace-log"})

    assert resp.status_code == 500
    assert any(record.message == "http_unexpected_error" for record in caplog.records)
    assert any(getattr(record, "correlation_id", None) == "trace-log" for record in caplog.records)
    assert "supersecreta" not in caplog.text


def test_openapi_documenta_health_correlation_id_e_erro_tecnico() -> None:
    schema = create_app().openapi()
    health = schema["paths"]["/health"]["get"]

    assert "security" not in health
    assert "200" in health["responses"]
    assert "503" in health["responses"]
    assert "500" in health["responses"]
    assert any(param["name"] == CORRELATION_ID_HEADER for param in health["parameters"])
    for response in health["responses"].values():
        assert CORRELATION_ID_HEADER in response["headers"]
