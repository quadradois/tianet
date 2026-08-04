"""TenantAtualizacaoService — caso de uso de atualização cadastral (IMP-030).

Orquestra: buscar → invocar Aggregate.atualizar_nome() → persistir → commit UoW.
Sem idempotência, sem auditoria (são responsabilidade de IMP-031+).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.platform.tenant import Tenant


class TenantAtualizacaoService:
    """Caso de uso para atualizar o nome de um Tenant (IMP-030)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def atualizar_nome(self, tenant_id: uuid.UUID, novo_nome: str) -> Tenant | None:
        """Atualiza o nome institucional do Tenant.

        Args:
            tenant_id: UUID do Tenant a ser atualizado.
            novo_nome: Novo nome institucional (validações no Aggregate).

        Returns:
            Aggregate `Tenant` atualizado, ou `None` se não encontrado.

        Raises:
            ViolacaoInvarianteError: se o nome violar regras de domínio.
        """
        with self._uow_factory() as uow:
            tenant = uow.tenant.find_by_id(tenant_id)
            if tenant is None:
                return None

            tenant.atualizar_nome(novo_nome)
            uow.tenant.save(tenant)
            uow.commit()
            return tenant
