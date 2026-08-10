"""Value Objects financeiros (IMP-151, EPIC-005)."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

from emprestimo.domain.common.errors import ViolacaoInvarianteError

__all__ = [
    "PeriodoFinanceiro",
    "RegraCalculo",
    "TaxaJuros",
    "TipoRegraCalculo",
    "ValorQuitacao",
]


class TipoRegraCalculo(Enum):
    """Tipos de regra reconhecidos pelo Motor Financeiro."""

    JUROS_SIMPLES_PERIODO_REAL = "juros_simples_periodo_real"
    PRAZO_FIXO = "prazo_fixo"
    LIVRE = "livre"


@dataclass(frozen=True)
class PeriodoFinanceiro:
    """Intervalo real usado como entrada de calculo financeiro."""

    data_inicio: date
    data_fim: date

    def __post_init__(self) -> None:
        if not isinstance(self.data_inicio, date):
            raise ViolacaoInvarianteError("EPIC-005", "data_inicio deve ser date")
        if not isinstance(self.data_fim, date):
            raise ViolacaoInvarianteError("EPIC-005", "data_fim deve ser date")
        if self.data_fim <= self.data_inicio:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "data_fim deve ser posterior a data_inicio",
            )

    @property
    def dias(self) -> int:
        """Quantidade real de dias no intervalo."""

        return (self.data_fim - self.data_inicio).days


@dataclass(frozen=True)
class TaxaJuros:
    """Taxa de juros representada com Decimal e periodicidade explicita."""

    valor: Decimal
    periodicidade: str

    def __post_init__(self) -> None:
        _validar_decimal("valor", self.valor)
        if self.valor < Decimal("0.00"):
            raise ViolacaoInvarianteError("EPIC-005", "taxa de juros nao pode ser negativa")
        if not self.periodicidade:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "periodicidade da taxa de juros nao pode ser vazia",
            )

    @classmethod
    def de_percentual(
        cls,
        *,
        percentual: Decimal,
        periodicidade: str,
    ) -> TaxaJuros:
        """Cria taxa a partir de percentual informado como Decimal."""

        _validar_decimal("percentual", percentual)
        return cls(valor=percentual / Decimal("100"), periodicidade=periodicidade)


@dataclass(frozen=True)
class RegraCalculo:
    """Identificacao rastreavel da regra financeira aplicavel."""

    tipo: TipoRegraCalculo
    parametros: Mapping[str, object] = field(default_factory=dict)
    versao: str = "1.0.0"

    def __post_init__(self) -> None:
        if not isinstance(self.tipo, TipoRegraCalculo):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                f"tipo deve ser TipoRegraCalculo, recebido {self.tipo!r}",
            )
        if not isinstance(self.parametros, Mapping):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "parametros da regra devem ser mapeaveis",
            )
        if not self.versao:
            raise ViolacaoInvarianteError("EPIC-005", "versao da regra nao pode ser vazia")
        object.__setattr__(self, "parametros", copy.deepcopy(dict(self.parametros)))


@dataclass(frozen=True)
class ValorQuitacao:
    """Valor necessario para liquidar a operacao em data de referencia."""

    valor_total: Decimal
    moeda: str
    data_referencia: date
    componentes: Mapping[str, Decimal] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validar_decimal("valor_total", self.valor_total)
        if self.valor_total < Decimal("0.00"):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "valor_total de quitacao nao pode ser negativo",
            )
        if not self.moeda:
            raise ViolacaoInvarianteError("EPIC-005", "moeda nao pode ser vazia")
        if not isinstance(self.data_referencia, date):
            raise ViolacaoInvarianteError("EPIC-005", "data_referencia deve ser date")
        if not isinstance(self.componentes, Mapping):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "componentes de quitacao devem ser mapeaveis",
            )
        componentes = dict(self.componentes)
        for nome, valor in componentes.items():
            _validar_decimal(nome, valor)
            if valor < Decimal("0.00"):
                raise ViolacaoInvarianteError(
                    "EPIC-005",
                    f"componente {nome} nao pode ser negativo",
                )
        if sum(componentes.values(), Decimal("0.00")) != self.valor_total:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "soma dos componentes deve igualar valor_total",
            )
        object.__setattr__(self, "componentes", copy.deepcopy(componentes))


def _validar_decimal(campo: str, valor: object) -> None:
    if not isinstance(valor, Decimal):
        raise ViolacaoInvarianteError(
            "EPIC-005",
            f"{campo} deve ser Decimal, recebido {valor!r}",
        )
