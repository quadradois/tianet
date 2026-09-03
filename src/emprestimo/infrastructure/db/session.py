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


def _valor_do_env(bruto: str) -> str:
    """Interpreta um valor do `.env` como o Docker Compose interpreta.

    Precisa casar com o Compose, e não "ser razoável": é o Compose que cria o
    container com essa senha. Qualquer divergência aqui produz de volta o
    `password authentication failed` que esta leitura existe para eliminar —
    com a agravante de o valor PARECER certo em quem lê o arquivo.

    Duas regras, e as duas foram apontadas em review:

    - **Valor entre aspas** termina na aspa de fechamento. O que vier depois é
      comentário e não faz parte da senha. Ingenuamente, `strip('"')` sobre
      `"segredo" # nota` devolve `segredo" # nota` — com aspa no meio.
    - **Valor sem aspas** aceita comentário inline, e ele começa num `#`
      **precedido de espaço**. A exigência do espaço não é capricho: `#` é
      caractere válido de senha, e cortar em todo `#` mutilaria
      `POSTGRES_PASSWORD=ab#cd`.
    """
    bruto = bruto.strip()
    if bruto[:1] in {'"', "'"}:
        aspa = bruto[0]
        fim = bruto.find(aspa, 1)
        if fim != -1:
            return bruto[1:fim]
        return bruto[1:]
    for sep in (" #", "	#"):
        corte = bruto.find(sep)
        if corte != -1:
            bruto = bruto[:corte]
    return bruto.strip()


def _env_do_arquivo(arquivo: Path | None = None) -> dict[str, str]:
    """Lê o `.env` da raiz do repositório. Vazio se não houver.

    Stdlib de propósito: são pares `CHAVE=valor` e não vale uma dependência —
    ainda menos uma que hoje só existe de forma transitiva e some numa
    atualização de lock. O que a dependência traria de valor está em
    `_valor_do_env`, e está coberto por teste sobre arquivo real.

    `arquivo=` existe para o teste exercitar o parser DE VERDADE. A primeira
    versão destes testes trocava esta função por um lambda, então validava a
    precedência e nunca a leitura — e foi exatamente na leitura que o defeito
    estava.
    """
    alvo = arquivo if arquivo is not None else Path(__file__).resolve().parents[4] / ".env"
    if not alvo.is_file():
        return {}
    valores: dict[str, str] = {}
    for linha in alvo.read_text(encoding="utf-8", errors="replace").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = _valor_do_env(valor)
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
