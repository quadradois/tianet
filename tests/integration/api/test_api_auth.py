"""Testes de integracao da API de autenticacao (IMP-090)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.application.autenticacao import AutenticacaoService, HmacAccessTokenService
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
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

EMAIL = "maria.api.auth@exemplo.com"
SEGREDO = "Senha forte 123"
JWT_SECRET = "segredo-api-auth"
REFRESH_SECRET = "refresh-secret-api"


@dataclass(frozen=True)
class _UsuarioApi:
    identificador_institucional: str
    email: str
    segredo: str
    usuario_id: uuid.UUID
    tenant_id: uuid.UUID


@pytest.fixture
def usuario_api(session: Session) -> _UsuarioApi:
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
    return _UsuarioApi(
        identificador_institucional=tenant.identificador_institucional,
        email=EMAIL,
        segredo=SEGREDO,
        usuario_id=usuario.id,
        tenant_id=tenant.id,
    )


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    app_instance = create_app()

    def montar_autenticacao() -> AutenticacaoService:
        return AutenticacaoService(
            uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
            auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
            access_tokens=HmacAccessTokenService(JWT_SECRET),
            refresh_secret_factory=lambda: REFRESH_SECRET,
        )

    app_instance.dependency_overrides[dependencies.get_autenticacao_service] = montar_autenticacao
    with TestClient(app_instance) as c:
        yield c


def _login(
    client: TestClient,
    identificador_institucional: str,
    email: str = EMAIL,
    segredo: str = SEGREDO,
) -> dict[str, Any]:
    resp = client.post(
        "/auth/login",
        json={
            "identificador_institucional": identificador_institucional,
            "email": email,
            "segredo": segredo,
        },
    )
    assert resp.status_code == 200
    return cast(dict[str, Any], resp.json())


def _assert_401_uniforme(resp: Response) -> None:
    assert resp.status_code == 401
    assert resp.json() == {
        "codigo": "autenticacao_recusada",
        "mensagem": "Autenticacao recusada",
    }


def _parse_dt(valor: str) -> datetime:
    return datetime.fromisoformat(valor)


def test_login_valido_retorna_tokens_e_persiste_sessao(
    client: TestClient,
    usuario_api: _UsuarioApi,
    session_factory: sessionmaker[Session],
) -> None:
    resp = client.post(
        "/auth/login",
        json={
            "identificador_institucional": usuario_api.identificador_institucional,
            "email": usuario_api.email,
            "segredo": usuario_api.segredo,
        },
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["usuario_id"]
    assert corpo["tenant_id"]
    assert corpo["access_token"]
    assert corpo["refresh_token"]
    assert corpo["access_token_expira_em"]
    assert corpo["refresh_token_expira_em"]
    diferenca_expiracao = _parse_dt(corpo["refresh_token_expira_em"]) - _parse_dt(
        corpo["access_token_expira_em"]
    )
    assert abs(diferenca_expiracao - (timedelta(days=7) - timedelta(minutes=15))) < timedelta(
        seconds=2
    )
    assert usuario_api.segredo not in str(corpo)
    with session_factory() as session:
        sessoes = session.scalars(select(SessaoORM)).all()
        assert len(sessoes) == 1
        assert usuario_api.segredo not in sessoes[0].refresh_token_hash


@pytest.mark.parametrize(
    ("email", "segredo"),
    [
        (EMAIL, "senha errada"),
        ("nao-existe@exemplo.com", SEGREDO),
    ],
)
def test_login_invalido_401_uniforme(
    client: TestClient,
    usuario_api: _UsuarioApi,
    email: str,
    segredo: str,
) -> None:
    resp = client.post(
        "/auth/login",
        json={
            "identificador_institucional": usuario_api.identificador_institucional,
            "email": email,
            "segredo": segredo,
        },
    )

    _assert_401_uniforme(resp)


def test_login_distingue_mesmo_email_em_tenants_diferentes(
    client: TestClient,
    usuario_api: _UsuarioApi,
    session: Session,
) -> None:
    outro_segredo = "Outra senha forte 456"
    outro_tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(outro_tenant)
    outro_usuario = UsuarioFactory.build(
        tenant_id=outro_tenant.id,
        email=usuario_api.email,
        estado=UsuarioState.ATIVO,
    )
    SqlAlchemyUsuarioRepository(session).save(outro_usuario)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=outro_usuario.id, segredo=outro_segredo)
    )
    session.commit()

    primeiro = _login(
        client,
        usuario_api.identificador_institucional,
        usuario_api.email,
        usuario_api.segredo,
    )
    segundo = _login(
        client,
        outro_tenant.identificador_institucional,
        outro_usuario.email,
        outro_segredo,
    )

    assert primeiro["usuario_id"] == str(usuario_api.usuario_id)
    assert primeiro["tenant_id"] == str(usuario_api.tenant_id)
    assert segundo["usuario_id"] == str(outro_usuario.id)
    assert segundo["tenant_id"] == str(outro_tenant.id)


def test_login_tenant_inativo_401_uniforme(client: TestClient, session: Session) -> None:
    tenant = TenantFactory.build(estado=TenantState.INATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(
        tenant_id=tenant.id,
        email="tenant.inativo@exemplo.com",
        estado=UsuarioState.ATIVO,
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=usuario.id, segredo=SEGREDO)
    )
    session.commit()

    resp = client.post(
        "/auth/login",
        json={
            "identificador_institucional": tenant.identificador_institucional,
            "email": usuario.email,
            "segredo": SEGREDO,
        },
    )

    _assert_401_uniforme(resp)


def test_login_usuario_nao_ativo_401_uniforme(
    client: TestClient,
    session: Session,
) -> None:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(
        tenant_id=tenant.id,
        email="convidado.auth@exemplo.com",
        estado=UsuarioState.CONVIDADO,
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=usuario.id, segredo=SEGREDO)
    )
    session.commit()

    resp = client.post(
        "/auth/login",
        json={
            "identificador_institucional": tenant.identificador_institucional,
            "email": usuario.email,
            "segredo": SEGREDO,
        },
    )

    _assert_401_uniforme(resp)


def test_login_payload_invalido_400(client: TestClient) -> None:
    resp = client.post(
        "/auth/login",
        json={"identificador_institucional": "IDENT", "email": "maria@exemplo.com"},
    )

    _assert_401_uniforme(resp)


def test_login_credencial_em_formato_invalido_401_uniforme_sem_ecoar_input(
    client: TestClient,
    usuario_api: _UsuarioApi,
) -> None:
    resp = client.post(
        "/auth/login",
        json={
            "identificador_institucional": usuario_api.identificador_institucional,
            "email": usuario_api.email,
            "segredo": [usuario_api.segredo],
        },
    )

    _assert_401_uniforme(resp)
    assert usuario_api.segredo not in resp.text


def test_login_corpo_nao_objeto_401_uniforme(client: TestClient) -> None:
    resp = client.post("/auth/login", json=["payload", "invalido"])

    _assert_401_uniforme(resp)


def test_login_corpo_ausente_ou_json_malformado_401_uniforme(client: TestClient) -> None:
    sem_corpo = client.post("/auth/login")
    malformado = client.post(
        "/auth/login",
        content=(
            '{"identificador_institucional": "IDENT", ' '"email": "maria@exemplo.com", "segredo": '
        ),
        headers={"Content-Type": "application/json"},
    )

    _assert_401_uniforme(sem_corpo)
    _assert_401_uniforme(malformado)


def test_refresh_valido_retorna_novo_access_token_sem_novo_refresh(
    client: TestClient,
    usuario_api: _UsuarioApi,
) -> None:
    login = _login(
        client,
        usuario_api.identificador_institucional,
        usuario_api.email,
        usuario_api.segredo,
    )

    resp = client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["usuario_id"] == login["usuario_id"]
    assert corpo["tenant_id"] == login["tenant_id"]
    assert corpo["access_token"]
    assert _parse_dt(corpo["access_token_expira_em"]) > _parse_dt(login["access_token_expira_em"])
    assert "refresh_token" not in corpo


def test_refresh_recusa_quando_tenant_foi_inativado(
    client: TestClient,
    usuario_api: _UsuarioApi,
    session: Session,
) -> None:
    login = _login(
        client,
        usuario_api.identificador_institucional,
        usuario_api.email,
        usuario_api.segredo,
    )
    repo = SqlAlchemyTenantRepository(session)
    tenant = repo.find_by_id(usuario_api.tenant_id)
    assert tenant is not None
    tenant.inativar()
    repo.save(tenant)
    session.commit()

    resp = client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})

    _assert_401_uniforme(resp)


def test_refresh_malformado_ou_revogado_401_uniforme(
    client: TestClient,
    usuario_api: _UsuarioApi,
) -> None:
    login = _login(
        client,
        usuario_api.identificador_institucional,
        usuario_api.email,
        usuario_api.segredo,
    )

    _assert_401_uniforme(client.post("/auth/refresh", json={"refresh_token": "malformado"}))
    logout = client.post("/auth/logout", json={"refresh_token": login["refresh_token"]})
    assert logout.status_code == 200

    resp = client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})

    _assert_401_uniforme(resp)


def test_refresh_vazio_401_uniforme(client: TestClient) -> None:
    resp = client.post("/auth/refresh", json={"refresh_token": ""})

    _assert_401_uniforme(resp)


def test_refresh_e_logout_corpo_ausente_401_uniforme(client: TestClient) -> None:
    _assert_401_uniforme(client.post("/auth/refresh"))
    _assert_401_uniforme(client.post("/auth/logout"))


def test_logout_valido_revoga_refresh_e_e_idempotente(
    client: TestClient,
    usuario_api: _UsuarioApi,
    session_factory: sessionmaker[Session],
) -> None:
    login = _login(
        client,
        usuario_api.identificador_institucional,
        usuario_api.email,
        usuario_api.segredo,
    )

    primeiro = client.post("/auth/logout", json={"refresh_token": login["refresh_token"]})
    segundo = client.post("/auth/logout", json={"refresh_token": login["refresh_token"]})

    assert primeiro.status_code == 200
    assert primeiro.json() == {"status": "ok"}
    assert segundo.status_code == 200
    assert segundo.json() == {"status": "ok"}
    with session_factory() as session:
        sessao = session.scalar(select(SessaoORM))
        assert sessao is not None
        assert sessao.revogado_em is not None


def test_auditoria_de_auth_nao_contem_segredo(
    client: TestClient,
    usuario_api: _UsuarioApi,
    session_factory: sessionmaker[Session],
) -> None:
    login = _login(
        client,
        usuario_api.identificador_institucional,
        usuario_api.email,
        usuario_api.segredo,
    )
    client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
    client.post("/auth/logout", json={"refresh_token": login["refresh_token"]})
    client.post(
        "/auth/login",
        json={
            "identificador_institucional": usuario_api.identificador_institucional,
            "email": usuario_api.email,
            "segredo": "senha errada",
        },
    )

    with session_factory() as session:
        detalhes = [d for d in session.scalars(select(AuditoriaLogORM.detalhes)).all() if d]
        acoes = set(session.scalars(select(AuditoriaLogORM.acao)).all())
    assert {"login.sucesso", "refresh.sucesso", "logout.sucesso", "login.recusado"} <= acoes
    assert all(usuario_api.segredo not in detalhe for detalhe in detalhes)
    assert all("senha errada" not in detalhe for detalhe in detalhes)
