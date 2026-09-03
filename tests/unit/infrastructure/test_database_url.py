"""Precedência da resolução de `DATABASE_URL` (conserto de 2026-09-03).

Este arquivo existe por causa de um defeito de ambiente que reapareceu mais de
uma vez e sempre com a mesma cara enganosa: `password authentication failed`.

A causa nunca foi credencial errada. O Docker Compose carrega o `.env` sozinho,
então a API subia; `pytest` rodando na máquina não lia esse arquivo em lugar
nenhum e caía na URL de convenção, cuja senha jamais bate com a
`POSTGRES_PASSWORD` que criou o container. Quem lia o erro procurava a senha, e
o problema era o arquivo não lido.

Os testes abaixo fixam a ordem para que o conserto não se desfaça em silêncio.
"""

from __future__ import annotations

import pytest

from emprestimo.infrastructure.db import session as mod


@pytest.fixture(autouse=True)
def _sem_database_url_no_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    """O ambiente real da suíte pode ter a variável; aqui ela é controlada."""
    monkeypatch.delenv("DATABASE_URL", raising=False)


def _env(monkeypatch: pytest.MonkeyPatch, valores: dict[str, str]) -> None:
    monkeypatch.setattr(mod, "_env_do_arquivo", lambda: valores)


def test_ambiente_vence_o_arquivo(monkeypatch: pytest.MonkeyPatch) -> None:
    """CI e Compose passam a URL explicitamente, e isso não pode ser sobreposto.

    Se o `.env` do desenvolvedor vencesse, um arquivo esquecido na máquina
    apontaria a suíte do CI para outro banco — falha que só aparece longe daqui.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://ci:ci@ci:5432/ci")
    _env(monkeypatch, {"DATABASE_URL": "postgresql+psycopg://x:x@local:5432/x"})

    assert mod.database_url() == "postgresql+psycopg://ci:ci@ci:5432/ci"


def test_url_do_arquivo_quando_o_ambiente_nao_traz(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, {"DATABASE_URL": "postgresql+psycopg://a:b@127.0.0.1:5432/c"})

    assert mod.database_url() == "postgresql+psycopg://a:b@127.0.0.1:5432/c"


def test_deriva_da_senha_quando_o_arquivo_so_tem_postgres_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O caso que quebrava: `.env` com a senha e SEM `DATABASE_URL`.

    É o estado real de quem seguiu o Compose sem ler o `.env.example` até o fim —
    e o Compose funciona assim, o que torna o buraco invisível até alguém rodar
    a suíte na máquina.
    """
    _env(monkeypatch, {"POSTGRES_PASSWORD": "senha-de-teste"})

    assert mod.database_url() == (
        "postgresql+psycopg://emprestimo:senha-de-teste@127.0.0.1:5432/emprestimo"
    )


def test_senha_com_caractere_reservado_e_escapada(monkeypatch: pytest.MonkeyPatch) -> None:
    """Senha gerada carrega `/`, `+` e `=`, e todos quebram o parsing da URL.

    Sem escapar, o `@` de uma senha corta o host ao meio e o erro resultante fala
    de host inexistente — mandando quem investiga para o lado errado outra vez.
    """
    _env(monkeypatch, {"POSTGRES_PASSWORD": "a/b+c=d@e"})

    assert mod.database_url() == (
        "postgresql+psycopg://emprestimo:a%2Fb%2Bc%3Dd%40e@127.0.0.1:5432/emprestimo"
    )


def test_sem_ambiente_e_sem_arquivo_cai_na_convencao(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clone limpo, sem `.env`: continua funcionando sem configurar nada."""
    _env(monkeypatch, {})

    assert mod.database_url() == mod.DEFAULT_DATABASE_URL


# ---------------------------------------------------------------------------
# O parser em si. A primeira versao destes testes trocava `_env_do_arquivo` por
# um lambda e validava so a precedencia — a leitura, onde o defeito estava,
# nunca rodava. Estes usam arquivo real.
# ---------------------------------------------------------------------------


def _arquivo(tmp_path, conteudo: str):
    alvo = tmp_path / ".env"
    alvo.write_text(conteudo, encoding="utf-8")
    return alvo


def test_comentario_inline_nao_entra_na_senha(tmp_path) -> None:
    """O Compose corta aqui, e nos precisamos cortar igual.

    Nao cortar devolvia `segredo # nota` como senha. O container fora criado com
    `segredo`, entao a autenticacao falhava — e o arquivo, lido por um humano,
    parecia certo. Era o defeito de origem voltando pela porta do conserto.
    """
    lido = mod._env_do_arquivo(_arquivo(tmp_path, "POSTGRES_PASSWORD=segredo # nota\n"))

    assert lido["POSTGRES_PASSWORD"] == "segredo"


def test_valor_entre_aspas_termina_na_aspa_de_fechamento(tmp_path) -> None:
    """`strip('"')` ingenuo devolvia `segredo" # nota`, com aspa no meio."""
    lido = mod._env_do_arquivo(_arquivo(tmp_path, 'POSTGRES_PASSWORD="segredo" # nota\n'))

    assert lido["POSTGRES_PASSWORD"] == "segredo"


def test_aspas_simples_tambem(tmp_path) -> None:
    lido = mod._env_do_arquivo(_arquivo(tmp_path, "POSTGRES_PASSWORD='seg redo'\n"))

    assert lido["POSTGRES_PASSWORD"] == "seg redo"


def test_cerquilha_sem_espaco_antes_e_senha_e_nao_comentario(tmp_path) -> None:
    """`#` e caractere valido de senha.

    Cortar em todo `#` mutilaria a senha em silencio — e senha mutilada falha
    autenticando, que e o mesmo sintoma enganoso de novo.
    """
    lido = mod._env_do_arquivo(_arquivo(tmp_path, "POSTGRES_PASSWORD=ab#cd\n"))

    assert lido["POSTGRES_PASSWORD"] == "ab#cd"


def test_linha_de_comentario_e_linha_vazia_sao_ignoradas(tmp_path) -> None:
    conteudo = "# comentario\n\nPOSTGRES_PASSWORD=x\n#OUTRA=y\n"
    lido = mod._env_do_arquivo(_arquivo(tmp_path, conteudo))

    assert lido == {"POSTGRES_PASSWORD": "x"}


def test_arquivo_ausente_devolve_vazio(tmp_path) -> None:
    assert mod._env_do_arquivo(tmp_path / "nao-existe") == {}


# ---------------------------------------------------------------------------
# Sintaxe do Compose que este leitor NAO interpreta. A regra e recusar alto:
# divergir em silencio e o defeito de origem, e ele reaparece com o mesmo
# sintoma enganoso de senha errada.
# ---------------------------------------------------------------------------


def test_interpolacao_e_recusada_em_vez_de_devolvida_literal(tmp_path) -> None:
    """O Compose expande `${...}`; nos nao. Devolver literal divergiria."""
    with pytest.raises(mod.EnvNaoSuportadoError, match=r"interpolacao"):
        mod._env_do_arquivo(_arquivo(tmp_path, "POSTGRES_PASSWORD=${BASE:-x}\n"))


def test_escape_dentro_de_aspas_e_recusado(tmp_path) -> None:
    """Valor com escape truncava em silencio no meio — pior que falhar."""
    with pytest.raises(mod.EnvNaoSuportadoError, match=r"escape"):
        mod._env_do_arquivo(_arquivo(tmp_path, 'POSTGRES_PASSWORD="x\\"y"\n'))


def test_aspa_aberta_e_nao_fechada_e_recusada(tmp_path) -> None:
    """Sem a aspa de fechamento nao ha como saber onde o valor termina."""
    with pytest.raises(mod.EnvNaoSuportadoError, match=r"nao fechada"):
        mod._env_do_arquivo(_arquivo(tmp_path, 'POSTGRES_PASSWORD="sem fim\n'))
