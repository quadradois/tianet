"""Pagamento (IMP-150, EPIC-005)."""

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
    chave_idempotencia: str | None = None
    parcelas_liquidadas: tuple[uuid.UUID, ...] = ()
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
        ):
            _validar_decimal(campo, getattr(self, campo))
        if self.valor_recebido <= Decimal("0.00"):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "valor_recebido deve ser maior que zero",
            )
        for campo in ("valor_juros", "valor_amortizacao", "valor_encargos"):
            if getattr(self, campo) < Decimal("0.00"):
                raise ViolacaoInvarianteError(
                    "EPIC-005",
                    f"{campo} nao pode ser negativo",
                )
        total_distribuido = self.valor_juros + self.valor_amortizacao + self.valor_encargos
        if total_distribuido > self.valor_recebido:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "distribuicao do pagamento nao pode exceder valor recebido",
            )
        if not isinstance(self.estado, PagamentoState):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                f"estado deve ser PagamentoState, recebido {self.estado!r}",
            )
        object.__setattr__(self, "parcelas_liquidadas", tuple(self.parcelas_liquidadas))
        object.__setattr__(self, "distribuicao", copy.deepcopy(self.distribuicao))

    @property
    def valor_distribuido(self) -> Decimal:
        return self.valor_juros + self.valor_amortizacao + self.valor_encargos

    def confirmar(self) -> Pagamento:
        """Retorna copia confirmada apos atualizacao do Emprestimo pelo Motor."""

        if self.estado is PagamentoState.ESTORNADO:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "pagamento estornado nao pode ser confirmado",
            )
        return self._com_estado(PagamentoState.CONFIRMADO)

    def estornar(self) -> Pagamento:
        """Retorna copia estornada preservando o registro original."""

        if self.estado is PagamentoState.ESTORNADO:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "pagamento ja esta estornado",
            )
        return self._com_estado(PagamentoState.ESTORNADO)

    def _com_estado(self, estado: PagamentoState) -> Pagamento:
        return Pagamento(
            id=self.id,
            emprestimo_id=self.emprestimo_id,
            valor_recebido=self.valor_recebido,
            recebido_em=self.recebido_em,
            valor_juros=self.valor_juros,
            valor_amortizacao=self.valor_amortizacao,
            valor_encargos=self.valor_encargos,
            chave_idempotencia=self.chave_idempotencia,
            parcelas_liquidadas=self.parcelas_liquidadas,
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
