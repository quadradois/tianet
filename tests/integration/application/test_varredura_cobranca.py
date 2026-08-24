"""Integracao do IMP-331: lancamento real ate a fila de cobranca."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.lancamento import (
    CondicoesLancamento,
    DevedorNovo,
    LancamentoService,
)
from emprestimo.application.motor_financeiro import (
    ConsultaSaldoService,
    PagamentoService,
    criar_emprestimo_e_plano_em,
)
from emprestimo.application.operacao_diaria import ConsultarFilaCobranca
from emprestimo.application.scheduler import SchedulerService
from emprestimo.application.varredura_cobranca import (
    TIPO_JOB_VARREDURA_COBRANCA,
    AgendadorVarreduraCobranca,
    VarreduraCobrancaService,
)
from emprestimo.domain.credit.automacao_ports import AutomacaoFiltros
from emprestimo.domain.credit.operacao_diaria import EstadoCobranca
from emprestimo.domain.credit.scheduler import EstadoJob
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import AuditoriaLogORM, CobrancaCasoORM, JobAgendadoORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.worker.scheduler_worker import SchedulerWorker, WorkerSettings


@dataclass(frozen=True)
class _Ambiente:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    usuario_id: uuid.UUID


def test_varredura_worker_cria_atualiza_e_encerra_caso_sem_insercao_lateral(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    hoje = datetime.now(UTC).date()
    lancamento = LancamentoService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        criar_emprestimo_e_plano_em,
        lambda _comprovante: None,
        SqlAlchemyAuditoriaRegistro(session_factory),
    ).lancar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        usuario_id=ambiente.usuario_id,
        devedor_novo=DevedorNovo(
            documento=_cpf(),
            nome="Devedor da varredura",
            contato_whatsapp="(11) 98888-7766",
        ),
        condicoes=CondicoesLancamento(
            valor_contratado="6000.00",
            taxa_juros_mensal="0.0300",
            dia_de_acerto=10,
        ),
        data_referencia=hoje,
        idempotency_key=str(uuid.uuid4()),
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        emprestimo = uow.emprestimo.find_by_id(lancamento.emprestimo_id)
    assert emprestimo is not None
    primeiro_acerto = emprestimo.proximo_acerto_em(hoje)
    assert primeiro_acerto is not None
    depois_do_acerto = primeiro_acerto + date.resolution

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    varredura = VarreduraCobrancaService(uow_factory, auditoria)
    agendador = AgendadorVarreduraCobranca(uow_factory, auditoria)

    agendador.agendar_dia(
        data_referencia=depois_do_acerto,
        executar_em=datetime.now(UTC),
    )
    assert _total_jobs_varredura(session_factory, ambiente) == 1
    assert (
        agendador.agendar_dia(
            data_referencia=depois_do_acerto,
            executar_em=datetime.now(UTC),
        )
        == 0
    )
    assert _total_jobs_varredura(session_factory, ambiente) == 1
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        jobs = uow.job_agendado.listar(
            AutomacaoFiltros(
                tenant_id=ambiente.tenant_id,
                carteira_id=ambiente.carteira_id,
            )
        ).items
    job = next(item for item in jobs if item.tipo == TIPO_JOB_VARREDURA_COBRANCA)
    _priorizar_job(session_factory, job.id)

    worker = SchedulerWorker(
        SchedulerService(uow_factory, auditoria),
        {TIPO_JOB_VARREDURA_COBRANCA: varredura.processar_job},
        WorkerSettings(concurrency=1, batch_size=1),
    )
    assert worker.cycle() == 1
    _aguardar_job_concluido(session_factory, job.id, ambiente.tenant_id)
    worker.stop()

    fila = ConsultarFilaCobranca(uow_factory).listar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
    )
    assert fila.total == 1
    caso_inicial = fila.items[0]
    assert caso_inicial.devedor_id == lancamento.devedor_id
    assert caso_inicial.emprestimo_id == lancamento.emprestimo_id
    assert caso_inicial.estado is EstadoCobranca.PENDENTE
    assert caso_inicial.total_pendente > Decimal("6000.00")

    segunda = varredura.executar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        data_referencia=depois_do_acerto,
    )
    assert segunda.casos_criados == 0
    assert segunda.casos_atualizados == 0
    assert segunda.casos_encerrados == 0
    assert len(segunda.devedores) == 1
    snapshot = segunda.devedores[0]
    assert snapshot.devedor_id == lancamento.devedor_id
    assert snapshot.saldo_devedor == caso_inicial.total_pendente
    assert snapshot.percentuais_juros == (Decimal("3.0000"),)
    assert snapshot.valor_juros_periodo > Decimal("0.00")
    assert snapshot.emprestimos[0].juros_pendente_acerto > Decimal("0.00")
    _assert_um_caso(session_factory, ambiente)

    juros_pendente = snapshot.emprestimos[0].juros_pendente_acerto
    pagamento_parcial = (juros_pendente / Decimal("2")).quantize(Decimal("0.01"))
    PagamentoService(uow_factory, auditoria).registrar(
        emprestimo_id=lancamento.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        valor=pagamento_parcial,
        recebido_em=datetime.combine(
            depois_do_acerto,
            datetime.min.time(),
            tzinfo=UTC,
        ),
        idempotency_key=str(uuid.uuid4()),
    )
    parcial = varredura.executar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        data_referencia=depois_do_acerto,
    )
    fila_parcial = ConsultarFilaCobranca(uow_factory).listar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
    )
    assert parcial.casos_atualizados == 1
    assert parcial.casos_encerrados == 0
    assert fila_parcial.total == 1
    assert Decimal("0.00") < fila_parcial.items[0].total_pendente < caso_inicial.total_pendente
    assert parcial.devedores[0].emprestimos[0].juros_pendente_acerto > Decimal("0.00")
    _assert_um_caso(session_factory, ambiente)

    saldo = ConsultaSaldoService(uow_factory).consultar(
        emprestimo_id=lancamento.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        data_referencia=depois_do_acerto,
    )
    PagamentoService(uow_factory, auditoria).registrar(
        emprestimo_id=lancamento.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        valor=saldo.total,
        recebido_em=datetime.combine(
            depois_do_acerto,
            datetime.max.time(),
            tzinfo=UTC,
        ),
        idempotency_key=str(uuid.uuid4()),
    )
    quitado = varredura.executar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        data_referencia=depois_do_acerto,
    )
    assert quitado.casos_encerrados == 1
    assert (
        ConsultarFilaCobranca(uow_factory)
        .listar(
            tenant_id=ambiente.tenant_id,
            carteira_id=ambiente.carteira_id,
        )
        .total
        == 0
    )
    encerrados = ConsultarFilaCobranca(uow_factory).listar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        estado=EstadoCobranca.ENCERRADO,
    )
    assert encerrados.total == 1
    assert encerrados.items[0].total_pendente == Decimal("0.00")
    _assert_um_caso(session_factory, ambiente)

    with session_factory() as session:
        acoes = session.scalars(
            select(AuditoriaLogORM.acao)
            .where(AuditoriaLogORM.entidade == "cobranca_varredura")
            .where(AuditoriaLogORM.detalhes.contains(str(ambiente.carteira_id)))
        ).all()
    assert acoes.count("varrer.inicio") == 4
    assert acoes.count("varrer.sucesso") == 4
    assert "varrer.falha" not in acoes


def test_varredura_audita_falha_em_sessao_independente(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    execucao_id = uuid.uuid4()
    with session_factory() as session:
        casos_antes = session.scalar(select(func.count()).select_from(CobrancaCasoORM))
    service = VarreduraCobrancaService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        SqlAlchemyAuditoriaRegistro(session_factory),
    )

    with pytest.raises(ValueError, match="carteira"):
        service.executar(
            tenant_id=ambiente.tenant_id,
            carteira_id=uuid.uuid4(),
            data_referencia=datetime.now(UTC).date(),
            execucao_id=execucao_id,
        )

    with session_factory() as session:
        acoes = session.scalars(
            select(AuditoriaLogORM.acao).where(
                AuditoriaLogORM.entidade == "cobranca_varredura",
                AuditoriaLogORM.entidade_id == execucao_id,
            )
        ).all()
        total_casos = session.scalar(select(func.count()).select_from(CobrancaCasoORM))
    assert len(acoes) == 2
    assert set(acoes) == {"varrer.inicio", "varrer.falha"}
    assert total_casos == casos_antes


def _ambiente(session_factory: sessionmaker[Session]) -> _Ambiente:
    with session_factory() as session:
        tenant = TenantFactory.build()
        SqlAlchemyTenantRepository(session).save(tenant)
        carteira = CarteiraFactory.build(tenant_id=tenant.id)
        SqlAlchemyCarteiraRepository(session).save(carteira)
        usuario = UsuarioFactory.build(tenant_id=tenant.id)
        SqlAlchemyUsuarioRepository(session).save(usuario)
        session.commit()
    return _Ambiente(tenant.id, carteira.id, usuario.id)


def _cpf() -> str:
    digitos = [int(digito) for digito in f"{uuid.uuid4().int % 10**9:09d}"]
    for _ in range(2):
        peso = len(digitos) + 1
        soma = sum(digito * (peso - indice) for indice, digito in enumerate(digitos))
        resto = (soma * 10) % 11
        digitos.append(0 if resto == 10 else resto)
    return "".join(str(digito) for digito in digitos)


def _aguardar_job_concluido(
    session_factory: sessionmaker[Session],
    job_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    limite = time.monotonic() + 5
    while time.monotonic() < limite:
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            job = uow.job_agendado.find_scoped(job_id, tenant_id)
        if job is not None and job.estado is EstadoJob.CONCLUIDO:
            return
        time.sleep(0.05)
    raise AssertionError("worker nao concluiu a varredura dentro do timeout")


def _total_jobs_varredura(
    session_factory: sessionmaker[Session],
    ambiente: _Ambiente,
) -> int:
    with session_factory() as session:
        return (
            session.scalar(
                select(func.count())
                .select_from(JobAgendadoORM)
                .where(
                    JobAgendadoORM.tenant_id == ambiente.tenant_id,
                    JobAgendadoORM.carteira_id == ambiente.carteira_id,
                    JobAgendadoORM.tipo == TIPO_JOB_VARREDURA_COBRANCA,
                )
            )
            or 0
        )


def _priorizar_job(
    session_factory: sessionmaker[Session],
    job_id: uuid.UUID,
) -> None:
    with session_factory() as session:
        job = session.get(JobAgendadoORM, job_id)
        assert job is not None
        job.proxima_execucao_em = datetime(2000, 1, 1, tzinfo=UTC)
        session.commit()


def _assert_um_caso(
    session_factory: sessionmaker[Session],
    ambiente: _Ambiente,
) -> None:
    with session_factory() as session:
        total = session.scalar(
            select(func.count())
            .select_from(CobrancaCasoORM)
            .where(
                CobrancaCasoORM.tenant_id == ambiente.tenant_id,
                CobrancaCasoORM.carteira_id == ambiente.carteira_id,
            )
        )
    assert total == 1
