"""Estrutura da migration de correlacao na trilha (IMP-356-F slice 4).

Nao executa contra banco real: `op` e mockado e o teste inspeciona as
chamadas de `upgrade`/`downgrade` mais os atributos de revisao. Valida
cadeia, aditividade e reversao cirurgica — só a coluna nova.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

import pytest

migration = cast(
    Any,
    import_module("migrations.versions.e5f6a7b8c9d0_correlacao_tool_call"),
)


def test_cadeia_de_revisao_parte_do_head_anterior() -> None:
    assert migration.revision == "e5f6a7b8c9d0"
    assert migration.down_revision == "d4e6f8a1b3c5"


def test_upgrade_adiciona_so_a_coluna(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adicionadas: list[tuple[Any, ...]] = []

    def _proibir_drop(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("upgrade nao pode remover nada")

    monkeypatch.setattr(migration.op, "add_column", lambda *a, **k: adicionadas.append((a, k)))
    monkeypatch.setattr(migration.op, "drop_column", _proibir_drop)
    monkeypatch.setattr(migration.op, "drop_table", _proibir_drop)
    migration.upgrade()
    assert len(adicionadas) == 1
    args, _ = adicionadas[0]
    assert args[0] == "tool_call_exec" and args[1].name == "correlation_id"


def test_downgrade_remove_so_a_coluna(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removidas: list[tuple[Any, ...]] = []

    def _proibir_create(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("downgrade nao pode criar nada")

    monkeypatch.setattr(migration.op, "drop_column", lambda *a, **k: removidas.append((a, k)))
    monkeypatch.setattr(migration.op, "add_column", _proibir_create)
    monkeypatch.setattr(migration.op, "create_table", _proibir_create)
    migration.downgrade()
    assert [(a[0], a[1]) for a, _ in removidas] == [("tool_call_exec", "correlation_id")]
