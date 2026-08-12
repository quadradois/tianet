"""Servicos de aplicacao de Notification."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from emprestimo.application.errors import (
    NotificacaoNaoEncontradaError,
    TemplateNotificacaoNaoEncontradoError,
    TransicaoEstadoInvalidaError,
)
from emprestimo.application.ports import UnitOfWork
from emprestimo.application.scheduler import ClaimScheduler, ResultadoExecucao
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.automacao_ports import (
    AutomacaoFiltros,
    NotificationChannel,
    ResultadoPaginado,
)
from emprestimo.domain.credit.contato import TipoContato
from emprestimo.domain.credit.notifications import (
    EstadoSolicitacaoNotificacao,
    ResultadoCanal,
    ResultadoEnvio,
    SolicitacaoNotificacao,
    TemplateNotificacao,
)
from emprestimo.domain.credit.operacao_diaria import CanalComunicacao, RegistroComunicacao
from emprestimo.domain.credit.scheduler import EstadoTentativaJob


class FakeNotificationChannel(NotificationChannel):
    """Fake deterministico sem rede ou credenciais."""

    def __init__(self, resultado: ResultadoCanal = ResultadoCanal.ACEITA) -> None:
        self.resultado = resultado
        self.envios: dict[str, ResultadoEnvio] = {}

    def enviar(
        self,
        *,
        destinatario: str,
        assunto: str,
        corpo: str,
        chave_idempotente: str,
    ) -> ResultadoEnvio:
        del destinatario, assunto, corpo
        existente = self.envios.get(chave_idempotente)
        if existente:
            return existente
        provider_id = f"fake-{uuid.uuid5(uuid.NAMESPACE_URL, chave_idempotente)}"
        resultado = ResultadoEnvio(
            self.resultado,
            provider_message_id=provider_id if self.resultado is ResultadoCanal.ACEITA else None,
            codigo="fake",
            chave_idempotente=chave_idempotente,
        )
        self.envios[chave_idempotente] = resultado
        return resultado

    def consultar_status(self, provider_message_id: str) -> ResultadoEnvio:
        for resultado in self.envios.values():
            if resultado.provider_message_id == provider_message_id:
                return resultado
        return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="fake-not-found")


class NotificationService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        channel: NotificationChannel,
    ) -> None:
        self._uow_factory = uow_factory
        self._channel = channel

    def preparar(self, solicitacao: SolicitacaoNotificacao) -> SolicitacaoNotificacao:
        with self._uow_factory() as uow:
            existente = uow.solicitacao_notificacao.find_by_chave(solicitacao.chave_idempotente)
            if existente:
                if existente.payload_hash != solicitacao.payload_hash:
                    raise TransicaoEstadoInvalidaError(
                        solicitacao.id,
                        "preparar_notificacao",
                        "payload divergente para a mesma chave",
                    )
                return existente
            uow.solicitacao_notificacao.save(solicitacao)
            uow.commit()
            return solicitacao

    def processar_lembrete(self, claim: ClaimScheduler) -> ResultadoExecucao:
        """Executa envio sem manter transacao aberta durante a chamada externa."""

        with self._uow_factory() as uow:
            lembrete = uow.lembrete.find_by_id(claim.job.origem_id)
            if lembrete is None or lembrete.tenant_id != claim.job.tenant_id:
                return ResultadoExecucao.FALHA_PERMANENTE
            assert lembrete.agenda_item_id is not None
            agenda = uow.agenda_item.find_by_id(lembrete.agenda_item_id)
            if agenda is None:
                return ResultadoExecucao.FALHA_PERMANENTE
            contatos = uow.contato.find_by_devedor(agenda.devedor_id)
            contato = None
            for item in contatos:
                if item.tipo is not TipoContato.EMAIL:
                    continue
                preferencia = uow.preferencia_notificacao.find_by_contato(
                    item.id, claim.job.tenant_id
                )
                if preferencia is not None and preferencia.permite_envio:
                    contato = item
                    break
            template = uow.template_notificacao.find_ativo(
                claim.job.tenant_id, "lembrete_operacional_v1"
            )
            if contato is None or template is None:
                return ResultadoExecucao.FALHA_PERMANENTE
            payload = {
                "data_hora": lembrete.horario.isoformat(),
                "canal_atendimento": "email",
            }
            solicitacao = SolicitacaoNotificacao.preparar(
                tenant_id=claim.job.tenant_id,
                carteira_id=claim.job.carteira_id,
                lembrete_id=lembrete.id,
                job_id=claim.job.id,
                tentativa_job_id=claim.tentativa.id,
                contato_id=contato.id,
                template_id=template.id,
                chave_idempotente=_chave_idempotente(
                    tenant_id=claim.job.tenant_id,
                    origem_tipo=claim.job.origem_tipo,
                    origem_id=claim.job.origem_id,
                    template=template,
                ),
                payload=payload,
            )
            existente = uow.solicitacao_notificacao.find_by_chave(solicitacao.chave_idempotente)
            if existente is not None:
                if existente.payload_hash != solicitacao.payload_hash:
                    return ResultadoExecucao.FALHA_PERMANENTE
                if existente.estado is EstadoSolicitacaoNotificacao.RESULTADO_DESCONHECIDO:
                    return ResultadoExecucao.RESULTADO_DESCONHECIDO
                if existente.estado is EstadoSolicitacaoNotificacao.PREPARADA and datetime.now(
                    UTC
                ) - existente.preparada_em >= timedelta(hours=24):
                    existente.registrar_resultado(
                        ResultadoEnvio(
                            ResultadoCanal.DESCONHECIDO,
                            codigo="idempotency_window_expired",
                        )
                    )
                    uow.solicitacao_notificacao.save(existente)
                    uow.commit()
                    return ResultadoExecucao.RESULTADO_DESCONHECIDO
                if existente.estado is EstadoSolicitacaoNotificacao.FALHA_TEMPORARIA:
                    try:
                        existente.preparar_retry(
                            tentativa_job_id=claim.tentativa.id,
                            agora=datetime.now(UTC),
                        )
                    except ViolacaoInvarianteError:
                        return ResultadoExecucao.RESULTADO_DESCONHECIDO
                    uow.solicitacao_notificacao.save(existente)
                    uow.commit()
                solicitacao = existente
            else:
                uow.solicitacao_notificacao.save(solicitacao)
                uow.commit()

        assunto = template.assunto.format(**payload)
        corpo = template.corpo.format(**payload)
        if claim.cancelamento.is_set():
            return ResultadoExecucao.FALHA_TEMPORARIA
        resultado = self._channel.enviar(
            destinatario=contato.valor,
            assunto=assunto,
            corpo=corpo,
            chave_idempotente=solicitacao.chave_idempotente,
        )
        if resultado.resultado is not ResultadoCanal.ACEITA:
            solicitacao.registrar_resultado(resultado)
            with self._uow_factory() as uow:
                uow.solicitacao_notificacao.save(solicitacao)
                uow.commit()
            return {
                ResultadoCanal.FALHA_TEMPORARIA: ResultadoExecucao.FALHA_TEMPORARIA,
                ResultadoCanal.FALHA_PERMANENTE: ResultadoExecucao.FALHA_PERMANENTE,
                ResultadoCanal.DESCONHECIDO: ResultadoExecucao.RESULTADO_DESCONHECIDO,
            }[resultado.resultado]

        with self._uow_factory() as uow:
            persistida = uow.solicitacao_notificacao.find_by_chave(solicitacao.chave_idempotente)
            job = uow.job_agendado.find_scoped(claim.job.id, claim.job.tenant_id)
            lembrete = uow.lembrete.find_by_id(claim.job.origem_id)
            agenda = None
            if lembrete is not None and lembrete.agenda_item_id is not None:
                agenda = uow.agenda_item.find_by_id(lembrete.agenda_item_id)
            if persistida is None or job is None or lembrete is None or agenda is None:
                return ResultadoExecucao.RESULTADO_DESCONHECIDO
            persistida.registrar_resultado(resultado)
            lembrete.enviar()
            job.concluir(claim.tentativa.lease_token, agora=datetime.now(UTC))
            claim.tentativa.finalizar(
                EstadoTentativaJob.SUCESSO,
                agora=datetime.now(UTC),
            )
            comunicacao = RegistroComunicacao(
                tenant_id=job.tenant_id,
                carteira_id=job.carteira_id,
                responsavel_id=None,
                ator_tipo="service",
                ator_identificador="scheduler-worker",
                canal=CanalComunicacao.EMAIL,
                ocorrido_em=datetime.now(UTC),
                resumo="Notificacao transacional aceita pelo provedor",
                resultado="aceita",
                devedor_id=agenda.devedor_id,
                emprestimo_id=agenda.emprestimo_id,
                agenda_item_id=agenda.id,
                notification_id=persistida.id,
                template_id=template.id,
                template_versao=template.versao,
                provider_message_id=resultado.provider_message_id,
            )
            uow.solicitacao_notificacao.save(persistida)
            uow.lembrete.save(lembrete)
            uow.registro_comunicacao.save(comunicacao)
            uow.tentativa_job.save(claim.tentativa)
            if not uow.job_agendado.finalizar_com_fencing(job, claim.tentativa.lease_token):
                return ResultadoExecucao.RESULTADO_DESCONHECIDO
            uow.commit()
        return ResultadoExecucao.FINALIZADO

    def enviar_preparada(
        self,
        solicitacao: SolicitacaoNotificacao,
        *,
        destinatario: str,
        assunto: str,
        corpo: str,
    ) -> SolicitacaoNotificacao:
        resultado = self._channel.enviar(
            destinatario=destinatario,
            assunto=assunto,
            corpo=corpo,
            chave_idempotente=solicitacao.chave_idempotente,
        )
        solicitacao.registrar_resultado(resultado)
        with self._uow_factory() as uow:
            uow.solicitacao_notificacao.save(solicitacao)
            uow.commit()
        return solicitacao

    def conciliar(
        self,
        *,
        tenant_id: uuid.UUID,
        solicitacao_id: uuid.UUID,
        provider_message_id: str,
        usuario_id: uuid.UUID,
        motivo: str,
        idempotency_key: str,
        lembrete_id_esperado: uuid.UUID | None = None,
    ) -> SolicitacaoNotificacao:
        if not motivo.strip():
            raise TransicaoEstadoInvalidaError(
                solicitacao_id, "conciliar_notificacao", "motivo obrigatorio"
            )
        with self._uow_factory() as uow:
            solicitacao = uow.solicitacao_notificacao.find_scoped(solicitacao_id, tenant_id)
            if solicitacao is None:
                raise NotificacaoNaoEncontradaError(solicitacao_id)
            if lembrete_id_esperado is not None and solicitacao.lembrete_id != lembrete_id_esperado:
                raise NotificacaoNaoEncontradaError(solicitacao_id)
        evidencia = self._channel.consultar_status(provider_message_id)
        with self._uow_factory() as uow:
            persistida = uow.solicitacao_notificacao.find_scoped_for_update(
                solicitacao_id, tenant_id
            )
            if persistida is None:
                raise NotificacaoNaoEncontradaError(solicitacao_id)
            try:
                alterada = persistida.conciliar(
                    evidencia,
                    idempotency_key=idempotency_key,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    solicitacao_id, "conciliar_notificacao", str(exc)
                ) from exc
            if not alterada:
                return persistida
            if evidencia.resultado is ResultadoCanal.ACEITA:
                lembrete = uow.lembrete.find_by_id(persistida.lembrete_id)
                job = uow.job_agendado.find_scoped(persistida.job_id, tenant_id)
                template = uow.template_notificacao.find_scoped(persistida.template_id, tenant_id)
                if lembrete is None or job is None or lembrete.agenda_item_id is None:
                    raise NotificacaoNaoEncontradaError(solicitacao_id)
                if template is None or evidencia.provider_message_id is None:
                    raise NotificacaoNaoEncontradaError(solicitacao_id)
                agenda = uow.agenda_item.find_by_id(lembrete.agenda_item_id)
                if agenda is None or job.carteira_id != persistida.carteira_id:
                    raise NotificacaoNaoEncontradaError(solicitacao_id)
                instante = evidencia.ocorrido_em
                lembrete.enviar()
                job.reconciliar_conclusao(agora=instante)
                uow.lembrete.save(lembrete)
                uow.job_agendado.save(job)
                uow.registro_comunicacao.save(
                    RegistroComunicacao(
                        tenant_id=tenant_id,
                        carteira_id=persistida.carteira_id,
                        responsavel_id=usuario_id,
                        canal=CanalComunicacao.EMAIL,
                        ocorrido_em=instante,
                        resumo="Notificacao conciliada com evidencia do provedor",
                        resultado=f"aceita; motivo={motivo.strip()}",
                        devedor_id=agenda.devedor_id,
                        emprestimo_id=agenda.emprestimo_id,
                        agenda_item_id=agenda.id,
                        notification_id=persistida.id,
                        template_id=persistida.template_id,
                        template_versao=template.versao,
                        provider_message_id=evidencia.provider_message_id,
                    )
                )
            uow.solicitacao_notificacao.save(persistida)
            uow.commit()
        return persistida

    def listar(self, filtros: AutomacaoFiltros) -> ResultadoPaginado[SolicitacaoNotificacao]:
        with self._uow_factory() as uow:
            return uow.solicitacao_notificacao.listar(filtros)

    def obter(self, *, tenant_id: uuid.UUID, solicitacao_id: uuid.UUID) -> SolicitacaoNotificacao:
        with self._uow_factory() as uow:
            solicitacao = uow.solicitacao_notificacao.find_scoped(solicitacao_id, tenant_id)
        if solicitacao is None:
            raise NotificacaoNaoEncontradaError(solicitacao_id)
        return solicitacao


class TemplateNotificacaoService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def criar(self, template: TemplateNotificacao) -> TemplateNotificacao:
        with self._uow_factory() as uow:
            existente = uow.template_notificacao.find_by_codigo_versao(
                template.tenant_id,
                template.codigo,
                template.versao,
            )
            if existente is not None:
                raise TransicaoEstadoInvalidaError(
                    template.id,
                    "criar_template",
                    "codigo e versao ja existem no tenant",
                )
            uow.template_notificacao.save(template)
            uow.commit()
        return template

    def aprovar(
        self,
        *,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str,
    ) -> TemplateNotificacao:
        with self._uow_factory() as uow:
            template = uow.template_notificacao.find_scoped(template_id, tenant_id)
            if template is None:
                raise TemplateNotificacaoNaoEncontradoError(template_id)
            try:
                template.aprovar(
                    usuario_id=usuario_id,
                    motivo=motivo,
                    agora=datetime.now(UTC),
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    template_id, "aprovar_template", str(exc)
                ) from exc
            uow.template_notificacao.save(template)
            uow.commit()
            return template

    def ativar(self, *, tenant_id: uuid.UUID, template_id: uuid.UUID) -> TemplateNotificacao:
        with self._uow_factory() as uow:
            template = uow.template_notificacao.find_scoped(template_id, tenant_id)
            if template is None:
                raise TemplateNotificacaoNaoEncontradoError(template_id)
            try:
                template.ativar(agora=datetime.now(UTC))
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    template_id, "ativar_template", str(exc)
                ) from exc
            uow.template_notificacao.save(template)
            uow.commit()
            return template

    def listar(self, filtros: AutomacaoFiltros) -> ResultadoPaginado[TemplateNotificacao]:
        with self._uow_factory() as uow:
            return uow.template_notificacao.listar(filtros)


def _chave_idempotente(
    *,
    tenant_id: uuid.UUID,
    origem_tipo: str,
    origem_id: uuid.UUID,
    template: TemplateNotificacao,
    versao_solicitacao: int = 1,
) -> str:
    bruto = json.dumps(
        {
            "tenant_id": str(tenant_id),
            "origem_tipo": origem_tipo,
            "origem_id": str(origem_id),
            "finalidade": template.codigo,
            "template_versao": template.versao,
            "solicitacao_versao": versao_solicitacao,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"notification/{hashlib.sha256(bruto.encode()).hexdigest()}"
