"""Leitura operacional da inbox do agente (S3, somente leitura).

A tela `/app/agent` mostra resumo e recentes para triagem. Leitura pura:
sem provedor, sem auditoria (GET não cria `audit_log`), sem commit — nada
aqui escreve, então não há o que confirmar.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from emprestimo.agent.conversa import ClasseContexto, EntradaConversa
from emprestimo.application.ports import UnitOfWork

LIMITE_PADRAO_RECENTES = 20
LIMITE_MAXIMO_RECENTES = 100


@dataclass(frozen=True)
class ResumoInboxAgente:
    total: int
    por_classe: dict[ClasseContexto, int] = field(default_factory=dict)
    recentes: tuple[EntradaConversa, ...] = ()


class ConsultarInboxAgente:
    """Resumo + recentes da inbox do Tenant, para a tela de operação."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def executar(
        self,
        tenant_id: uuid.UUID,
        limite: int = LIMITE_PADRAO_RECENTES,
    ) -> ResumoInboxAgente:
        teto = max(1, min(limite, LIMITE_MAXIMO_RECENTES))
        with self._uow_factory() as uow:
            total = uow.inbox_conversa.contar(tenant_id)
            por_classe = uow.inbox_conversa.contar_por_classe(tenant_id)
            recentes = uow.inbox_conversa.listar_recentes(tenant_id, teto)
        return ResumoInboxAgente(total=total, por_classe=dict(por_classe), recentes=tuple(recentes))
