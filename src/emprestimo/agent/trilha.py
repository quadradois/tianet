"""Trilha própria do executor (IMP-356-F slice 4).

Liga o gancho `observador_tool` do executor ao repositório: cada
tool-call vira uma linha em `tool_call_exec` (ferramenta, schema,
parâmetros canônicos, resumo, latência, correlação) — nunca em
`audit_log`, nunca com PII além do protegido, nunca com dinheiro.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from emprestimo.agent.conversa import ToolCallExec


def criar_observador(uow_factory: Callable[[], Any]) -> Callable[[ToolCallExec], None]:
    """Devolve o observador que persiste cada tool-call executado."""

    def _observar(execucao: ToolCallExec) -> None:
        with uow_factory() as uow:
            uow.tool_call_exec.registrar(execucao)
            uow.commit()

    return _observar
