"""Eventos financeiros do Motor (IMP-154, EPIC-005)."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.emprestimo import EmprestimoState

__all__ = [
    "EmprestimoQuitado",
    "EmprestimoRenegociado",
    "EventoFinanceiro",
    "PagamentoRegistrado",
]


@dataclass(frozen=True)
class EventoFinanceiro:
    """Evento base para trilha financeira auditavel."""

    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    usuario_id: uuid.UUID
    tipo: str
    ocorrido_em: datetime
    memoria_calculo_id: uuid.UUID | None = None
    pagamento_id: uuid.UUID | None = None
    estado_anterior: EmprestimoState | None = None
    estado_posterior: EmprestimoState | None = None
    valor: Decimal | None = None
    detalhes: Mapping[str, object] | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        for campo in ("emprestimo_id", "tenant_id", "carteira_id", "devedor_id", "usuario_id"):
            _validar_uuid(campo, getattr(self, campo))
        _validar_uuid("id", self.id)
        if self.memoria_calculo_id is not None:
            _validar_uuid("memoria_calculo_id", self.memoria_calculo_id)
        if self.pagamento_id is not None:
            _validar_uuid("pagamento_id", self.pagamento_id)
        if not self.tipo:
            raise ViolacaoInvarianteError("EPIC-005", "tipo do evento financeiro nao pode vazio")
        if not isinstance(self.ocorrido_em, datetime):
            raise ViolacaoInvarianteError("EPIC-005", "ocorrido_em deve ser datetime")
        if self.valor is not None and not isinstance(self.valor, Decimal):
            raise ViolacaoInvarianteError("EPIC-005", "valor do evento deve ser Decimal")
        if self.estado_anterior is not None and not isinstance(
            self.estado_anterior,
            EmprestimoState,
        ):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "estado_anterior deve ser EmprestimoState",
            )
        if self.estado_posterior is not None and not isinstance(
            self.estado_posterior,
            EmprestimoState,
        ):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "estado_posterior deve ser EmprestimoState",
            )
        if self.detalhes is not None:
            object.__setattr__(self, "detalhes", copy.deepcopy(dict(self.detalhes)))

    @property
    def nome_evento(self) -> str:
        return self.__class__.__name__

    def to_audit_dict(self) -> dict[str, object]:
        return {
            "evento": self.nome_evento,
            "tipo": self.tipo,
            "id": str(self.id),
            "emprestimo_id": str(self.emprestimo_id),
            "tenant_id": str(self.tenant_id),
            "carteira_id": str(self.carteira_id),
            "devedor_id": str(self.devedor_id),
            "usuario_id": str(self.usuario_id),
            "memoria_calculo_id": (
                str(self.memoria_calculo_id) if self.memoria_calculo_id else None
            ),
            "pagamento_id": str(self.pagamento_id) if self.pagamento_id else None,
            "estado_anterior": self.estado_anterior.value if self.estado_anterior else None,
            "estado_posterior": self.estado_posterior.value if self.estado_posterior else None,
            "valor": str(self.valor) if self.valor is not None else None,
            "detalhes": dict(self.detalhes) if self.detalhes is not None else None,
            "ocorrido_em": self.ocorrido_em.isoformat(),
        }


@dataclass(frozen=True)
class PagamentoRegistrado(EventoFinanceiro):
    """Evento emitido apos o Motor distribuir um pagamento."""


@dataclass(frozen=True)
class EmprestimoQuitado(EventoFinanceiro):
    """Evento emitido quando o Emprestimo e quitado."""


@dataclass(frozen=True)
class EmprestimoRenegociado(EventoFinanceiro):
    """Evento emitido quando parametros financeiros sao renegociados."""


def _validar_uuid(campo: str, valor: object) -> None:
    if not isinstance(valor, uuid.UUID):
        raise ViolacaoInvarianteError(
            "EPIC-005",
            f"{campo} deve ser uuid.UUID, recebido {valor!r}",
        )
