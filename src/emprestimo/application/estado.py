"""TenantEstadoService — caso de uso de transições de estado (IMP-034/035).

Orquestra: buscar → invocar Aggregate (inativar()/reativar()) → persistir →
commit UoW, registrando a trilha de auditoria append-only (ADR-002). A
infraestrutura de auditoria é a mesma do provisionamento (IMP-016) e da
atualização (IMP-031) — nenhum mecanismo novo.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable

from emprestimo.application.errors import TransicaoEstadoInvalidaError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.tenant import Tenant


class TenantEstadoService:
    """Caso de uso para inativar/reativar um Tenant (IMP-034, IMP-035)."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def inativar(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Inativa um Tenant (US-013): transição Ativo → Inativo.

        Args:
            tenant_id: UUID do Tenant a ser inativado.

        Returns:
            Aggregate `Tenant` inativado, ou `None` se não encontrado.
            Quando o Tenant não existe, nenhum evento de auditoria é registrado.

        Raises:
            TransicaoEstadoInvalidaError: se o Aggregate rejeitar a transição
            (ex.: Tenant já Inativo — estado divergente, IMP-036).
        """
        return self._transicionar(tenant_id, "inativar", Tenant.inativar)

    def reativar(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Reativa um Tenant (US-014): transição Inativo → Ativo.

        Args:
            tenant_id: UUID do Tenant a ser reativado.

        Returns:
            Aggregate `Tenant` reativado, ou `None` se não encontrado.
            Quando o Tenant não existe, nenhum evento de auditoria é registrado.

        Raises:
            TransicaoEstadoInvalidaError: se o Aggregate rejeitar a transição
            (ex.: Tenant já Ativo — estado divergente, IMP-036).
        """
        return self._transicionar(tenant_id, "reativar", Tenant.reativar)

    def _transicionar(
        self,
        tenant_id: uuid.UUID,
        acao: str,
        transicao: Callable[[Tenant], None],
    ) -> Tenant | None:
        """Executa a transição com trilha de auditoria em transação única."""
        with self._uow_factory() as uow:
            tenant = uow.tenant.find_by_id(tenant_id)
            if tenant is None:
                return None

            self._auditoria.registrar(
                "tenant",
                tenant.id,
                f"{acao}.inicio",
                "iniciado",
                detalhes=json.dumps({"tenant_id": str(tenant.id)}),
            )
            try:
                transicao(tenant)
                uow.tenant.save(tenant)
                uow.commit()
            except ViolacaoInvarianteError as exc:
                self._auditoria.registrar(
                    "tenant",
                    tenant.id,
                    f"{acao}.falha",
                    "falhou",
                    detalhes=f"{type(exc).__name__}: {exc}",
                )
                raise TransicaoEstadoInvalidaError(tenant.id, acao, exc.mensagem) from exc
            except Exception as exc:
                self._auditoria.registrar(
                    "tenant",
                    tenant.id,
                    f"{acao}.falha",
                    "falhou",
                    detalhes=f"{type(exc).__name__}: {exc}",
                )
                raise
            self._auditoria.registrar(
                "tenant",
                tenant.id,
                f"{acao}.sucesso",
                "ok",
                detalhes=json.dumps({"tenant_id": str(tenant.id)}),
            )
            return tenant
