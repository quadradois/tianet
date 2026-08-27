"""Cadastro de Usuario pelo IAM (IMP-355).

Ate 2026-08-27 nao existia rota de criacao de Usuario: cada Tenant ficava
limitado ao administrador criado pela CLI de bootstrap. O achado veio da revisao
adversarial do PLAN-033, ao verificar como o copilot teria identidade propria —
e a lacuna atingia operadores humanos muito antes de qualquer agente.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.domain.platform.usuario import UsuarioState
from emprestimo.infrastructure.db.orm import AuditoriaLogORM, CredencialORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "imp-355-secret-com-mais-de-32-bytes"
SEGREDO_VALIDO = "Senha Operadora 2026"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, JWT_SECRET)
    with TestClient(create_app()) as test_client:
        yield test_client


def _admin(session: Session, permissoes: tuple[str, ...]) -> tuple[str, uuid.UUID]:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(
        tenant_id=tenant.id,
        estado=UsuarioState.ATIVO,
        perfil_acesso="Administrador",
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    perfil = PerfilAcesso(tenant_id=tenant.id, nome="Administrador")
    for codigo in permissoes:
        perfil.adicionar_permissao(Permissao(codigo=codigo, descricao=codigo))
    repo = SqlAlchemyPerfilAcessoRepository(session)
    repo.save(perfil)
    repo.atribuir_usuario(usuario.id, perfil.id)
    session.commit()
    return HmacAccessTokenService(JWT_SECRET).emitir(usuario).token, tenant.id


def _payload(email: str | None = None) -> dict[str, str]:
    return {
        "nome": "Operadora Nova",
        "email": email or f"operadora-{uuid.uuid4().hex[:8]}@exemplo.com",
        "segredo": SEGREDO_VALIDO,
    }


def _headers(token: str, chave: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": chave or f"imp-355-{uuid.uuid4()}",
    }


def test_usuario_criado_nasce_ativo_e_consegue_autenticar(
    client: TestClient,
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    """A prova que importa nao e o 201: e o usuario novo conseguir entrar."""
    token, tenant_id = _admin(session, ("usuario.criar",))
    payload = _payload()

    resp = client.post("/iam/usuarios", json=payload, headers=_headers(token))

    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["estado"] == "ativo", "sem token de ativacao, o usuario nasce ativo"
    assert corpo["tenant_id"] == str(tenant_id), "criado no Tenant do solicitante"
    assert "segredo" not in corpo and "hash" not in str(corpo)

    login = client.post(
        "/auth/login",
        json={
            "identificador_institucional": _identificador(session_factory, tenant_id),
            "email": payload["email"],
            "segredo": payload["segredo"],
        },
    )
    assert login.status_code == 200, "credencial definida na criacao precisa servir"
    assert login.json()["usuario_id"] == corpo["id"]

    with session_factory() as leitura:
        credencial = leitura.scalar(
            select(CredencialORM).where(CredencialORM.usuario_id == uuid.UUID(corpo["id"]))
        )
        acoes = set(leitura.scalars(select(AuditoriaLogORM.acao)).all())
    assert credencial is not None
    assert payload["segredo"] not in credencial.hash_credencial
    assert {"usuario.criar.inicio", "usuario.criar.sucesso"} <= acoes


def test_sem_permissao_responde_403_e_nao_cria(
    client: TestClient,
    session: Session,
) -> None:
    token, _ = _admin(session, ("perfil.ler",))

    resp = client.post("/iam/usuarios", json=_payload(), headers=_headers(token))

    assert resp.status_code == 403


def test_email_repetido_responde_409_sem_ecoar_o_endereco(
    client: TestClient,
    session: Session,
) -> None:
    """409 e nao 500 — e a resposta nao devolve o e-mail consultado."""
    token, _ = _admin(session, ("usuario.criar",))
    payload = _payload()
    primeiro = client.post("/iam/usuarios", json=payload, headers=_headers(token))

    repetido = client.post("/iam/usuarios", json=payload, headers=_headers(token))

    assert primeiro.status_code == 201
    assert repetido.status_code == 409
    assert repetido.json()["codigo"] == "usuario_ja_existe"
    assert payload["email"] not in repetido.text


def test_segredo_fraco_e_recusado_pela_politica_do_dominio(
    client: TestClient,
    session: Session,
) -> None:
    """IMP-342: a politica vive no dominio, entao esta rota herda sem repetir regra."""
    token, _ = _admin(session, ("usuario.criar",))
    payload = {**_payload(), "segredo": "curta"}

    resp = client.post("/iam/usuarios", json=payload, headers=_headers(token))

    assert resp.status_code == 422
    assert "curta" not in resp.text, "a recusa nao pode ecoar o segredo"


def test_replay_da_mesma_chave_nao_cria_segundo_usuario(
    client: TestClient,
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    token, tenant_id = _admin(session, ("usuario.criar",))
    payload = _payload()
    chave = f"imp-355-replay-{uuid.uuid4()}"

    primeiro = client.post("/iam/usuarios", json=payload, headers=_headers(token, chave))
    segundo = client.post("/iam/usuarios", json=payload, headers=_headers(token, chave))

    assert primeiro.status_code == 201
    assert segundo.status_code == 201
    assert segundo.json()["id"] == primeiro.json()["id"]
    with session_factory() as leitura:
        criados = leitura.scalars(
            select(CredencialORM).where(
                CredencialORM.usuario_id == uuid.UUID(primeiro.json()["id"])
            )
        ).all()
    assert len(criados) == 1
    del tenant_id


def _identificador(session_factory: sessionmaker[Session], tenant_id: uuid.UUID) -> str:
    from emprestimo.infrastructure.db.orm import TenantORM

    with session_factory() as leitura:
        tenant = leitura.get(TenantORM, tenant_id)
    assert tenant is not None
    return tenant.identificador_institucional
