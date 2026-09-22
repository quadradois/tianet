"""DTOs do recebimento: interruptor do Mercado Pago (IMP-388) e chave Pix (IMP-390).

A resposta **nunca** carrega segredo: diz se a credencial existe, quando foi
testada e se a integracao esta ligada. Quem precisa do valor e o provedor, e
ele recebe direto da cifra.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from emprestimo.application.chave_pix import ChavePixCredora
from emprestimo.application.comprovante_pagamento import ComprovantePagamentoResultado
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


class ChavePixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: str = Field(min_length=3, max_length=20)
    valor: str = Field(min_length=3, max_length=140)
    favorecido: str = Field(min_length=2, max_length=140)


class ChavePixResponse(BaseModel):
    """Chave que o agente oferece ao devedor no caminho sem taxa."""

    tipo: str | None
    valor: str | None
    favorecido: str | None
    configurada: bool

    @classmethod
    def de(cls, chave: ChavePixCredora) -> ChavePixResponse:
        return cls(
            tipo=chave.tipo.value if chave.tipo else None,
            valor=chave.valor,
            favorecido=chave.favorecido,
            configurada=chave.configurada,
        )


class ComprovanteResponse(BaseModel):
    """Estado do comprovante. **Nunca carrega o binario.**"""

    id: uuid.UUID
    emprestimo_id: uuid.UUID
    devedor_id: uuid.UUID
    sha256: str
    tipo_midia: str
    tamanho: int
    estado: str
    valor_extraido: Decimal | None
    valor_informado: Decimal | None
    divergente: bool
    recebido_em: datetime
    duplicado: bool

    @classmethod
    def de(cls, resultado: ComprovantePagamentoResultado) -> ComprovanteResponse:
        return cls(
            id=resultado.id,
            emprestimo_id=resultado.emprestimo_id,
            devedor_id=resultado.devedor_id,
            sha256=resultado.sha256,
            tipo_midia=resultado.tipo_midia,
            tamanho=resultado.tamanho,
            estado=resultado.estado.value,
            valor_extraido=resultado.valor_extraido,
            valor_informado=resultado.valor_informado,
            divergente=resultado.divergente,
            recebido_em=resultado.recebido_em,
            duplicado=resultado.duplicado,
        )


class ComprovanteCreateRequest(BaseModel):
    """O binario chega em base64: o canal de origem (WhatsApp) ja o entrega assim."""

    model_config = ConfigDict(extra="forbid")

    conteudo_base64: str = Field(min_length=8, max_length=8 * 1024 * 1024)
    tipo_midia: str = Field(min_length=5, max_length=40)
    valor_extraido: Decimal | None = None
    valor_informado: Decimal | None = None
