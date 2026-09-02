"""DTOs da conexão de WhatsApp (IMP-368, PLAN-034).

Um DTO por recurso (RA-012): a Presentation nunca devolve o Aggregate, e nunca
devolve o **token** — ele é segredo, vive cifrado, e não tem campo aqui nem por
engano.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from emprestimo.application.conexao_whatsapp import EstadoConexaoWhatsApp, QrCodeConexao


class ConexaoWhatsAppResponse(BaseModel):
    """Estado da conexão, e o que a tela deve oferecer a partir dele.

    `existe` e `pareada` são separados de propósito: "não existe" pede criar a
    instância, "existe e não pareou" pede escanear o QR. Uma flag só faria a
    tela oferecer a ação errada em metade dos casos.

    `numero` e `nome_exibicao` são **coisas diferentes** — o telefone da conta e
    o push name (`"Barbosa"`). Rotular um como o outro foi defeito real, pego em
    review; a tela mostra os dois, cada um com seu rótulo.
    """

    existe: bool
    pareada: bool
    conectado: bool
    instancia_nome: str | None = Field(
        default=None,
        description="Nome da instância no provedor. Gerado pela plataforma, nunca digitado.",
    )
    nome_exibicao: str | None = Field(
        default=None, description="Push name da conta do WhatsApp — NÃO é o telefone."
    )
    numero: str | None = Field(
        default=None, description="Telefone da conta pareada, extraído do jid do provedor."
    )
    qrcode_base64: str | None = Field(
        default=None,
        description=(
            "QR em data URI PNG enquanto o pareamento está pendente. "
            "Nulo quando já pareou ou quando o provedor ainda está gerando."
        ),
    )

    @classmethod
    def de(cls, estado: EstadoConexaoWhatsApp) -> ConexaoWhatsAppResponse:
        return cls(
            existe=estado.existe,
            pareada=estado.pareada,
            conectado=estado.conectado,
            instancia_nome=estado.instancia_nome,
            nome_exibicao=estado.nome_exibicao,
            numero=estado.numero,
            qrcode_base64=estado.qrcode_base64,
        )


class QrCodeConexaoResponse(BaseModel):
    """QR de agora, ou nulo enquanto o provedor ainda o gera.

    Nulo **não é falha**: logo após conectar, o provedor responde "no QR code
    available, aguarde e tente de novo". A tela faz polling; transformar isso em
    erro faria o caminho feliz parecer quebrado.
    """

    qrcode_base64: str | None = None

    @classmethod
    def de(cls, qrcode: QrCodeConexao) -> QrCodeConexaoResponse:
        return cls(qrcode_base64=qrcode.qrcode_base64)
