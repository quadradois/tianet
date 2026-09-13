"""Estrutura da migration de inbox/sessao conversacional (IMP-356-A).

Nao executa contra banco real: `op` e mockado e o teste inspeciona as chamadas
de `upgrade`/`downgrade` mais os atributos de revisao. Valida cadeia,
aditividade (duas tabelas novas, nada de credito tocado) e reversao cirurgica.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

import pytest

migration = cast(
    Any,
    import_module("migrations.versions.c9a4f2e71b83d_inbox_e_sessao_conversa"),
)


def test_cadeia_de_revisao_parte_do_head_anterior() -> None:
    assert migration.revision == "c9a4f2e71b83d"
    assert migration.down_revision == "d2e4f6a8b0c1"


def test_upgrade_cria_somente_as_duas_tabelas_novas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    criadas: list[tuple[Any, ...]] = []

    def _proibir_drop(*args: Any) -> None:
        raise AssertionError("upgrade nao pode remover nada")

    monkeypatch.setattr(migration.op, "create_table", lambda *args: criadas.append(args))
    monkeypatch.setattr(migration.op, "drop_table", _proibir_drop)
    monkeypatch.setattr(migration.op, "create_index", lambda *args: None)

    migration.upgrade()

    assert [args[0] for args in criadas] == ["inbox_conversa", "sessao_conversa"]


def test_downgrade_remove_somente_as_duas_tabelas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removidas: list[tuple[Any, ...]] = []

    def _proibir_create(*args: Any) -> None:
        raise AssertionError("downgrade nao pode criar nada")

    monkeypatch.setattr(migration.op, "drop_table", lambda *args: removidas.append(args))
    monkeypatch.setattr(migration.op, "create_table", _proibir_create)
    monkeypatch.setattr(migration.op, "create_index", lambda *args, **kwargs: None)
    monkeypatch.setattr(migration.op, "drop_index", lambda *args, **kwargs: None)

    migration.downgrade()

    assert removidas == [("sessao_conversa",), ("inbox_conversa",)]
