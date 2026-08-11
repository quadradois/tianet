"""Guardrails de não cálculo financeiro para EPIC-007 (IMP-172)."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src" / "emprestimo"

OPERATION_DAILY_SOURCE_PATTERNS = (
    "domain/credit/operacao_diaria.py",
    "domain/credit/promessa.py",
)

FORBIDDEN_FUNCTION_PREFIXES = {
    "calcular_juros",
    "calcular_mora",
    "calcular_multa",
    "calcular_amortizacao",
    "calcular_saldo",
    "calcular_quitacao",
    "gerar_memoria",
    "memoria_de_calculo",
}

FORBIDDEN_IMPORT_PARTS = (
    "motor_financeiro",
    "memoria_calculo",
)

FORBIDDEN_CLASS_NAMES = (
    "MotorFinanceiro",
    "MemoriaCalculo",
)


def _source_paths() -> list[Path]:
    paths: list[Path] = []
    for pattern in OPERATION_DAILY_SOURCE_PATTERNS:
        paths.extend(SRC_ROOT.glob(pattern))
    return sorted(path for path in paths if path.is_file())


def _module_name(path: Path) -> str:
    relative = path.relative_to(PROJECT_ROOT / "src").with_suffix("")
    return ".".join(relative.parts)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _is_forbidden_import(name: str) -> bool:
    parts = set(name.lower().replace("-", "_").split("."))
    return bool(parts.intersection(FORBIDDEN_IMPORT_PARTS))


def test_operacao_diaria_nao_declara_calculo_financeiro_definitivo() -> None:
    violations: list[str] = []

    for path in _source_paths():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.FunctionDef) and any(
                node.name.startswith(prefix) for prefix in FORBIDDEN_FUNCTION_PREFIXES
            ):
                violations.append(f"{_module_name(path)}:{node.lineno}: def {node.name}")
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and any(
                    func.attr.startswith(prefix) for prefix in FORBIDDEN_FUNCTION_PREFIXES
                ):
                    violations.append(f"{_module_name(path)}:{node.lineno}: call {func.attr}()")

    assert violations == []


def test_operacao_diaria_nao_importa_memoria_ou_motor_que_viola_contorno() -> None:
    violations: list[str] = []

    for path in _source_paths():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_names = ".".join(alias.name for alias in node.names)
                candidate = f"{node.module}.{imported_names}"
                if _is_forbidden_import(candidate):
                    violations.append(f"{_module_name(path)}:{node.lineno}: from {candidate}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_forbidden_import(alias.name):
                        violations.append(
                            f"{_module_name(path)}:{node.lineno}: import {alias.name}"
                        )

    assert violations == []


def test_operacao_diaria_nao_instancia_motor_ou_memoria() -> None:
    violations: list[str] = []

    for path in _source_paths():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in FORBIDDEN_CLASS_NAMES:
                    violations.append(f"{_module_name(path)}:{node.lineno}: {func.id}()")
                elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_CLASS_NAMES:
                    violations.append(f"{_module_name(path)}:{node.lineno}: .{func.attr}()")

    assert violations == []
