"""Ingress público do agente — webhook do Evolution (IMP-356-A).

Regras de porta, sem exceção:
- Nenhum campo do envelope autentica nada: instância, remetente, classe e
  URLs vêm da configuração do servidor. O envelope só carrega dados.
- Tudo que é aceito entra na inbox persistente ANTES do `2xx`; replay
  responde `2xx` sem reprocessar. Descarte tratável também responde `2xx`
  (o provedor repete até `4xx`), com motivo fixo — nunca conteúdo.
- 400 só para corpo que nem objeto JSON é: erro do remetente, não recusa
  de processamento. Nenhum LLM, ferramenta ou envio existe neste slice.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from emprestimo.agent.conversa import (
    ClasseContexto,
    ConfiguracaoIngress,
    EntradaConversa,
    MotivoDescarte,
    classificar_entrada,
    eh_remetente_de_grupo,
)
from emprestimo.application.ports import UnitOfWork

ESTADO_RECEBIDA = "recebida"


def _texto_da_mensagem(data: dict[str, Any]) -> str | None:
    mensagem = data.get("Message")
    if not isinstance(mensagem, dict):
        return None
    conversa = mensagem.get("conversation")
    return conversa if isinstance(conversa, str) and conversa else None


def _descartar(motivo: MotivoDescarte) -> JSONResponse:
    return JSONResponse(status_code=200, content={"message": "discarded", "motivo": motivo.value})


def _aceitar(*, duplicada: bool, classe: ClasseContexto) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "message": "accepted",
            "duplicada": duplicada,
            "classe": classe.value,
        },
    )


def create_ingress_app(
    config: ConfiguracaoIngress,
    uow_factory: Callable[[], UnitOfWork],
    instancia_id_esperada: str,
) -> FastAPI:
    """Monta o app de ingress com configuração e fábrica injetadas (testável)."""

    app = FastAPI(title="TiaNet — Ingress do agente")

    @app.post("/whatsapp/webhook")
    async def receber_webhook(request: Request) -> JSONResponse:
        try:
            envelope = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"message": "corpo-invalido"})
        if not isinstance(envelope, dict):
            return JSONResponse(status_code=400, content={"message": "corpo-invalido"})

        if envelope.get("event") != "Message":
            return _descartar(MotivoDescarte.EVENTO_NAO_SUPORTADO)
        if envelope.get("instanceId") != instancia_id_esperada:
            return _descartar(MotivoDescarte.INSTANCIA_DESCONHECIDA)

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

        classificada = classificar_entrada(
            config=config,
            provider_input_id=provider_input_id,
            sender=sender,
            texto=_texto_da_mensagem(data),
        )

        with uow_factory() as uow:
            existente = uow.inbox_conversa.buscar_por_chave(
                config.tenant_id, config.instancia_ref, provider_input_id
            )
            if existente is not None:
                # Replay: nada é reprocessado, nada é recriado. O commit
                # abaixo só confirma a leitura; o estado não muda.
                uow.commit()
                return _aceitar(duplicada=True, classe=existente.classe)
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
