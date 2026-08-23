"""Integracao do IMP-330: lancamento real ate a entrega do comprovante."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.comprovante import (
    ORIGEM_COMPROVANTE,
    TIPO_JOB_COMPROVANTE,
    ComprovanteService,
    EntregaComprovanteService,
)
from emprestimo.application.lancamento import (
    CondicoesLancamento,
    DevedorNovo,
    LancamentoResultado,
    LancamentoService,
)
from emprestimo.application.motor_financeiro import criar_emprestimo_e_plano_em
from emprestimo.application.scheduler import SchedulerService
from emprestimo.domain.credit.automacao_ports import AutomacaoFiltros, NotificationChannel
from emprestimo.domain.credit.notifications import (
    EstadoSolicitacaoNotificacao,
    ResultadoCanal,
    ResultadoEnvio,
    SolicitacaoNotificacao,
)
from emprestimo.domain.credit.scheduler import EstadoJob, JobAgendado
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import AuditoriaLogORM, RegistroComunicacaoORM
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


class _CanalSequencial(NotificationChannel):
    def __init__(self, *resultados: ResultadoCanal) -> None:
        self._resultados = list(resultados)
        self.envios: list[dict[str, str]] = []

    def enviar(
        self,
        *,
        destinatario: str,
        assunto: str,
        corpo: str,
        chave_idempotente: str,
    ) -> ResultadoEnvio:
        self.envios.append(
            {
                "destinatario": destinatario,
                "assunto": assunto,
                "corpo": corpo,
                "chave_idempotente": chave_idempotente,
            }
        )
        resultado = self._resultados.pop(0)
        return ResultadoEnvio(
            resultado,
            provider_message_id=(
                f"evolution-{len(self.envios)}" if resultado is ResultadoCanal.ACEITA else None
            ),
            codigo=f"teste_{resultado.value}",
            chave_idempotente=chave_idempotente,
        )

    def consultar_status(self, provider_message_id: str) -> ResultadoEnvio:
        del provider_message_id
        return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="nao_consultavel")


def test_lancamento_real_worker_conclui_e_registra_entrega(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    lancamento, job = _lancar(session_factory, ambiente)
    canal = _CanalSequencial(ResultadoCanal.ACEITA)
    worker = _worker(session_factory, canal)

    assert job.estado is EstadoJob.AGENDADO
    assert worker.cycle() == 1
    concluido = _aguardar_estado_job(
        session_factory,
        job.id,
        ambiente.tenant_id,
        EstadoJob.CONCLUIDO,
    )
    worker.stop()

    notificacoes = _notificacoes(session_factory, ambiente)
    assert concluido.tentativas == 1
    assert len(canal.envios) == 1
    assert canal.envios[0]["destinatario"] == "(11) 98888-7766"
    assert "Comprovante do lancamento" in canal.envios[0]["corpo"]
    assert len(notificacoes) == 1
    assert notificacoes[0].estado is EstadoSolicitacaoNotificacao.ACEITA
    assert notificacoes[0].lembrete_id is None
    assert notificacoes[0].template_id is None

    with session_factory() as session:
        comunicacao = session.scalar(
            select(RegistroComunicacaoORM).where(
                RegistroComunicacaoORM.emprestimo_id == lancamento.emprestimo_id
            )
        )
        acoes = session.scalars(
            select(AuditoriaLogORM.acao).where(AuditoriaLogORM.entidade == "comprovante_entrega")
        ).all()
    assert comunicacao is not None
    assert comunicacao.canal == "whatsapp"
    assert comunicacao.notification_id == notificacoes[0].id
    assert comunicacao.provider_message_id == "evolution-1"
    assert set(acoes) == {"entregar.inicio", "entregar.resultado"}


def test_falha_temporaria_reagenda_e_retry_conclui_mesma_solicitacao(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    _, job = _lancar(session_factory, ambiente)
    canal = _CanalSequencial(ResultadoCanal.FALHA_TEMPORARIA, ResultadoCanal.ACEITA)
    worker = _worker(session_factory, canal)

    assert worker.cycle() == 1
    falha = _aguardar_estado_job(
        session_factory,
        job.id,
        ambiente.tenant_id,
        EstadoJob.FALHA_TEMPORARIA,
    )
    primeira = _notificacoes(session_factory, ambiente)
    assert falha.tentativas == 1
    assert falha.proxima_execucao_em is not None
    assert falha.proxima_execucao_em > datetime.now(UTC)
    assert len(primeira) == 1
    assert primeira[0].estado is EstadoSolicitacaoNotificacao.FALHA_TEMPORARIA

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        reagendado = uow.job_agendado.find_scoped(job.id, ambiente.tenant_id)
        assert reagendado is not None
        reagendado.proxima_execucao_em = datetime.now(UTC) - timedelta(seconds=1)
        uow.job_agendado.save(reagendado)
        uow.commit()

    _executar_ate_reivindicar(worker)
    concluido = _aguardar_estado_job(
        session_factory,
        job.id,
        ambiente.tenant_id,
        EstadoJob.CONCLUIDO,
    )
    worker.stop()

    segunda = _notificacoes(session_factory, ambiente)
    assert concluido.tentativas == 2
    assert len(canal.envios) == 2
    assert canal.envios[0]["chave_idempotente"] == canal.envios[1]["chave_idempotente"]
    assert len(segunda) == 1
    assert segunda[0].id == primeira[0].id
    assert segunda[0].estado is EstadoSolicitacaoNotificacao.ACEITA


def test_falha_permanente_e_terminal_e_nao_entra_em_retry_infinito(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    _, job = _lancar(session_factory, ambiente)
    canal = _CanalSequencial(ResultadoCanal.FALHA_PERMANENTE)
    worker = _worker(session_factory, canal)

    assert worker.cycle() == 1
    falha = _aguardar_estado_job(
        session_factory,
        job.id,
        ambiente.tenant_id,
        EstadoJob.FALHA_PERMANENTE,
    )
    time.sleep(0.05)
    assert worker.cycle() == 0
    worker.stop()

    notificacoes = _notificacoes(session_factory, ambiente)
    assert falha.tentativas == 1
    assert len(canal.envios) == 1
    assert len(notificacoes) == 1
    assert notificacoes[0].estado is EstadoSolicitacaoNotificacao.FALHA_PERMANENTE


def test_resultado_desconhecido_e_terminal_para_evitar_comprovante_duplicado(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    _, job = _lancar(session_factory, ambiente)
    canal = _CanalSequencial(ResultadoCanal.DESCONHECIDO)
    worker = _worker(session_factory, canal)

    assert worker.cycle() == 1
    falha = _aguardar_estado_job(
        session_factory,
        job.id,
        ambiente.tenant_id,
        EstadoJob.FALHA_PERMANENTE,
    )
    time.sleep(0.05)
    assert worker.cycle() == 0
    worker.stop()

    notificacoes = _notificacoes(session_factory, ambiente)
    assert falha.tentativas == 1
    assert len(canal.envios) == 1
    assert len(notificacoes) == 1
    assert notificacoes[0].estado is EstadoSolicitacaoNotificacao.RESULTADO_DESCONHECIDO


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


def _lancar(
    session_factory: sessionmaker[Session],
    ambiente: _Ambiente,
) -> tuple[LancamentoResultado, JobAgendado]:
    comprovantes = ComprovanteService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        SqlAlchemyAuditoriaRegistro(session_factory),
    )
    resultado = LancamentoService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        criar_emprestimo_e_plano_em,
        comprovantes.enfileirar,
        SqlAlchemyAuditoriaRegistro(session_factory),
    ).lancar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        usuario_id=ambiente.usuario_id,
        devedor_novo=DevedorNovo(
            documento=_cpf(),
            nome="Devedor do comprovante",
            contato_whatsapp="(11) 98888-7766",
        ),
        condicoes=CondicoesLancamento(
            valor_contratado="6000.00",
            taxa_juros_mensal="0.0300",
            dia_de_acerto=10,
        ),
        data_referencia=date(2026, 8, 16),
        idempotency_key=str(uuid.uuid4()),
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        job = uow.job_agendado.find_by_origem(
            tenant_id=ambiente.tenant_id,
            origem_tipo=ORIGEM_COMPROVANTE,
            origem_id=resultado.emprestimo_id,
        )
    assert job is not None
    assert job.tipo == TIPO_JOB_COMPROVANTE
    return resultado, job


def _worker(
    session_factory: sessionmaker[Session],
    canal: NotificationChannel,
) -> SchedulerWorker:
    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    entrega = EntregaComprovanteService(
        uow_factory,
        canal,
        SqlAlchemyAuditoriaRegistro(session_factory),
    )
    return SchedulerWorker(
        SchedulerService(uow_factory, SqlAlchemyAuditoriaRegistro(session_factory)),
        {TIPO_JOB_COMPROVANTE: entrega.processar_comprovante},
        WorkerSettings(concurrency=1, batch_size=1),
    )


def _notificacoes(
    session_factory: sessionmaker[Session],
    ambiente: _Ambiente,
) -> list[SolicitacaoNotificacao]:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        return list(
            uow.solicitacao_notificacao.listar(
                AutomacaoFiltros(
                    tenant_id=ambiente.tenant_id,
                    carteira_id=ambiente.carteira_id,
                )
            ).items
        )


def _aguardar_estado_job(
    session_factory: sessionmaker[Session],
    job_id: uuid.UUID,
    tenant_id: uuid.UUID,
    esperado: EstadoJob,
) -> JobAgendado:
    limite = time.monotonic() + 5
    while time.monotonic() < limite:
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            job = uow.job_agendado.find_scoped(job_id, tenant_id)
        if job is not None and job.estado is esperado:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job nao atingiu estado {esperado.value} dentro do timeout")


def _executar_ate_reivindicar(worker: SchedulerWorker) -> None:
    limite = time.monotonic() + 2
    while time.monotonic() < limite:
        if worker.cycle() == 1:
            return
        time.sleep(0.01)
    raise AssertionError("worker nao reivindicou o retry")


def _cpf() -> str:
    digitos = [int(digito) for digito in f"{uuid.uuid4().int % 10**9:09d}"]
    for _ in range(2):
        peso = len(digitos) + 1
        soma = sum(digito * (peso - indice) for indice, digito in enumerate(digitos))
        resto = (soma * 10) % 11
        digitos.append(0 if resto == 10 else resto)
    return "".join(str(digito) for digito in digitos)
