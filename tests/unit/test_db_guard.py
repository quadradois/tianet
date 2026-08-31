"""Cobre a guarda que impede a suíte de integração de apagar um schema remoto."""

import pytest
from tests.db_guard import exigir_host_descartavel


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "::1", "postgres", "LOCALHOST"])
def test_aceita_hosts_descartaveis(host: str) -> None:
    exigir_host_descartavel(host)


def test_aceita_host_ausente() -> None:
    exigir_host_descartavel(None)


@pytest.mark.parametrize("host", ["db.tianet.com.br", "10.0.0.5", "rds.amazonaws.com"])
def test_recusa_host_remoto(host: str) -> None:
    with pytest.raises(RuntimeError, match="nao descartavel"):
        exigir_host_descartavel(host)


DEV = "postgresql+psycopg://u:p@127.0.0.1:5432/emprestimo"


def test_deriva_banco_de_teste_separado_do_de_desenvolvimento() -> None:
    from tests.db_guard import url_de_teste

    assert url_de_teste(DEV).endswith("/emprestimo_test")
    # A senha nao pode virar "***" no caminho: a URL derivada e usada para conectar.
    assert ":p@" in url_de_teste(DEV)


def test_derivacao_e_idempotente() -> None:
    from tests.db_guard import url_de_teste

    uma_vez = url_de_teste(DEV)
    assert url_de_teste(uma_vez) == uma_vez


def test_ponto_de_entrada_recusa_host_remoto_antes_de_derivar() -> None:
    """A ordem importa: validar o host primeiro evita criar banco em producao."""
    from tests.db_guard import preparar_banco_descartavel

    with pytest.raises(RuntimeError, match="nao descartavel"):
        preparar_banco_descartavel("postgresql+psycopg://u:p@db.tianet.com.br:5432/emprestimo")
