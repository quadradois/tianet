"""Cliente do Mercado Pago (IMP-388: so a verificacao de credencial).

O escopo aqui e deliberadamente minimo: `verificar_credencial` existe para o
botao **Testar** do painel dar um veredito antes de a Credora ligar a
integracao. Criar cobranca, consultar pagamento e cancelar entram no IMP-375,
no mesmo modulo.

Sem SDK: `httpx` ja existe no projeto e o contrato e HTTP simples. O token
nunca aparece em `repr`, log ou excecao — o que sobe e o codigo da falha.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

__all__ = ["ResultadoVerificacao", "verificar_credencial"]

BASE_URL = "https://api.mercadopago.com"
TIMEOUT_PADRAO = 10.0


@dataclass(frozen=True)
class ResultadoVerificacao:
    """Veredito do botao Testar. `detalhe` e codigo, nunca corpo do provedor."""

    valido: bool
    detalhe: str


def verificar_credencial(
    access_token: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = TIMEOUT_PADRAO,
) -> ResultadoVerificacao:
    """Leitura autenticada, sem criar nada no provedor.

    `/users/me` e a chamada mais barata que prova posse da credencial: nao
    movimenta dinheiro, nao cria cobranca e responde 401 quando o token nao
    vale. Falha de transporte vira veredito negativo com codigo proprio —
    quem nao conseguiu falar com o provedor nao pode ligar a integracao.
    """
    proprio = client is None
    http = client or httpx.Client(base_url=BASE_URL, timeout=timeout)
    try:
        resposta = http.get(
            "/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except httpx.HTTPError:
        return ResultadoVerificacao(valido=False, detalhe="falha_de_transporte")
    finally:
        if proprio:
            http.close()

    if resposta.status_code == httpx.codes.OK:
        return ResultadoVerificacao(valido=True, detalhe="ok")
    if resposta.status_code in (httpx.codes.UNAUTHORIZED, httpx.codes.FORBIDDEN):
        return ResultadoVerificacao(valido=False, detalhe="credencial_recusada")
    return ResultadoVerificacao(valido=False, detalhe=f"resposta_inesperada:{resposta.status_code}")
