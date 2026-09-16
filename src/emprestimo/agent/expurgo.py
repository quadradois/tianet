"""Expurgo das tabelas conversacionais (IMP-356-F slice 4, DR-005 §4).

Remove em lotes as linhas com mais de 90 dias de inbox, sessão,
mensagem, tool-call e credencial do copiloto, mais referências já
expiradas — em ordem de dependência, sem tocar em `audit_log`
(append-only) nem em tabelas de negócio. Restore com egress incerto
pertence ao 356-E (sem egress, nada a bloquear aqui).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

RETENCAO_DIAS = 90


@dataclass(frozen=True)
class ResultadoExpurgo:
    removidas_mensagem: int = 0
    removidas_tool_call: int = 0
    removidas_referencia: int = 0
    removidas_sessao: int = 0
    removidas_inbox: int = 0
    removidas_credencial: int = 0
    removidas_egress: int = 0

    @property
    def total(self) -> int:
        return (
            self.removidas_mensagem
            + self.removidas_tool_call
            + self.removidas_referencia
            + self.removidas_sessao
            + self.removidas_inbox
            + self.removidas_credencial
            + self.removidas_egress
        )


class ExpurgoRepository(ABC):
    """Porta de remoção em lotes das tabelas do agente."""

    @abstractmethod
    def remover_mensagens_antigas(self, corte: datetime, lote: int) -> int: ...

    @abstractmethod
    def remover_tool_calls_antigos(self, corte: datetime, lote: int) -> int: ...

    @abstractmethod
    def remover_referencias_expiradas(self, agora: datetime, lote: int) -> int: ...

    @abstractmethod
    def remover_credenciais_antigas(self, corte: datetime, lote: int) -> int: ...

    @abstractmethod
    def remover_sessoes_antigas(self, corte: datetime, lote: int) -> int: ...

    @abstractmethod
    def remover_inbox_antiga(self, corte: datetime, lote: int) -> int: ...

    @abstractmethod
    def remover_egress_antigos(self, corte: datetime, lote: int) -> int: ...


def executar_expurgo(
    uow_factory: Callable[[], Any], agora: datetime, lote: int = 1000
) -> ResultadoExpurgo:
    """Expurga em lotes; retorna contagens. Nunca apaga auditoria."""
    if lote <= 0:
        raise ValueError("lote deve ser positivo")
    corte = agora - timedelta(days=RETENCAO_DIAS)
    acumulado = {
        "mensagem": 0,
        "tool_call": 0,
        "referencia": 0,
        "sessao": 0,
        "inbox": 0,
        "credencial": 0,
        "egress": 0,
    }

    def _rodada(filhos: bool) -> dict[str, int]:
        with uow_factory() as uow:
            if filhos:
                rodada = {
                    "mensagem": uow.expurgo.remover_mensagens_antigas(corte, lote),
                    "tool_call": uow.expurgo.remover_tool_calls_antigos(corte, lote),
                    "referencia": uow.expurgo.remover_referencias_expiradas(agora, lote),
                    "egress": uow.expurgo.remover_egress_antigos(corte, lote),
                    "credencial": uow.expurgo.remover_credenciais_antigas(corte, lote),
                    "sessao": 0,
                    "inbox": 0,
                }
            else:
                rodada = {
                    "mensagem": 0,
                    "tool_call": 0,
                    "referencia": 0,
                    "egress": 0,
                    "credencial": 0,
                    "sessao": uow.expurgo.remover_sessoes_antigas(corte, lote),
                    "inbox": uow.expurgo.remover_inbox_antiga(corte, lote),
                }
            uow.commit()
            return rodada

    # Filhos até zerar e só então os pais: lote parcial nunca viola FK.
    while True:
        rodada = _rodada(filhos=True)
        for chave, quantidade in rodada.items():
            acumulado[chave] += quantidade
        if sum(rodada.values()) == 0:
            break
    while True:
        rodada = _rodada(filhos=False)
        for chave, quantidade in rodada.items():
            acumulado[chave] += quantidade
        if sum(rodada.values()) == 0:
            break
    return ResultadoExpurgo(
        removidas_mensagem=acumulado["mensagem"],
        removidas_tool_call=acumulado["tool_call"],
        removidas_referencia=acumulado["referencia"],
        removidas_sessao=acumulado["sessao"],
        removidas_inbox=acumulado["inbox"],
        removidas_credencial=acumulado["credencial"],
        removidas_egress=acumulado["egress"],
    )
