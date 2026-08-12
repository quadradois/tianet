"""Adapter REST do Resend atras de NotificationChannel."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.domain.credit.notifications import ResultadoCanal, ResultadoEnvio


class ResendNotificationChannel(NotificationChannel):
    def __init__(
        self,
        *,
        api_key: str,
        remetente: str,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip() or not remetente.strip():
            raise ValueError("credenciais Resend incompletas")
        self._remetente = remetente
        self._client = client or httpx.Client(
            base_url="https://api.resend.com",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
            trust_env=False,
        )

    def enviar(
        self,
        *,
        destinatario: str,
        assunto: str,
        corpo: str,
        chave_idempotente: str,
    ) -> ResultadoEnvio:
        try:
            response = self._client.post(
                "/emails",
                headers={"Idempotency-Key": chave_idempotente},
                json={
                    "from": self._remetente,
                    "to": [destinatario],
                    "subject": assunto,
                    "text": corpo,
                    "headers": {"X-Entity-Ref-ID": chave_idempotente},
                },
            )
        except (httpx.TimeoutException, httpx.TransportError):
            return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="transport_unknown")
        return _classificar_resposta(response, chave_idempotente)

    def consultar_status(self, provider_message_id: str) -> ResultadoEnvio:
        try:
            response = self._client.get(f"/emails/{provider_message_id}")
        except (httpx.TimeoutException, httpx.TransportError):
            return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="status_unknown")
        if response.status_code == 404:
            return ResultadoEnvio(ResultadoCanal.FALHA_PERMANENTE, codigo="provider_not_found")
        if response.status_code >= 500:
            return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="provider_5xx")
        dados = _json_seguro(response)
        if response.is_success and dados.get("id") == provider_message_id:
            chave = _chave_da_evidencia(dados)
            if chave is None:
                return ResultadoEnvio(
                    ResultadoCanal.DESCONHECIDO,
                    codigo="status_without_idempotency_evidence",
                )
            return ResultadoEnvio(
                ResultadoCanal.ACEITA,
                provider_message_id=provider_message_id,
                codigo=str(dados.get("last_event", "accepted")),
                chave_idempotente=chave,
                ocorrido_em=datetime.now(UTC),
            )
        return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="status_malformed")


def _classificar_resposta(response: httpx.Response, chave_idempotente: str) -> ResultadoEnvio:
    dados = _json_seguro(response)
    if response.is_success:
        message_id = dados.get("id")
        if isinstance(message_id, str) and message_id:
            return ResultadoEnvio(
                ResultadoCanal.ACEITA,
                provider_message_id=message_id,
                codigo="accepted",
                chave_idempotente=chave_idempotente,
            )
        return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="success_malformed")
    if response.status_code == 429:
        return ResultadoEnvio(ResultadoCanal.FALHA_TEMPORARIA, codigo="rate_limited")
    if 400 <= response.status_code < 500:
        return ResultadoEnvio(ResultadoCanal.FALHA_PERMANENTE, codigo="provider_4xx")
    return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="provider_5xx")


def _json_seguro(response: httpx.Response) -> dict[str, Any]:
    try:
        dados = response.json()
    except ValueError:
        return {}
    return dados if isinstance(dados, dict) else {}


def _chave_da_evidencia(dados: dict[str, Any]) -> str | None:
    headers = dados.get("headers")
    if not isinstance(headers, dict):
        return None
    for nome, valor in headers.items():
        if str(nome).lower() == "x-entity-ref-id" and isinstance(valor, str):
            return valor
    return None
