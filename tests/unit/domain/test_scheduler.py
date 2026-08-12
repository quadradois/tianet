import uuid
from datetime import UTC, datetime, timedelta

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.scheduler import EstadoJob, JobAgendado, calcular_backoff


def _job(agora: datetime) -> JobAgendado:
    return JobAgendado(
        tenant_id=uuid.uuid4(),
        carteira_id=uuid.uuid4(),
        tipo="enviar_lembrete",
        executar_em=agora,
        correlation_id="corr-1",
        payload={"lembrete_id": str(uuid.uuid4())},
        origem_tipo="lembrete",
        origem_id=uuid.uuid4(),
    )


def test_claim_cria_lease_e_execution_id_filho() -> None:
    agora = datetime(2026, 8, 11, tzinfo=UTC)
    job = _job(agora)
    tentativa = job.reivindicar(agora=agora, duracao=timedelta(seconds=30))
    assert job.estado is EstadoJob.EM_EXECUCAO
    assert tentativa.lease_token == job.lease_token
    assert tentativa.execution_id != job.id
    assert job.correlation_id == "corr-1"


def test_token_expirado_nao_conclui() -> None:
    agora = datetime(2026, 8, 11, tzinfo=UTC)
    job = _job(agora)
    tentativa = job.reivindicar(agora=agora, duracao=timedelta(seconds=10))
    with pytest.raises(ViolacaoInvarianteError, match="lease expirado"):
        job.concluir(tentativa.lease_token, agora=agora + timedelta(seconds=10))


def test_job_com_lease_expirado_pode_ser_recuperado() -> None:
    agora = datetime(2026, 8, 11, tzinfo=UTC)
    job = _job(agora)
    primeira = job.reivindicar(agora=agora, duracao=timedelta(seconds=10))
    segunda = job.reivindicar(agora=agora + timedelta(seconds=11), duracao=timedelta(seconds=10))
    assert primeira.lease_token != segunda.lease_token
    assert segunda.numero == 2


def test_backoff_e_limitado_e_validado() -> None:
    assert calcular_backoff(1).total_seconds() == 15
    assert calcular_backoff(5, jitter_segundos=30).total_seconds() <= 330
    with pytest.raises(ViolacaoInvarianteError):
        calcular_backoff(6)
