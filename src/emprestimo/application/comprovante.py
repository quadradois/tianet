"""Comprovante do lancamento, gerado no backend e enviado de forma assincrona.

O texto recebe um snapshot financeiro pronto do Motor. Este modulo apenas
apresenta esses valores e cria o job duravel; nao consulta nem recalcula dados
financeiros.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from emprestimo.application.auditoria_escrita import auditar_escrita
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.application.scheduler import ClaimScheduler, ResultadoExecucao
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.domain.credit.contato import TipoContato
from emprestimo.domain.credit.notifications import (
    EstadoSolicitacaoNotificacao,
    ResultadoCanal,
    ResultadoEnvio,
    SolicitacaoNotificacao,
)
from emprestimo.domain.credit.operacao_diaria import CanalComunicacao, RegistroComunicacao
from emprestimo.domain.credit.scheduler import EstadoTentativaJob, JobAgendado

TIPO_JOB_COMPROVANTE = "enviar_comprovante_whatsapp"
ORIGEM_COMPROVANTE = "comprovante_lancamento"


@dataclass(frozen=True)
class ComprovanteLancamento:
    """Snapshot imutavel necessario para montar e entregar o comprovante."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    nome_devedor: str
    destinatario_whatsapp: str
    emprestimo_id: uuid.UUID
    valor_contratado: Decimal
    moeda: str
    taxa_juros_mensal_percentual: Decimal
    dia_de_acerto: int
    primeiro_acerto_em: date


def montar_texto_comprovante(dados: ComprovanteLancamento) -> str:
    """Apresenta, sem derivar valores, o snapshot devolvido pelo Motor."""

    valor = _formatar_decimal(dados.valor_contratado, casas=2)
    taxa = _formatar_decimal(dados.taxa_juros_mensal_percentual, casas=2)
    return "\n".join(
        (
            "Comprovante do lancamento",
            f"Devedor: {dados.nome_devedor}",
            f"Emprestimo: {dados.emprestimo_id}",
            f"Valor contratado: {dados.moeda} {valor}",
            f"Taxa de juros mensal: {taxa}%",
            f"Dia de acerto: {dados.dia_de_acerto}",
            f"Primeiro acerto: {dados.primeiro_acerto_em:%d/%m/%Y}",
        )
    )


class ComprovanteService:
    """Enfileira uma unica entrega por lancamento em UnitOfWork proprio."""

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

    @auditar_escrita("comprovante", "enfileirar")
    def enfileirar(self, comprovante: ComprovanteLancamento) -> JobAgendado:
        with self._uow_factory() as uow:
            existente = uow.job_agendado.find_by_origem(
                tenant_id=comprovante.tenant_id,
                origem_tipo=ORIGEM_COMPROVANTE,
                origem_id=comprovante.emprestimo_id,
            )
            if existente is not None:
                return existente

            instante = self._agora()
            job = JobAgendado(
                tenant_id=comprovante.tenant_id,
                carteira_id=comprovante.carteira_id,
                tipo=TIPO_JOB_COMPROVANTE,
                executar_em=instante,
                correlation_id=f"lancamento:{comprovante.emprestimo_id}",
                payload={
                    "canal": CanalComunicacao.WHATSAPP.value,
                    "destinatario": comprovante.destinatario_whatsapp,
                    "texto": montar_texto_comprovante(comprovante),
                },
                origem_tipo=ORIGEM_COMPROVANTE,
                origem_id=comprovante.emprestimo_id,
            )
            uow.job_agendado.save(job)
            uow.commit()
            return job


class EntregaComprovanteService:
    """Entrega o snapshot do lancamento pelo canal duravel de WhatsApp."""

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

    def processar_comprovante(self, claim: ClaimScheduler) -> ResultadoExecucao:
        """Executa envio sem manter transacao aberta durante a chamada externa."""

        detalhes = {
            "tenant_id": str(claim.job.tenant_id),
            "carteira_id": str(claim.job.carteira_id),
            "job_id": str(claim.job.id),
            "emprestimo_id": str(claim.job.origem_id),
        }
        self._auditoria.registrar(
            "comprovante_entrega",
            claim.tentativa.execution_id,
            "entregar.inicio",
            "iniciado",
            detalhes=json.dumps(detalhes, sort_keys=True),
        )
        try:
            resultado = self._processar(claim)
        except Exception as exc:
            self._auditoria.registrar(
                "comprovante_entrega",
                claim.tentativa.execution_id,
                "entregar.falha",
                "falhou",
                detalhes=json.dumps(
                    {**detalhes, "erro_tipo": type(exc).__name__},
                    sort_keys=True,
                ),
            )
            raise
        self._auditoria.registrar(
            "comprovante_entrega",
            claim.tentativa.execution_id,
            "entregar.resultado",
            # IMP-350: aqui havia um mapeamento para "desconhecido" porque
            # `audit_log.status` era VARCHAR(20) e nao cabia os 22 caracteres de
            # `resultado_desconhecido`. A coluna foi alargada; o remendo saiu, e
            # a trilha passa a gravar o mesmo vocabulario que o dominio usa.
            resultado.value,
            detalhes=json.dumps(
                {**detalhes, "resultado": resultado.value},
                sort_keys=True,
            ),
        )
        return resultado

    def _processar(self, claim: ClaimScheduler) -> ResultadoExecucao:
        payload = _payload_comprovante(claim)
        if payload is None:
            return ResultadoExecucao.FALHA_PERMANENTE
        destinatario, texto = payload
        instante = self._agora()
        with self._uow_factory() as uow:
            emprestimo = uow.emprestimo.find_by_id(claim.job.origem_id)
            if (
                emprestimo is None
                or emprestimo.tenant_id != claim.job.tenant_id
                or emprestimo.carteira_id != claim.job.carteira_id
            ):
                return ResultadoExecucao.FALHA_PERMANENTE
            contato = next(
                (
                    item
                    for item in uow.contato.find_by_devedor(emprestimo.devedor_id)
                    if item.tipo is TipoContato.WHATSAPP and item.valor == destinatario
                ),
                None,
            )
            if contato is None:
                return ResultadoExecucao.FALHA_PERMANENTE
            solicitacao = SolicitacaoNotificacao.preparar_comprovante(
                tenant_id=claim.job.tenant_id,
                carteira_id=claim.job.carteira_id,
                job_id=claim.job.id,
                tentativa_job_id=claim.tentativa.id,
                contato_id=contato.id,
                chave_idempotente=_chave_idempotente_comprovante(claim),
                payload=claim.job.payload,
            )
            existente = uow.solicitacao_notificacao.find_by_chave(solicitacao.chave_idempotente)
            if existente is not None:
                if existente.payload_hash != solicitacao.payload_hash:
                    return ResultadoExecucao.FALHA_PERMANENTE
                if existente.estado is EstadoSolicitacaoNotificacao.RESULTADO_DESCONHECIDO:
                    return ResultadoExecucao.RESULTADO_DESCONHECIDO
                if existente.estado is EstadoSolicitacaoNotificacao.FALHA_PERMANENTE:
                    return ResultadoExecucao.FALHA_PERMANENTE
                if existente.estado in (
                    EstadoSolicitacaoNotificacao.ACEITA,
                    EstadoSolicitacaoNotificacao.CONCILIADA,
                ):
                    return ResultadoExecucao.RESULTADO_DESCONHECIDO
                if (
                    existente.estado is EstadoSolicitacaoNotificacao.PREPARADA
                    and instante - existente.preparada_em >= timedelta(hours=24)
                ):
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
                            agora=instante,
                        )
                    except ViolacaoInvarianteError:
                        return ResultadoExecucao.RESULTADO_DESCONHECIDO
                    uow.solicitacao_notificacao.save(existente)
                    uow.commit()
                solicitacao = existente
            else:
                uow.solicitacao_notificacao.save(solicitacao)
                uow.commit()

        if claim.cancelamento.is_set():
            return ResultadoExecucao.FALHA_TEMPORARIA
        resultado = self._channel.enviar(
            destinatario=destinatario,
            assunto="Comprovante do lancamento",
            corpo=texto,
            chave_idempotente=solicitacao.chave_idempotente,
        )
        if resultado.resultado is ResultadoCanal.ACEITA and not resultado.provider_message_id:
            resultado = ResultadoEnvio(
                ResultadoCanal.DESCONHECIDO,
                codigo="accepted_without_provider_message_id",
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
            emprestimo = uow.emprestimo.find_by_id(claim.job.origem_id)
            if persistida is None or job is None or emprestimo is None:
                return ResultadoExecucao.RESULTADO_DESCONHECIDO
            instante = self._agora()
            persistida.registrar_resultado(resultado)
            job.concluir(claim.tentativa.lease_token, agora=instante)
            claim.tentativa.finalizar(EstadoTentativaJob.SUCESSO, agora=instante)
            uow.solicitacao_notificacao.save(persistida)
            uow.registro_comunicacao.save(
                RegistroComunicacao(
                    tenant_id=job.tenant_id,
                    carteira_id=job.carteira_id,
                    responsavel_id=None,
                    ator_tipo="service",
                    ator_identificador="scheduler-worker",
                    canal=CanalComunicacao.WHATSAPP,
                    ocorrido_em=instante,
                    resumo="Comprovante de lancamento aceito pelo provedor",
                    resultado="aceita",
                    devedor_id=emprestimo.devedor_id,
                    emprestimo_id=emprestimo.id,
                    notification_id=persistida.id,
                    provider_message_id=resultado.provider_message_id,
                )
            )
            uow.tentativa_job.save(claim.tentativa)
            if not uow.job_agendado.finalizar_com_fencing(job, claim.tentativa.lease_token):
                return ResultadoExecucao.RESULTADO_DESCONHECIDO
            uow.commit()
        return ResultadoExecucao.FINALIZADO


def _payload_comprovante(claim: ClaimScheduler) -> tuple[str, str] | None:
    if (
        claim.job.tipo != TIPO_JOB_COMPROVANTE
        or claim.job.origem_tipo != ORIGEM_COMPROVANTE
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


def _chave_idempotente_comprovante(claim: ClaimScheduler) -> str:
    bruto = json.dumps(
        {
            "tenant_id": str(claim.job.tenant_id),
            "origem_tipo": claim.job.origem_tipo,
            "origem_id": str(claim.job.origem_id),
            "finalidade": "comprovante_lancamento_whatsapp",
            "versao_solicitacao": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"notification/{hashlib.sha256(bruto.encode()).hexdigest()}"


def _formatar_decimal(valor: Decimal, *, casas: int) -> str:
    bruto = f"{valor:,.{casas}f}"
    return bruto.replace(",", "_").replace(".", ",").replace("_", ".")
