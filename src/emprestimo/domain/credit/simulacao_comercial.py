"""Simulacao Comercial (IMP-106, EPIC-003).

Registro nao vinculante de parametros comerciais para uma Carteira e um
Devedor. Nao cria obrigacao financeira nem executa calculo definitivo.
"""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from emprestimo.domain.common.errors import ViolacaoInvarianteError


@dataclass
class SimulacaoComercial:
    """Registro comercial nao vinculante de uma simulacao de credito."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    criada_por_usuario_id: uuid.UUID
    _parametros: dict[str, object]
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        _validar_uuid("devedor_id", self.devedor_id)
        _validar_uuid("criada_por_usuario_id", self.criada_por_usuario_id)
        if not isinstance(self.id, uuid.UUID):
            raise ViolacaoInvarianteError(
                "EPIC-003",
                f"id deve ser uuid.UUID, recebido {self.id!r}",
            )
        self._parametros = _copiar_parametros(self._parametros)

    @classmethod
    def criar(
        cls,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        criada_por_usuario_id: uuid.UUID,
        parametros: Mapping[str, object],
    ) -> SimulacaoComercial:
        """Cria uma simulacao comercial sem gerar obrigacao financeira."""

        return cls(
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            criada_por_usuario_id=criada_por_usuario_id,
            _parametros=_copiar_parametros(parametros),
        )

    @classmethod
    def restaurar(
        cls,
        *,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        criada_por_usuario_id: uuid.UUID,
        parametros: Mapping[str, object],
        criado_em: datetime,
    ) -> SimulacaoComercial:
        """Reconstitui uma simulacao comercial a partir da persistencia."""

        return cls(
            id=id,
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            criada_por_usuario_id=criada_por_usuario_id,
            _parametros=_copiar_parametros(parametros),
            criado_em=criado_em,
        )

    @property
    def parametros(self) -> dict[str, object]:
        """Parametros comerciais informados, protegidos contra mutacao externa."""

        return copy.deepcopy(self._parametros)


def _validar_uuid(campo: str, valor: object) -> None:
    if not isinstance(valor, uuid.UUID):
        raise ViolacaoInvarianteError(
            "EPIC-003",
            f"{campo} deve ser uuid.UUID, recebido {valor!r}",
        )


def _copiar_parametros(parametros: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(parametros, Mapping):
        raise ViolacaoInvarianteError(
            "EPIC-003",
            f"parametros deve ser mapeavel, recebido {parametros!r}",
        )
    if not parametros:
        raise ViolacaoInvarianteError(
            "EPIC-003",
            "parametros comerciais nao podem ser vazios",
        )
    return copy.deepcopy(dict(parametros))
