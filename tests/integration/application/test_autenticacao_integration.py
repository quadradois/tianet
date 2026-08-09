"""Testes de integracao da camada de Aplicacao - Autenticacao (IMP-088)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.application.autenticacao import AutenticacaoService, HmacAccessTokenService
from emprestimo.application.errors import AutenticacaoRecusadaError
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.domain.platform.usuario import UsuarioState
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import AuditoriaLogORM, SessaoORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCredencialRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

AGORA = datetime(2026, 8, 8, 12, tzinfo=UTC)
EMAIL = "maria.auth@exemplo.com"
SEGREDO = "Senha forte 123"


@dataclass
class _Ambiente:
    service: AutenticacaoService
    session_factory: sessionmaker[Session]
    identificador_institucional: str


@pytest.fixture
def ambiente(session_factory: sessionmaker[Session], session: Session) -> _Ambiente:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(
        tenant_id=tenant.id,
        email=EMAIL,
        estado=UsuarioState.ATIVO,
        perfil_acesso="Operador",
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=usuario.id, segredo=SEGREDO)
    )
    session.commit()

    service = AutenticacaoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
        access_tokens=HmacAccessTokenService("segredo-integracao"),
        refresh_secret_factory=lambda: "refresh-secret",
    )
    return _Ambiente(
        service=service,
        session_factory=session_factory,
        identificador_institucional=tenant.identificador_institucional,
    )


def test_login_persiste_sessao_e_auditoria_sem_segredo(ambiente: _Ambiente) -> None:
    resultado = ambiente.service.login(
        identificador_institucional=ambiente.identificador_institucional,
        email=EMAIL,
        segredo=SEGREDO,
        agora=AGORA,
    )

    with ambiente.session_factory() as session:
        sessoes = session.scalars(select(SessaoORM)).all()
        assert len(sessoes) == 1
        assert sessoes[0].usuario_id == resultado.usuario_id
        assert SEGREDO not in sessoes[0].refresh_token_hash
        acoes = set(session.scalars(select(AuditoriaLogORM.acao)).all())
        assert "login.inicio" in acoes
        assert "login.sucesso" in acoes
        detalhes = [d for d in session.scalars(select(AuditoriaLogORM.detalhes)).all() if d]
        assert all(SEGREDO not in detalhe for detalhe in detalhes)


def test_refresh_e_logout_revogam_refresh_persistido(ambiente: _Ambiente) -> None:
    login = ambiente.service.login(
        identificador_institucional=ambiente.identificador_institucional,
        email=EMAIL,
        segredo=SEGREDO,
        agora=AGORA,
    )

    renovacao = ambiente.service.refresh(
        refresh_token=login.refresh_token,
        agora=AGORA + timedelta(minutes=5),
    )
    ambiente.service.logout(
        refresh_token=login.refresh_token,
        agora=AGORA + timedelta(minutes=6),
    )

    assert renovacao.usuario_id == login.usuario_id
    with ambiente.session_factory() as session:
        sessao = session.scalar(select(SessaoORM))
        assert sessao is not None
        assert sessao.revogado_em is not None

    with pytest.raises(AutenticacaoRecusadaError):
        ambiente.service.refresh(
            refresh_token=login.refresh_token,
            agora=AGORA + timedelta(minutes=7),
        )
    ambiente.service.logout(
        refresh_token=login.refresh_token,
        agora=AGORA + timedelta(minutes=8),
    )


def test_login_invalido_audita_recusa_sem_criar_sessao(ambiente: _Ambiente) -> None:
    with pytest.raises(AutenticacaoRecusadaError):
        ambiente.service.login(
            identificador_institucional=ambiente.identificador_institucional,
            email=EMAIL,
            segredo="senha errada",
            agora=AGORA,
        )

    with ambiente.session_factory() as session:
        assert session.scalar(select(SessaoORM)) is None
        recusas = session.scalars(
            select(AuditoriaLogORM).where(AuditoriaLogORM.acao == "login.recusado")
        ).all()
        assert len(recusas) == 1
        assert "senha errada" not in (recusas[0].detalhes or "")
