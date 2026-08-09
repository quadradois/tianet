from __future__ import annotations

import hashlib

import pytest

from emprestimo.presentation.cli import bootstrap_plataforma as cli
from emprestimo.presentation.cli.bootstrap_plataforma import (
    ENV_HABILITADO,
    ENV_HASH_AUTORIZACAO,
    BootstrapRecusadoError,
    validar_autorizacao,
)

SEGREDO = "segredo-operacional-com-mais-de-32-caracteres"


def _ambiente() -> dict[str, str]:
    return {
        ENV_HABILITADO: "true",
        ENV_HASH_AUTORIZACAO: hashlib.sha256(SEGREDO.encode()).hexdigest(),
    }


def test_gate_aceita_segredo_forte_com_hash_configurado() -> None:
    validar_autorizacao(SEGREDO, _ambiente())


@pytest.mark.parametrize(
    ("segredo", "ambiente"),
    [
        (SEGREDO, {}),
        (SEGREDO, {ENV_HABILITADO: "false", ENV_HASH_AUTORIZACAO: "0" * 64}),
        (SEGREDO, {ENV_HABILITADO: "true", ENV_HASH_AUTORIZACAO: "invalido"}),
        ("curto", {ENV_HABILITADO: "true", ENV_HASH_AUTORIZACAO: "0" * 64}),
        ("x" * 40, {ENV_HABILITADO: "true", ENV_HASH_AUTORIZACAO: "0" * 64}),
    ],
)
def test_gate_falha_fechado(segredo: str, ambiente: dict[str, str]) -> None:
    with pytest.raises(BootstrapRecusadoError):
        validar_autorizacao(segredo, ambiente)


def test_cli_recusada_nao_inicia_banco_nem_expoe_segredo(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv(ENV_HABILITADO, raising=False)
    monkeypatch.setattr(
        "emprestimo.presentation.cli.bootstrap_plataforma.getpass.getpass",
        lambda _: SEGREDO,
    )
    monkeypatch.setattr(
        cli,
        "get_session_factory",
        lambda: pytest.fail("banco nao deveria ser acessado"),
    )

    codigo = cli.main(
        [
            "--tenant-identificador",
            "PLATAFORMA-CONTROLE",
            "--tenant-nome",
            "Controle",
            "--admin-nome",
            "Root",
            "--admin-email",
            "root@plataforma.local",
        ]
    )

    saida = capsys.readouterr()
    assert codigo == 1
    assert SEGREDO not in saida.out + saida.err


def test_cli_recusa_confirmacao_de_credencial_divergente_antes_do_banco(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ambiente = _ambiente()
    for chave, valor in ambiente.items():
        monkeypatch.setenv(chave, valor)
    respostas = iter([SEGREDO, "Credencial Inicial Forte 123", "Outra Credencial 456"])
    monkeypatch.setattr(
        "emprestimo.presentation.cli.bootstrap_plataforma.getpass.getpass",
        lambda _: next(respostas),
    )
    monkeypatch.setattr(
        cli,
        "get_session_factory",
        lambda: pytest.fail("banco nao deveria ser acessado"),
    )

    codigo = cli.main(
        [
            "--tenant-identificador",
            "PLATAFORMA-CONTROLE",
            "--tenant-nome",
            "Controle",
            "--admin-nome",
            "Root",
            "--admin-email",
            "root@plataforma.local",
        ]
    )

    saida = capsys.readouterr()
    assert codigo == 1
    assert "Credencial Inicial Forte 123" not in saida.out + saida.err
    assert "Outra Credencial 456" not in saida.out + saida.err
