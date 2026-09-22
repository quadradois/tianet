"""Configuracao do recebimento por Pix (Mercado Pago) — IMP-388, PLAN-045.

A integracao e **opcional e nasce desligada**. O provedor cobra por
recebimento e a Credora ja tem o caminho sem taxa: o devedor paga no Pix dela
e o agente registra quando ela avisa. Ligar e decisao economica dela, tomada
no painel — por isso o desligado e um estado de primeira classe, e nao o
efeito colateral de uma credencial ausente.

Segredos entram e saem **cifrados**: este objeto nunca ve o valor claro, e
`repr` nao expoe nem o cifrado.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from emprestimo.domain.common.errors import ViolacaoInvarianteError

__all__ = ["ConfiguracaoMercadoPago"]


@dataclass
class ConfiguracaoMercadoPago:
    """Interruptor e credenciais do provedor de recebimento, por Tenant."""

    tenant_id: uuid.UUID
    criado_em: datetime
    atualizado_em: datetime
    habilitado: bool = False
    access_token_cifrado: bytes | None = field(default=None, repr=False)
    webhook_secret_cifrado: bytes | None = field(default=None, repr=False)
    testado_em: datetime | None = None
    atualizado_por: uuid.UUID | None = None

    @classmethod
    def nova(
        cls, *, tenant_id: uuid.UUID, agora: datetime | None = None
    ) -> ConfiguracaoMercadoPago:
        instante = agora or datetime.now(UTC)
        return cls(tenant_id=tenant_id, criado_em=instante, atualizado_em=instante)

    @property
    def credenciais_completas(self) -> bool:
        return self.access_token_cifrado is not None and self.webhook_secret_cifrado is not None

    def definir_credenciais(
        self,
        *,
        access_token_cifrado: bytes | None,
        webhook_secret_cifrado: bytes | None,
        usuario_id: uuid.UUID,
        agora: datetime | None = None,
    ) -> None:
        """Grava as credenciais e **invalida o teste anterior**.

        Credencial nova nao herda o aval da antiga: manter `testado_em` aqui
        permitiria ligar a integracao com um segredo que nunca foi exercitado.
        """
        self.access_token_cifrado = access_token_cifrado
        self.webhook_secret_cifrado = webhook_secret_cifrado
        self.testado_em = None
        self._marcar(usuario_id, agora)

    def registrar_teste_bem_sucedido(self, *, agora: datetime | None = None) -> None:
        self.testado_em = agora or datetime.now(UTC)

    def habilitar(self, *, usuario_id: uuid.UUID, agora: datetime | None = None) -> None:
        if not self.credenciais_completas:
            raise ViolacaoInvarianteError(
                "INV-001",
                "habilitar exige access_token e webhook_secret: sem os dois o "
                "recebimento nasce quebrado e a notificacao nao e verificavel",
            )
        if self.testado_em is None:
            raise ViolacaoInvarianteError(
                "INV-002",
                "habilitar exige teste bem-sucedido: credencial gravada nao "
                "prova credencial valida",
            )
        self.habilitado = True
        self._marcar(usuario_id, agora)

    def desabilitar(self, *, usuario_id: uuid.UUID, agora: datetime | None = None) -> None:
        """Desligar nao e esquecer: credenciais e teste ficam para religar.

        Tambem nao invalida `CobrancaPix` pendente — isso e regra da aplicacao
        (PLAN-045 §3.12), e dinheiro em transito nunca se perde por mudanca de
        configuracao.
        """
        self.habilitado = False
        self._marcar(usuario_id, agora)

    def _marcar(self, usuario_id: uuid.UUID, agora: datetime | None) -> None:
        self.atualizado_por = usuario_id
        self.atualizado_em = agora or datetime.now(UTC)
