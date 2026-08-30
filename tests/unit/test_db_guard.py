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
