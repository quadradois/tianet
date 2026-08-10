"""Guardrails anti-Motor para o contexto Contratos (IMP-126)."""

from __future__ import annotations

import ast
from pathlib import Path

CONTRATOS_FONTES = (
    Path("src/emprestimo/domain/credit/contrato_credito.py"),
    Path("src/emprestimo/domain/credit/contrato_liberado.py"),
    Path("src/emprestimo/application/contratos.py"),
)

NOMES_PROIBIDOS = {
    "Emprestimo",
    "Parcela",
    "Pagamento",
    "MotorFinanceiro",
    "MemoriaCalculo",
}

FUNCOES_PROIBIDAS = {
    "calcular_juros",
    "calcular_saldo",
    "calcular_quitacao",
    "calcular_amortizacao",
    "gerar_parcelas",
}


def _arvores_existentes() -> list[ast.AST]:
    arvores: list[ast.AST] = []
    for fonte in CONTRATOS_FONTES:
        if fonte.exists():
            arvores.append(ast.parse(fonte.read_text(encoding="utf-8")))
    return arvores


def test_contratos_nao_importa_entidades_financeiras() -> None:
    for arvore in _arvores_existentes():
        for node in ast.walk(arvore):
            if isinstance(node, ast.ImportFrom):
                modulo = node.module or ""
                assert "emprestimo.domain.credit.emprestimo" not in modulo
                assert "emprestimo.domain.credit.parcela" not in modulo
                assert "emprestimo.domain.credit.pagamento" not in modulo
                assert "motor" not in modulo.lower()


def test_contratos_nao_instancia_entidades_financeiras() -> None:
    for arvore in _arvores_existentes():
        for node in ast.walk(arvore):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    assert func.id not in NOMES_PROIBIDOS
                    assert func.id not in FUNCOES_PROIBIDAS
                if isinstance(func, ast.Attribute):
                    assert func.attr not in FUNCOES_PROIBIDAS
