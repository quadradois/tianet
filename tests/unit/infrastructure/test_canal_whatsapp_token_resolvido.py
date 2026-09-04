"""Canal de WhatsApp que resolve o token a cada envio (IMP-370).

A dobra que este canal existe para desfazer: o canal concreto recebe o token
**no construtor**, e o worker montava um so, na subida, a partir da variavel de
ambiente. Com o token vindo do banco isso deixa de servir — ele muda quando o
operador reconecta pela tela.
"""

from __future__ import annotations

from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.domain.credit.notifications import ResultadoCanal, ResultadoEnvio
from emprestimo.infrastructure.notifications import CanalWhatsAppComTokenResolvido


class _CanalFake(NotificationChannel):
    def __init__(self, token: str) -> None:
        self.token = token
        self.envios = 0

    def enviar(
        self,
        *,
        destinatario: str,
        assunto: str,
        corpo: str,
        chave_idempotente: str,
    ) -> ResultadoEnvio:
        self.envios += 1
        return ResultadoEnvio(ResultadoCanal.ACEITA, provider_message_id=self.token)

    def consultar_status(self, provider_message_id: str) -> ResultadoEnvio:
        return ResultadoEnvio(ResultadoCanal.ACEITA, provider_message_id=self.token)


def _enviar(canal: CanalWhatsAppComTokenResolvido) -> ResultadoEnvio:
    return canal.enviar(
        destinatario="556299999999",
        assunto="Comprovante",
        corpo="corpo",
        chave_idempotente="idem-1",
    )


def test_sem_token_e_falha_temporaria_e_nao_permanente() -> None:
    """Permanente descartaria a mensagem para sempre. Nao ha token porque
    ninguem conectou ainda — e isso se resolve quando o operador parear."""

    canal = CanalWhatsAppComTokenResolvido(
        resolver_token=lambda: None,
        fabrica=lambda token: _CanalFake(token),
    )

    resultado = _enviar(canal)

    assert resultado.resultado is ResultadoCanal.FALHA_TEMPORARIA
    assert resultado.codigo == "whatsapp_sem_conexao"


def test_token_em_branco_conta_como_ausente() -> None:
    """Um token de espacos passaria pela checagem de `None` e daria 401 em tudo."""

    canal = CanalWhatsAppComTokenResolvido(
        resolver_token=lambda: "   ",
        fabrica=lambda token: _CanalFake(token),
    )

    assert _enviar(canal).codigo == "whatsapp_sem_conexao"


def test_token_novo_reconstroi_o_canal() -> None:
    """O caso que motiva a classe: reconectar pela tela pode criar instancia
    nova, e o canal montado na subida seguiria com o token velho ate o restart."""

    tokens = iter(["tok-antigo", "tok-novo"])
    construidos: list[_CanalFake] = []

    def fabrica(token: str) -> NotificationChannel:
        canal = _CanalFake(token)
        construidos.append(canal)
        return canal

    canal = CanalWhatsAppComTokenResolvido(
        resolver_token=lambda: next(tokens),
        fabrica=fabrica,
    )

    primeiro = _enviar(canal)
    segundo = _enviar(canal)

    assert primeiro.provider_message_id == "tok-antigo"
    assert segundo.provider_message_id == "tok-novo"
    assert len(construidos) == 2


def test_token_igual_reaproveita_o_canal() -> None:
    """Sem isto haveria um `httpx.Client` novo por mensagem, e sockets
    acumulando por envio em vez de por conexao."""

    construidos: list[_CanalFake] = []

    def fabrica(token: str) -> NotificationChannel:
        canal = _CanalFake(token)
        construidos.append(canal)
        return canal

    canal = CanalWhatsAppComTokenResolvido(
        resolver_token=lambda: "tok-estavel",
        fabrica=fabrica,
    )

    _enviar(canal)
    _enviar(canal)
    _enviar(canal)

    assert len(construidos) == 1
    assert construidos[0].envios == 3


def test_consultar_status_sem_token_e_desconhecido() -> None:
    """Nao e falha de envio: e ausencia de canal para perguntar. Dizer
    `FALHA_PERMANENTE` marcaria como perdida uma mensagem que pode ter saido."""

    canal = CanalWhatsAppComTokenResolvido(
        resolver_token=lambda: None,
        fabrica=lambda token: _CanalFake(token),
    )

    resultado = canal.consultar_status("provider-1")

    assert resultado.resultado is ResultadoCanal.DESCONHECIDO
    assert resultado.codigo == "whatsapp_sem_conexao"
