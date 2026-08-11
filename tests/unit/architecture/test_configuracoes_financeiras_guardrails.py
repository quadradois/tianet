"""Guardrails de Configuracoes Financeiras sem calculo definitivo."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src" / "emprestimo"

CONFIGURACOES_SOURCE_PATTERNS = (
    "domain/credit/*configuracao_financeira*.py",
    "domain/credit/*configuracoes_financeiras*.py",
    "application/configuracoes_financeiras.py",
    "presentation/api/configuracoes_financeiras*.py",
)

FORBIDDEN_FUNCTION_PREFIXES = (
    "calcular_juros",
    "calcular_mora",
    "calcular_multa",
    "calcular_amortizacao",
    "calcular_saldo",
    "calcular_quitacao",
    "calcular_valor_quitacao",
    "gerar_memoria",
    "gerar_parcela",
    "gerar_parcelas",
    "gerar_plano_parcelas",
    "amortizar",
    "quitar",
)

FORBIDDEN_IMPORT_PARTS = {
    "motor_financeiro",
    "memoria_calculo",
}

FORBIDDEN_CLASS_NAMES = {
    "MotorFinanceiro",
    "MemoriaCalculo",
}


def _source_paths() -> list[Path]:
    paths: set[Path] = set()
    for pattern in CONFIGURACOES_SOURCE_PATTERNS:
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


def _violations(tree: ast.AST, module_name: str) -> list[str]:
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden_import(alias.name):
                    violations.append(f"{module_name}:{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names = ".".join(alias.name for alias in node.names)
            candidate = f"{node.module}.{imported_names}"
            if _is_forbidden_import(candidate):
                violations.append(f"{module_name}:{node.lineno}: from {candidate}")
        elif isinstance(node, ast.FunctionDef) and node.name.startswith(
            FORBIDDEN_FUNCTION_PREFIXES
        ):
            violations.append(f"{module_name}:{node.lineno}: def {node.name}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id in FORBIDDEN_CLASS_NAMES:
                    violations.append(f"{module_name}:{node.lineno}: {func.id}()")
                elif func.id == "float":
                    violations.append(f"{module_name}:{node.lineno}: float()")
            elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_CLASS_NAMES:
                violations.append(f"{module_name}:{node.lineno}: .{func.attr}()")

    return violations


def test_configuracoes_financeiras_nao_declaram_calculo_definitivo() -> None:
    violations: list[str] = []

    for path in _source_paths():
        violations.extend(_violations(_tree(path), _module_name(path)))

    assert violations == []


def test_guardrail_detecta_tentativa_de_calculo_financeiro() -> None:
    source = """
from emprestimo.domain.credit.motor_financeiro import MotorFinanceiro
from emprestimo.domain.credit.memoria_calculo import MemoriaCalculo

def calcular_juros_configurados():
    motor = MotorFinanceiro()
    memoria = MemoriaCalculo()
    return float("1.0"), motor, memoria
"""
    tree = ast.parse(source)

    violations = _violations(tree, "fixture.configuracoes_financeiras")

    assert any("motor_financeiro" in violation for violation in violations)
    assert any("memoria_calculo" in violation for violation in violations)
    assert any("def calcular_juros_configurados" in violation for violation in violations)
    assert any("MotorFinanceiro()" in violation for violation in violations)
    assert any("MemoriaCalculo()" in violation for violation in violations)
    assert any("float()" in violation for violation in violations)
