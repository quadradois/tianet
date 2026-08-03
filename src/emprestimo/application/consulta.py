"""Casos de uso de consulta de Tenant (IMP-025, IMP-026, IMP-027).

Reutilizam exclusivamente métodos do TenantRepository.
Retornam o Aggregate `Tenant` ou `None` — sem transformação para DTO.
A responsabilidade pelo tratamento de "não encontrado" permanece na camada Presentation.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.platform.ports import TenantFiltro, TenantOrdenacao, TenantPaginado
from emprestimo.domain.platform.tenant import Tenant


class TenantConsultaService:
    """Caso de uso para consultar Tenant por identificador institucional (IMP-025)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def consultar_por_identificador(self, identificador_institucional: str) -> Tenant | None:
        """Busca um Tenant pelo seu identificador institucional.

        Args:
            identificador_institucional: Identificador único da instituição.

        Returns:
            Aggregate `Tenant` se encontrado, `None` caso contrário.
        """
        with self._uow_factory() as uow:
            return uow.tenant.find_by_identificador_institucional(identificador_institucional)


class TenantConsultaPorIdService:
    """Caso de uso para consultar Tenant por ID (IMP-026)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def consultar_por_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Busca um Tenant pelo seu ID.

        Args:
            tenant_id: UUID do Tenant.

        Returns:
            Aggregate `Tenant` se encontrado, `None` caso contrário.
        """
        with self._uow_factory() as uow:
            return uow.tenant.find_by_id(tenant_id)


class TenantListagemService:
    """Caso de uso para listagem paginada de Tenants (IMP-027)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def listar(
        self,
        page: int = 1,
        size: int = 20,
        ordenacao: TenantOrdenacao | None = None,
        filtro: TenantFiltro | None = None,
    ) -> TenantPaginado:
        """Lista Tenants com paginação, ordenação e filtro.

        Args:
            page: Número da página (base 1, default 1).
            size: Tamanho da página (default 20, max 100).
            ordenacao: Ordenação dos resultados (default criado_em asc).
            filtro: Filtros opcionais (estado).

        Returns:
            TenantPaginado com items, total, page, size, pages.
        """
        with self._uow_factory() as uow:
            return uow.tenant.find_all_paginated(
                page=page,
                size=size,
                ordenacao=ordenacao,
                filtro=filtro,
            )
