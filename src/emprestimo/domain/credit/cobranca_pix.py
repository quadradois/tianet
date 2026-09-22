"""Aggregate CobrancaPix (PLAN-045, ADR-021).

Um Pix dinamico do acerto apurado. O valor e livre — o devedor diz quanto quer
pagar —, mas nasce contido pelo que o Motor apurou no momento: no minimo o juro
do periodo, no maximo a quitacao. O Aggregate nao calcula nada: recebe os dois
limites ja apurados e se recusa a existir fora deles.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from emprestimo.domain.common.errors import ViolacaoInvarianteError

__all__ = [
    "VALIDADE_PADRAO",
    "CobrancaPix",
    "CobrancaPixState",
    "OrigemCobrancaPix",
]

VALIDADE_PADRAO = timedelta(minutes=60)


class CobrancaPixState(StrEnum):
    """Ciclo do Pix. Os tres ultimos sao terminais."""

    PENDENTE = "pendente"
    PAGO = "pago"
    EXPIRADO = "expirado"
    CANCELADO = "cancelado"


class OrigemCobrancaPix(StrEnum):
    """Quem pediu o Pix — a Credora pela tela ou o devedor na conversa."""

    TELA = "tela"
    COPILOT_DEVEDOR = "copilot_devedor"


_TERMINAIS = frozenset(
    {CobrancaPixState.PAGO, CobrancaPixState.EXPIRADO, CobrancaPixState.CANCELADO}
)


@dataclass
class CobrancaPix:
    """Pix do acerto, correlacionado ao provedor por `external_reference`."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    emprestimo_id: uuid.UUID
    devedor_id: uuid.UUID
    valor: Decimal
    expira_em: datetime
    origem: OrigemCobrancaPix
    criado_por: uuid.UUID
    criado_em: datetime
    estado: CobrancaPixState = CobrancaPixState.PENDENTE
    mp_payment_id: str | None = None
    copia_cola: str | None = None
    qr_base64: str | None = field(default=None, repr=False)
    valor_recebido: Decimal | None = None
    divergente: bool = False

    @property
    def external_reference(self) -> str:
        """Identificador nosso que viaja ate o provedor e volta (ADR-021 §4)."""
        return str(self.id)

    @classmethod
    def criar(
        cls,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        emprestimo_id: uuid.UUID,
        devedor_id: uuid.UUID,
        valor: Decimal,
        juro_periodo: Decimal,
        quitacao: Decimal,
        origem: OrigemCobrancaPix,
        criado_por: uuid.UUID,
        agora: datetime | None = None,
        validade: timedelta = VALIDADE_PADRAO,
    ) -> CobrancaPix:
        instante = agora or datetime.now(UTC)
        if not juro_periodo <= valor <= quitacao:
            raise ViolacaoInvarianteError(
                "INV-001",
                "valor do Pix fora do intervalo apurado pelo Motor "
                f"(minimo {juro_periodo}, maximo {quitacao})",
            )
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            emprestimo_id=emprestimo_id,
            devedor_id=devedor_id,
            valor=valor,
            expira_em=instante + validade,
            origem=origem,
            criado_por=criado_por,
            criado_em=instante,
        )

    def registrar_no_provedor(self, *, mp_payment_id: str, copia_cola: str, qr_base64: str) -> None:
        """Anota o que o provedor devolveu na criacao, antes de qualquer pagamento."""
        self._exigir_pendente()
        self.mp_payment_id = mp_payment_id
        self.copia_cola = copia_cola
        self.qr_base64 = qr_base64

    def pagar(self, *, mp_payment_id: str, valor_recebido: Decimal) -> None:
        """Confirma o pagamento pelo valor que de fato entrou.

        Valor diferente do pedido nao e recusado — o dinheiro ja entrou na
        conta do Credor. Fica marcado `divergente` para a Credora conferir.
        """
        self._exigir_pendente()
        self.estado = CobrancaPixState.PAGO
        self.mp_payment_id = mp_payment_id
        self.valor_recebido = valor_recebido
        self.divergente = valor_recebido != self.valor

    def expirar(self, *, agora: datetime | None = None) -> None:
        self._exigir_pendente()
        instante = agora or datetime.now(UTC)
        if instante <= self.expira_em:
            raise ViolacaoInvarianteError(
                "INV-003", "Pix ainda dentro da validade nao pode ser expirado"
            )
        self.estado = CobrancaPixState.EXPIRADO

    def cancelar(self) -> None:
        self._exigir_pendente()
        self.estado = CobrancaPixState.CANCELADO

    def _exigir_pendente(self) -> None:
        if self.estado in _TERMINAIS:
            raise ViolacaoInvarianteError(
                "INV-002", f"CobrancaPix em estado terminal ({self.estado.value}) nao transiciona"
            )
