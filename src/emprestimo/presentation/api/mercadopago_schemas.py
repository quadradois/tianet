"""DTOs do interruptor do Mercado Pago (IMP-388).

A resposta **nunca** carrega segredo: diz se a credencial existe, quando foi
testada e se a integracao esta ligada. Quem precisa do valor e o provedor, e
ele recebe direto da cifra.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from emprestimo.application.configuracao_mercadopago import ConfiguracaoMercadoPagoResultado


class CredenciaisMercadoPagoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str = Field(min_length=10, max_length=512)
    webhook_secret: str = Field(min_length=8, max_length=512)


class ConfiguracaoMercadoPagoResponse(BaseModel):
    """Estado visivel da integracao; sem `access_token` nem `webhook_secret`."""

    tenant_id: uuid.UUID
    habilitado: bool
    credencial_configurada: bool
    assinatura_configurada: bool
    testado_em: datetime | None
    atualizado_em: datetime
    atualizado_por: uuid.UUID | None

    @classmethod
    def de(cls, resultado: ConfiguracaoMercadoPagoResultado) -> ConfiguracaoMercadoPagoResponse:
        return cls(
            tenant_id=resultado.tenant_id,
            habilitado=resultado.habilitado,
            credencial_configurada=resultado.credencial_configurada,
            assinatura_configurada=resultado.assinatura_configurada,
            testado_em=resultado.testado_em,
            atualizado_em=resultado.atualizado_em,
            atualizado_por=resultado.atualizado_por,
        )
