"""Guardrails do Comercial contra Contratos e Motor Financeiro (IMP-105)."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src" / "emprestimo"

COMMERCIAL_SOURCE_PATTERNS = (
    "domain/credit/*comercial*.py",
    "domain/credit/proposta_aprovada.py",
    "application/comercial*.py",
)

FORBIDDEN_IMPORT_PARTS = (
    "contrato",
    "contratos",
    "emprestimos",
    "parcela",
    "parcelas",
    "pagamento",
    "pagamentos",
    "motor_financeiro",
)

FORBIDDEN_CLASS_NAMES = {
    "Contrato",
    "ContratoDeCredito",
    "Emprestimo",
    "Parcela",
    "Pagamento",
    "MotorFinanceiro",
}

FORBIDDEN_FUNCTION_PREFIXES = (
    "calcular_juros",
    "calcular_amortizacao",
    "calcular_saldo",
    "calcular_quitacao",
    "calcular_parcela",
    "gerar_parcela",
    "gerar_cronograma",
    "amortizar",
    "quitar",
)


def _commercial_source_paths() -> list[Path]:
    paths: set[Path] = set()
    for pattern in COMMERCIAL_SOURCE_PATTERNS:
        paths.update(SRC_ROOT.glob(pattern))
    return sorted(path for path in paths if path.is_file())


def _module_name(path: Path) -> str:
    relative = path.relative_to(PROJECT_ROOT / "src").with_suffix("")
    return ".".join(relative.parts)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _is_forbidden_import(name: str) -> bool:
    parts = set(name.lower().replace("-", "_").split("."))
    return bool(parts.intersection(FORBIDDEN_IMPORT_PARTS))


def test_comercial_nao_importa_contratos_ou_motor_financeiro() -> None:
    violations: list[str] = []

    for path in _commercial_source_paths():
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


def test_comercial_nao_instancia_artefatos_financeiros_definitivos() -> None:
    violations: list[str] = []

    for path in _commercial_source_paths():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in FORBIDDEN_CLASS_NAMES:
                    violations.append(f"{_module_name(path)}:{node.lineno}: {func.id}()")
                elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_CLASS_NAMES:
                    violations.append(f"{_module_name(path)}:{node.lineno}: .{func.attr}()")

    assert violations == []


def test_comercial_nao_declara_calculo_financeiro_definitivo() -> None:
    violations: list[str] = []

    for path in _commercial_source_paths():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.FunctionDef) and node.name.startswith(
                FORBIDDEN_FUNCTION_PREFIXES
            ):
                violations.append(f"{_module_name(path)}:{node.lineno}: def {node.name}")

    assert violations == []
