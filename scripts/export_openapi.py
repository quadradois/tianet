"""Exporta o contrato OpenAPI governado em formato deterministico."""

from __future__ import annotations

import json
from pathlib import Path

from emprestimo.presentation.api.main import create_app

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json"


def exportar_openapi(destino: Path = DEFAULT_OUTPUT) -> Path:
    conteudo = (
        json.dumps(
            create_app().openapi(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8", newline="\n")
    return destino


if __name__ == "__main__":
    print(exportar_openapi())
