import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory

from emprestimo.domain.credit.scheduler import EstadoJob, JobAgendado
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyJobAgendadoRepository,
    SqlAlchemyTenantRepository,
)


def test_dois_workers_nao_reivindicam_o_mesmo_job(
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    tenant = TenantFactory.build()
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyTenantRepository(session).save(tenant)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    agora = datetime.now(UTC)
    job = JobAgendado(
        tenant_id=tenant.id,
        carteira_id=carteira.id,
        tipo="enviar_lembrete",
        executar_em=agora,
        correlation_id="corr-concurrency",
        payload={"lembrete_id": "fixture"},
        origem_tipo="lembrete",
        origem_id=tenant.id,
    )
    SqlAlchemyJobAgendadoRepository(session).save(job)
    session.commit()

    first = session_factory()
    second = session_factory()
    try:
        claims_first = SqlAlchemyJobAgendadoRepository(first).claim(
            agora=agora, limite=1, duracao=timedelta(seconds=30)
        )
        claims_second = SqlAlchemyJobAgendadoRepository(second).claim(
            agora=agora, limite=1, duracao=timedelta(seconds=30)
        )
        assert len(claims_first) == 1
        assert claims_second == []
    finally:
        first.rollback()
        second.rollback()
        first.close()
        second.close()


def test_token_antigo_nao_finaliza_apos_recuperacao(
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    tenant = TenantFactory.build()
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyTenantRepository(session).save(tenant)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    agora = datetime.now(UTC)
    job = JobAgendado(
        tenant_id=tenant.id,
        carteira_id=carteira.id,
        tipo="enviar_lembrete",
        executar_em=agora,
        correlation_id="corr-fencing",
        payload={},
        origem_tipo="lembrete",
        origem_id=carteira.id,
    )
    repo = SqlAlchemyJobAgendadoRepository(session)
    repo.save(job)
    session.commit()
    primeiro = repo.claim(agora=agora, limite=1, duracao=timedelta(seconds=1))[0]
    token_antigo = primeiro[1].lease_token
    session.commit()

    other = session_factory()
    try:
        novo = SqlAlchemyJobAgendadoRepository(other).claim(
            agora=agora + timedelta(seconds=2),
            limite=1,
            duracao=timedelta(seconds=30),
        )[0]
        other.commit()
    finally:
        other.close()

    primeiro[0].estado = EstadoJob.CONCLUIDO
    assert not repo.finalizar_com_fencing(primeiro[0], token_antigo)
    assert novo[1].lease_token != token_antigo


def test_token_expirado_nao_finaliza_antes_de_novo_claim(session: Session) -> None:
    tenant = TenantFactory.build()
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyTenantRepository(session).save(tenant)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    agora = datetime.now(UTC) - timedelta(seconds=2)
    job = JobAgendado(
        tenant_id=tenant.id,
        carteira_id=carteira.id,
        tipo="enviar_lembrete",
        executar_em=agora,
        correlation_id="corr-expired-fencing",
        payload={},
        origem_tipo="lembrete",
        origem_id=uuid.uuid4(),
    )
    repo = SqlAlchemyJobAgendadoRepository(session)
    repo.save(job)
    session.commit()
    reivindicado, tentativa = repo.claim(
        agora=agora,
        limite=1,
        duracao=timedelta(milliseconds=1),
    )[0]
    session.commit()
    time.sleep(0.01)
    reivindicado.estado = EstadoJob.CONCLUIDO

    assert not repo.finalizar_com_fencing(reivindicado, tentativa.lease_token)
