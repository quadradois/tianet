"""Guardas do banco usado por testes e pela validação de migrations.

Duas proteções, para dois erros diferentes:

1. `exigir_host_descartavel` — recusa apagar o schema de um host que não seja
   local. Defende contra `DATABASE_URL` apontando para produção.
2. `url_de_teste` + `garantir_banco` — separa fisicamente o banco de teste do de
   desenvolvimento. Defende contra o caso que o guard de host **não** cobre: a
   suíte rodando na própria máquina onde a aplicação está em uso.

O segundo existe porque o primeiro não bastava. Em 2026-08-31, com o guard de
host já em vigor, rodar a suíte apagou o banco que a aplicação estava usando
três vezes no mesmo dia — API em 503, login em 500, worker morto com
`relation "audit_log" does not exist`. O host era `127.0.0.1`, legitimamente
descartável; o banco é que era o mesmo.
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

HOSTS_DESCARTAVEIS = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})

SUFIXO_TESTE = "_test"
"""Sufixo do banco de teste. O de desenvolvimento nunca é tocado."""


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


def url_de_teste(url: str) -> str:
    """Deriva a URL do banco de teste a partir da URL de desenvolvimento.

    O banco do compose se chama `emprestimo`, igual ao de produção e igual ao
    que a aplicação usa em desenvolvimento. Suffixar isola o descartável do
    que alguém pode estar usando. Idempotente: uma URL já de teste volta igual.
    """
    parsed = make_url(url)
    nome = parsed.database or ""
    if nome.endswith(SUFIXO_TESTE):
        return url
    return parsed.set(database=nome + SUFIXO_TESTE).render_as_string(hide_password=False)


def garantir_banco(url: str) -> None:
    """Cria o banco de `url` se ele ainda não existir.

    Conecta no `postgres` de manutenção porque `CREATE DATABASE` não roda dentro
    do próprio banco alvo. Sem isso, separar dev de teste exigiria um passo
    manual em cada máquina e no CI — e um passo manual é um passo esquecido.
    """
    parsed = make_url(url)
    alvo = parsed.database
    manutencao = parsed.set(database="postgres").render_as_string(hide_password=False)
    engine = create_engine(manutencao, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conexao:
            existe = conexao.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :nome"), {"nome": alvo}
            ).scalar()
            if not existe:
                # Identificador não aceita bind parameter; aspas duplas evitam
                # qualquer interpretação do nome derivado.
                conexao.execute(text(f'CREATE DATABASE "{alvo}"'))
    finally:
        engine.dispose()


def preparar_banco_descartavel(url: str) -> str:
    """Valida o host, deriva o banco de teste e garante que ele existe.

    Ponto único de entrada: quem for apagar schema chama isto e recebe a URL
    que pode destruir sem medo.
    """
    exigir_host_descartavel(make_url(url).host)
    destino = url_de_teste(url)
    garantir_banco(destino)
    return destino
