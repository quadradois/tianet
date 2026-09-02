"""Persistência da conexão de WhatsApp (IMP-365, PLAN-034)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory

from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp
from emprestimo.infrastructure.cifra import CifraToken
from emprestimo.infrastructure.db.orm import ConexaoWhatsAppORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyConexaoWhatsAppRepository,
    SqlAlchemyTenantRepository,
)

TOKEN = "5f29f723-7f3c-4ffa-9cbc-1df51d5eb9e5"


def _tenant(session: Session) -> uuid.UUID:
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    SqlAlchemyCarteiraRepository(session).save(CarteiraFactory.build(tenant_id=tenant.id))
    session.flush()
    return tenant.id


def _repo(session: Session) -> SqlAlchemyConexaoWhatsAppRepository:
    cifra = CifraToken(CifraToken.gerar_chave())
    return SqlAlchemyConexaoWhatsAppRepository(session, lambda: cifra)


def _conexao(tenant_id: uuid.UUID) -> ConexaoWhatsApp:
    return ConexaoWhatsApp.criar(
        tenant_id=tenant_id,
        instancia_id="8a8c901f-16f9-4431-b19d-ed69cccc46c0",
        instancia_nome="adm_tianet",
    )


def test_grava_e_recupera_a_conexao(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        tenant_id = _tenant(session)
        repo = _repo(session)
        repo.save(_conexao(tenant_id), token=TOKEN)
        session.commit()

        recuperada = repo.find_by_tenant_id(tenant_id)
        assert recuperada is not None
        assert recuperada.instancia_nome == "adm_tianet"
        assert recuperada.pareada is False
        assert repo.find_token(tenant_id) == TOKEN


def test_o_token_nao_fica_em_texto_claro_no_banco(session_factory: sessionmaker[Session]) -> None:
    """O guardrail que justifica o IMP-364 existir.

    Le a coluna crua, sem passar pelo repositorio: se alguem trocar a cifra por
    identidade, ou esquecer de cifrar num caminho novo, o token aparece aqui.
    """
    with session_factory() as session:
        tenant_id = _tenant(session)
        _repo(session).save(_conexao(tenant_id), token=TOKEN)
        session.commit()

        bruto = session.scalar(
            select(ConexaoWhatsAppORM.token_cifrado).where(
                ConexaoWhatsAppORM.tenant_id == tenant_id
            )
        )
        assert bruto is not None
        assert TOKEN.encode("utf-8") not in bruto
        assert TOKEN not in bruto.decode("utf-8", errors="ignore")


def test_save_sem_token_preserva_o_ja_guardado(session_factory: sessionmaker[Session]) -> None:
    """Parear nao pode apagar o token.

    Sem isto, a conexao continuaria existindo e aparecendo como pareada — mas
    sem poder enviar nada, porque o segredo teria sido sobrescrito por vazio.
    """
    with session_factory() as session:
        tenant_id = _tenant(session)
        repo = _repo(session)
        conexao = _conexao(tenant_id)
        repo.save(conexao, token=TOKEN)
        session.commit()

        repo.save(conexao.parear("556284290661"))
        session.commit()

        recuperada = repo.find_by_tenant_id(tenant_id)
        assert recuperada is not None
        assert recuperada.numero_pareado == "556284290661"
        assert repo.find_token(tenant_id) == TOKEN


def test_conexao_nova_sem_token_e_recusada(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        tenant_id = _tenant(session)
        with pytest.raises(ValueError, match="token e obrigatorio"):
            _repo(session).save(_conexao(tenant_id))


def test_tenant_sem_conexao_devolve_none(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        repo = _repo(session)
        assert repo.find_by_tenant_id(uuid.uuid4()) is None
        assert repo.find_token(uuid.uuid4()) is None


def test_um_tenant_nao_pode_ter_duas_conexoes(session_factory: sessionmaker[Session]) -> None:
    """A ADR-003 fixou um Credor, um Tenant, uma instancia.

    A restricao vive no banco, e nao so na aplicacao: invariante que existe
    apenas em codigo e invariante que uma escrita concorrente viola.
    """
    with session_factory() as session:
        tenant_id = _tenant(session)
        repo = _repo(session)
        repo.save(_conexao(tenant_id), token=TOKEN)
        session.commit()

        repo.save(_conexao(tenant_id), token=TOKEN)
        with pytest.raises(Exception, match="uq_conexao_whatsapp_tenant|UniqueViolation"):
            session.commit()
        session.rollback()
        session.execute(text("SELECT 1"))


def test_delete_apaga_a_conexao_e_o_token_cifrado(
    session_factory: sessionmaker[Session],
) -> None:
    """Par local do `excluir_instancia` (IMP-368).

    Manter a linha depois de a instancia ter sido apagada no provedor deixaria
    uma conexao apontando para nada e um token que nao autentica mais em lugar
    nenhum — e o `UNIQUE (tenant_id)` impediria criar a proxima.
    """
    with session_factory() as session:
        tenant_id = _tenant(session)
        repo = _repo(session)
        repo.save(_conexao(tenant_id), token=TOKEN)
        session.commit()

        repo.delete(tenant_id)
        session.commit()

        assert repo.find_by_tenant_id(tenant_id) is None
        assert repo.find_token(tenant_id) is None
        # Direto na tabela, filtrando por este Tenant: outros testes deste
        # arquivo compartilham o banco, entao um `select` sem `where` mediria a
        # sujeira deles, nao o efeito deste delete.
        linha = session.scalar(
            select(ConexaoWhatsAppORM).where(ConexaoWhatsAppORM.tenant_id == tenant_id)
        )
        assert linha is None


def test_delete_de_conexao_ausente_nao_e_erro(
    session_factory: sessionmaker[Session],
) -> None:
    """Ausencia e o mesmo desfecho pedido. Levantar aqui faria uma limpeza
    repetida — ou concorrente — virar incidente."""
    with session_factory() as session:
        tenant_id = _tenant(session)
        session.commit()

        _repo(session).delete(tenant_id)
        session.commit()
