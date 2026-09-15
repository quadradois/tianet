"""Estrutura da migration da credencial do copiloto (IMP-356-F slice 2).

Nao executa contra banco real: `op` e mockado e o teste inspeciona as
chamadas de `upgrade`/`downgrade` mais os atributos de revisao. Valida
cadeia, aditividade e reversao cirurgica — só a tabela nova.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

import pytest

migration = cast(
    Any,
    import_module("migrations.versions.d4e6f8a1b3c5_credencial_copilot"),
)


def test_cadeia_de_revisao_parte_do_head_anterior() -> None:
    assert migration.revision == "d4e6f8a1b3c5"
    assert migration.down_revision == "c8d3e5f7a2b4"


def test_upgrade_cria_so_a_tabela(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    criadas: list[tuple[Any, ...]] = []

    def _proibir_drop(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("upgrade nao pode remover nada")

    monkeypatch.setattr(migration.op, "create_table", lambda *a, **k: criadas.append(a))
    monkeypatch.setattr(migration.op, "drop_table", _proibir_drop)
    migration.upgrade()
    assert [args[0] for args in criadas] == ["credencial_copilot"]


def test_downgrade_remove_so_a_tabela(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removidas: list[tuple[Any, ...]] = []

    def _proibir_create(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("downgrade nao pode criar nada")

    monkeypatch.setattr(migration.op, "drop_table", lambda *a, **k: removidas.append(a))
    monkeypatch.setattr(migration.op, "create_table", _proibir_create)
    migration.downgrade()
    assert [args[0] for args in removidas] == ["credencial_copilot"]
