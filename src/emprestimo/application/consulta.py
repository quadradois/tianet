"""Caso de uso de consulta de Tenant por identificador institucional (IMP-025).

Reutiliza exclusivamente `TenantRepository.find_by_identificador_institucional()`.
Retorna o Aggregate `Tenant` ou `None` — sem transformação para DTO.
A responsabilidade pelo tratamento de "não encontrado" permanece na camada Presentation.
"""

from __future__ import annotations

from collections.abc import Callable

from emprestimo.application.ports import UnitOfWork
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
        identificador = identificador_institucional.strip()
        with self._uow_factory() as uow:
            return uow.tenant.find_by_identificador_institucional(identificador)
