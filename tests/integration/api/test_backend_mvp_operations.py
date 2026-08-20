"""Recertificacao P3 de operacao, migrations e worker do Backend MVP."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient
from tests.factories import CarteiraFactory, TenantFactory

from emprestimo.application.scheduler import ResultadoExecucao, SchedulerService
from emprestimo.domain.credit.scheduler import EstadoJob, JobAgendado
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyJobAgendadoRepository,
    SqlAlchemyTenantRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app
from emprestimo.presentation.api.observability import CORRELATION_ID_HEADER
from emprestimo.worker.scheduler_worker import SchedulerWorker, WorkerSettings

ROOT = Path(__file__).resolve().parents[3]


def test_imp_266_quality_migrations_gate_e_unico_head_alembic() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    workflow = (ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8")
    validator = (ROOT / "scripts/validate_migrations.py").read_text(encoding="utf-8")
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    script = ScriptDirectory.from_config(config)

    assert (
        package["scripts"]["quality:migrations"] == "uv run python scripts/validate_migrations.py"
    )
    assert 'MIGRATION_VALIDATION_ALLOW_DESTRUCTIVE: "1"' in workflow
    assert "npm run quality:migrations" in workflow
    assert "DROP SCHEMA IF EXISTS public CASCADE" in validator
    assert "Refusing to run destructive migration validation" in validator
    assert script.get_current_head() == "0017_remove_plano_de_parcelas"


def test_imp_267_health_correlation_e_erro_tecnico_sem_vazamento(
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
) -> None:
    del session
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, "plan020-operacoes-secret")
    app = create_app()

    @app.get("/plan020/bad", include_in_schema=False)
    def bad_request() -> None:
        raise HTTPException(status_code=400, detail={"codigo": "bad", "mensagem": "bad"})

    @app.get("/plan020/boom", include_in_schema=False)
    def boom() -> None:
        raise RuntimeError("token=segredo; postgresql://usuario:senha@host/db")

    with TestClient(app, raise_server_exceptions=False) as client:
        health = client.get("/health", headers={CORRELATION_ID_HEADER: "plan020-health"})
        nao_autenticado = client.get(
            "/platform/tenants",
            headers={CORRELATION_ID_HEADER: "plan020-401"},
        )
        bad = client.get("/plan020/bad", headers={CORRELATION_ID_HEADER: "plan020-400"})
        boom_response = client.get(
            "/plan020/boom",
            headers={CORRELATION_ID_HEADER: "plan020-500"},
        )

    assert health.status_code == 200
    assert health.headers[CORRELATION_ID_HEADER] == "plan020-health"
    assert health.json()["checks"] == {"database": "healthy"}
    assert nao_autenticado.status_code == 401
    assert nao_autenticado.headers[CORRELATION_ID_HEADER] == "plan020-401"
    assert bad.status_code == 400
    assert bad.headers[CORRELATION_ID_HEADER] == "plan020-400"
    assert boom_response.status_code == 500
    assert boom_response.headers[CORRELATION_ID_HEADER] == "plan020-500"
    assert boom_response.json() == {
        "codigo": "erro_interno",
        "mensagem": "erro inesperado no servidor",
    }
    conteudo_publico = " ".join(
        [health.text, nao_autenticado.text, bad.text, boom_response.text]
    ).lower()
    for proibido in ("postgresql://", "segredo", "senha", "token=", "stack"):
        assert proibido not in conteudo_publico


def test_imp_268_worker_scheduler_smoke_com_banco_e_shutdown(
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    tenant = TenantFactory.build()
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyTenantRepository(session).save(tenant)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    job = JobAgendado(
        tenant_id=tenant.id,
        carteira_id=carteira.id,
        tipo="enviar_lembrete",
        executar_em=datetime.now(UTC),
        correlation_id="plan020-worker-smoke",
        payload={"lembrete_id": str(uuid.uuid4())},
        origem_tipo="lembrete",
        origem_id=uuid.uuid4(),
    )
    SqlAlchemyJobAgendadoRepository(session).save(job)
    session.commit()

    processados: list[uuid.UUID] = []

    def handler(item: Any) -> ResultadoExecucao:
        processados.append(item.job.id)
        return ResultadoExecucao.SUCESSO

    worker = SchedulerWorker(
        SchedulerService(lambda: SqlAlchemyUnitOfWork(session_factory)),
        {"enviar_lembrete": handler},
        WorkerSettings(concurrency=1, batch_size=1),
        heartbeat=lambda _ativos, _falha: None,
    )

    assert worker.cycle() == 1
    _aguardar_job_concluido(session_factory, job.id, tenant.id)
    worker.stop()

    assert processados == [job.id]


def _aguardar_job_concluido(
    session_factory: sessionmaker[Session],
    job_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    limite = time.monotonic() + 5
    while time.monotonic() < limite:
        with session_factory() as consulta:
            job = SqlAlchemyJobAgendadoRepository(consulta).find_scoped(job_id, tenant_id)
            if job is not None and job.estado is EstadoJob.CONCLUIDO:
                return
        time.sleep(0.05)
    raise AssertionError("worker nao concluiu o job dentro do timeout")
