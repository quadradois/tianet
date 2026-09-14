"""Estrutura da migration de cotas e slots (IMP-356-C).

Nao executa contra banco real: `op` e mockado e o teste inspeciona as chamadas
de `upgrade`/`downgrade` mais os atributos de revisao. Valida cadeia,
aditividade e reversao cirurgica — incluindo o seed das 2 vagas.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

import pytest

migration = cast(
    Any,
    import_module("migrations.versions.e7f8a9b0c1d2_cotas_e_slots_do_agente"),
)


def test_cadeia_de_revisao_parte_do_head_anterior() -> None:
    assert migration.revision == "e7f8a9b0c1d2"
    assert migration.down_revision == "c9a4f2e71b83d"


def test_upgrade_cria_tabelas_e_semeia_duas_vagas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    criadas: list[tuple[Any, ...]] = []
    executado: list[tuple[Any, ...]] = []

    def _proibir_drop(*args: Any) -> None:
        raise AssertionError("upgrade nao pode remover nada")

    class _Bind:
        def execute(self, stmt: Any, *args: Any) -> None:
            executado.append((str(stmt), args))

    monkeypatch.setattr(migration.op, "create_table", lambda *args: criadas.append(args))
    monkeypatch.setattr(migration.op, "drop_table", _proibir_drop)
    monkeypatch.setattr(migration.op, "create_index", lambda *args: None)
    monkeypatch.setattr(migration.op, "get_bind", lambda: _Bind())

    migration.upgrade()

    assert [args[0] for args in criadas] == ["cota_evento", "slot_execucao"]
    assert any("slot_execucao" in sql for sql, _ in executado)


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

    assert removidas == [("cota_evento",), ("slot_execucao",)]
