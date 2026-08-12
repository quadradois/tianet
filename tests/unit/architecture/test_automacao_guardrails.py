from pathlib import Path

ROOT = Path(__file__).parents[3]


def test_dominio_nao_depende_de_frameworks_ou_provedor() -> None:
    fontes = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src/emprestimo/domain/credit").glob("*.py")
    ).lower()
    assert "from fastapi" not in fontes
    assert "from sqlalchemy" not in fontes
    assert "import resend" not in fontes


def test_automacao_nao_implementa_calculo_financeiro() -> None:
    arquivos = [
        ROOT / "src/emprestimo/domain/credit/scheduler.py",
        ROOT / "src/emprestimo/domain/credit/notifications.py",
    ]
    fontes = "\n".join(path.read_text(encoding="utf-8") for path in arquivos).lower()
    for termo in ("juros", "amortizacao", "saldo_devedor", "multa_financeira"):
        assert termo not in fontes
