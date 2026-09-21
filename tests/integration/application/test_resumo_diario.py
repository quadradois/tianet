"""IMP-353: varredura real -> resumo diario ao Credor pelo worker."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.lancamento import (
    CondicoesLancamento,
    DevedorNovo,
    LancamentoService,
)
from emprestimo.application.motor_financeiro import criar_emprestimo_e_plano_em
from emprestimo.application.resumo_diario import (
    TIPO_JOB_RESUMO_DIARIO,
    EntregaResumoDiarioService,
    ResumoDiarioService,
)
from emprestimo.application.scheduler import SchedulerService
from emprestimo.application.varredura_cobranca import (
    TIPO_JOB_VARREDURA_COBRANCA,
    AgendadorVarreduraCobranca,
    VarreduraCobrancaService,
)
from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.domain.credit.notifications import ResultadoCanal, ResultadoEnvio
from emprestimo.domain.credit.scheduler import EstadoJob, JobAgendado
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import JobAgendadoORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyConfiguracaoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.worker.scheduler_worker import SchedulerWorker, WorkerSettings

WHATSAPP_CREDOR = "5511977776655"
FUTURO = datetime(2099, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class _Ambiente:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    usuario_id: uuid.UUID


class _CanalGravador(NotificationChannel):
    def __init__(self) -> None:
        self.envios: list[dict[str, str]] = []

    def enviar(
        self, *, destinatario: str, assunto: str, corpo: str, chave_idempotente: str
    ) -> ResultadoEnvio:
        self.envios.append({"destinatario": destinatario, "corpo": corpo})
        return ResultadoEnvio(
            ResultadoCanal.ACEITA,
            provider_message_id=f"evolution-resumo-{len(self.envios)}",
            chave_idempotente=chave_idempotente,
        )

    def consultar_status(self, provider_message_id: str) -> ResultadoEnvio:
        del provider_message_id
        return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="nao_consultavel")


def test_varredura_pelo_worker_enfileira_resumo_e_worker_envia_ao_credor(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory, com_credor=True)
    dia_do_acerto = _lancar(session_factory, ambiente, nome="Maria da Silva")

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    resumo = ResumoDiarioService(uow_factory, auditoria)
    varredura = VarreduraCobrancaService(uow_factory, auditoria, apos_sucesso=resumo.enfileirar)
    canal = _CanalGravador()
    entrega = EntregaResumoDiarioService(uow_factory, canal, auditoria)

    AgendadorVarreduraCobranca(uow_factory, auditoria).agendar_dia(
        data_referencia=dia_do_acerto, executar_em=datetime.now(UTC)
    )
    worker = SchedulerWorker(
        SchedulerService(uow_factory, auditoria),
        {
            TIPO_JOB_VARREDURA_COBRANCA: varredura.processar_job,
            TIPO_JOB_RESUMO_DIARIO: entrega.processar,
        },
        WorkerSettings(concurrency=1, batch_size=1),
    )
    job_varredura = _aguardar_job(session_factory, ambiente, TIPO_JOB_VARREDURA_COBRANCA)
    try:
        # O banco e compartilhado com outros testes: prioriza o proprio job
        # para o worker nao reivindicar sobras de outro tenant.
        _priorizar_job(session_factory, job_varredura.id)
        _rodar_ate_concluir(worker, session_factory, job_varredura.id, ambiente.tenant_id)
        job_resumo = _aguardar_job(session_factory, ambiente, TIPO_JOB_RESUMO_DIARIO)
        _priorizar_job(session_factory, job_resumo.id)
        _rodar_ate_concluir(worker, session_factory, job_resumo.id, ambiente.tenant_id)
    finally:
        worker.stop()

    assert len(canal.envios) == 1
    assert canal.envios[0]["destinatario"] == WHATSAPP_CREDOR
    assert "Maria da Silva" in canal.envios[0]["corpo"]
    assert canal.envios[0]["corpo"].startswith(
        f"Acertos de hoje ({dia_do_acerto.strftime('%d/%m/%Y')}): 1"
    )


def test_mesma_carteira_e_dia_nao_cria_segundo_resumo(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory, com_credor=True)
    dia_do_acerto = _lancar(session_factory, ambiente, nome="Joao")

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    # Agendado no futuro: o banco e compartilhado, e um job elegivel sobrando
    # aqui seria reivindicado pelo worker de outro teste.
    resumo = ResumoDiarioService(uow_factory, auditoria, agora=lambda: FUTURO)
    varredura = VarreduraCobrancaService(uow_factory, auditoria)
    resultado = varredura.executar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        data_referencia=dia_do_acerto,
    )

    primeiro = resumo.enfileirar(ambiente.tenant_id, ambiente.carteira_id, resultado)
    segundo = resumo.enfileirar(ambiente.tenant_id, ambiente.carteira_id, resultado)

    assert primeiro is not None
    assert segundo is not None and segundo.id == primeiro.id
    assert _total_jobs(session_factory, ambiente, TIPO_JOB_RESUMO_DIARIO) == 1


def test_dia_sem_acerto_nao_enfileira(session_factory: sessionmaker[Session]) -> None:
    ambiente = _ambiente(session_factory, com_credor=True)
    dia_do_acerto = _lancar(session_factory, ambiente, nome="Ana")

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    resultado = VarreduraCobrancaService(uow_factory, auditoria).executar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        data_referencia=dia_do_acerto - date.resolution,
    )
    assert not resultado.vencem_hoje

    job = ResumoDiarioService(uow_factory, auditoria).enfileirar(
        ambiente.tenant_id, ambiente.carteira_id, resultado
    )

    assert job is None
    assert _total_jobs(session_factory, ambiente, TIPO_JOB_RESUMO_DIARIO) == 0


def test_dia_so_com_atraso_enfileira_bloco_de_atraso(
    session_factory: sessionmaker[Session],
) -> None:
    """Cinco dias depois do acerto, sem pagamento: ninguem vence hoje, mas o
    Motor apura juro exigivel e a Credora precisa saber (PLAN-045 D5)."""
    ambiente = _ambiente(session_factory, com_credor=True)
    dia_do_acerto = _lancar(session_factory, ambiente, nome="Carlos")

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    resultado = VarreduraCobrancaService(uow_factory, auditoria).executar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        data_referencia=dia_do_acerto + timedelta(days=5),
    )
    assert not resultado.vencem_hoje
    assert len(resultado.em_atraso) == 1

    job = ResumoDiarioService(uow_factory, auditoria, agora=lambda: FUTURO).enfileirar(
        ambiente.tenant_id, ambiente.carteira_id, resultado
    )

    assert job is not None
    texto = job.payload["texto"]
    assert texto.startswith("Em atraso: 1")
    assert f"Carlos - desde {dia_do_acerto.strftime('%d/%m')} (5 dias) - juro R$ " in texto
    assert "Acertos de hoje" not in texto


def test_sem_credor_whatsapp_nao_enfileira_e_audita(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory, com_credor=False)
    dia_do_acerto = _lancar(session_factory, ambiente, nome="Pedro")

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    resultado = VarreduraCobrancaService(uow_factory, auditoria).executar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        data_referencia=dia_do_acerto,
    )

    job = ResumoDiarioService(uow_factory, auditoria).enfileirar(
        ambiente.tenant_id, ambiente.carteira_id, resultado
    )

    assert job is None
    assert _total_jobs(session_factory, ambiente, TIPO_JOB_RESUMO_DIARIO) == 0


def _ambiente(session_factory: sessionmaker[Session], *, com_credor: bool) -> _Ambiente:
    with session_factory() as session:
        tenant = TenantFactory.build()
        SqlAlchemyTenantRepository(session).save(tenant)
        carteira = CarteiraFactory.build(tenant_id=tenant.id)
        SqlAlchemyCarteiraRepository(session).save(carteira)
        usuario = UsuarioFactory.build(tenant_id=tenant.id)
        SqlAlchemyUsuarioRepository(session).save(usuario)
        if com_credor:
            SqlAlchemyConfiguracaoRepository(session).save(
                Configuracao(tenant_id=tenant.id, chave="credor_whatsapp", valor=WHATSAPP_CREDOR)
            )
        session.commit()
    return _Ambiente(tenant.id, carteira.id, usuario.id)


def _lancar(session_factory: sessionmaker[Session], ambiente: _Ambiente, *, nome: str) -> date:
    """Lanca um emprestimo e devolve a data do primeiro acerto."""
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
        devedor_novo=DevedorNovo(documento=_cpf(), nome=nome, contato_whatsapp="(11) 98888-7766"),
        condicoes=CondicoesLancamento(
            valor_contratado="6000.00", taxa_juros_mensal="0.0300", dia_de_acerto=10
        ),
        data_referencia=hoje,
        idempotency_key=str(uuid.uuid4()),
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        emprestimo = uow.emprestimo.find_by_id(lancamento.emprestimo_id)
    assert emprestimo is not None
    primeiro_acerto = emprestimo.proximo_acerto_em(hoje)
    assert primeiro_acerto is not None
    return primeiro_acerto


def _total_jobs(session_factory: sessionmaker[Session], ambiente: _Ambiente, tipo: str) -> int:
    with session_factory() as session:
        return len(
            session.scalars(
                select(JobAgendadoORM.id)
                .where(JobAgendadoORM.tenant_id == ambiente.tenant_id)
                .where(JobAgendadoORM.carteira_id == ambiente.carteira_id)
                .where(JobAgendadoORM.tipo == tipo)
            ).all()
        )


def _aguardar_job(
    session_factory: sessionmaker[Session], ambiente: _Ambiente, tipo: str
) -> JobAgendado:
    limite = time.monotonic() + 5
    while time.monotonic() < limite:
        with session_factory() as session:
            job_id = session.scalar(
                select(JobAgendadoORM.id)
                .where(JobAgendadoORM.tenant_id == ambiente.tenant_id)
                .where(JobAgendadoORM.tipo == tipo)
            )
        if job_id is not None:
            with SqlAlchemyUnitOfWork(session_factory) as uow:
                job = uow.job_agendado.find_scoped(job_id, ambiente.tenant_id)
            if job is not None:
                return job
        time.sleep(0.05)
    raise AssertionError(f"job {tipo} nao apareceu dentro do timeout")


def _priorizar_job(session_factory: sessionmaker[Session], job_id: uuid.UUID) -> None:
    with session_factory() as session:
        job = session.get(JobAgendadoORM, job_id)
        assert job is not None
        job.proxima_execucao_em = datetime(2000, 1, 1, tzinfo=UTC)
        session.commit()


def _rodar_ate_concluir(
    worker: SchedulerWorker,
    session_factory: sessionmaker[Session],
    job_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    """Cicla o worker ate o job concluir; sobras de outros testes so atrasam."""
    limite = time.monotonic() + 10
    while time.monotonic() < limite:
        worker.cycle()
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            job = uow.job_agendado.find_scoped(job_id, tenant_id)
        if job is not None and job.estado is EstadoJob.CONCLUIDO:
            return
        time.sleep(0.05)
    raise AssertionError("job nao concluiu dentro do timeout")


def _cpf() -> str:
    digitos = [int(digito) for digito in f"{uuid.uuid4().int % 10**9:09d}"]
    for _ in range(2):
        peso = len(digitos) + 1
        soma = sum(digito * (peso - indice) for indice, digito in enumerate(digitos))
        resto = (soma * 10) % 11
        digitos.append(0 if resto == 10 else resto)
    return "".join(str(digito) for digito in digitos)
