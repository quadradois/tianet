"""Run the destructive Alembic migration validation cycle.

The cycle is intentionally destructive: upgrade to head, downgrade to base, then
upgrade to head again. It must only run against a disposable database.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

ALLOW_ENV = "MIGRATION_VALIDATION_ALLOW_DESTRUCTIVE"


_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ))

from tests.db_guard import preparar_banco_descartavel  # noqa: E402


def _alembic_config() -> Config:
    root = _RAIZ
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    return config


def _database_url(config: Config) -> str:
    return os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))


def _reset_public_schema(database_url: str) -> None:
    engine = create_engine(database_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()


def main() -> int:
    if os.environ.get(ALLOW_ENV) != "1":
        print(
            f"Refusing to run destructive migration validation. Set {ALLOW_ENV}=1 "
            "and use a disposable database."
        )
        return 2

    config = _alembic_config()
    # O ciclo e destrutivo por desenho. Ate 2026-08-31 ele rodava no banco de
    # desenvolvimento, apagando o schema que a aplicacao estava usando.
    destino = preparar_banco_descartavel(_database_url(config))
    os.environ["DATABASE_URL"] = destino
    config.set_main_option("sqlalchemy.url", destino)
    _reset_public_schema(destino)
    print("Validating Alembic cycle: upgrade head -> downgrade base -> upgrade head")
    command.upgrade(config, "head")
    command.current(config, check_heads=True)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.current(config, check_heads=True)
    print("Migration validation cycle completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
