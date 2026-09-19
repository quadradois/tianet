"""Migration da permissao agent.inbox.ler (S3).

Nao executa contra banco real: `op.get_bind` e mockado e o teste inspeciona
o SQL emitido. Valida cadeia, insercao idempotente nos dois perfis admin e
reversao cirurgica (so o codigo desta migration).
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

migration = cast(
    Any,
    import_module("migrations.versions.62c5a6f94173_permissao_agent_inbox_ler"),
)


class _BindFake:
    def __init__(self) -> None:
        self.executados: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> None:
        self.executados.append((str(statement), dict(params or {})))


def _rodar(operacao: str) -> _BindFake:
    bind = _BindFake()
    original = migration.op.get_bind
    migration.op.get_bind = lambda: bind
    try:
        if operacao == "upgrade":
            migration.upgrade()
        else:
            migration.downgrade()
    finally:
        migration.op.get_bind = original
    return bind


def test_cadeia_de_revisao_parte_do_head() -> None:
    assert migration.revision == "62c5a6f94173"
    assert migration.down_revision == "f6a7b8c9d0e1"


def test_upgrade_insere_permissao_nos_dois_perfis_admin() -> None:
    bind = _rodar("upgrade")
    textos = [sql for sql, _ in bind.executados]
    assert any("INSERT INTO permissao" in sql for sql in textos)
    vinculos = [p for sql, p in bind.executados if "perfil_permissao" in sql]
    assert vinculos
    for params in vinculos:
        assert params["codigo"] == "agent.inbox.ler"
        assert sorted(params["perfis"]) == ["administrador", "administrador_plataforma"]


def test_downgrade_remove_somente_agent_inbox_ler() -> None:
    bind = _rodar("downgrade")
    assert bind.executados
    for _, params in bind.executados:
        assert params.get("codigo", "agent.inbox.ler") == "agent.inbox.ler"
