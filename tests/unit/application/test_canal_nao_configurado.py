"""Canal sem credencial recusa em vez de fingir entrega.

Decisao de 2026-08-25: e-mail saiu do escopo do MVP — nao ha conta Resend, e o
canal real da operacao e o WhatsApp. Antes, `APP_ENV=production` sem
`RESEND_API_KEY` derrubava o worker na subida, bloqueando o deploy inteiro por
um canal que ninguem usa.

A saida obvia seria cair no `FakeNotificationChannel`. Seria a pior opcao: ele
devolve `ACEITA` com `provider_message_id` sintetico, e a trilha passaria a
registrar como **entregue** um e-mail que nunca saiu. Estes testes fixam a
diferenca entre as duas coisas.
"""

from __future__ import annotations

from emprestimo.application.notifications import (
    CanalNaoConfiguradoNotificationChannel,
    FakeNotificationChannel,
)
from emprestimo.domain.credit.notifications import ResultadoCanal

CHAVE = "notification/abc123"


def _enviar(canal: object) -> object:
    return canal.enviar(  # type: ignore[attr-defined]
        destinatario="operador@exemplo.com",
        assunto="Lembrete",
        corpo="corpo",
        chave_idempotente=CHAVE,
    )


def test_canal_sem_credencial_recusa_e_nao_inventa_comprovante() -> None:
    resultado = _enviar(CanalNaoConfiguradoNotificationChannel("email"))

    assert resultado.resultado is ResultadoCanal.FALHA_PERMANENTE  # type: ignore[attr-defined]
    assert resultado.provider_message_id is None, (  # type: ignore[attr-defined]
        "comprovante de entrega sem entrega e exatamente o que nao pode acontecer"
    )
    assert resultado.codigo == "canal_nao_configurado:email"  # type: ignore[attr-defined]


def test_a_recusa_e_terminal_e_nao_entra_em_retry() -> None:
    """Retry nao resolve falta de configuracao — so gasta ciclo ate desistir."""
    resultado = _enviar(CanalNaoConfiguradoNotificationChannel("email"))

    assert resultado.resultado is not ResultadoCanal.FALHA_TEMPORARIA  # type: ignore[attr-defined]


def test_o_fake_finge_entrega_e_por_isso_nao_serve_em_producao() -> None:
    """Prova o motivo da existencia do canal acima, em vez de so afirma-lo."""
    resultado = _enviar(FakeNotificationChannel())

    assert resultado.resultado is ResultadoCanal.ACEITA  # type: ignore[attr-defined]
    assert resultado.provider_message_id is not None  # type: ignore[attr-defined]


def test_consultar_status_tambem_nao_afirma_entrega() -> None:
    canal = CanalNaoConfiguradoNotificationChannel("email")

    resultado = canal.consultar_status("qualquer-id")

    assert resultado.resultado is ResultadoCanal.DESCONHECIDO
    assert resultado.codigo == "canal_nao_configurado:email"
