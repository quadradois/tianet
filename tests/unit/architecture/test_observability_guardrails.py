"""Guardrails de observabilidade sem calculo financeiro fora do Motor."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src" / "emprestimo"

OBSERVABILITY_PATTERNS = (
    "domain/common/events.py",
    "presentation/api/observability.py",
)

FORBIDDEN_FUNCTION_PREFIXES = (
    "calcular_juros",
    "calcular_mora",
    "calcular_multa",
    "calcular_amortizacao",
    "calcular_saldo",
    "calcular_quitacao",
    "gerar_memoria",
    "gerar_parcelas",
    "amortizar",
    "quitar",
)

FORBIDDEN_IMPORT_PARTS = {
    "financeiro",
    "motor_financeiro",
    "memoria_calculo",
}

FORBIDDEN_CLASS_NAMES = {
    "MotorFinanceiro",
    "MemoriaCalculo",
}


def _source_paths() -> list[Path]:
    return sorted(path for pattern in OBSERVABILITY_PATTERNS for path in SRC_ROOT.glob(pattern))


def _module_name(path: Path) -> str:
    relative = path.relative_to(PROJECT_ROOT / "src").with_suffix("")
    return ".".join(relative.parts)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _is_forbidden_import(name: str) -> bool:
    parts = set(name.lower().replace("-", "_").split("."))
    return bool(parts.intersection(FORBIDDEN_IMPORT_PARTS))


def test_observabilidade_nao_importa_motor_ou_memoria_de_calculo() -> None:
    violations: list[str] = []

    for path in _source_paths():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_forbidden_import(alias.name):
                        violations.append(
                            f"{_module_name(path)}:{node.lineno}: import {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names = ".".join(alias.name for alias in node.names)
                candidate = f"{node.module}.{imported_names}"
                if _is_forbidden_import(candidate):
                    violations.append(f"{_module_name(path)}:{node.lineno}: from {candidate}")

    assert violations == []


def test_observabilidade_nao_declara_formula_financeira() -> None:
    violations: list[str] = []

    for path in _source_paths():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.FunctionDef) and node.name.startswith(
                FORBIDDEN_FUNCTION_PREFIXES
            ):
                violations.append(f"{_module_name(path)}:{node.lineno}: def {node.name}")
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in FORBIDDEN_CLASS_NAMES:
                    violations.append(f"{_module_name(path)}:{node.lineno}: {func.id}()")
                elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_CLASS_NAMES:
                    violations.append(f"{_module_name(path)}:{node.lineno}: .{func.attr}()")

    assert violations == []
