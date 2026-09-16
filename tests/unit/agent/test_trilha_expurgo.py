"""Trilha própria e expurgo — regras puras (IMP-356-F slice 4).

Persistência via fakes: o observador grava sem tocar em audit_log, e o
expurgo recusa lote inválido sem rede. PG real vive na integração.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from emprestimo.agent.conversa import ToolCallExec
from emprestimo.agent.expurgo import RETENCAO_DIAS, ResultadoExpurgo, executar_expurgo
from emprestimo.agent.trilha import criar_observador

T0 = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


class UowFalso:
    def __init__(self, tool_calls: list[ToolCallExec]) -> None:
        self.tool_call_exec = _Tools(tool_calls)
        self.commits = 0

    def __enter__(self) -> UowFalso:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1


class _Tools:
    def __init__(self, destino: list[ToolCallExec]) -> None:
        self._destino = destino

    def registrar(self, execucao: ToolCallExec) -> None:
        self._destino.append(execucao)


def _tool() -> ToolCallExec:
    return ToolCallExec(
        id=uuid.uuid4(),
        sessao_id=uuid.uuid4(),
        inbox_id=uuid.uuid4(),
        call_id="call_1",
        ferramenta="consultar_acertos",
        schema_versao="consulta_operadora_v1",
        parametros={},
        resultado={"estado": "ok"},
        latencia_ms=12,
        completa=True,
        criado_em=T0,
        correlation_id="corr-1",
    )


def test_observador_persiste_sem_audit_log() -> None:
    gravadas: list[ToolCallExec] = []
    observador = criar_observador(lambda: UowFalso(gravadas))
    observador(_tool())
    assert len(gravadas) == 1
    assert gravadas[0].correlation_id == "corr-1"
    assert gravadas[0].latencia_ms == 12


def test_expurgo_recusa_lote_invalido() -> None:
    assert RETENCAO_DIAS == 90
    with pytest.raises(ValueError):
        executar_expurgo(lambda: UowFalso([]), T0, lote=0)


def test_resultado_expurgo_soma_totais() -> None:
    resultado = ResultadoExpurgo(removidas_mensagem=2, removidas_inbox=3)
    assert resultado.total == 5


def test_tool_call_sem_dinheiro_nem_segredo_por_construcao() -> None:
    ferramenta = _tool()
    assert set(ferramenta.resultado) == {"estado"}
    texto = str(ferramenta.__dict__)
    assert "Bearer" not in texto and "sk-" not in texto
