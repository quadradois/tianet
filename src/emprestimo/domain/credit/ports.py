"""Ports do Credit Context — contratos de persistência (DECISION-001 / ADR-001)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.documento import Documento

if TYPE_CHECKING:
    from collections.abc import Sequence

    from emprestimo.domain.credit.contato import Contato
    from emprestimo.domain.credit.devedor import Devedor


class CarteiraRepository(ABC):
    """Persistência do Aggregate Carteira (IMP-007)."""

    @abstractmethod
    def save(self, carteira: Carteira) -> None: ...

    @abstractmethod
    def find_by_id(self, carteira_id: uuid.UUID) -> Carteira | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Carteira]: ...


class DevedorUniquenessChecker(ABC):
    """Contrato mínimo para verificação de unicidade do Devedor (IMP-046).

    Usado pelo UnicidadeDevedorService (DOMAIN-023) sem acoplar ao
    repositório completo (IMP-048).
    """

    @abstractmethod
    def exists_by_documento_carteira(
        self, documento: Documento, carteira_id: uuid.UUID
    ) -> bool: ...


@dataclass(frozen=True)
class DevedorFiltros:
    """Filtros para listagem paginada de Devedores (IMP-053)."""

    nome: str | None = None
    estado: str | None = None  # "ativo" | "inativo"
    documento: str | None = None


@dataclass(frozen=True)
class Paginacao:
    """Parâmetros de paginação (IMP-053)."""

    pagina: int = 1
    tamanho: int = 20

    def __post_init__(self) -> None:
        if self.pagina < 1:
            raise ValueError("pagina deve ser >= 1")
        if self.tamanho < 1 or self.tamanho > 100:
            raise ValueError("tamanho deve ser entre 1 e 100")

    @property
    def offset(self) -> int:
        return (self.pagina - 1) * self.tamanho

    @property
    def limit(self) -> int:
        return self.tamanho


@dataclass(frozen=True)
class DevedorResultadoPaginado:
    """Resultado de listagem paginada de Devedores (IMP-053)."""

    items: Sequence[Devedor]
    total: int
    pagina: int
    tamanho: int

    @property
    def paginas(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.tamanho - 1) // self.tamanho


class DevedorRepository(ABC):
    """Contrato de persistência do Aggregate Devedor (IMP-048).

    Segue o padrão do EPIC-001: merge/flush no repositório, commit no UoW.
    Sem acoplamento a SQLAlchemy no Domain.
    """

    @abstractmethod
    def save(self, devedor: Devedor) -> None: ...

    @abstractmethod
    def find_by_id(self, devedor_id: uuid.UUID) -> Devedor | None: ...

    @abstractmethod
    def find_by_documento_carteira(
        self, documento: Documento, carteira_id: uuid.UUID
    ) -> Devedor | None: ...

    @abstractmethod
    def listar_paginado(
        self,
        carteira_id: uuid.UUID,
        filtros: DevedorFiltros,
        paginacao: Paginacao,
    ) -> DevedorResultadoPaginado: ...


class ContatoRepository(ABC):
    """Contrato de persistência da Entity Contato (IMP-048).

    Segue o mesmo padrão: merge/flush no repositório, commit no UoW.
    """

    @abstractmethod
    def save(self, contato: Contato) -> None: ...

    @abstractmethod
    def find_by_id(self, contato_id: uuid.UUID) -> Contato | None: ...
