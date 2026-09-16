"""Estrutura da migration de egress (IMP-356-E slice 2).

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
    import_module("migrations.versions.f6a7b8c9d0e1_egress_conversa"),
)


def test_cadeia_de_revisao_parte_do_head_anterior() -> None:
    assert migration.revision == "f6a7b8c9d0e1"
    assert migration.down_revision == "e5f6a7b8c9d0"


def test_upgrade_cria_so_a_tabela(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    criadas: list[tuple[Any, ...]] = []
    indices: list[tuple[Any, ...]] = []

    def _proibir_drop(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("upgrade nao pode remover nada")

    monkeypatch.setattr(migration.op, "create_table", lambda *a, **k: criadas.append(a))
    monkeypatch.setattr(migration.op, "create_index", lambda *a, **k: indices.append(a))
    monkeypatch.setattr(migration.op, "drop_table", _proibir_drop)
    monkeypatch.setattr(migration.op, "drop_index", _proibir_drop)
    migration.upgrade()
    assert [args[0] for args in criadas] == ["egress_conversa"]
    assert len(indices) == 1


def test_downgrade_remove_so_a_tabela(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removidas: list[tuple[Any, ...]] = []

    def _proibir_create(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("downgrade nao pode criar nada")

    monkeypatch.setattr(migration.op, "drop_table", lambda *a, **k: removidas.append(a))
    monkeypatch.setattr(migration.op, "drop_index", lambda *a, **k: None)
    monkeypatch.setattr(migration.op, "create_table", _proibir_create)
    monkeypatch.setattr(migration.op, "create_index", _proibir_create)
    migration.downgrade()
    assert [args[0] for args in removidas] == ["egress_conversa"]
