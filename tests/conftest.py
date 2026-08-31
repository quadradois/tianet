"""Fixtures de integração — PostgreSQL real (DATABASE_URL, padrão Docker Compose).

Schema criado/destruído por sessão de teste via Base.metadata; cada teste
inicia com as tabelas truncadas. O commit é controlado pelo Unit of Work
nos testes de aplicação (AD-001).
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.infrastructure.db import orm  # noqa: F401 — registra tabelas no metadata
from emprestimo.infrastructure.db.base import Base
from emprestimo.infrastructure.db.session import database_url
from tests.db_guard import exigir_host_descartavel, preparar_banco_descartavel

# Exportado no import do conftest, ANTES de qualquer teste importar a aplicacao.
#
# Nao basta a fixture usar o banco de teste: o app FastAPI resolve a propria
# sessao por `database_url()`, que le DATABASE_URL. Se so a fixture mudar, os
# testes criam usuario num banco e a autenticacao procura no outro — toda a
# suite de API responde 401. Foi exatamente o que o gate pegou em 2026-08-31.
#
# `session.py` guarda a engine num global preguicoso, entao a troca precisa
# acontecer antes do primeiro `get_engine()`, e nao dentro de uma fixture.
DATABASE_URL_TESTE = preparar_banco_descartavel(database_url())
os.environ["DATABASE_URL"] = DATABASE_URL_TESTE

TABELAS_TRUNCATE = (
    "notificacao_evidencia",
    "solicitacao_notificacao",
    "template_notificacao",
    "preferencia_notificacao",
    "scheduler_worker_heartbeat",
    "tentativa_job",
    "job_agendado",
    "snapshot_configuracao_contratual",
    "configuracao_financeira_evento",
    "configuracao_financeira",
    "calendario_financeiro",
    "modalidade_financeira",
    "evento_financeiro",
    "memoria_calculo",
    "pagamento",
    "emprestimo",
    "evento_contrato",
    "contrato_credito",
    "decisao_comercial",
    "proposta_comercial",
    "simulacao_comercial",
    "comunicacao_registro",
    "lembrete",
    "agenda_item",
    "promessa_apropriacao",
    "promessa_pagamento",
    "cobranca_acao",
    "cobranca_caso",
    "relatorio_operacional_cache",
    "token_ativacao",
    "usuario_perfil",
    "perfil_permissao",
    "sessao",
    "credencial",
    "perfil_acesso",
    "permissao",
    "contato",
    "devedor",
    "idempotency_key",
    "audit_log",
    "usuario",
    "configuracao",
    "carteira",
    "tenant",
)

TABELAS_DROP = (
    "notificacao_evidencia",
    "solicitacao_notificacao",
    "template_notificacao",
    "preferencia_notificacao",
    "scheduler_worker_heartbeat",
    "tentativa_job",
    "job_agendado",
    "snapshot_configuracao_contratual",
    "configuracao_financeira_evento",
    "configuracao_financeira",
    "calendario_financeiro",
    "modalidade_financeira",
    "evento_financeiro",
    "memoria_calculo",
    "pagamento",
    "emprestimo",
    "evento_contrato",
    "contrato_credito",
    "decisao_comercial",
    "proposta_comercial",
    "simulacao_comercial",
    "comunicacao_registro",
    "lembrete",
    "agenda_item",
    "promessa_apropriacao",
    "promessa_pagamento",
    "cobranca_acao",
    "cobranca_caso",
    "relatorio_operacional_cache",
    "token_ativacao",
    "usuario_perfil",
    "perfil_permissao",
    "sessao",
    "credencial",
    "perfil_acesso",
    "permissao",
    "contato",
    "devedor",
    "idempotency_key",
    "audit_log",
    "usuario",
    "configuracao",
    "carteira",
    "tenant",
)


def _get_existing_tables(engine: Engine) -> set[str]:
    """Retorna conjunto de tabelas que existem no banco."""
    insp = inspect(engine)
    return set(insp.get_table_names())


def _reset_public_schema(engine: Engine) -> None:
    """Remove objetos residuais de Alembic para iniciar testes com metadata limpa."""
    exigir_host_descartavel(engine.url.host)
    with engine.begin() as conn:
        conn.execute(sa.text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(sa.text("CREATE SCHEMA public"))


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    # Banco de teste separado do de desenvolvimento: a fixture apaga o schema
    # inteiro, e ate 2026-08-31 fazia isso no banco que a aplicacao usava.
    e = create_engine(DATABASE_URL_TESTE)
    _reset_public_schema(e)
    Base.metadata.create_all(e)
    yield e
    # Drop tables in FK-respecting order to avoid FK constraint errors
    existing = _get_existing_tables(e)
    with e.begin() as conn:
        for tabela in TABELAS_DROP:
            if tabela in existing:
                conn.execute(sa.text(f"DROP TABLE IF EXISTS {tabela} CASCADE"))


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    s = session_factory()
    # Truncate only tables that exist in the database
    assert isinstance(s.bind, Engine)
    existing = _get_existing_tables(s.bind)
    truncate_list = [t for t in TABELAS_TRUNCATE if t in existing]
    if truncate_list:
        s.execute(sa.text(f"TRUNCATE TABLE {', '.join(truncate_list)} CASCADE"))
        s.commit()
    yield s
    s.rollback()
    s.close()
