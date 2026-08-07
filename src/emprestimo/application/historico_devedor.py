"""DevedorHistoricoService — leitura do histórico cadastral do Devedor (US-027).

O histórico não é uma estrutura própria: é a trilha append-only já gravada
pelos casos de uso de escrita (ADR-002), filtrada pela entidade ``devedor`` e
pelo ID consultado.

Consulta pura — não gera trilha (ADR-002: somente escrita é auditada).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from emprestimo.application.ports import AuditoriaConsulta, EventoAuditoria, UnitOfWork

ENTIDADE = "devedor"
"""Discriminador da entidade na trilha (``audit_log.entidade``)."""


class DevedorHistoricoService:
    """Caso de uso de consulta do histórico cadastral do Devedor (US-027)."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria_consulta: AuditoriaConsulta,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria_consulta = auditoria_consulta

    def consultar(self, devedor_id: uuid.UUID) -> list[EventoAuditoria] | None:
        """Retorna a trilha do Devedor em ordem cronológica.

        A existência do Devedor é verificada antes da leitura da trilha: sem
        isso, um ID inexistente devolveria uma lista vazia indistinguível de um
        Devedor sem eventos, e o 404 exigido pela US-027 seria impossível.

        Args:
            devedor_id: UUID do Devedor.

        Returns:
            Lista de eventos, ou ``None`` se o Devedor não existir — o
            tratamento do "não encontrado" pertence à Presentation.
        """
        with self._uow_factory() as uow:
            if uow.devedor.find_by_id(devedor_id) is None:
                return None
        return self._auditoria_consulta.listar_por_entidade(ENTIDADE, devedor_id)
