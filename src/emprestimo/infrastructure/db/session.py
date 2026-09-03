"""Engine e session factory (SQLAlchemy 2.x) para o PostgreSQL.

A URL padrão reflete o Docker Compose; pode ser sobrescrita por
DATABASE_URL (ver .env.example). O Unit of Work e o controle transacional
pertencem à fase de Aplicação (IMP-014).
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# 127.0.0.1 em vez de localhost de proposito: localhost resolve ::1 primeiro e
# espera o timeout inteiro antes de cair para IPv4, o que faz a suite parecer
# travada em vez de falhar (caveat 4.1 do handoff de 2026-08-20).
DEFAULT_DATABASE_URL = "postgresql+psycopg://emprestimo:emprestimo@127.0.0.1:5432/emprestimo"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _env_do_arquivo() -> dict[str, str]:
    """Lê o `.env` da raiz do repositório. Vazio se não houver.

    Stdlib de propósito: são pares `CHAVE=valor` e não vale uma dependência —
    ainda menos uma que hoje só existe de forma transitiva e some numa
    atualização de lock.
    """
    raiz = Path(__file__).resolve().parents[4]
    arquivo = raiz / ".env"
    if not arquivo.is_file():
        return {}
    valores: dict[str, str] = {}
    for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def database_url() -> str:
    """URL do banco, na ordem de precedência que cada ambiente espera.

    1. `DATABASE_URL` no ambiente — o Compose a injeta nos containers e o CI a
       define no workflow. Quem passa explicitamente sempre vence.
    2. `DATABASE_URL` no `.env` — para quem prefere escrever a URL inteira.
    3. `POSTGRES_PASSWORD` no `.env` — a URL é **derivada** dela.
    4. `DEFAULT_DATABASE_URL` — convenção sem configuração nenhuma.

    **Por que o passo 3 existe**, e ele é o conserto de um defeito real: o
    Compose carrega o `.env` sozinho, então a API subia e o banco funcionava,
    enquanto `pytest` rodando na máquina não lia esse arquivo em lugar nenhum e
    caía no passo 4 — com a senha de convenção, que nunca bate com a
    `POSTGRES_PASSWORD` que de fato criou o container. O sintoma era
    `password authentication failed`, que parece credencial errada e é, na
    verdade, arquivo não lido. Custou uma sessão de review incompleta em
    2026-09-03, e não era a primeira vez.

    **E por que DERIVAR em vez de pedir a URL inteira:** `.env.example` mandava
    escrever a senha duas vezes, em `POSTGRES_PASSWORD` e de novo dentro de
    `DATABASE_URL`. Duas cópias divergem — alguém troca uma e esquece a outra, e
    o erro reaparece com outra cara. Uma fonte só torna a divergência impossível.
    """
    do_ambiente = os.environ.get("DATABASE_URL")
    if do_ambiente:
        return do_ambiente

    arquivo = _env_do_arquivo()
    if arquivo.get("DATABASE_URL"):
        return arquivo["DATABASE_URL"]

    senha = arquivo.get("POSTGRES_PASSWORD")
    if senha:
        # `quote` porque senha gerada carrega `/`, `+` e `=` a torto e a direito,
        # e qualquer um deles quebra o parsing da URL de um jeito ilegivel.
        return (
            f"postgresql+psycopg://emprestimo:{quote(senha, safe='')}" "@127.0.0.1:5432/emprestimo"
        )

    return DEFAULT_DATABASE_URL


def get_engine() -> Engine:
    """Engine única do processo (lazy)."""
    global _engine
    if _engine is None:
        _engine = create_engine(database_url())
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Session factory única do processo (lazy)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def create_session() -> Session:
    """Cria uma nova sessão."""
    return get_session_factory()()
