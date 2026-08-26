"""Servicos de aplicacao de Notification."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from emprestimo.application.auditoria_escrita import auditar_escrita
from emprestimo.application.errors import (
    NotificacaoNaoEncontradaError,
    TemplateNotificacaoNaoEncontradoError,
    TransicaoEstadoInvalidaError,
)
from emprestimo.application.idempotencia import (
    concluir_idempotencia,
    dataclass_do_resultado,
    iniciar_idempotencia,
    resultado_de_dataclass,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
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
from emprestimo.domain.credit.scheduler import EstadoTentativaJob, JobAgendado

TIPO_JOB_AVISO_SOBRA = "avisar_sobra_pagamento_whatsapp"
ORIGEM_AVISO_SOBRA = "sobra_pagamento"
CHAVE_WHATSAPP_CREDOR = "credor_whatsapp"


@dataclass(frozen=True)
class AvisoSobraPagamento:
    """Snapshot do excedente reconhecido pelo Motor para avisar o Credor."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    emprestimo_id: uuid.UUID
    pagamento_id: uuid.UUID
    valor_recebido: Decimal
    valor_distribuido: Decimal
    valor_devolvido: Decimal


def montar_texto_aviso_sobra(dados: AvisoSobraPagamento) -> str:
    return "\n".join(
        (
            "Pagamento recebido com valor excedente",
            f"Pagamento: {dados.pagamento_id}",
            f"Emprestimo: {dados.emprestimo_id}",
            f"Valor recebido: R$ {_formatar_valor(dados.valor_recebido)}",
            f"Valor distribuido: R$ {_formatar_valor(dados.valor_distribuido)}",
            f"Sobra a devolver: R$ {_formatar_valor(dados.valor_devolvido)}",
            "Faca o PIX de devolucao por fora e registre o estorno no sistema.",
        )
    )


class AvisoSobraPagamentoService:
    """Enfileira o aviso ou audita explicitamente a falta de destinatario."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
        *,
        agora: Callable[[], datetime] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria
        self._agora = agora or (lambda: datetime.now(UTC))

    def enfileirar(self, aviso: AvisoSobraPagamento) -> JobAgendado | None:
        detalhes = {
            "tenant_id": str(aviso.tenant_id),
            "pagamento_id": str(aviso.pagamento_id),
        }
        self._auditoria.registrar(
            "sobra_pagamento_aviso",
            aviso.pagamento_id,
            "enfileirar.inicio",
            "iniciado",
            detalhes=json.dumps(detalhes, sort_keys=True),
        )
        try:
            return self._enfileirar(aviso)
        except Exception as exc:
            self._auditoria.registrar(
                "sobra_pagamento_aviso",
                aviso.pagamento_id,
                "enfileirar.falha",
                "falhou",
                detalhes=json.dumps({**detalhes, "erro_tipo": type(exc).__name__}, sort_keys=True),
            )
            self._auditoria.registrar(
                "sobra_pagamento_aviso",
                aviso.pagamento_id,
                "enfileirar.rollback",
                "rollback_aplicado",
                detalhes=json.dumps(detalhes, sort_keys=True),
            )
            raise

    def _enfileirar(self, aviso: AvisoSobraPagamento) -> JobAgendado | None:
        with self._uow_factory() as uow:
            existente = uow.job_agendado.find_by_origem(
                tenant_id=aviso.tenant_id,
                origem_tipo=ORIGEM_AVISO_SOBRA,
                origem_id=aviso.pagamento_id,
            )
            if existente is not None:
                return existente
            numero = next(
                (
                    item.valor.strip()
                    for item in uow.configuracao.find_by_tenant_id(aviso.tenant_id)
                    if item.chave == CHAVE_WHATSAPP_CREDOR and item.valor.strip()
                ),
                None,
            )
            if numero is None:
                self._auditoria.registrar(
                    "sobra_pagamento_aviso",
                    aviso.pagamento_id,
                    "enfileirar.ignorado",
                    "nao_configurado",
                    detalhes=json.dumps(
                        {
                            "tenant_id": str(aviso.tenant_id),
                            "motivo": "credor_whatsapp_nao_configurado",
                            "chave_configuracao": CHAVE_WHATSAPP_CREDOR,
                        },
                        sort_keys=True,
                    ),
                )
                return None
            instante = self._agora()
            job = JobAgendado(
                tenant_id=aviso.tenant_id,
                carteira_id=aviso.carteira_id,
                tipo=TIPO_JOB_AVISO_SOBRA,
                executar_em=instante,
                correlation_id=f"pagamento-sobra:{aviso.pagamento_id}",
                payload={
                    "canal": CanalComunicacao.WHATSAPP.value,
                    "destinatario": numero,
                    "texto": montar_texto_aviso_sobra(aviso),
                    "devedor_id": str(aviso.devedor_id),
                    "emprestimo_id": str(aviso.emprestimo_id),
                },
                origem_tipo=ORIGEM_AVISO_SOBRA,
                origem_id=aviso.pagamento_id,
            )
            uow.job_agendado.save(job)
            uow.commit()
        self._auditoria.registrar(
            "sobra_pagamento_aviso",
            aviso.pagamento_id,
            "enfileirar.sucesso",
            "ok",
            detalhes=json.dumps(
                {"tenant_id": str(aviso.tenant_id), "job_id": str(job.id)},
                sort_keys=True,
            ),
        )
        return job


class EntregaAvisoSobraPagamentoService:
    """Entrega o aviso ao Credor pelo mesmo scheduler duravel do comprovante."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        channel: NotificationChannel,
        auditoria: AuditoriaRegistro,
        *,
        agora: Callable[[], datetime] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._channel = channel
        self._auditoria = auditoria
        self._agora = agora or (lambda: datetime.now(UTC))

    def processar_aviso(self, claim: ClaimScheduler) -> ResultadoExecucao:
        detalhes = {
            "tenant_id": str(claim.job.tenant_id),
            "job_id": str(claim.job.id),
            "pagamento_id": str(claim.job.origem_id),
        }
        self._auditoria.registrar(
            "sobra_pagamento_aviso",
            claim.job.origem_id,
            "entregar.inicio",
            "iniciado",
            detalhes=json.dumps(detalhes, sort_keys=True),
        )
        try:
            resultado = self._processar(claim)
        except Exception as exc:
            self._auditoria.registrar(
                "sobra_pagamento_aviso",
                claim.job.origem_id,
                "entregar.falha",
                "falhou",
                detalhes=json.dumps(
                    {**detalhes, "erro_tipo": type(exc).__name__},
                    sort_keys=True,
                ),
            )
            raise
        self._auditoria.registrar(
            "sobra_pagamento_aviso",
            claim.job.origem_id,
            "entregar.resultado",
            resultado.value,
            detalhes=json.dumps({**detalhes, "resultado": resultado.value}, sort_keys=True),
        )
        return resultado

    def _processar(self, claim: ClaimScheduler) -> ResultadoExecucao:
        payload = _payload_aviso_sobra(claim)
        if payload is None:
            return ResultadoExecucao.FALHA_PERMANENTE
        destinatario, texto = payload
        with self._uow_factory() as uow:
            pagamento = uow.pagamento.find_by_id(claim.job.origem_id)
            if pagamento is None or pagamento.valor_devolvido <= Decimal("0.00"):
                return ResultadoExecucao.FALHA_PERMANENTE
            emprestimo = uow.emprestimo.find_by_id(pagamento.emprestimo_id)
            if (
                emprestimo is None
                or emprestimo.tenant_id != claim.job.tenant_id
                or emprestimo.carteira_id != claim.job.carteira_id
            ):
                return ResultadoExecucao.FALHA_PERMANENTE
        if claim.cancelamento.is_set():
            return ResultadoExecucao.FALHA_TEMPORARIA
        resultado = self._channel.enviar(
            destinatario=destinatario,
            assunto="Pagamento com valor excedente",
            corpo=texto,
            chave_idempotente=_chave_aviso_sobra(claim),
        )
        if resultado.resultado is ResultadoCanal.ACEITA and not resultado.provider_message_id:
            resultado = ResultadoEnvio(
                ResultadoCanal.DESCONHECIDO,
                codigo="accepted_without_provider_message_id",
            )
        if resultado.resultado is not ResultadoCanal.ACEITA:
            return {
                ResultadoCanal.FALHA_TEMPORARIA: ResultadoExecucao.FALHA_TEMPORARIA,
                ResultadoCanal.FALHA_PERMANENTE: ResultadoExecucao.FALHA_PERMANENTE,
                ResultadoCanal.DESCONHECIDO: ResultadoExecucao.RESULTADO_DESCONHECIDO,
            }[resultado.resultado]

        with self._uow_factory() as uow:
            job = uow.job_agendado.find_scoped(claim.job.id, claim.job.tenant_id)
            pagamento = uow.pagamento.find_by_id(claim.job.origem_id)
            if job is None or pagamento is None:
                return ResultadoExecucao.RESULTADO_DESCONHECIDO
            emprestimo = uow.emprestimo.find_by_id(pagamento.emprestimo_id)
            if emprestimo is None:
                return ResultadoExecucao.RESULTADO_DESCONHECIDO
            instante = self._agora()
            job.concluir(claim.tentativa.lease_token, agora=instante)
            claim.tentativa.finalizar(EstadoTentativaJob.SUCESSO, agora=instante)
            uow.registro_comunicacao.save(
                RegistroComunicacao(
                    tenant_id=job.tenant_id,
                    carteira_id=job.carteira_id,
                    responsavel_id=None,
                    ator_tipo="service",
                    ator_identificador="scheduler-worker",
                    canal=CanalComunicacao.WHATSAPP,
                    ocorrido_em=instante,
                    resumo="Aviso de sobra de pagamento aceito pelo provedor",
                    resultado="aceita",
                    devedor_id=emprestimo.devedor_id,
                    emprestimo_id=emprestimo.id,
                    provider_message_id=resultado.provider_message_id,
                )
            )
            uow.tentativa_job.save(claim.tentativa)
            if not uow.job_agendado.finalizar_com_fencing(job, claim.tentativa.lease_token):
                return ResultadoExecucao.RESULTADO_DESCONHECIDO
            uow.commit()
        return ResultadoExecucao.FINALIZADO


def _payload_aviso_sobra(claim: ClaimScheduler) -> tuple[str, str] | None:
    if (
        claim.job.tipo != TIPO_JOB_AVISO_SOBRA
        or claim.job.origem_tipo != ORIGEM_AVISO_SOBRA
        or claim.job.payload.get("canal") != CanalComunicacao.WHATSAPP.value
    ):
        return None
    destinatario = claim.job.payload.get("destinatario")
    texto = claim.job.payload.get("texto")
    if (
        not isinstance(destinatario, str)
        or not destinatario.strip()
        or not isinstance(texto, str)
        or not texto.strip()
    ):
        return None
    return destinatario, texto


def _chave_aviso_sobra(claim: ClaimScheduler) -> str:
    bruto = json.dumps(
        {
            "tenant_id": str(claim.job.tenant_id),
            "origem_tipo": claim.job.origem_tipo,
            "origem_id": str(claim.job.origem_id),
            "finalidade": "aviso_sobra_pagamento_whatsapp",
            "versao_solicitacao": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"notification/{hashlib.sha256(bruto.encode()).hexdigest()}"


def _formatar_valor(valor: Decimal) -> str:
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


class CanalNaoConfiguradoNotificationChannel(NotificationChannel):
    """Recusa nomeada para canal sem credencial. **Nunca finge entrega.**

    O `FakeNotificationChannel` devolve `ACEITA` com um `provider_message_id`
    sintetico — correto em teste, mentira em producao: a trilha registraria como
    entregue algo que nunca saiu, e o Credor acreditaria nela.

    `FALHA_PERMANENTE`, e nao temporaria, porque retry nao resolve falta de
    configuracao: ficaria em loop ate estourar as tentativas, gastando ciclo do
    worker para chegar no mesmo lugar. Terminal e nomeado aparece na trilha com
    o motivo, que e o que o operador precisa ver.
    """

    def __init__(self, canal: str) -> None:
        self._canal = canal

    def enviar(
        self,
        *,
        destinatario: str,
        assunto: str,
        corpo: str,
        chave_idempotente: str,
    ) -> ResultadoEnvio:
        del destinatario, assunto, corpo
        return ResultadoEnvio(
            ResultadoCanal.FALHA_PERMANENTE,
            codigo=f"canal_nao_configurado:{self._canal}",
            chave_idempotente=chave_idempotente,
        )

    def consultar_status(self, provider_message_id: str) -> ResultadoEnvio:
        del provider_message_id
        return ResultadoEnvio(
            ResultadoCanal.DESCONHECIDO,
            codigo=f"canal_nao_configurado:{self._canal}",
        )


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
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._channel = channel
        self._auditoria = auditoria

    @auditar_escrita("solicitacao_notificacao", "preparar")
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

    @auditar_escrita("solicitacao_notificacao", "processar_lembrete")
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

    @auditar_escrita("solicitacao_notificacao", "enviar_preparada", identificador="solicitacao_id")
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

    @auditar_escrita("solicitacao_notificacao", "conciliar", identificador="solicitacao_id")
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
                if persistida.lembrete_id is None or persistida.template_id is None:
                    raise NotificacaoNaoEncontradaError(solicitacao_id)
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
    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("template_notificacao", "criar")
    def criar(
        self, template: TemplateNotificacao, *, idempotency_key: str | None = None
    ) -> TemplateNotificacao:
        with self._uow_factory() as uow:
            escopo = "notificacao-template-criar"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "tenant_id": template.tenant_id,
                    "codigo": template.codigo,
                    "versao": template.versao,
                    "assunto": template.assunto,
                    "corpo": template.corpo,
                    "parametros_permitidos": template.parametros_permitidos,
                    "criado_por_usuario_id": template.criado_por_usuario_id,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    TemplateNotificacao,
                    chave=idempotency_key,
                )
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
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(template),
            )
            uow.commit()
        return template

    @auditar_escrita("template_notificacao", "aprovar", identificador="template_id")
    def aprovar(
        self,
        *,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str,
        idempotency_key: str | None = None,
    ) -> TemplateNotificacao:
        with self._uow_factory() as uow:
            template = uow.template_notificacao.find_scoped(template_id, tenant_id)
            if template is None:
                raise TemplateNotificacaoNaoEncontradoError(template_id)
            escopo = "notificacao-template-aprovar"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "tenant_id": tenant_id,
                    "template_id": template_id,
                    "usuario_id": usuario_id,
                    "motivo": motivo,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    TemplateNotificacao,
                    chave=idempotency_key,
                )
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
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(template),
            )
            uow.commit()
            return template

    @auditar_escrita("template_notificacao", "ativar", identificador="template_id")
    def ativar(
        self,
        *,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> TemplateNotificacao:
        with self._uow_factory() as uow:
            template = uow.template_notificacao.find_scoped(template_id, tenant_id)
            if template is None:
                raise TemplateNotificacaoNaoEncontradoError(template_id)
            escopo = "notificacao-template-ativar"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={"tenant_id": tenant_id, "template_id": template_id},
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    TemplateNotificacao,
                    chave=idempotency_key,
                )
            try:
                template.ativar(agora=datetime.now(UTC))
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    template_id, "ativar_template", str(exc)
                ) from exc
            uow.template_notificacao.save(template)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(template),
            )
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
