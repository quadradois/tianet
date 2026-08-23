"""TenantAtualizacaoService — caso de uso de atualização cadastral (IMP-030/031).

Orquestra: buscar → invocar Aggregate.atualizar_nome() → persistir → commit UoW,
registrando a trilha de auditoria append-only (ADR-002). A infraestrutura de
auditoria é a mesma do provisionamento (IMP-016) — nenhum mecanismo novo.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable

from emprestimo.application.idempotencia import (
    concluir_idempotencia,
    dataclass_do_resultado,
    iniciar_idempotencia,
    resultado_de_dataclass,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.tenant import Tenant


class TenantAtualizacaoService:
    """Caso de uso para atualizar o nome de um Tenant (IMP-030, IMP-031)."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def atualizar_nome(
        self,
        tenant_id: uuid.UUID,
        novo_nome: str,
        *,
        idempotency_key: str | None = None,
    ) -> Tenant | None:
        """Atualiza o nome institucional do Tenant.

        Args:
            tenant_id: UUID do Tenant a ser atualizado.
            novo_nome: Novo nome institucional (validações no Aggregate).

        Returns:
            Aggregate `Tenant` atualizado, ou `None` se não encontrado.
            Quando o Tenant não existe, nenhum evento de auditoria é registrado.

        Raises:
            ViolacaoInvarianteError: se o nome violar regras de domínio.
        """
        with self._uow_factory() as uow:
            tenant = uow.tenant.find_by_id(tenant_id)
            if tenant is None:
                return None

            escopo = "tenant-atualizar"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={"tenant_id": tenant_id, "novo_nome": novo_nome},
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    Tenant,
                    chave=idempotency_key,
                )

            self._auditoria.registrar(
                "tenant",
                tenant.id,
                "atualizar.inicio",
                "iniciado",
                detalhes=json.dumps({"tenant_id": str(tenant.id)}),
            )
            try:
                tenant.atualizar_nome(novo_nome)
                uow.tenant.save(tenant)
                concluir_idempotencia(
                    uow,
                    chave=idempotency_key,
                    escopo=escopo,
                    resultado=resultado_de_dataclass(tenant),
                )
                uow.commit()
            except Exception as exc:
                self._auditoria.registrar(
                    "tenant",
                    tenant.id,
                    "atualizar.falha",
                    "falhou",
                    detalhes=f"{type(exc).__name__}: {exc}",
                )
                raise
            self._auditoria.registrar(
                "tenant",
                tenant.id,
                "atualizar.sucesso",
                "ok",
                detalhes=json.dumps({"tenant_id": str(tenant.id)}),
            )
            return tenant
