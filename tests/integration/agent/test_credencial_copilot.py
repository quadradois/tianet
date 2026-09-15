"""Credencial do copiloto com auth e cifra reais (IMP-356-F slice 2).

`AutenticacaoService` de verdade contra PostgreSQL real, refresh cifrado
com Fernet de verdade no store de verdade: entrar, renovar, revogar e o
isolamento por tenant/instância. O 401-duplo determinístico vive nos
testes unitários com fakes; aqui, o ciclo feliz e a revogação real.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.agent.credencial import (
    CredenciaisLogin,
    ProvedorTokenCopilot,
    RenovacaoEsgotadaError,
)
from emprestimo.application.autenticacao import (
    AutenticacaoService,
    HmacAccessTokenService,
)
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.domain.platform.usuario import UsuarioState
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.cifra import CifraToken
from emprestimo.infrastructure.db.orm import CredencialCopilotORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyArmazenRefresh,
    SqlAlchemyCredencialRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

SEGREDO = "Senha forte 123"
EMAIL = "copilot@exemplo.com"
INSTANCIA = "tianet_teste"
AGORA = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def usuario(session: Session) -> tuple[uuid.UUID, uuid.UUID, str]:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    user = UsuarioFactory.build(
        tenant_id=tenant.id,
        email=EMAIL,
        estado=UsuarioState.ATIVO,
        perfil_acesso="Operador",
    )
    SqlAlchemyUsuarioRepository(session).save(user)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=user.id, segredo=SEGREDO)
    )
    session.commit()
    return tenant.id, user.id, tenant.identificador_institucional


@pytest.fixture
def autenticacao(
    session_factory: sessionmaker[Session],
) -> AutenticacaoService:
    return AutenticacaoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
        access_tokens=HmacAccessTokenService("segredo-jwt-teste-com-32-caracteres!!"),
        refresh_secret_factory=lambda: "refresh-fixo-teste",
    )


@pytest.fixture
def cifra() -> CifraToken:
    return CifraToken(Fernet.generate_key().decode("utf-8"))


@pytest.fixture
def provedor(
    session: Session,
    usuario: tuple[uuid.UUID, uuid.UUID, str],
    autenticacao: AutenticacaoService,
    cifra: CifraToken,
) -> ProvedorTokenCopilot:
    tenant_id, _, _ = usuario
    return ProvedorTokenCopilot(
        autenticacao,
        SqlAlchemyArmazenRefresh(session),
        cifra.cifrar,
        cifra.decifrar,
        tenant_id=tenant_id,
        instancia_ref=INSTANCIA,
    )


def test_entrar_token_e_isolamento(
    session: Session,
    usuario: tuple[uuid.UUID, uuid.UUID, str],
    provedor: ProvedorTokenCopilot,
) -> None:
    _, _, identificador = usuario
    provedor.entrar(
        CredenciaisLogin(identificador_institucional=identificador, email=EMAIL, segredo=SEGREDO)
    )
    session.commit()
    assert provedor.token()
    assert provedor._stored.carregar(uuid.uuid4(), INSTANCIA) is None
    assert provedor._stored.carregar(provedor._tenant_id, "outra") is None


def test_refresh_repousa_cifrado(
    session: Session,
    session_factory: sessionmaker[Session],
    usuario: tuple[uuid.UUID, uuid.UUID, str],
    provedor: ProvedorTokenCopilot,
) -> None:
    _, _, identificador = usuario
    provedor.entrar(
        CredenciaisLogin(identificador_institucional=identificador, email=EMAIL, segredo=SEGREDO)
    )
    session.commit()
    with session_factory() as leitura:
        row = leitura.scalars(select(CredencialCopilotORM)).one()
        assert b"refresh-fixo-teste" not in bytes(row.refresh_cifrado)
        assert row.chave_id == "v1"


def test_revogacao_encerra_na_renovacao(
    session: Session,
    usuario: tuple[uuid.UUID, uuid.UUID, str],
    autenticacao: AutenticacaoService,
    cifra: CifraToken,
    provedor: ProvedorTokenCopilot,
) -> None:
    tenant_id, _, identificador = usuario
    provedor.entrar(
        CredenciaisLogin(identificador_institucional=identificador, email=EMAIL, segredo=SEGREDO)
    )
    session.commit()
    guardado = SqlAlchemyArmazenRefresh(session).carregar(tenant_id, INSTANCIA)
    assert guardado is not None
    refresh_completo = cifra.decifrar(guardado[0])
    autenticacao.logout(refresh_token=refresh_completo, agora=AGORA)
    provedor._expira_em = AGORA - timedelta(minutes=1)
    with pytest.raises(RenovacaoEsgotadaError):
        provedor.token()
    provedor._agora = lambda: AGORA + timedelta(minutes=14)
    with pytest.raises(RenovacaoEsgotadaError):
        provedor.token()
