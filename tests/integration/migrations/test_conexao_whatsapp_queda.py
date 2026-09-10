"""Estrutura da migration do estado de queda (IMP-370, Slice 1).

Nao executa contra banco real: `op` e mockado e o teste inspeciona as chamadas
de `upgrade`/`downgrade` mais os atributos de revisao. Valida cadeia,
aditividade (uma coluna, nullable, com timezone) e reversao cirurgica.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

import pytest
import sqlalchemy as sa

migration = cast(
    Any,
    import_module("migrations.versions.c1d2e3f4a5b6_conexao_whatsapp_queda"),
)


def test_cadeia_de_revisao_parte_do_head_anterior() -> None:
    assert migration.revision == "c1d2e3f4a5b6"
    assert migration.down_revision == "b58e3f21c4d7"


def test_upgrade_adiciona_uma_coluna_nullable_com_timezone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adicionadas: list[tuple[Any, ...]] = []

    def _proibir_drop(*args: Any) -> None:
        raise AssertionError("upgrade nao pode remover coluna")

    monkeypatch.setattr(migration.op, "add_column", lambda *args: adicionadas.append(args))
    monkeypatch.setattr(migration.op, "drop_column", _proibir_drop)

    migration.upgrade()

    assert len(adicionadas) == 1
    nome_tabela, coluna = adicionadas[0]
    assert nome_tabela == "conexao_whatsapp"
    assert isinstance(coluna, sa.Column)
    assert coluna.name == "queda_detectada_em"
    assert coluna.nullable is True
    assert isinstance(coluna.type, sa.DateTime)
    assert coluna.type.timezone is True


def test_downgrade_remove_somente_a_coluna_nova(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removidas: list[tuple[Any, ...]] = []

    def _proibir_add(*args: Any) -> None:
        raise AssertionError("downgrade nao pode adicionar coluna")

    monkeypatch.setattr(migration.op, "drop_column", lambda *args: removidas.append(args))
    monkeypatch.setattr(migration.op, "add_column", _proibir_add)

    migration.downgrade()

    assert removidas == [("conexao_whatsapp", "queda_detectada_em")]
