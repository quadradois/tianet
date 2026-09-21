"""Resumo diario ao Credor pelo WhatsApp (IMP-353).

Sem IA: o texto e montado em codigo a partir do snapshot da varredura, com
os valores exatamente como o Motor devolveu. Elegivel so depois do sucesso
da varredura da mesma data; um job por carteira e dia; dia vazio nao envia.
Segue o padrao do aviso de sobra em `application/notifications.py`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime
from decimal import Decimal

from emprestimo.application.notifications import CHAVE_WHATSAPP_CREDOR
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.application.scheduler import ClaimScheduler, ResultadoExecucao
from emprestimo.application.varredura_cobranca import (
    DevedorVarreduraCobranca,
    ResultadoVarreduraCobranca,
)
from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.domain.credit.notifications import ResultadoCanal, ResultadoEnvio
from emprestimo.domain.credit.operacao_diaria import CanalComunicacao
from emprestimo.domain.credit.scheduler import EstadoTentativaJob, JobAgendado

TIPO_JOB_RESUMO_DIARIO = "enviar_resumo_diario_whatsapp"
ORIGEM_RESUMO_DIARIO = "resumo_diario_cobranca"
_NAMESPACE_RESUMO = uuid.UUID("5d0c2a4e-6f3b-5a8e-9c1d-2b7e4f6a8c0d")


def _formatar_valor(valor: Decimal) -> str:
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _ordenar(
    devedores: Iterable[DevedorVarreduraCobranca],
) -> list[DevedorVarreduraCobranca]:
    return sorted(devedores, key=lambda item: (item.devedor_nome, str(item.devedor_id)))


def montar_texto_resumo_diario(
    data_referencia: date, devedores: Iterable[DevedorVarreduraCobranca]
) -> str:
    """Dois blocos, ambos so leitura da varredura: vence hoje e em atraso.

    Um devedor aparece em um bloco so. O juro do atraso e o exigivel que o
    Motor ja apurou (`juros_pendente_acerto`); os dias sao contados a partir
    do acerto em aberto mais antigo.
    """
    todos = list(devedores)
    hoje = _ordenar(item for item in todos if item.vence_hoje and not item.em_atraso)
    atrasados = _ordenar(item for item in todos if item.em_atraso)
    linhas: list[str] = []
    if hoje:
        linhas.append(f"Acertos de hoje ({data_referencia.strftime('%d/%m/%Y')}): {len(hoje)}")
        linhas.extend(
            f"{item.devedor_nome} - juro R$ {_formatar_valor(item.valor_juros_periodo)}"
            f" - saldo R$ {_formatar_valor(item.saldo_devedor)}"
            for item in hoje
        )
    if atrasados:
        linhas.append(f"Em atraso: {len(atrasados)}")
        for item in atrasados:
            desde = item.atraso_desde or data_referencia
            dias = (data_referencia - desde).days
            plural = "dia" if dias == 1 else "dias"
            linhas.append(
                f"{item.devedor_nome} - desde {desde.strftime('%d/%m')} ({dias} {plural})"
                f" - juro R$ {_formatar_valor(item.juros_pendente_acerto)}"
                f" - saldo R$ {_formatar_valor(item.saldo_devedor)}"
            )
    return "\n".join(linhas)


class ResumoDiarioService:
    """Enfileira um resumo por carteira e data, ou audita por que nao."""

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

    def enfileirar(
        self,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        resultado: ResultadoVarreduraCobranca,
    ) -> JobAgendado | None:
        origem_id = uuid.uuid5(
            _NAMESPACE_RESUMO, f"{carteira_id}:{resultado.data_referencia.isoformat()}"
        )
        detalhes = {
            "tenant_id": str(tenant_id),
            "carteira_id": str(carteira_id),
            "data_referencia": resultado.data_referencia.isoformat(),
        }
        relevantes = resultado.vencem_hoje + resultado.em_atraso
        if not relevantes:
            return None
        with self._uow_factory() as uow:
            existente = uow.job_agendado.find_by_origem(
                tenant_id=tenant_id, origem_tipo=ORIGEM_RESUMO_DIARIO, origem_id=origem_id
            )
            if existente is not None:
                return existente
            numero = next(
                (
                    item.valor.strip()
                    for item in uow.configuracao.find_by_tenant_id(tenant_id)
                    if item.chave == CHAVE_WHATSAPP_CREDOR and item.valor.strip()
                ),
                None,
            )
            if numero is None:
                self._auditoria.registrar(
                    "resumo_diario",
                    origem_id,
                    "enfileirar.ignorado",
                    "nao_configurado",
                    detalhes=json.dumps(
                        {**detalhes, "motivo": "credor_whatsapp_nao_configurado"}, sort_keys=True
                    ),
                )
                return None
            job = JobAgendado(
                id=uuid.uuid5(_NAMESPACE_RESUMO, f"job:{origem_id}"),
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                tipo=TIPO_JOB_RESUMO_DIARIO,
                executar_em=self._agora(),
                correlation_id=f"resumo:{carteira_id}:{resultado.data_referencia.isoformat()}",
                payload={
                    "canal": CanalComunicacao.WHATSAPP.value,
                    "destinatario": numero,
                    "texto": montar_texto_resumo_diario(resultado.data_referencia, relevantes),
                    "data_referencia": resultado.data_referencia.isoformat(),
                },
                origem_tipo=ORIGEM_RESUMO_DIARIO,
                origem_id=origem_id,
            )
            uow.job_agendado.save_if_absent(job)
            uow.commit()
        self._auditoria.registrar(
            "resumo_diario",
            origem_id,
            "enfileirar.sucesso",
            "ok",
            detalhes=json.dumps({**detalhes, "job_id": str(job.id)}, sort_keys=True),
        )
        return job


class EntregaResumoDiarioService:
    """Handler do worker: envia o texto do payload e conclui o job com fencing."""

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

    def processar(self, claim: ClaimScheduler) -> ResultadoExecucao:
        detalhes = {"tenant_id": str(claim.job.tenant_id), "job_id": str(claim.job.id)}
        try:
            resultado = self._processar(claim)
        except Exception as exc:
            self._auditoria.registrar(
                "resumo_diario",
                claim.job.origem_id,
                "entregar.falha",
                "falhou",
                detalhes=json.dumps({**detalhes, "erro_tipo": type(exc).__name__}, sort_keys=True),
            )
            raise
        self._auditoria.registrar(
            "resumo_diario",
            claim.job.origem_id,
            "entregar.resultado",
            resultado.value,
            detalhes=json.dumps(detalhes, sort_keys=True),
        )
        return resultado

    def _processar(self, claim: ClaimScheduler) -> ResultadoExecucao:
        destinatario = claim.job.payload.get("destinatario")
        texto = claim.job.payload.get("texto")
        if (
            claim.job.tipo != TIPO_JOB_RESUMO_DIARIO
            or not isinstance(destinatario, str)
            or not destinatario.strip()
            or not isinstance(texto, str)
            or not texto.strip()
        ):
            return ResultadoExecucao.FALHA_PERMANENTE
        if claim.cancelamento.is_set():
            return ResultadoExecucao.FALHA_TEMPORARIA
        resultado = self._channel.enviar(
            destinatario=destinatario,
            assunto="Acertos de hoje",
            corpo=texto,
            chave_idempotente=_chave_envio(claim),
        )
        if resultado.resultado is ResultadoCanal.ACEITA and not resultado.provider_message_id:
            resultado = ResultadoEnvio(
                ResultadoCanal.DESCONHECIDO, codigo="accepted_without_provider_message_id"
            )
        if resultado.resultado is not ResultadoCanal.ACEITA:
            return {
                ResultadoCanal.FALHA_TEMPORARIA: ResultadoExecucao.FALHA_TEMPORARIA,
                ResultadoCanal.FALHA_PERMANENTE: ResultadoExecucao.FALHA_PERMANENTE,
                ResultadoCanal.DESCONHECIDO: ResultadoExecucao.RESULTADO_DESCONHECIDO,
            }[resultado.resultado]
        with self._uow_factory() as uow:
            job = uow.job_agendado.find_scoped(claim.job.id, claim.job.tenant_id)
            if job is None:
                return ResultadoExecucao.RESULTADO_DESCONHECIDO
            instante = self._agora()
            job.concluir(claim.tentativa.lease_token, agora=instante)
            claim.tentativa.finalizar(EstadoTentativaJob.SUCESSO, agora=instante)
            uow.tentativa_job.save(claim.tentativa)
            if not uow.job_agendado.finalizar_com_fencing(job, claim.tentativa.lease_token):
                return ResultadoExecucao.RESULTADO_DESCONHECIDO
            uow.commit()
        return ResultadoExecucao.FINALIZADO


def _chave_envio(claim: ClaimScheduler) -> str:
    bruto = json.dumps(
        {
            "tenant_id": str(claim.job.tenant_id),
            "origem_tipo": claim.job.origem_tipo,
            "origem_id": str(claim.job.origem_id),
            "finalidade": TIPO_JOB_RESUMO_DIARIO,
            "versao_solicitacao": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"notification/{hashlib.sha256(bruto.encode()).hexdigest()}"
