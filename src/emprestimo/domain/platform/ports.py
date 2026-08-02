"""Ports do Platform Context — contratos de persistência (Repository Pattern).

A camada Domain define os contratos; a Infrastructure implementa. O Domain
não conhece SQLAlchemy nem FastAPI (DECISION-001 / ADR-001).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.tenant import Tenant
from emprestimo.domain.platform.usuario import Usuario


class TenantRepository(ABC):
    """Persistência do Aggregate Tenant (IMP-004)."""

    @abstractmethod
    def save(self, tenant: Tenant) -> None: ...

    @abstractmethod
    def find_by_id(self, tenant_id: uuid.UUID) -> Tenant | None: ...

    @abstractmethod
    def find_by_identificador_institucional(self, identificador: str) -> Tenant | None: ...

    @abstractmethod
    def find_all(self) -> list[Tenant]: ...


class UsuarioRepository(ABC):
    """Persistência da Entity Usuário (IMP-005)."""

    @abstractmethod
    def save(self, usuario: Usuario) -> None: ...

    @abstractmethod
    def find_by_id(self, usuario_id: uuid.UUID) -> Usuario | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Usuario]: ...


class ConfiguracaoRepository(ABC):
    """Persistência da Entity Configuração (IMP-006)."""

    @abstractmethod
    def save(self, configuracao: Configuracao) -> None: ...

    @abstractmethod
    def find_by_id(self, configuracao_id: uuid.UUID) -> Configuracao | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Configuracao]: ...
