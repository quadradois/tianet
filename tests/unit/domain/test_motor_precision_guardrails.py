"""Guardrails de precisao financeira do Motor (IMP-147)."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src" / "emprestimo"

MOTOR_SOURCE_PATTERNS = (
    "domain/credit/emprestimo.py",
    "domain/credit/parcela.py",
    "domain/credit/pagamento.py",
    "domain/credit/financeiro.py",
    "domain/credit/motor_financeiro.py",
    "domain/credit/memoria_calculo.py",
    "domain/credit/eventos_financeiros.py",
    "application/motor_financeiro.py",
)

FORBIDDEN_FLOAT_NAMES = {"float"}
FORBIDDEN_IMPLICIT_PERIOD_NAMES = {
    "DIAS_MES",
    "DIAS_NO_MES",
    "MES_FIXO",
    "PERIODO_FIXO",
}
FORBIDDEN_IMPLICIT_PERIOD_VALUES = {30, 360}


def _motor_source_paths() -> list[Path]:
    paths: set[Path] = set()
    for pattern in MOTOR_SOURCE_PATTERNS:
        paths.update(SRC_ROOT.glob(pattern))
    return sorted(path for path in paths if path.is_file())


def _module_name(path: Path) -> str:
    relative = path.relative_to(PROJECT_ROOT / "src").with_suffix("")
    return ".".join(relative.parts)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_motor_financeiro_nao_usa_float_em_regras_financeiras() -> None:
    violations: list[str] = []

    for path in _motor_source_paths():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_FLOAT_NAMES:
                violations.append(f"{_module_name(path)}:{node.lineno}: {node.id}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, float):
                violations.append(f"{_module_name(path)}:{node.lineno}: literal float")

    assert violations == []


def test_motor_financeiro_importa_decimal_quando_houver_codigo_de_calculo() -> None:
    paths = _motor_source_paths()
    if not paths:
        return

    modules_with_decimal: list[str] = []
    for path in paths:
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.ImportFrom) and node.module == "decimal":
                imported = {alias.name for alias in node.names}
                if "Decimal" in imported:
                    modules_with_decimal.append(_module_name(path))
            elif isinstance(node, ast.Import):
                if any(alias.name == "decimal" for alias in node.names):
                    modules_with_decimal.append(_module_name(path))

    assert modules_with_decimal != []


def test_motor_financeiro_nao_declara_periodo_fixo_implicito() -> None:
    violations: list[str] = []

    for path in _motor_source_paths():
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Assign):
                target_names = {
                    target.id
                    for target in node.targets
                    if isinstance(target, ast.Name)
                    and target.id.upper() in FORBIDDEN_IMPLICIT_PERIOD_NAMES
                }
                if target_names:
                    violations.append(f"{_module_name(path)}:{node.lineno}: {target_names}")
            elif (
                isinstance(node, ast.Constant)
                and node.value in FORBIDDEN_IMPLICIT_PERIOD_VALUES
                and isinstance(node.value, int)
            ):
                violations.append(f"{_module_name(path)}:{node.lineno}: periodo fixo {node.value}")

    assert violations == []
