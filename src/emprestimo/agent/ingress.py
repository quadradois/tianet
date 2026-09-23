"""Ingress público do agente — webhook do Evolution (IMP-356-A/B).

Regras de porta, sem exceção:
- Nenhum campo do envelope autentica nada: instância, remetente, classe e
  URLs vêm da configuração do servidor. O envelope só carrega dados.
- Tamanho primeiro: o corpo é medido antes de qualquer parse ou
  persistência; acima do limite, descarte fixo sem LLM (356-B).
- Só texto e metadados mínimos seguem; mídia sem texto é descartada antes
  de persistir (356-B). Métricas contam bytes e motivos, nunca conteúdo.
- Tudo que é aceito entra na inbox persistente ANTES do `2xx`; replay
  responde `2xx` sem reprocessar. Descarte tratável também responde `2xx`
  (o provedor repete até `4xx`), com motivo fixo — nunca conteúdo.
- 400 só para corpo que nem objeto JSON é: erro do remetente, não recusa
  de processamento. Nenhum LLM, ferramenta ou envio existe neste slice.
"""

from __future__ import annotations

import hmac
import json
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from emprestimo.agent.admissao import ControleAdmissao
from emprestimo.agent.conversa import (
    ClasseContexto,
    ConfiguracaoIngress,
    EntradaConversa,
    MotivoDescarte,
    chave_telefone,
    classificar_entrada,
    eh_remetente_de_grupo,
)
from emprestimo.agent.metricas import METRICAS, MetricasIngress
from emprestimo.application.notifications import CHAVE_WHATSAPP_CREDOR
from emprestimo.application.ports import UnitOfWork

ESTADO_RECEBIDA = "recebida"
_LOGGER = logging.getLogger(__name__)


def _texto_da_mensagem(data: dict[str, Any]) -> tuple[str | None, bool]:
    """Devolve (texto, eh_midia): mídia sem texto é descarte, não inbox."""
    mensagem = data.get("Message")
    if not isinstance(mensagem, dict) or not mensagem:
        return None, False
    conversa = mensagem.get("conversation")
    if isinstance(conversa, str) and conversa:
        return conversa, False
    estendida = mensagem.get("extendedTextMessage")
    if isinstance(estendida, dict):
        texto = estendida.get("text")
        if isinstance(texto, str) and texto:
            # Legenda ou citação: o texto segue, a mídia citada fica para trás.
            return texto, False
    return None, True


def _descartar(motivo: MotivoDescarte, metricas: MetricasIngress = METRICAS) -> JSONResponse:
    metricas.registrar_descarte(motivo.value)
    return JSONResponse(status_code=200, content={"message": "discarded", "motivo": motivo.value})


def _aceitar(
    *, duplicada: bool, classe: ClasseContexto, metricas: MetricasIngress = METRICAS
) -> JSONResponse:
    metricas.registrar_aceita(duplicada=duplicada)
    return JSONResponse(
        status_code=200,
        content={
            "message": "accepted",
            "duplicada": duplicada,
            "classe": classe.value,
        },
    )


def _token_confere(
    uow_factory: Callable[[], UnitOfWork],
    config: ConfiguracaoIngress,
    recebido: object,
) -> bool:
    """Compara o `instanceToken` do envelope com o token guardado da instancia.

    O webhook do Evolution nao tem autenticacao nenhuma — a URL e o unico
    segredo (contexto externo §2.1). O `instanceToken` e o segredo da instancia
    que so o Evolution e a TiaNet conhecem; e o que prova que o pacote saiu do
    provedor. Comparacao em tempo constante.

    Sem cache, de proposito: o token e lido e decifrado a cada mensagem, entao
    rotacionar a instancia na tela vale na hora, sem invalidacao para errar.
    Falha fechada em tudo — token ausente, conexao apagada, cifra que nao abre.
    """
    if not isinstance(recebido, str) or not recebido:
        return False
    try:
        with uow_factory() as uow:
            esperado = uow.conexao_whatsapp.find_token(config.tenant_id)
    except Exception as exc:  # cifra indisponivel, token ilegivel: fail-closed
        _LOGGER.warning("token da instancia indisponivel: %s", type(exc).__name__)
        return False
    return bool(esperado) and hmac.compare_digest(recebido, esperado or "")


def _numero_credora(uow: UnitOfWork, tenant_id: uuid.UUID) -> str | None:
    """O `credor_whatsapp` do Tenant: quem recebe os avisos responde por eles."""
    for item in uow.configuracao.find_by_tenant_id(tenant_id):
        if item.chave == CHAVE_WHATSAPP_CREDOR and item.valor.strip():
            return item.valor
    return None


def create_ingress_app(
    config: ConfiguracaoIngress,
    uow_factory: Callable[[], UnitOfWork],
    instancia_id_esperada: str,
    admissao: ControleAdmissao | None = None,
) -> FastAPI:
    """Monta o app de ingress com configuração e fábrica injetadas (testável).

    Sem `admissao`, o comportamento é o da Entrega 356-A. Com admissao, a
    ordem é fixa: dedupe primeiro (duplicata nunca consome quota), quota
    depois, inserção por último — e recusa é `2xx` fixa, sem tempestade.
    """

    app = FastAPI(title="TiaNet — Ingress do agente")

    @app.post("/whatsapp/webhook")
    async def receber_webhook(request: Request) -> JSONResponse:
        corpo = await request.body()
        METRICAS.registrar_entrada(len(corpo))
        if len(corpo) > config.max_bytes:
            # Acima do limite: descarte fixo sem parse, sem persistência e
            # sem LLM — e com 2xx, para não provocar tempestade de retries.
            return _descartar(MotivoDescarte.CARGA_EXCEDIDA)
        try:
            envelope = json.loads(corpo.decode("utf-8"))
        except Exception:
            return JSONResponse(status_code=400, content={"message": "corpo-invalido"})
        if not isinstance(envelope, dict):
            return JSONResponse(status_code=400, content={"message": "corpo-invalido"})

        if envelope.get("event") != "Message":
            return _descartar(MotivoDescarte.EVENTO_NAO_SUPORTADO)
        if envelope.get("instanceId") != instancia_id_esperada:
            return _descartar(MotivoDescarte.INSTANCIA_DESCONHECIDA)
        if not _token_confere(uow_factory, config, envelope.get("instanceToken")):
            # Slice 6: sem o token da instancia, `Sender` e so texto que
            # qualquer um escreve. Nada abaixo desta linha le o remetente.
            return _descartar(MotivoDescarte.TOKEN_INVALIDO)

        data = envelope.get("data")
        if not isinstance(data, dict):
            return JSONResponse(status_code=400, content={"message": "corpo-invalido"})
        info = data.get("Info")
        if not isinstance(info, dict):
            return JSONResponse(status_code=400, content={"message": "corpo-invalido"})
        provider_input_id = info.get("ID")
        if not isinstance(provider_input_id, str) or not provider_input_id:
            return _descartar(MotivoDescarte.SEM_ID)
        if info.get("IsFromMe") is True:
            return _descartar(MotivoDescarte.PROPRIA)
        sender = info.get("Sender")
        if not isinstance(sender, str) or not sender:
            return _descartar(MotivoDescarte.SEM_ID)
        if info.get("IsGroup") is True or eh_remetente_de_grupo(sender):
            return _descartar(MotivoDescarte.GRUPO)

        texto, eh_midia = _texto_da_mensagem(data)
        if eh_midia:
            return _descartar(MotivoDescarte.MIDIA_SEM_TEXTO)

        with uow_factory() as uow:
            # Lidos a cada mensagem, sem cache: trocar o numero de avisos na
            # tela vale para a proxima mensagem, sem restart do agent.
            classificada = classificar_entrada(
                provider_input_id=provider_input_id,
                sender=sender,
                texto=texto,
                numero_credora=_numero_credora(uow, config.tenant_id),
                telefones_devedores=frozenset(
                    chave
                    for chave in map(
                        chave_telefone,
                        uow.contato.telefones_de_devedores_ativos(config.tenant_id),
                    )
                    if chave
                ),
            )
            existente = uow.inbox_conversa.buscar_por_chave(
                config.tenant_id, config.instancia_ref, provider_input_id
            )
            if existente is not None:
                # Replay: nada é reprocessado, nada é recriado. O commit
                # abaixo só confirma a leitura; o estado não muda.
                uow.commit()
                return _aceitar(duplicada=True, classe=existente.classe)
            if admissao is not None:
                decisao = admissao.avaliar(
                    uow.admissao,
                    tenant_id=config.tenant_id,
                    instancia_ref=config.instancia_ref,
                    classe=classificada.classe.value,
                    remetente=classificada.remetente_normalizado,
                )
                if not decisao.admitida:
                    uow.rollback()
                    METRICAS.registrar_recusa(decisao.motivo)
                    return JSONResponse(
                        status_code=200,
                        content={"message": "recusada", "motivo": decisao.motivo},
                    )
            entrada = EntradaConversa(
                id=uuid.uuid4(),
                tenant_id=config.tenant_id,
                instancia_ref=config.instancia_ref,
                envelope_instance_id=envelope.get("instanceId", ""),
                provider_input_id=provider_input_id,
                remetente_normalizado=classificada.remetente_normalizado,
                classe=classificada.classe,
                texto=classificada.texto,
                estado=ESTADO_RECEBIDA,
                recebido_em=datetime.now(UTC),
            )
            inseriu = uow.inbox_conversa.salvar(entrada)
            if not inseriu:
                # Corrida: outro executor persistiu primeiro nesta transação.
                # A classe da resposta vem da linha vencedora, nunca de
                # reclassificação — o vencedor e o dono da verdade.
                uow.rollback()
                vencedora = uow.inbox_conversa.buscar_por_chave(
                    config.tenant_id, config.instancia_ref, provider_input_id
                )
                uow.commit()
                classe_resposta = vencedora.classe if vencedora is not None else classificada.classe
                return _aceitar(duplicada=True, classe=classe_resposta)
            uow.sessao_conversa.garantir(
                config.tenant_id,
                config.instancia_ref,
                classificada.classe,
                classificada.remetente_normalizado,
            )
            uow.commit()
            return _aceitar(duplicada=False, classe=classificada.classe)

    return app
