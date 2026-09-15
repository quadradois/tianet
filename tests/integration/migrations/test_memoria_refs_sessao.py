"""Estrutura da migration de memoria e refs da sessao (IMP-356-F slice 1).

Nao executa contra banco real: `op` e mockado e o teste inspeciona as
chamadas de `upgrade`/`downgrade` mais os atributos de revisao. Valida
cadeia, aditividade e reversao cirurgica — só as três tabelas novas.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

import pytest

migration = cast(
    Any,
    import_module("migrations.versions.c8d3e5f7a2b4_memoria_e_refs_da_sessao"),
)

TABELAS = {"mensagem_conversa", "tool_call_exec", "referencia_sessao"}


def test_cadeia_de_revisao_parte_do_head_anterior() -> None:
    assert migration.revision == "c8d3e5f7a2b4"
    assert migration.down_revision == "e7f8a9b0c1d2"


def test_upgrade_cria_so_as_tres_tabelas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    criadas: list[tuple[Any, ...]] = []
    indices: list[tuple[Any, ...]] = []

    def _proibir_drop(*args: Any) -> None:
        raise AssertionError("upgrade nao pode remover nada")

    monkeypatch.setattr(migration.op, "create_table", lambda *args: criadas.append(args))
    monkeypatch.setattr(migration.op, "create_index", lambda *args: indices.append(args))
    monkeypatch.setattr(migration.op, "drop_table", _proibir_drop)
    monkeypatch.setattr(migration.op, "drop_index", _proibir_drop)
    migration.upgrade()
    assert {args[0] for args in criadas} == TABELAS
    assert len(indices) == 3


def test_downgrade_remove_so_as_tres_tabelas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removidas: list[tuple[Any, ...]] = []

    def _proibir_create(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("downgrade nao pode criar nada")

    monkeypatch.setattr(migration.op, "drop_table", lambda *args, **kwargs: removidas.append(args))
    monkeypatch.setattr(migration.op, "drop_index", lambda *args, **kwargs: None)
    monkeypatch.setattr(migration.op, "create_table", _proibir_create)
    monkeypatch.setattr(migration.op, "create_index", _proibir_create)
    migration.downgrade()
    assert {args[0] for args in removidas} == TABELAS
