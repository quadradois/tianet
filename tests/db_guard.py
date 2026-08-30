"""Guarda de segurança da suíte de integração.

`_reset_public_schema` executa `DROP SCHEMA IF EXISTS public CASCADE` antes de
criar a metadata. O banco do docker-compose se chama `emprestimo` — o mesmo nome
usado em produção — então o nome do banco não distingue os dois ambientes.
Apenas o host distingue: produção é remota. Um `DATABASE_URL` apontando para
fora da máquina destruiria o schema remoto sem aviso.
"""

HOSTS_DESCARTAVEIS = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})


def exigir_host_descartavel(host: str | None) -> None:
    """Recusa apagar o schema quando o host não é local/efêmero.

    `host` ausente significa socket local, que não alcança máquina remota.
    """
    if host is None or host.lower() in HOSTS_DESCARTAVEIS:
        return
    raise RuntimeError(
        f"Recusando DROP SCHEMA em host nao descartavel: {host!r}. "
        "A suite de integracao apaga o schema public inteiro; aponte "
        f"DATABASE_URL para um Postgres local ({', '.join(sorted(HOSTS_DESCARTAVEIS))})."
    )
