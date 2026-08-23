"""Pagamento (IMP-150, EPIC-005, IMP-332)."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from emprestimo.domain.common.errors import ViolacaoInvarianteError

__all__ = ["Pagamento", "PagamentoState"]


class PagamentoState(Enum):
    """Estados do registro financeiro de pagamento."""

    RECEBIDO = "recebido"
    PROCESSADO = "processado"
    CONFIRMADO = "confirmado"
    ESTORNADO = "estornado"


@dataclass(frozen=True)
class Pagamento:
    """Registro do resultado de um pagamento processado pelo Motor."""

    emprestimo_id: uuid.UUID
    valor_recebido: Decimal
    recebido_em: datetime
    valor_juros: Decimal
    valor_amortizacao: Decimal
    valor_encargos: Decimal = Decimal("0.00")
    valor_devolvido: Decimal = Decimal("0.00")
    valor_estornado: Decimal = Decimal("0.00")
    chave_idempotencia: str | None = None
    distribuicao: dict[str, object] = field(default_factory=dict)
    usuario_id: uuid.UUID | None = None
    estado: PagamentoState = PagamentoState.PROCESSADO
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime | None = None

    def __post_init__(self) -> None:
        _validar_uuid("emprestimo_id", self.emprestimo_id)
        _validar_uuid("id", self.id)
        if self.usuario_id is not None:
            _validar_uuid("usuario_id", self.usuario_id)
        if not isinstance(self.recebido_em, datetime):
            raise ViolacaoInvarianteError("EPIC-005", "recebido_em deve ser datetime")
        for campo in (
            "valor_recebido",
            "valor_juros",
            "valor_amortizacao",
            "valor_encargos",
            "valor_devolvido",
            "valor_estornado",
        ):
            _validar_decimal(campo, getattr(self, campo))
        if self.valor_recebido <= Decimal("0.00"):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "valor_recebido deve ser maior que zero",
            )
        for campo in (
            "valor_juros",
            "valor_amortizacao",
            "valor_encargos",
            "valor_devolvido",
            "valor_estornado",
        ):
            if getattr(self, campo) < Decimal("0.00"):
                raise ViolacaoInvarianteError(
                    "EPIC-005",
                    f"{campo} nao pode ser negativo",
                )
        total_destinado = self.valor_distribuido + self.valor_devolvido
        if total_destinado != self.valor_recebido:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "distribuicao e devolucao devem ser iguais ao valor recebido",
            )
        if self.valor_estornado > self.valor_devolvido:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "valor estornado nao pode exceder valor devolvido",
            )
        if not isinstance(self.estado, PagamentoState):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                f"estado deve ser PagamentoState, recebido {self.estado!r}",
            )
        object.__setattr__(self, "distribuicao", copy.deepcopy(self.distribuicao))

    @property
    def valor_distribuido(self) -> Decimal:
        return self.valor_juros + self.valor_amortizacao + self.valor_encargos

    @property
    def valor_sobra(self) -> Decimal:
        """Valor destinado a devolucao que ainda nao teve estorno lancado."""

        return self.valor_devolvido - self.valor_estornado

    @property
    def reconciliado(self) -> bool:
        """Indica que toda a devolucao reconhecida ja foi registrada."""

        return self.valor_sobra == Decimal("0.00")

    def confirmar(self) -> Pagamento:
        """Retorna copia confirmada apos atualizacao do Emprestimo pelo Motor."""

        if self.estado is PagamentoState.ESTORNADO:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "pagamento estornado nao pode ser confirmado",
            )
        return self._com_estado(PagamentoState.CONFIRMADO)

    def estornar(self, valor: Decimal) -> Pagamento:
        """Registra estorno parcial da devolucao sem apagar o pagamento bruto."""

        _validar_decimal("valor", valor)
        if valor <= Decimal("0.00"):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "valor do estorno deve ser maior que zero",
            )
        if valor > self.valor_sobra:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "valor do estorno nao pode exceder a sobra do pagamento",
            )
        return self._com_estorno(self.valor_estornado + valor)

    def _com_estorno(self, valor_estornado: Decimal) -> Pagamento:
        return self._copia(estado=self.estado, valor_estornado=valor_estornado)

    def _com_estado(self, estado: PagamentoState) -> Pagamento:
        return self._copia(estado=estado, valor_estornado=self.valor_estornado)

    def _copia(self, *, estado: PagamentoState, valor_estornado: Decimal) -> Pagamento:
        return Pagamento(
            id=self.id,
            emprestimo_id=self.emprestimo_id,
            valor_recebido=self.valor_recebido,
            recebido_em=self.recebido_em,
            valor_juros=self.valor_juros,
            valor_amortizacao=self.valor_amortizacao,
            valor_encargos=self.valor_encargos,
            valor_devolvido=self.valor_devolvido,
            valor_estornado=valor_estornado,
            chave_idempotencia=self.chave_idempotencia,
            distribuicao=self.distribuicao,
            usuario_id=self.usuario_id,
            estado=estado,
            criado_em=self.criado_em,
        )


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
