"""Contratos integrados das FEATURE-010 e FEATURE-011."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.application.iam_catalogo import CATALOGO_POR_CODIGO
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.domain.platform.token_ativacao import TokenAtivacao
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.db.orm import (
    AuditoriaLogORM,
    CredencialORM,
    TokenAtivacaoORM,
    UsuarioPerfilORM,
)
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCredencialRepository,
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyTokenAtivacaoRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "segredo-api-iam-management"
SENHA_ADMIN = "Senha Admin 123"


@dataclass(frozen=True)
class AmbienteIam:
    admin: Usuario
    alvo: Usuario
    tenant_id: uuid.UUID
    token: str


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, JWT_SECRET)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def ambiente(session: Session) -> AmbienteIam:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    admin = UsuarioFactory.build(
        tenant_id=tenant.id,
        estado=UsuarioState.ATIVO,
        perfil_acesso="administrador",
    )
    alvo = UsuarioFactory.build(tenant_id=tenant.id, estado=UsuarioState.ATIVO)
    SqlAlchemyUsuarioRepository(session).save(admin)
    SqlAlchemyUsuarioRepository(session).save(alvo)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=admin.id, segredo=SENHA_ADMIN)
    )
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=alvo.id, segredo="Senha Alvo 123")
    )
    perfil = PerfilAcesso(tenant_id=tenant.id, nome="administrador")
    for codigo in ("perfil.gerir", "perfil.ler", "credencial.redefinir"):
        perfil.adicionar_permissao(CATALOGO_POR_CODIGO[codigo])
    repo_perfil = SqlAlchemyPerfilAcessoRepository(session)
    repo_perfil.save(perfil)
    repo_perfil.atribuir_usuario(admin.id, perfil.id)
    session.commit()
    token = HmacAccessTokenService(JWT_SECRET).emitir(admin).token
    return AmbienteIam(admin, alvo, tenant.id, token)


def _headers(token: str, chave: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if chave:
        headers["Idempotency-Key"] = chave
    return headers


def test_ativacao_descartavel_define_credencial_sem_persistir_segredo(
    client: TestClient,
    session: Session,
) -> None:
    tenant = TenantFactory.build()
    usuario = UsuarioFactory.build(tenant_id=tenant.id, estado=UsuarioState.CONVIDADO)
    SqlAlchemyTenantRepository(session).save(tenant)
    SqlAlchemyUsuarioRepository(session).save(usuario)
    token = TokenAtivacao.emitir(
        usuario_id=usuario.id,
        tenant_id=tenant.id,
        segredo="segredo-descartavel",
    )
    SqlAlchemyTokenAtivacaoRepository(session).save(token)
    session.commit()
    token_publico = f"{token.id}.segredo-descartavel"

    resposta = client.post(
        "/auth/ativar",
        json={"token_ativacao": token_publico, "segredo": "Nova Senha 456"},
    )
    repeticao = client.post(
        "/auth/ativar",
        json={"token_ativacao": token_publico, "segredo": "Outra Senha 789"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "ativo"
    assert repeticao.status_code == 401
    session.expire_all()
    credencial = session.scalar(select(CredencialORM).where(CredencialORM.usuario_id == usuario.id))
    ativacao = session.get(TokenAtivacaoORM, token.id)
    assert credencial is not None and "Nova Senha 456" not in credencial.hash_credencial
    assert ativacao is not None and ativacao.utilizado_em is not None
    assert "segredo-descartavel" not in ativacao.token_hash


def test_gestao_completa_de_perfil_idempotente_e_auditada(
    client: TestClient,
    session: Session,
    ambiente: AmbienteIam,
) -> None:
    headers = _headers(ambiente.token, "perfil-criar-1")
    criado = client.post("/iam/perfis", json={"nome": "Operador"}, headers=headers)
    replay = client.post("/iam/perfis", json={"nome": "Operador"}, headers=headers)
    assert criado.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["id"] == criado.json()["id"]
    perfil_id = criado.json()["id"]

    associado = client.put(
        f"/iam/perfis/{perfil_id}/permissoes/devedor.ler",
        headers=_headers(ambiente.token, "perfil-permissao-1"),
    )
    assert associado.status_code == 200
    assert associado.json()["permissoes"] == ["devedor.ler"]

    atribuido = client.put(
        f"/iam/usuarios/{ambiente.alvo.id}/perfil/{perfil_id}",
        headers=_headers(ambiente.token, "usuario-perfil-1"),
    )
    assert atribuido.status_code == 200
    assert atribuido.json()["permissoes"] == ["devedor.ler"]
    assert (
        session.scalar(
            select(func.count())
            .select_from(UsuarioPerfilORM)
            .where(UsuarioPerfilORM.usuario_id == ambiente.alvo.id)
        )
        == 1
    )

    antes_get = session.scalar(select(func.count()).select_from(AuditoriaLogORM)) or 0
    efetivas = client.get(
        f"/iam/usuarios/{ambiente.alvo.id}/permissoes",
        headers=_headers(ambiente.token),
    )
    depois_get = session.scalar(select(func.count()).select_from(AuditoriaLogORM)) or 0
    assert efetivas.status_code == 200
    assert efetivas.json()["perfil_nome"] == "Operador"
    assert depois_get == antes_get

    em_uso = client.post(
        f"/iam/perfis/{perfil_id}/inativar",
        headers=_headers(ambiente.token, "perfil-inativar-em-uso"),
    )
    assert em_uso.status_code == 409

    removido = client.delete(
        f"/iam/usuarios/{ambiente.alvo.id}/perfil",
        headers=_headers(ambiente.token, "usuario-perfil-remover-1"),
    )
    assert removido.status_code == 200
    inativado = client.post(
        f"/iam/perfis/{perfil_id}/inativar",
        headers=_headers(ambiente.token, "perfil-inativar-1"),
    )
    assert inativado.status_code == 200
    assert inativado.json()["estado"] == "inativo"
    acoes = set(session.scalars(select(AuditoriaLogORM.acao)).all())
    assert {
        "perfil.criado",
        "perfil.permissao_associada",
        "usuario.perfil_atribuido",
        "usuario.perfil_removido",
        "perfil.inativado",
    } <= acoes


def test_administrador_de_tenant_nao_pode_associar_permissao_de_plataforma(
    client: TestClient,
    ambiente: AmbienteIam,
) -> None:
    criado = client.post(
        "/iam/perfis",
        json={"nome": "tentativa-elevacao"},
        headers=_headers(ambiente.token, "perfil-elevacao-criar"),
    )

    resposta = client.put(
        f"/iam/perfis/{criado.json()['id']}/permissoes/tenant.criar",
        headers=_headers(ambiente.token, "perfil-elevacao-associar"),
    )

    assert criado.status_code == 201
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "acesso_negado"


def test_perfil_de_outro_tenant_responde_404(
    client: TestClient,
    session: Session,
    ambiente: AmbienteIam,
) -> None:
    outro = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(outro)
    perfil = PerfilAcesso(tenant_id=outro.id, nome="Oculto")
    SqlAlchemyPerfilAcessoRepository(session).save(perfil)
    session.commit()

    resposta = client.get(f"/iam/perfis/{perfil.id}", headers=_headers(ambiente.token))

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "recurso_nao_encontrado"


def test_alterar_e_redefinir_credenciais_revoga_sessoes_e_nao_expoe_segredo(
    client: TestClient,
    session: Session,
    ambiente: AmbienteIam,
) -> None:
    alterada = client.patch(
        "/iam/credencial",
        json={"segredo_atual": SENHA_ADMIN, "novo_segredo": "Senha Admin Nova 456"},
        headers=_headers(ambiente.token),
    )
    redefinida = client.post(
        f"/iam/usuarios/{ambiente.alvo.id}/credencial/redefinir",
        json={"novo_segredo": "Senha Alvo Nova 456"},
        headers=_headers(ambiente.token),
    )

    assert alterada.status_code == 200
    assert redefinida.status_code == 200
    assert "Senha Admin Nova 456" not in alterada.text
    assert "Senha Alvo Nova 456" not in redefinida.text
    detalhes = [valor for valor in session.scalars(select(AuditoriaLogORM.detalhes)).all() if valor]
    assert all("Senha Admin Nova 456" not in valor for valor in detalhes)
    assert all("Senha Alvo Nova 456" not in valor for valor in detalhes)


def test_rotas_iam_exigem_autenticacao_e_permissao(
    client: TestClient,
    session: Session,
    ambiente: AmbienteIam,
) -> None:
    sem_token = client.get("/iam/perfis")

    usuario = UsuarioFactory.build(
        tenant_id=ambiente.tenant_id,
        estado=UsuarioState.ATIVO,
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    session.commit()
    token_sem_perfil = HmacAccessTokenService(JWT_SECRET).emitir(usuario).token
    sem_permissao = client.get("/iam/perfis", headers=_headers(token_sem_perfil))

    assert sem_token.status_code == 401
    assert sem_permissao.status_code == 403


def test_conflitos_e_validacoes_de_perfil(
    client: TestClient,
    session: Session,
    ambiente: AmbienteIam,
) -> None:
    primeiro = client.post(
        "/iam/perfis",
        json={"nome": "Operador"},
        headers=_headers(ambiente.token, "criar-operador-a"),
    )
    duplicado = client.post(
        "/iam/perfis",
        json={"nome": "Operador"},
        headers=_headers(ambiente.token, "criar-operador-b"),
    )
    conflito_idempotencia = client.post(
        "/iam/perfis",
        json={"nome": "Outro"},
        headers=_headers(ambiente.token, "criar-operador-a"),
    )
    desconhecida = client.put(
        f"/iam/perfis/{primeiro.json()['id']}/permissoes/fora.catalogo",
        headers=_headers(ambiente.token, "permissao-desconhecida"),
    )

    assert primeiro.status_code == 201
    assert duplicado.status_code == 409
    assert conflito_idempotencia.status_code == 409
    assert desconhecida.status_code == 422
    acoes = set(session.scalars(select(AuditoriaLogORM.acao)).all())
    assert {"perfil.criar.falha", "perfil.criar.rollback"} <= acoes


def test_perfil_inativo_recusa_alteracao_de_permissao_com_409(
    client: TestClient,
    ambiente: AmbienteIam,
) -> None:
    criado = client.post(
        "/iam/perfis",
        json={"nome": "Temporario"},
        headers=_headers(ambiente.token, "criar-temporario"),
    )
    perfil_id = criado.json()["id"]
    inativado = client.post(
        f"/iam/perfis/{perfil_id}/inativar",
        headers=_headers(ambiente.token, "inativar-temporario"),
    )
    associar = client.put(
        f"/iam/perfis/{perfil_id}/permissoes/devedor.ler",
        headers=_headers(ambiente.token, "alterar-inativo"),
    )

    assert inativado.status_code == 200
    assert associar.status_code == 409


def test_redefinicao_propria_e_usuario_cross_tenant_sao_recusados(
    client: TestClient,
    session: Session,
    ambiente: AmbienteIam,
) -> None:
    autorredefinicao = client.post(
        f"/iam/usuarios/{ambiente.admin.id}/credencial/redefinir",
        json={"novo_segredo": "Senha indevida 123"},
        headers=_headers(ambiente.token),
    )

    outro_tenant = TenantFactory.build(estado=TenantState.ATIVO)
    outro_usuario = UsuarioFactory.build(
        tenant_id=outro_tenant.id,
        estado=UsuarioState.ATIVO,
    )
    SqlAlchemyTenantRepository(session).save(outro_tenant)
    SqlAlchemyUsuarioRepository(session).save(outro_usuario)
    perfil = PerfilAcesso(tenant_id=ambiente.tenant_id, nome="Operador")
    SqlAlchemyPerfilAcessoRepository(session).save(perfil)
    session.commit()
    atribuicao = client.put(
        f"/iam/usuarios/{outro_usuario.id}/perfil/{perfil.id}",
        headers=_headers(ambiente.token, "atribuir-cross-tenant"),
    )

    assert autorredefinicao.status_code == 403
    assert atribuicao.status_code == 404


def test_administrador_da_plataforma_inativa_e_reativa_outro_tenant_com_auth_real(
    client: TestClient,
    session: Session,
) -> None:
    controle = TenantFactory.build(estado=TenantState.ATIVO)
    alvo = TenantFactory.build(estado=TenantState.ATIVO)
    admin = UsuarioFactory.build(tenant_id=controle.id, estado=UsuarioState.ATIVO)
    repo_tenant = SqlAlchemyTenantRepository(session)
    repo_tenant.save(controle)
    repo_tenant.save(alvo)
    SqlAlchemyUsuarioRepository(session).save(admin)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=admin.id, segredo="Senha Plataforma 123")
    )
    perfil = PerfilAcesso(tenant_id=controle.id, nome="administrador_plataforma")
    for codigo in (
        "tenant.criar",
        "tenant.ler",
        "tenant.atualizar",
        "tenant.inativar",
        "tenant.reativar",
    ):
        perfil.adicionar_permissao(CATALOGO_POR_CODIGO[codigo])
    repo_perfil = SqlAlchemyPerfilAcessoRepository(session)
    repo_perfil.save(perfil)
    repo_perfil.atribuir_usuario(admin.id, perfil.id)
    session.commit()

    login = client.post(
        "/auth/login",
        json={
            "identificador_institucional": controle.identificador_institucional,
            "email": admin.email,
            "segredo": "Senha Plataforma 123",
        },
    )
    assert login.status_code == 200
    headers = _headers(login.json()["access_token"])

    inativado = client.post(f"/platform/tenants/{alvo.id}/inativar", headers=headers)
    reativado = client.post(f"/platform/tenants/{alvo.id}/reativar", headers=headers)

    assert inativado.status_code == 200
    assert inativado.json()["estado"] == "inativo"
    assert reativado.status_code == 200
    assert reativado.json()["estado"] == "ativo"
