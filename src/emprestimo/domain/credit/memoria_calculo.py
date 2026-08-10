"""Memoria de Calculo (IMP-153, EPIC-005)."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from emprestimo.domain.common.errors import ViolacaoInvarianteError

__all__ = ["MemoriaCalculo", "PassoCalculo"]


@dataclass(frozen=True)
class PassoCalculo:
    """Passo reproduzivel de uma operacao financeira."""

    nome: str
    entradas: Mapping[str, object] = field(default_factory=dict)
    saidas: Mapping[str, object] = field(default_factory=dict)
    arredondamento: str | None = None

    def __post_init__(self) -> None:
        if not self.nome:
            raise ViolacaoInvarianteError("EPIC-005", "nome do passo nao pode ser vazio")
        _validar_mapping("entradas do passo", self.entradas)
        _validar_mapping("saidas do passo", self.saidas)
        object.__setattr__(self, "entradas", copy.deepcopy(dict(self.entradas)))
        object.__setattr__(self, "saidas", copy.deepcopy(dict(self.saidas)))


@dataclass(frozen=True)
class MemoriaCalculo:
    """Registro imutavel e auditavel de uma saida financeira relevante."""

    tipo: str
    entradas: Mapping[str, object]
    regra: Mapping[str, object]
    periodos: Sequence[Mapping[str, object]] = ()
    passos: Sequence[PassoCalculo] = ()
    arredondamentos: Sequence[str] = ()
    resultados: Mapping[str, object] = field(default_factory=dict)
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.tipo:
            raise ViolacaoInvarianteError("EPIC-005", "tipo da memoria nao pode ser vazio")
        _validar_mapping("entradas da memoria", self.entradas)
        _validar_mapping("regra da memoria", self.regra)
        _validar_mapping("resultados da memoria", self.resultados)
        if not isinstance(self.id, uuid.UUID):
            raise ViolacaoInvarianteError("EPIC-005", "id da memoria deve ser uuid.UUID")
        if not isinstance(self.criado_em, datetime):
            raise ViolacaoInvarianteError("EPIC-005", "criado_em deve ser datetime")
        periodos = tuple(copy.deepcopy(dict(periodo)) for periodo in self.periodos)
        passos = tuple(self._normalizar_passo(passo) for passo in self.passos)
        arredondamentos = tuple(str(item) for item in self.arredondamentos)
        object.__setattr__(self, "entradas", copy.deepcopy(dict(self.entradas)))
        object.__setattr__(self, "regra", copy.deepcopy(dict(self.regra)))
        object.__setattr__(self, "periodos", periodos)
        object.__setattr__(self, "passos", passos)
        object.__setattr__(self, "arredondamentos", arredondamentos)
        object.__setattr__(self, "resultados", copy.deepcopy(dict(self.resultados)))

    @staticmethod
    def _normalizar_passo(passo: PassoCalculo) -> PassoCalculo:
        if not isinstance(passo, PassoCalculo):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                f"passos devem ser PassoCalculo, recebido {passo!r}",
            )
        return passo


def _validar_mapping(nome: str, valor: object) -> None:
    if not isinstance(valor, Mapping):
        raise ViolacaoInvarianteError("EPIC-005", f"{nome} deve ser mapeavel")
