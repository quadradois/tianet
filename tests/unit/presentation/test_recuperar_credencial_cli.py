from __future__ import annotations

import hashlib
from typing import Any

import pytest

from emprestimo.presentation.cli import recuperar_credencial as cli
from emprestimo.presentation.cli.bootstrap_plataforma import ENV_HABILITADO, ENV_HASH_AUTORIZACAO

SEGREDO = "segredo-operacional-com-mais-de-32-caracteres"


def _ambiente(monkeypatch: pytest.MonkeyPatch, *, habilitado: str = "true") -> None:
    monkeypatch.setenv(ENV_HABILITADO, habilitado)
    monkeypatch.setenv(ENV_HASH_AUTORIZACAO, hashlib.sha256(SEGREDO.encode()).hexdigest())


def _respostas(monkeypatch: pytest.MonkeyPatch, *valores: str) -> None:
    fila = list(valores)
    monkeypatch.setattr("getpass.getpass", lambda _prompt: fila.pop(0))


def test_gate_desabilitado_recusa_antes_de_pedir_a_nova_credencial(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _ambiente(monkeypatch, habilitado="false")
    _respostas(monkeypatch, SEGREDO)
    tocou_banco = []
    monkeypatch.setattr(cli, "get_session_factory", lambda: tocou_banco.append(1))

    assert cli.main(["--email", "admin@tianet.local"]) == 1
    assert "desabilitado" in capsys.readouterr().err
    assert tocou_banco == []


def test_confirmacao_divergente_recusa_sem_tocar_o_banco(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _ambiente(monkeypatch)
    _respostas(monkeypatch, SEGREDO, "Nova Credencial 123", "Outra Coisa 456")
    tocou_banco = []
    monkeypatch.setattr(cli, "get_session_factory", lambda: tocou_banco.append(1))

    assert cli.main(["--email", "admin@tianet.local"]) == 1
    assert "diverge" in capsys.readouterr().err
    assert tocou_banco == []


def test_caminho_feliz_chama_o_servico_com_email_e_segredo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _ambiente(monkeypatch)
    _respostas(monkeypatch, SEGREDO, "Nova Credencial 123", "Nova Credencial 123")
    chamadas: list[dict[str, Any]] = []

    class _Resultado:
        usuario_id = "u"
        tenant_id = "t"

        class estado:  # noqa: N801 -- imita StrEnum
            value = "ativo"

    class _Service:
        def __init__(self, **_: Any) -> None: ...

        def recuperar_operacional(self, **kwargs: Any) -> _Resultado:
            chamadas.append(kwargs)
            return _Resultado()

    monkeypatch.setattr(cli, "get_session_factory", lambda: object())
    monkeypatch.setattr(cli, "SqlAlchemyAuditoriaRegistro", lambda _sf: object())
    monkeypatch.setattr(cli, "CredenciaisService", _Service)

    assert cli.main(["--email", "Admin@TiaNet.local"]) == 0
    assert chamadas == [{"email": "Admin@TiaNet.local", "novo_segredo": "Nova Credencial 123"}]
    assert '"sessoes_revogadas": true' in capsys.readouterr().out
