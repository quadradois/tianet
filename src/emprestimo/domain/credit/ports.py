"""Ports do Credit Context — contrato de persistência da Carteira.

O Domain define o contrato; a Infrastructure implementa (DECISION-001 / ADR-001).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from emprestimo.domain.credit.carteira import Carteira


class CarteiraRepository(ABC):
    """Persistência do Aggregate Carteira (IMP-007)."""

    @abstractmethod
    def save(self, carteira: Carteira) -> None: ...

    @abstractmethod
    def find_by_id(self, carteira_id: uuid.UUID) -> Carteira | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Carteira]: ...
