"""Guardrails de exclusividade do Motor Financeiro (IMP-148)."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src" / "emprestimo"

ALLOWED_MOTOR_PARTS = {
    "emprestimo.py",
    "parcela.py",
    "pagamento.py",
    "financeiro.py",
    "motor_financeiro.py",
    "memoria_calculo.py",
    "eventos_financeiros.py",
}

ALLOWED_PERSISTENCE_BOUNDARIES = {
    SRC_ROOT / "domain" / "credit" / "ports.py",
    SRC_ROOT / "infrastructure" / "repositories" / "__init__.py",
}

FORBIDDEN_IMPORT_PARTS = {
    "motor_financeiro",
    "memoria_calculo",
}

FORBIDDEN_FUNCTION_PREFIXES = (
    "calcular_juros",
    "calcular_amortizacao",
    "calcular_saldo",
    "calcular_quitacao",
    "calcular_valor_quitacao",
    "gerar_parcelas",
    "gerar_plano_parcelas",
    "amortizar",
    "quitar",
)

FORBIDDEN_CLASS_NAMES = {
    "MotorFinanceiro",
    "MemoriaCalculo",
}


def _source_paths_outside_motor() -> list[Path]:
    paths = SRC_ROOT.rglob("*.py")
    return sorted(
        path
        for path in paths
        if path.is_file()
        and path.name not in ALLOWED_MOTOR_PARTS
        and "__pycache__" not in path.parts
    )


def _module_name(path: Path) -> str:
    relative = path.relative_to(PROJECT_ROOT / "src").with_suffix("")
    return ".".join(relative.parts)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _is_forbidden_import(name: str) -> bool:
    parts = set(name.lower().replace("-", "_").split("."))
    return bool(parts.intersection(FORBIDDEN_IMPORT_PARTS))


def _allows_memoria_reference(path: Path) -> bool:
    return path in ALLOWED_PERSISTENCE_BOUNDARIES


def test_contextos_fora_do_motor_nao_importam_motor_financeiro() -> None:
    violations: list[str] = []

    for path in _source_paths_outside_motor():
        if _allows_memoria_reference(path):
            continue
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


def test_contextos_fora_do_motor_nao_declaram_calculo_financeiro_definitivo() -> None:
    violations: list[str] = []

    for path in _source_paths_outside_motor():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.FunctionDef) and node.name.startswith(
                FORBIDDEN_FUNCTION_PREFIXES
            ):
                violations.append(f"{_module_name(path)}:{node.lineno}: def {node.name}")

    assert violations == []


def test_contextos_fora_do_motor_nao_instanciam_motor_ou_memoria_de_calculo() -> None:
    violations: list[str] = []

    for path in _source_paths_outside_motor():
        if _allows_memoria_reference(path):
            continue
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in FORBIDDEN_CLASS_NAMES:
                    violations.append(f"{_module_name(path)}:{node.lineno}: {func.id}()")
                elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_CLASS_NAMES:
                    violations.append(f"{_module_name(path)}:{node.lineno}: .{func.attr}()")

    assert violations == []
