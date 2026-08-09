"""Saida logica de Proposta aprovada para Contratos futuro (IMP-109)."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

ParametroAprovado = object


@dataclass(frozen=True)
class PropostaAprovadaLogica:
    """Contrato logico de integracao, sem criar entidade financeira."""

    proposta_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    parametros_aprovados: Mapping[str, ParametroAprovado]
    aprovada_por_usuario_id: uuid.UUID
    aprovada_em: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "parametros_aprovados",
            _congelar_mapping(self.parametros_aprovados),
        )

    def to_dict(self) -> dict[str, object]:
        """Serializa a saida logica para consumo futuro da camada Contratos."""

        return {
            "proposta_id": str(self.proposta_id),
            "tenant_id": str(self.tenant_id),
            "carteira_id": str(self.carteira_id),
            "devedor_id": str(self.devedor_id),
            "parametros_aprovados": _descongelar(self.parametros_aprovados),
            "aprovada_por_usuario_id": str(self.aprovada_por_usuario_id),
            "aprovada_em": self.aprovada_em.isoformat(),
        }


def _congelar_mapping(
    parametros: Mapping[str, ParametroAprovado],
) -> Mapping[str, ParametroAprovado]:
    return MappingProxyType({chave: _congelar(valor) for chave, valor in parametros.items()})


def _congelar(valor: ParametroAprovado) -> ParametroAprovado:
    if isinstance(valor, Mapping):
        return _congelar_mapping(valor)
    if isinstance(valor, tuple):
        return tuple(_congelar(item) for item in valor)
    if isinstance(valor, list):
        return tuple(_congelar(item) for item in valor)
    if isinstance(valor, set):
        return frozenset(_congelar(item) for item in valor)
    return copy.deepcopy(valor)


def _descongelar(valor: ParametroAprovado) -> ParametroAprovado:
    if isinstance(valor, Mapping):
        return {chave: _descongelar(item) for chave, item in valor.items()}
    if isinstance(valor, Sequence) and not isinstance(valor, str):
        return [_descongelar(item) for item in valor]
    if isinstance(valor, frozenset):
        return [_descongelar(item) for item in valor]
    return copy.deepcopy(valor)
