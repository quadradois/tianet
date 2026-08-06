"""Ports do Credit Context — contratos de persistência (DECISION-001 / ADR-001)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.documento import Documento


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
