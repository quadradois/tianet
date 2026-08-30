"""Integracao do IMP-350: pagamento excedente real ate a entrega do aviso.

O IMP-332 entregou o enfileiramento do aviso e o estorno, e o teste de API
(`test_pagamento_excedente_enfileira_aviso_e_estorno_reconcilia`) cobre essa
metade. A outra metade — o handler que o worker executa — nao tinha teste
nenhum: `EntregaAvisoSobraPagamentoService` estava com 0% no caminho de
processamento enquanto o handler ja rodava registrado no worker.

E o mesmo buraco do IMP-330, no item seguinte. La, o job virava
`handler_ausente` em silencio porque nada exercitava a cadeia inteira.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.lancamento import (
    CondicoesLancamento,
    DevedorNovo,
    LancamentoService,
)
from emprestimo.application.motor_financeiro import (
    PagamentoService,
    criar_emprestimo_e_plano_em,
)
from emprestimo.application.notifications import (
    ORIGEM_AVISO_SOBRA,
    TIPO_JOB_AVISO_SOBRA,
    AvisoSobraPagamentoService,
    EntregaAvisoSobraPagamentoService,
)
from emprestimo.application.scheduler import SchedulerService
from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.domain.credit.notifications import ResultadoCanal, ResultadoEnvio
from emprestimo.domain.credit.scheduler import EstadoJob, JobAgendado
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import AuditoriaLogORM, RegistroComunicacaoORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyConfiguracaoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.worker.scheduler_worker import SchedulerWorker, WorkerSettings

WHATSAPP_CREDOR = "5511977776655"


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
                f"evolution-sobra-{len(self.envios)}"
                if resultado is ResultadoCanal.ACEITA
                else None
            ),
            codigo=f"teste_{resultado.value}",
            chave_idempotente=chave_idempotente,
        )

    def consultar_status(self, provider_message_id: str) -> ResultadoEnvio:
        del provider_message_id
        return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="nao_consultavel")


def test_sobra_real_worker_entrega_aviso_e_registra_comunicacao(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    job, emprestimo_id = _pagar_com_sobra(session_factory, ambiente)
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

    assert concluido.tentativas == 1
    assert len(canal.envios) == 1
    assert canal.envios[0]["destinatario"] == WHATSAPP_CREDOR
    assert "Sobra a devolver" in canal.envios[0]["corpo"]
    assert "PIX de devolucao" in canal.envios[0]["corpo"]

    with session_factory() as session:
        comunicacao = session.scalar(
            select(RegistroComunicacaoORM).where(
                RegistroComunicacaoORM.emprestimo_id == emprestimo_id
            )
        )
    acoes = _aguardar_acoes_auditoria(
        session_factory,
        "sobra_pagamento_aviso",
        {"entregar.inicio", "entregar.resultado"},
    )
    assert comunicacao is not None
    assert comunicacao.canal == "whatsapp"
    assert comunicacao.provider_message_id == "evolution-sobra-1"
    assert {"entregar.inicio", "entregar.resultado"} <= set(acoes)


def test_falha_temporaria_reagenda_e_retry_reusa_a_mesma_chave(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    job, _ = _pagar_com_sobra(session_factory, ambiente)
    canal = _CanalSequencial(ResultadoCanal.FALHA_TEMPORARIA, ResultadoCanal.ACEITA)
    worker = _worker(session_factory, canal)

    assert worker.cycle() == 1
    falha = _aguardar_estado_job(
        session_factory,
        job.id,
        ambiente.tenant_id,
        EstadoJob.FALHA_TEMPORARIA,
    )
    assert falha.tentativas == 1
    assert falha.proxima_execucao_em is not None
    assert falha.proxima_execucao_em > datetime.now(UTC)

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

    assert concluido.tentativas == 2
    assert len(canal.envios) == 2
    # A chave idempotente vem da origem, nao da tentativa: o provedor reconhece
    # o retry como o mesmo aviso e o Credor nao e avisado duas vezes.
    assert canal.envios[0]["chave_idempotente"] == canal.envios[1]["chave_idempotente"]


def test_falha_permanente_e_terminal_e_nao_entra_em_retry_infinito(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    job, _ = _pagar_com_sobra(session_factory, ambiente)
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

    assert falha.tentativas == 1
    assert len(canal.envios) == 1


def test_sem_prova_de_entrega_nao_registra_comunicacao(
    session_factory: sessionmaker[Session],
) -> None:
    """Resultado desconhecido nao prova entrega — nao pode virar registro."""
    ambiente = _ambiente(session_factory)
    job, emprestimo_id = _pagar_com_sobra(session_factory, ambiente)
    canal = _CanalSequencial(ResultadoCanal.DESCONHECIDO)
    worker = _worker(session_factory, canal)

    assert worker.cycle() == 1
    _aguardar_estado_job(
        session_factory,
        job.id,
        ambiente.tenant_id,
        EstadoJob.FALHA_PERMANENTE,
    )
    worker.stop()

    with session_factory() as session:
        comunicacao = session.scalar(
            select(RegistroComunicacaoORM).where(
                RegistroComunicacaoORM.emprestimo_id == emprestimo_id
            )
        )
    assert comunicacao is None, "sem prova de entrega nao se registra comunicacao"


def _ambiente(session_factory: sessionmaker[Session]) -> _Ambiente:
    with session_factory() as session:
        tenant = TenantFactory.build()
        SqlAlchemyTenantRepository(session).save(tenant)
        carteira = CarteiraFactory.build(tenant_id=tenant.id)
        SqlAlchemyCarteiraRepository(session).save(carteira)
        usuario = UsuarioFactory.build(tenant_id=tenant.id)
        SqlAlchemyUsuarioRepository(session).save(usuario)
        SqlAlchemyConfiguracaoRepository(session).save(
            Configuracao(
                tenant_id=tenant.id,
                chave="credor_whatsapp",
                valor=WHATSAPP_CREDOR,
            )
        )
        session.commit()
    return _Ambiente(tenant.id, carteira.id, usuario.id)


def _pagar_com_sobra(
    session_factory: sessionmaker[Session],
    ambiente: _Ambiente,
) -> tuple[JobAgendado, uuid.UUID]:
    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    lancamento = LancamentoService(
        uow_factory,
        criar_emprestimo_e_plano_em,
        lambda _resultado: None,
        auditoria,
    ).lancar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        usuario_id=ambiente.usuario_id,
        devedor_novo=DevedorNovo(
            documento=_cpf(),
            nome="Devedor da sobra",
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

    avisos = AvisoSobraPagamentoService(uow_factory, auditoria)
    # Valor muito acima do devido: o Motor distribui o que cabe e devolve o resto.
    pagamento = PagamentoService(
        uow_factory,
        auditoria,
        enfileirar_aviso=avisos.enfileirar,
    ).registrar(
        emprestimo_id=lancamento.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        valor=Decimal("12000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key=str(uuid.uuid4()),
    )
    assert pagamento.valor_devolvido > Decimal("0.00"), "cenario exige sobra real"

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        job = uow.job_agendado.find_by_origem(
            tenant_id=ambiente.tenant_id,
            origem_tipo=ORIGEM_AVISO_SOBRA,
            origem_id=pagamento.pagamento_id,
        )
    assert job is not None, "pagamento excedente deveria ter enfileirado o aviso"
    assert job.tipo == TIPO_JOB_AVISO_SOBRA
    return job, lancamento.emprestimo_id


def _worker(
    session_factory: sessionmaker[Session],
    canal: NotificationChannel,
) -> SchedulerWorker:
    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    entrega = EntregaAvisoSobraPagamentoService(
        uow_factory,
        canal,
        SqlAlchemyAuditoriaRegistro(session_factory),
    )
    return SchedulerWorker(
        SchedulerService(uow_factory, SqlAlchemyAuditoriaRegistro(session_factory)),
        {TIPO_JOB_AVISO_SOBRA: entrega.processar_aviso},
        WorkerSettings(concurrency=1, batch_size=1),
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


def _aguardar_acoes_auditoria(
    session_factory: sessionmaker[Session],
    entidade: str,
    esperadas: set[str],
) -> list[str]:
    """Espera os eventos da trilha aparecerem, em vez de assumi-los (ADR-002).

    A auditoria commita em sessao INDEPENDENTE da transacao de negocio, por
    desenho: ela precisa sobreviver ao rollback. O preco e que ela pousa DEPOIS
    de o job ja constar CONCLUIDO — `entregar.resultado` e gravado apos
    `job.concluir`, e o worker roda em thread propria.

    Sincronizar no estado do job e, portanto, uma premissa errada: em maquina
    lenta a thread principal ganha a corrida e le a trilha incompleta. Foi assim
    que o CI reprovou enquanto a suite passava local.
    """
    limite = time.monotonic() + 5
    vistas: set[str] = set()
    while time.monotonic() < limite:
        with session_factory() as session:
            vistas = set(
                session.scalars(
                    select(AuditoriaLogORM.acao).where(AuditoriaLogORM.entidade == entidade)
                ).all()
            )
        if esperadas <= vistas:
            return sorted(vistas)
        time.sleep(0.05)
    faltando = sorted(esperadas - vistas)
    raise AssertionError(f"trilha de {entidade} sem {faltando} dentro do timeout")


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
