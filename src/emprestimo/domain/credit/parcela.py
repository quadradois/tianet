"""Parcela (IMP-150, EPIC-005)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.financeiro import PeriodoFinanceiro

__all__ = ["Parcela", "ParcelaState"]


class ParcelaState(Enum):
    """Estados da obrigacao financeira prevista."""

    PREVISTA = "prevista"
    VENCIDA = "vencida"
    PARCIALMENTE_LIQUIDADA = "parcialmente_liquidada"
    LIQUIDADA = "liquidada"
    CANCELADA = "cancelada"


@dataclass
class Parcela:
    """Obrigacao financeira prevista para um Emprestimo."""

    emprestimo_id: uuid.UUID
    numero: int
    vencimento: date
    valor_previsto: Decimal
    principal: Decimal = Decimal("0.00")
    juros: Decimal = Decimal("0.00")
    encargos: Decimal = Decimal("0.00")
    valor_liquidado: Decimal = Decimal("0.00")
    periodo: PeriodoFinanceiro | None = None
    estado: ParcelaState = ParcelaState.PREVISTA
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criada_em: datetime | None = None
    atualizada_em: datetime | None = None

    def __post_init__(self) -> None:
        _validar_uuid("emprestimo_id", self.emprestimo_id)
        _validar_uuid("id", self.id)
        if self.numero <= 0:
            raise ViolacaoInvarianteError("EPIC-005", "numero da parcela deve ser positivo")
        if not isinstance(self.vencimento, date):
            raise ViolacaoInvarianteError("EPIC-005", "vencimento deve ser date")
        if self.periodo is not None and not isinstance(self.periodo, PeriodoFinanceiro):
            raise ViolacaoInvarianteError("EPIC-005", "periodo deve ser PeriodoFinanceiro")
        for campo in ("valor_previsto", "principal", "juros", "encargos", "valor_liquidado"):
            _validar_decimal(campo, getattr(self, campo))
        if self.valor_previsto <= Decimal("0.00"):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "valor_previsto da parcela deve ser maior que zero",
            )
        if self.valor_liquidado < Decimal("0.00"):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "valor_liquidado da parcela nao pode ser negativo",
            )
        if not isinstance(self.estado, ParcelaState):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                f"estado deve ser ParcelaState, recebido {self.estado!r}",
            )

    @property
    def saldo_pendente(self) -> Decimal:
        """Valor ainda nao liquidado, sem acrescimos calculados."""

        saldo = self.valor_previsto - self.valor_liquidado
        if saldo < Decimal("0.00"):
            return Decimal("0.00")
        return saldo

    def registrar_liquidacao(
        self,
        *,
        valor: Decimal,
        liquidado_em: datetime,
    ) -> None:
        """Registra liquidacao determinada pelo Motor Financeiro."""

        _validar_decimal("valor", valor)
        if valor <= Decimal("0.00"):
            raise ViolacaoInvarianteError("EPIC-005", "valor de liquidacao deve ser positivo")
        if self.estado in {ParcelaState.LIQUIDADA, ParcelaState.CANCELADA}:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                f"parcela em {self.estado.value} nao pode receber liquidacao",
            )
        novo_total = self.valor_liquidado + valor
        if novo_total >= self.valor_previsto:
            self.valor_liquidado = self.valor_previsto
            self.estado = ParcelaState.LIQUIDADA
        else:
            self.valor_liquidado = novo_total
            self.estado = ParcelaState.PARCIALMENTE_LIQUIDADA
        self.atualizada_em = liquidado_em

    def cancelar(self, *, cancelada_em: datetime) -> None:
        """Cancela a obrigacao prevista preservando seu historico."""

        if self.estado is ParcelaState.LIQUIDADA:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "parcela liquidada nao pode ser cancelada",
            )
        self.estado = ParcelaState.CANCELADA
        self.atualizada_em = cancelada_em


def _validar_uuid(campo: str, valor: object) -> None:
    if not isinstance(valor, uuid.UUID):
        raise ViolacaoInvarianteError(
            "EPIC-005",
            f"{campo} deve ser uuid.UUID, recebido {valor!r}",
        )


def _validar_decimal(campo: str, valor: object) -> None:
    if not isinstance(valor, Decimal):
        raise ViolacaoInvarianteError(
            "EPIC-005",
            f"{campo} deve ser Decimal, recebido {valor!r}",
        )
