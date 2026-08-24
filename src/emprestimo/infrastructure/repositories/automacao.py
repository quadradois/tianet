"""Repositories SQLAlchemy de Scheduler e Notification."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from emprestimo.domain.common.errors import TemplateNotificacaoJaExisteError
from emprestimo.domain.credit.automacao_ports import (
    AutomacaoFiltros,
    JobAgendadoRepository,
    PreferenciaNotificacaoRepository,
    ResultadoPaginado,
    SolicitacaoNotificacaoRepository,
    TemplateNotificacaoRepository,
    TentativaJobRepository,
)
from emprestimo.domain.credit.notifications import (
    EstadoPreferenciaNotificacao,
    EstadoSolicitacaoNotificacao,
    EstadoTemplateNotificacao,
    PreferenciaNotificacao,
    SolicitacaoNotificacao,
    TemplateNotificacao,
)
from emprestimo.domain.credit.scheduler import (
    EstadoJob,
    EstadoTentativaJob,
    JobAgendado,
    TentativaJob,
)
from emprestimo.infrastructure.db.orm import (
    JobAgendadoORM,
    NotificacaoEvidenciaORM,
    PreferenciaNotificacaoORM,
    SolicitacaoNotificacaoORM,
    TemplateNotificacaoORM,
    TentativaJobORM,
)


class SqlAlchemyJobAgendadoRepository(JobAgendadoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, job: JobAgendado) -> None:
        self._session.merge(_job_orm(job))
        self._session.flush()

    def save_if_absent(self, job: JobAgendado) -> bool:
        inserido = self._session.scalar(
            postgresql_insert(JobAgendadoORM)
            .values(id=job.id, **_job_values(job))
            .on_conflict_do_nothing(constraint="uq_job_origem_tenant")
            .returning(JobAgendadoORM.id)
        )
        self._session.flush()
        return inserido is not None

    def find_scoped(self, job_id: uuid.UUID, tenant_id: uuid.UUID) -> JobAgendado | None:
        row = self._session.scalar(
            select(JobAgendadoORM).where(
                JobAgendadoORM.id == job_id,
                JobAgendadoORM.tenant_id == tenant_id,
            )
        )
        return _job_domain(row) if row else None

    def find_by_origem(
        self,
        *,
        tenant_id: uuid.UUID,
        origem_tipo: str,
        origem_id: uuid.UUID,
    ) -> JobAgendado | None:
        row = self._session.scalar(
            select(JobAgendadoORM).where(
                JobAgendadoORM.tenant_id == tenant_id,
                JobAgendadoORM.origem_tipo == origem_tipo,
                JobAgendadoORM.origem_id == origem_id,
            )
        )
        return _job_domain(row) if row else None

    def listar(self, filtros: AutomacaoFiltros) -> ResultadoPaginado[JobAgendado]:
        condicoes: list[Any] = [JobAgendadoORM.tenant_id == filtros.tenant_id]
        if filtros.carteira_id is not None:
            condicoes.append(JobAgendadoORM.carteira_id == filtros.carteira_id)
        total = (
            self._session.scalar(select(func.count()).select_from(JobAgendadoORM).where(*condicoes))
            or 0
        )
        rows = self._session.scalars(
            select(JobAgendadoORM)
            .where(*condicoes)
            .order_by(JobAgendadoORM.criado_em.desc(), JobAgendadoORM.id)
            .offset((filtros.page - 1) * filtros.size)
            .limit(filtros.size)
        ).all()
        return ResultadoPaginado(
            items=[_job_domain(row) for row in rows],
            total=total,
            page=filtros.page,
            size=filtros.size,
        )

    def claim(
        self,
        *,
        agora: datetime,
        limite: int,
        duracao: timedelta,
    ) -> list[tuple[JobAgendado, TentativaJob]]:
        if limite <= 0:
            return []
        elegiveis = self._session.scalars(
            select(JobAgendadoORM)
            .where(
                JobAgendadoORM.cancelamento_solicitado.is_(False),
                JobAgendadoORM.tentativas < JobAgendadoORM.max_tentativas,
                or_(
                    (
                        JobAgendadoORM.estado.in_(["agendado", "falha_temporaria"])
                        & (JobAgendadoORM.proxima_execucao_em <= agora)
                    ),
                    (
                        (JobAgendadoORM.estado == "em_execucao")
                        & (JobAgendadoORM.lease_ate <= agora)
                    ),
                ),
            )
            .order_by(
                JobAgendadoORM.proxima_execucao_em, JobAgendadoORM.criado_em, JobAgendadoORM.id
            )
            .limit(limite)
            .with_for_update(skip_locked=True)
        ).all()
        claims: list[tuple[JobAgendado, TentativaJob]] = []
        for row in elegiveis:
            job = _job_domain(row)
            tentativa = job.reivindicar(agora=agora, duracao=duracao)
            _copiar_job(row, job)
            self._session.add(_tentativa_orm(tentativa))
            claims.append((job, tentativa))
        self._session.flush()
        return claims

    def renovar_lease(
        self,
        job_id: uuid.UUID,
        lease_token: uuid.UUID,
        *,
        agora: datetime,
        duracao: timedelta,
    ) -> bool:
        result = cast(
            CursorResult[Any],
            self._session.execute(
                update(JobAgendadoORM)
                .where(
                    JobAgendadoORM.id == job_id,
                    JobAgendadoORM.estado == EstadoJob.EM_EXECUCAO.value,
                    JobAgendadoORM.lease_token == lease_token,
                    JobAgendadoORM.lease_ate > agora,
                )
                .values(lease_ate=agora + duracao, atualizado_em=agora)
            ),
        )
        self._session.flush()
        return bool(result.rowcount)

    def finalizar_com_fencing(self, job: JobAgendado, lease_token: uuid.UUID) -> bool:
        valores = _job_values(job)
        result = cast(
            CursorResult[Any],
            self._session.execute(
                update(JobAgendadoORM)
                .where(
                    JobAgendadoORM.id == job.id,
                    JobAgendadoORM.estado == EstadoJob.EM_EXECUCAO.value,
                    JobAgendadoORM.lease_token == lease_token,
                    JobAgendadoORM.lease_ate > func.clock_timestamp(),
                )
                .values(**valores)
            ),
        )
        self._session.flush()
        return bool(result.rowcount)

    def purgar_terminais_antes(self, limite: datetime) -> int:
        result = cast(
            CursorResult[Any],
            self._session.execute(
                delete(JobAgendadoORM).where(
                    JobAgendadoORM.estado.in_(["concluido", "falha_permanente", "cancelado"]),
                    JobAgendadoORM.atualizado_em < limite,
                )
            ),
        )
        self._session.flush()
        return int(result.rowcount or 0)


class SqlAlchemyTentativaJobRepository(TentativaJobRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, tentativa: TentativaJob) -> None:
        self._session.merge(_tentativa_orm(tentativa))
        self._session.flush()

    def listar_por_job(self, job_id: uuid.UUID) -> list[TentativaJob]:
        rows = self._session.scalars(
            select(TentativaJobORM)
            .where(TentativaJobORM.job_id == job_id)
            .order_by(TentativaJobORM.numero)
        ).all()
        return [_tentativa_domain(row) for row in rows]


class SqlAlchemyPreferenciaNotificacaoRepository(PreferenciaNotificacaoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, preferencia: PreferenciaNotificacao) -> None:
        self._session.merge(
            PreferenciaNotificacaoORM(
                id=preferencia.id,
                tenant_id=preferencia.tenant_id,
                carteira_id=preferencia.carteira_id,
                contato_id=preferencia.contato_id,
                estado=preferencia.estado.value,
                evidencia=preferencia.evidencia,
                origem=preferencia.origem,
                ator_id=preferencia.ator_id,
                registrada_em=preferencia.registrada_em,
                revogada_em=preferencia.revogada_em,
            )
        )
        self._session.flush()

    def find_by_contato(
        self, contato_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PreferenciaNotificacao | None:
        row = self._session.scalar(
            select(PreferenciaNotificacaoORM).where(
                PreferenciaNotificacaoORM.contato_id == contato_id,
                PreferenciaNotificacaoORM.tenant_id == tenant_id,
            )
        )
        return _preferencia_domain(row) if row else None


class SqlAlchemyTemplateNotificacaoRepository(TemplateNotificacaoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, template: TemplateNotificacao) -> None:
        try:
            self._session.merge(_template_orm(template))
            self._session.flush()
        except IntegrityError as exc:
            if "uq_template_versao" in str(exc.orig):
                raise TemplateNotificacaoJaExisteError(template.codigo, template.versao) from exc
            raise

    def find_scoped(
        self, template_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> TemplateNotificacao | None:
        row = self._session.scalar(
            select(TemplateNotificacaoORM).where(
                TemplateNotificacaoORM.id == template_id,
                TemplateNotificacaoORM.tenant_id == tenant_id,
            )
        )
        return _template_domain(row) if row else None

    def find_ativo(self, tenant_id: uuid.UUID, codigo: str) -> TemplateNotificacao | None:
        row = self._session.scalar(
            select(TemplateNotificacaoORM).where(
                TemplateNotificacaoORM.tenant_id == tenant_id,
                TemplateNotificacaoORM.codigo == codigo,
                TemplateNotificacaoORM.estado == EstadoTemplateNotificacao.ATIVO.value,
            )
        )
        return _template_domain(row) if row else None

    def find_by_codigo_versao(
        self, tenant_id: uuid.UUID, codigo: str, versao: int
    ) -> TemplateNotificacao | None:
        row = self._session.scalar(
            select(TemplateNotificacaoORM).where(
                TemplateNotificacaoORM.tenant_id == tenant_id,
                TemplateNotificacaoORM.codigo == codigo,
                TemplateNotificacaoORM.versao == versao,
            )
        )
        return _template_domain(row) if row else None

    def listar(self, filtros: AutomacaoFiltros) -> ResultadoPaginado[TemplateNotificacao]:
        condicoes = [TemplateNotificacaoORM.tenant_id == filtros.tenant_id]
        total = (
            self._session.scalar(
                select(func.count()).select_from(TemplateNotificacaoORM).where(*condicoes)
            )
            or 0
        )
        rows = self._session.scalars(
            select(TemplateNotificacaoORM)
            .where(*condicoes)
            .order_by(TemplateNotificacaoORM.codigo, TemplateNotificacaoORM.versao.desc())
            .offset((filtros.page - 1) * filtros.size)
            .limit(filtros.size)
        ).all()
        return ResultadoPaginado(
            list(map(_template_domain, rows)), total, filtros.page, filtros.size
        )


class SqlAlchemySolicitacaoNotificacaoRepository(SolicitacaoNotificacaoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, solicitacao: SolicitacaoNotificacao) -> None:
        self._session.merge(_solicitacao_orm(solicitacao))
        if solicitacao.resultado_em is not None:
            evidencia_id = uuid.uuid5(
                solicitacao.id,
                "|".join(
                    (
                        solicitacao.estado.value,
                        solicitacao.provider_message_id or "",
                        solicitacao.codigo_resultado or "",
                        solicitacao.resultado_em.isoformat(),
                    )
                ),
            )
            self._session.merge(
                NotificacaoEvidenciaORM(
                    id=evidencia_id,
                    solicitacao_id=solicitacao.id,
                    tentativa_job_id=solicitacao.tentativa_job_id,
                    tenant_id=solicitacao.tenant_id,
                    carteira_id=solicitacao.carteira_id,
                    provider_message_id=solicitacao.provider_message_id,
                    status=solicitacao.estado.value,
                    chave_idempotente=solicitacao.chave_idempotente,
                    ocorrido_em=solicitacao.resultado_em,
                )
            )
        self._session.flush()

    def find_scoped(
        self, solicitacao_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SolicitacaoNotificacao | None:
        row = self._session.scalar(
            select(SolicitacaoNotificacaoORM).where(
                SolicitacaoNotificacaoORM.id == solicitacao_id,
                SolicitacaoNotificacaoORM.tenant_id == tenant_id,
            )
        )
        return _solicitacao_domain(row) if row else None

    def find_by_chave(self, chave: str) -> SolicitacaoNotificacao | None:
        row = self._session.scalar(
            select(SolicitacaoNotificacaoORM).where(
                SolicitacaoNotificacaoORM.chave_idempotente == chave
            )
        )
        return _solicitacao_domain(row) if row else None

    def find_scoped_for_update(
        self, solicitacao_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SolicitacaoNotificacao | None:
        row = self._session.scalar(
            select(SolicitacaoNotificacaoORM)
            .where(
                SolicitacaoNotificacaoORM.id == solicitacao_id,
                SolicitacaoNotificacaoORM.tenant_id == tenant_id,
            )
            .with_for_update()
        )
        return _solicitacao_domain(row) if row else None

    def listar(self, filtros: AutomacaoFiltros) -> ResultadoPaginado[SolicitacaoNotificacao]:
        condicoes: list[Any] = [SolicitacaoNotificacaoORM.tenant_id == filtros.tenant_id]
        if filtros.carteira_id is not None:
            condicoes.append(SolicitacaoNotificacaoORM.carteira_id == filtros.carteira_id)
        total = (
            self._session.scalar(
                select(func.count()).select_from(SolicitacaoNotificacaoORM).where(*condicoes)
            )
            or 0
        )
        rows = self._session.scalars(
            select(SolicitacaoNotificacaoORM)
            .where(*condicoes)
            .order_by(
                SolicitacaoNotificacaoORM.resultado_em.desc().nullsfirst(),
                SolicitacaoNotificacaoORM.id,
            )
            .offset((filtros.page - 1) * filtros.size)
            .limit(filtros.size)
        ).all()
        return ResultadoPaginado(
            list(map(_solicitacao_domain, rows)), total, filtros.page, filtros.size
        )


def _job_values(job: JobAgendado) -> dict[str, Any]:
    return {
        "tenant_id": job.tenant_id,
        "carteira_id": job.carteira_id,
        "tipo": job.tipo,
        "executar_em": job.executar_em,
        "correlation_id": job.correlation_id,
        "payload": job.payload,
        "origem_tipo": job.origem_tipo,
        "origem_id": job.origem_id,
        "estado": job.estado.value,
        "max_tentativas": job.max_tentativas,
        "tentativas": job.tentativas,
        "proxima_execucao_em": job.proxima_execucao_em,
        "lease_token": job.lease_token,
        "lease_ate": job.lease_ate,
        "cancelamento_solicitado": job.cancelamento_solicitado,
        "criado_em": job.criado_em,
        "atualizado_em": job.atualizado_em,
    }


def _job_orm(job: JobAgendado) -> JobAgendadoORM:
    return JobAgendadoORM(id=job.id, **_job_values(job))


def _copiar_job(row: JobAgendadoORM, job: JobAgendado) -> None:
    for nome, valor in _job_values(job).items():
        setattr(row, nome, valor)


def _job_domain(row: JobAgendadoORM) -> JobAgendado:
    return JobAgendado(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        tipo=row.tipo,
        executar_em=row.executar_em,
        correlation_id=row.correlation_id,
        payload=dict(row.payload),
        origem_tipo=row.origem_tipo,
        origem_id=row.origem_id,
        estado=EstadoJob(row.estado),
        max_tentativas=row.max_tentativas,
        tentativas=row.tentativas,
        proxima_execucao_em=row.proxima_execucao_em,
        lease_token=row.lease_token,
        lease_ate=row.lease_ate,
        cancelamento_solicitado=row.cancelamento_solicitado,
        criado_em=row.criado_em,
        atualizado_em=row.atualizado_em,
    )


def _tentativa_orm(item: TentativaJob) -> TentativaJobORM:
    return TentativaJobORM(
        id=item.id,
        job_id=item.job_id,
        tenant_id=item.tenant_id,
        carteira_id=item.carteira_id,
        lease_token=item.lease_token,
        execution_id=item.execution_id,
        numero=item.numero,
        estado=item.estado.value,
        iniciada_em=item.iniciada_em,
        finalizada_em=item.finalizada_em,
        erro_codigo=item.erro_codigo,
    )


def _tentativa_domain(row: TentativaJobORM) -> TentativaJob:
    return TentativaJob(
        id=row.id,
        job_id=row.job_id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        lease_token=row.lease_token,
        execution_id=row.execution_id,
        numero=row.numero,
        estado=EstadoTentativaJob(row.estado),
        iniciada_em=row.iniciada_em,
        finalizada_em=row.finalizada_em,
        erro_codigo=row.erro_codigo,
    )


def _preferencia_domain(row: PreferenciaNotificacaoORM) -> PreferenciaNotificacao:
    return PreferenciaNotificacao(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        contato_id=row.contato_id,
        estado=EstadoPreferenciaNotificacao(row.estado),
        evidencia=row.evidencia,
        origem=row.origem,
        ator_id=row.ator_id,
        registrada_em=row.registrada_em,
        revogada_em=row.revogada_em,
    )


def _template_orm(item: TemplateNotificacao) -> TemplateNotificacaoORM:
    return TemplateNotificacaoORM(
        id=item.id,
        tenant_id=item.tenant_id,
        codigo=item.codigo,
        versao=item.versao,
        assunto=item.assunto,
        corpo=item.corpo,
        parametros_permitidos=list(item.parametros_permitidos),
        hash_conteudo=item.hash_conteudo,
        criado_por_usuario_id=item.criado_por_usuario_id,
        estado=item.estado.value,
        aprovado_por_usuario_id=item.aprovado_por_usuario_id,
        aprovado_em=item.aprovado_em,
        ativado_em=item.ativado_em,
        motivo_aprovacao=item.motivo_aprovacao,
    )


def _template_domain(row: TemplateNotificacaoORM) -> TemplateNotificacao:
    return TemplateNotificacao(
        id=row.id,
        tenant_id=row.tenant_id,
        codigo=row.codigo,
        versao=row.versao,
        assunto=row.assunto,
        corpo=row.corpo,
        parametros_permitidos=tuple(row.parametros_permitidos),
        criado_por_usuario_id=row.criado_por_usuario_id,
        estado=EstadoTemplateNotificacao(row.estado),
        aprovado_por_usuario_id=row.aprovado_por_usuario_id,
        aprovado_em=row.aprovado_em,
        ativado_em=row.ativado_em,
        motivo_aprovacao=row.motivo_aprovacao,
    )


def _solicitacao_orm(item: SolicitacaoNotificacao) -> SolicitacaoNotificacaoORM:
    return SolicitacaoNotificacaoORM(
        id=item.id,
        tenant_id=item.tenant_id,
        carteira_id=item.carteira_id,
        lembrete_id=item.lembrete_id,
        job_id=item.job_id,
        tentativa_job_id=item.tentativa_job_id,
        contato_id=item.contato_id,
        template_id=item.template_id,
        chave_idempotente=item.chave_idempotente,
        payload_canonico=item.payload_canonico,
        payload_hash=item.payload_hash,
        versao_solicitacao=item.versao_solicitacao,
        preparada_em=item.preparada_em,
        estado=item.estado.value,
        provider_message_id=item.provider_message_id,
        resultado_em=item.resultado_em,
        codigo_resultado=item.codigo_resultado,
        conciliacao_chave=item.conciliacao_chave,
    )


def _solicitacao_domain(row: SolicitacaoNotificacaoORM) -> SolicitacaoNotificacao:
    return SolicitacaoNotificacao(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        lembrete_id=row.lembrete_id,
        job_id=row.job_id,
        tentativa_job_id=row.tentativa_job_id,
        contato_id=row.contato_id,
        template_id=row.template_id,
        chave_idempotente=row.chave_idempotente,
        payload_canonico=dict(row.payload_canonico),
        payload_hash=row.payload_hash,
        versao_solicitacao=row.versao_solicitacao,
        preparada_em=row.preparada_em,
        estado=EstadoSolicitacaoNotificacao(row.estado),
        provider_message_id=row.provider_message_id,
        resultado_em=row.resultado_em,
        codigo_resultado=row.codigo_resultado,
        conciliacao_chave=row.conciliacao_chave,
    )
