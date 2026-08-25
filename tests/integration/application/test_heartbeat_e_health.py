"""Cadeia completa do heartbeat: quem escreve e quem le (IMP-343, IMP-350).

O IMP-343 deu consumidor ao heartbeat — `HealthService` passou a somar o estado
do worker aos `checks` do `/health`. Mas o teste que veio com ele cobria so o
lado da leitura, com uma `Session` falsa. O lado que **escreve**,
`HeartbeatStore.registrar`, nunca teve teste: quem calculava o lag, decidia o
estado e limpava registros velhos rodava sem nenhuma prova.

Testar as duas pontas separadamente deixaria passar justamente o que importa —
que o vocabulario gravado e o mesmo que o leitor entende. Aqui a cadeia e
exercitada inteira, contra PostgreSQL real.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory

from emprestimo.application.health import HealthService
from emprestimo.infrastructure.db.orm import JobAgendadoORM, SchedulerWorkerHeartbeatORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyTenantRepository,
)
from emprestimo.worker.scheduler_worker import HeartbeatStore


@pytest.fixture(autouse=True)
def _tabela_de_heartbeat_limpa(session_factory: sessionmaker[Session]) -> Iterator[None]:
    """Limpa antes **e depois**, porque a tabela e global e sem tenant_id.

    Um heartbeat fresco deixado para tras faz o `/health` responder `healthy` em
    outra suite — e `test_healthcheck_publico_retorna_saude_minima_sem_dados_sensiveis`
    espera `degraded`, ja que a suite nao sobe worker. Sem o cleanup final, esses
    testes so passariam pela ordem em que o pytest os coleta.
    """
    _limpar_heartbeats(session_factory)
    yield
    _limpar_heartbeats(session_factory)


def test_heartbeat_escrito_pelo_worker_e_lido_pelo_health(
    session_factory: sessionmaker[Session],
) -> None:
    """A ponta que escreve e a que le tem que falar a mesma lingua."""
    store = HeartbeatStore(f"scheduler-{uuid.uuid4()}", session_factory)

    store.registrar(0, concorrencia=2)

    report = HealthService(session_factory).verificar()
    assert report.checks["worker"] == "healthy"
    assert report.status == "healthy"
    assert report.http_status == 200


def test_fila_atrasada_por_tres_ciclos_degrada_o_health(
    session_factory: sessionmaker[Session],
) -> None:
    """Lag sustentado e o sinal; um ciclo ruim isolado nao pode virar alarme."""
    _job_vencido_ha(session_factory, timedelta(minutes=30))
    store = HeartbeatStore(f"scheduler-{uuid.uuid4()}", session_factory)

    store.registrar(1, concorrencia=2)
    assert HealthService(session_factory).verificar().checks["worker"] == "healthy"
    store.registrar(1, concorrencia=2)
    assert HealthService(session_factory).verificar().checks["worker"] == "healthy"
    store.registrar(1, concorrencia=2)

    report = HealthService(session_factory).verificar()
    assert report.checks["worker"] == "degraded"
    assert report.status == "degraded"
    assert report.http_status == 200, "worker atrasado nao tira a API de rotacao"

    with session_factory() as session:
        linha = session.scalars(select(SchedulerWorkerHeartbeatORM)).one()
    assert linha.lag_segundos > 60
    assert linha.em_execucao == 1
    assert linha.concorrencia == 2


def test_falha_do_supervisor_marca_unhealthy_sem_depender_de_lag(
    session_factory: sessionmaker[Session],
) -> None:
    store = HeartbeatStore(f"scheduler-{uuid.uuid4()}", session_factory)

    store.registrar(0, concorrencia=2, falha_supervisor=True)

    report = HealthService(session_factory).verificar()
    assert report.checks["worker"] == "unhealthy"
    assert report.status == "degraded", "worker morto degrada a operacao, nao o banco"
    assert report.http_status == 200


def test_heartbeat_de_worker_extinto_e_descartado_depois_de_24h(
    session_factory: sessionmaker[Session],
) -> None:
    """Sem a limpeza, cada reinicio deixaria um worker fantasma na tabela."""
    antigo = f"scheduler-extinto-{uuid.uuid4()}"
    with session_factory() as session:
        session.add(
            SchedulerWorkerHeartbeatORM(
                worker_id=antigo,
                estado="healthy",
                concorrencia=1,
                em_execucao=0,
                ultimo_heartbeat_em=datetime.now(UTC) - timedelta(hours=30),
                lag_segundos=0,
            )
        )
        session.commit()

    HeartbeatStore(f"scheduler-{uuid.uuid4()}", session_factory).registrar(0, concorrencia=1)

    with session_factory() as session:
        restantes = session.scalars(select(SchedulerWorkerHeartbeatORM.worker_id)).all()
    assert antigo not in restantes


def _limpar_heartbeats(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        for linha in session.scalars(select(SchedulerWorkerHeartbeatORM)).all():
            session.delete(linha)
        session.commit()


def _job_vencido_ha(session_factory: sessionmaker[Session], atraso: timedelta) -> None:
    with session_factory() as session:
        tenant = TenantFactory.build()
        SqlAlchemyTenantRepository(session).save(tenant)
        carteira = CarteiraFactory.build(tenant_id=tenant.id)
        SqlAlchemyCarteiraRepository(session).save(carteira)
        vencido = datetime.now(UTC) - atraso
        session.add(
            JobAgendadoORM(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                carteira_id=carteira.id,
                tipo="enviar_lembrete",
                executar_em=vencido,
                correlation_id=f"heartbeat-lag:{uuid.uuid4()}",
                payload={},
                origem_tipo="teste_lag",
                origem_id=uuid.uuid4(),
                estado="agendado",
                max_tentativas=3,
                tentativas=0,
                proxima_execucao_em=vencido,
                cancelamento_solicitado=False,
                criado_em=vencido,
            )
        )
        session.commit()
