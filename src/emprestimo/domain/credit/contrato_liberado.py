"""Saida logica de Contrato liberado para Motor Financeiro futuro."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

ParametroContratual = object


@dataclass(frozen=True)
class ContratoLiberadoLogico:
    """Contrato imutavel de integracao, sem criar operacao financeira."""

    contrato_id: uuid.UUID
    proposta_comercial_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    parametros_contratados: Mapping[str, ParametroContratual]
    liberado_por_usuario_id: uuid.UUID
    liberado_em: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "parametros_contratados",
            _congelar_mapping(self.parametros_contratados),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "contrato_id": str(self.contrato_id),
            "proposta_comercial_id": str(self.proposta_comercial_id),
            "tenant_id": str(self.tenant_id),
            "carteira_id": str(self.carteira_id),
            "devedor_id": str(self.devedor_id),
            "parametros_contratados": _descongelar(self.parametros_contratados),
            "liberado_por_usuario_id": str(self.liberado_por_usuario_id),
            "liberado_em": self.liberado_em.isoformat(),
        }


def _congelar_mapping(
    parametros: Mapping[str, ParametroContratual],
) -> Mapping[str, ParametroContratual]:
    return MappingProxyType({chave: _congelar(valor) for chave, valor in parametros.items()})


def _congelar(valor: ParametroContratual) -> ParametroContratual:
    if isinstance(valor, Mapping):
        return _congelar_mapping(valor)
    if isinstance(valor, tuple):
        return tuple(_congelar(item) for item in valor)
    if isinstance(valor, list):
        return tuple(_congelar(item) for item in valor)
    if isinstance(valor, set):
        return frozenset(_congelar(item) for item in valor)
    return copy.deepcopy(valor)


def _descongelar(valor: ParametroContratual) -> ParametroContratual:
    if isinstance(valor, Mapping):
        return {chave: _descongelar(item) for chave, item in valor.items()}
    if isinstance(valor, Sequence) and not isinstance(valor, str):
        return [_descongelar(item) for item in valor]
    if isinstance(valor, frozenset):
        return [_descongelar(item) for item in valor]
    return copy.deepcopy(valor)
