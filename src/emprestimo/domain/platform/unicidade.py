"""Domain Service de unicidade do Tenant (IMP-008, UC-002).

Garante que a organização ainda não exista na plataforma antes do
provisionamento (AD-002). A verificação depende apenas do contrato de
persistência (port) — sem qualquer dependência de infraestrutura.
"""

from __future__ import annotations

from emprestimo.domain.common.errors import TenantJaExisteError
from emprestimo.domain.platform.ports import TenantRepository


class UnicidadeTenantService:
    """Valida a unicidade do ``identificador_institucional`` do Tenant."""

    def __init__(self, tenant_repository: TenantRepository) -> None:
        self._tenant_repository = tenant_repository

    def verificar(self, identificador_institucional: str) -> None:
        """Levanta ``TenantJaExisteError`` se a organização já existir.

        O identificador é normalizado (trim) para evitar falsos duplicados
        decorrentes de espaços à margem.
        """
        identificador = identificador_institucional.strip()
        if self._tenant_repository.find_by_identificador_institucional(identificador) is not None:
            raise TenantJaExisteError(identificador)
