"""Adapter REST do Evolution Go atras de NotificationChannel."""

from __future__ import annotations

from typing import Any

import httpx

from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.domain.credit.notifications import ResultadoCanal, ResultadoEnvio


class EvolutionWhatsAppNotificationChannel(NotificationChannel):
    """Envia texto com o token da instancia, sem credenciais de Tenant."""

    def __init__(
        self,
        *,
        host: str,
        instance_token: str,
        client: httpx.Client | None = None,
    ) -> None:
        host_normalizado = host.strip().rstrip("/")
        token_normalizado = instance_token.strip()
        if not host_normalizado or not token_normalizado:
            raise ValueError("credenciais Evolution Go incompletas")
        self._instance_token = token_normalizado
        self._client = client or httpx.Client(
            base_url=host_normalizado,
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
        del assunto
        try:
            response = self._client.post(
                "/send/text",
                headers={"apikey": self._instance_token},
                json={
                    "number": destinatario,
                    "text": corpo,
                    "id": chave_idempotente,
                },
            )
        except (httpx.TimeoutException, httpx.TransportError):
            return ResultadoEnvio(
                ResultadoCanal.FALHA_TEMPORARIA,
                codigo="transport_temporary",
            )
        return _classificar_resposta(response, chave_idempotente)

    def consultar_status(self, provider_message_id: str) -> ResultadoEnvio:
        """Declara a ausencia de consulta: entrega chega somente pelo Receipt."""

        del provider_message_id
        return ResultadoEnvio(
            ResultadoCanal.DESCONHECIDO,
            codigo="status_available_by_receipt_only",
        )


def _classificar_resposta(response: httpx.Response, chave_idempotente: str) -> ResultadoEnvio:
    dados = _json_seguro(response)
    if response.is_success:
        message_id = _identificador_mensagem(dados)
        if message_id is not None:
            return ResultadoEnvio(
                ResultadoCanal.ACEITA,
                provider_message_id=message_id,
                codigo="accepted",
                chave_idempotente=chave_idempotente,
            )
        return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="success_malformed")
    if response.status_code == 401:
        codigo = "tenant_inactive" if _indica_tenant_inativo(dados) else "auth_invalid"
        return ResultadoEnvio(ResultadoCanal.FALHA_PERMANENTE, codigo=codigo)
    if response.status_code == 403:
        return ResultadoEnvio(ResultadoCanal.FALHA_PERMANENTE, codigo="tenant_inactive")
    if response.status_code == 429:
        return ResultadoEnvio(ResultadoCanal.FALHA_TEMPORARIA, codigo="rate_limited")
    if response.status_code >= 500:
        return ResultadoEnvio(ResultadoCanal.FALHA_TEMPORARIA, codigo="provider_5xx")
    if 400 <= response.status_code < 500:
        return ResultadoEnvio(ResultadoCanal.FALHA_PERMANENTE, codigo="provider_4xx")
    return ResultadoEnvio(ResultadoCanal.DESCONHECIDO, codigo="provider_unexpected_status")


def _identificador_mensagem(dados: dict[str, Any]) -> str | None:
    data = dados.get("data")
    if not isinstance(data, dict):
        return None
    info = data.get("Info")
    if not isinstance(info, dict):
        return None
    message_id = info.get("ID")
    if not isinstance(message_id, str) or not message_id.strip():
        return None
    return message_id


def _indica_tenant_inativo(dados: dict[str, Any]) -> bool:
    mensagem = dados.get("error", dados.get("message", ""))
    return isinstance(mensagem, str) and (
        "tenant inactive" in mensagem.lower() or "tenant is inactive" in mensagem.lower()
    )


def _json_seguro(response: httpx.Response) -> dict[str, Any]:
    try:
        dados = response.json()
    except ValueError:
        return {}
    return dados if isinstance(dados, dict) else {}
