"""Contratos HTTP de autorizacao e isolamento cross-tenant (IMP-092)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import cast

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.db.orm import AuditoriaLogORM, DevedorORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyContatoRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "segredo-api-authorization"
DEVEDOR_PAYLOAD = {
    "documento": "52998224725",
    "nome": "Joao da Silva",
    "contatos": [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}],
}


@dataclass(frozen=True)
class UsuarioAutorizacao:
    usuario: Usuario
    tenant: Tenant
    token: str


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, JWT_SECRET)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _criar_usuario(
    session: Session,
    *,
    perfil_nome: str | None,
    permissoes: tuple[str, ...] = (),
    persistir_perfil: bool = True,
) -> UsuarioAutorizacao:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(
        tenant_id=tenant.id,
        estado=UsuarioState.ATIVO,
        perfil_acesso=perfil_nome,
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    if perfil_nome is not None and persistir_perfil:
        perfil = PerfilAcesso(tenant_id=tenant.id, nome=perfil_nome)
        for codigo in permissoes:
            perfil.adicionar_permissao(Permissao(codigo=codigo, descricao=codigo))
        perfil_repo = SqlAlchemyPerfilAcessoRepository(session)
        perfil_repo.save(perfil)
        perfil_repo.atribuir_usuario(usuario.id, perfil.id)
    session.commit()
    token = HmacAccessTokenService(JWT_SECRET).emitir(usuario).token
    return UsuarioAutorizacao(usuario=usuario, tenant=tenant, token=token)


def _criar_carteira(session: Session, tenant_id: uuid.UUID) -> uuid.UUID:
    carteira = CarteiraFactory.build(tenant_id=tenant_id)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    session.commit()
    return carteira.id


def _criar_devedor(session: Session, carteira_id: uuid.UUID) -> uuid.UUID:
    devedor = Devedor.criar(
        carteira_id=carteira_id,
        documento=Documento.from_str("52998224725"),
        nome="Joao da Silva",
        contatos=[
            Contato(
                devedor_id=uuid.UUID(int=0),
                tipo=TipoContato.TELEFONE,
                valor="(11) 1234-5678",
                preferencial=True,
            )
        ],
    )
    SqlAlchemyDevedorRepository(session).save(devedor)
    for contato in devedor.contatos:
        SqlAlchemyContatoRepository(session).save(contato)
    session.commit()
    return devedor.id


def _contar_devedores(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(DevedorORM)) or 0


def test_token_valido_sem_permissao_responde_403(
    client: TestClient,
    session: Session,
) -> None:
    usuario = _criar_usuario(session, perfil_nome="SemPermissao")

    resp = client.get("/platform/tenants", headers=_headers(usuario.token))

    assert resp.status_code == 403
    assert resp.json() == {"codigo": "acesso_negado", "mensagem": "Acesso negado"}
    assert "operacao.negada" in set(session.scalars(select(AuditoriaLogORM.acao)).all())


def test_token_ausente_responde_401_e_audita_recusa(
    client: TestClient,
    session: Session,
) -> None:
    resp = client.get("/platform/tenants")

    assert resp.status_code == 401
    assert "principal.recusado" in set(session.scalars(select(AuditoriaLogORM.acao)).all())


def test_token_valido_sem_perfil_responde_403(
    client: TestClient,
    session: Session,
) -> None:
    usuario = _criar_usuario(session, perfil_nome=None)

    resp = client.get("/platform/tenants", headers=_headers(usuario.token))

    assert resp.status_code == 403
    assert resp.json()["codigo"] == "acesso_negado"


def test_token_valido_com_perfil_inexistente_responde_403(
    client: TestClient,
    session: Session,
) -> None:
    usuario = _criar_usuario(session, perfil_nome="PerfilAusente", persistir_perfil=False)

    resp = client.get("/platform/tenants", headers=_headers(usuario.token))

    assert resp.status_code == 403
    assert resp.json()["codigo"] == "acesso_negado"


def test_token_emitido_de_tenant_inativado_responde_401(
    client: TestClient,
    session: Session,
) -> None:
    usuario = _criar_usuario(
        session,
        perfil_nome="Leitor",
        permissoes=("tenant.ler",),
    )
    usuario.tenant.inativar()
    SqlAlchemyTenantRepository(session).save(usuario.tenant)
    session.commit()

    resp = client.get("/platform/tenants", headers=_headers(usuario.token))

    assert resp.status_code == 401
    assert resp.json()["codigo"] == "autenticacao_recusada"


@pytest.mark.parametrize(
    ("metodo", "path_template", "kwargs"),
    [
        ("get", "/platform/tenants", {}),
        ("get", "/platform/tenants/{tenant_id}", {}),
        ("patch", "/platform/tenants/{tenant_id}", {"json": {"nome": "Novo Nome"}}),
        ("post", "/platform/tenants/{tenant_id}/inativar", {}),
        ("post", "/platform/tenants/{tenant_id}/reativar", {}),
        (
            "post",
            "/credit/carteiras/{carteira_id}/devedores",
            {"json": DEVEDOR_PAYLOAD, "headers": {"Idempotency-Key": "imp-092-devedor-criar"}},
        ),
        ("get", "/credit/carteiras/{carteira_id}/devedores", {}),
        ("get", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}", {}),
        ("get", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/historico", {}),
        (
            "patch",
            "/credit/carteiras/{carteira_id}/devedores/{devedor_id}",
            {"json": {"nome": "Joao Santos"}, "headers": {"Idempotency-Key": "imp-092-patch"}},
        ),
        (
            "post",
            "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar",
            {"headers": {"Idempotency-Key": "imp-092-inativar"}},
        ),
        (
            "post",
            "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/reativar",
            {"headers": {"Idempotency-Key": "imp-092-reativar"}},
        ),
    ],
)
def test_matriz_endpoints_protegidos_sem_permissao_responde_403(
    client: TestClient,
    session: Session,
    metodo: str,
    path_template: str,
    kwargs: dict[str, object],
) -> None:
    usuario = _criar_usuario(session, perfil_nome="SemPermissao")
    carteira_id = _criar_carteira(session, usuario.tenant.id)
    devedor_id = _criar_devedor(session, carteira_id)
    path = path_template.format(
        tenant_id=usuario.tenant.id,
        carteira_id=carteira_id,
        devedor_id=devedor_id,
    )
    request_kwargs = {**kwargs}
    request_kwargs["headers"] = {
        **cast(dict[str, str], request_kwargs.get("headers", {})),
        **_headers(usuario.token),
    }

    resp = getattr(client, metodo)(path, **request_kwargs)

    assert resp.status_code == 403
    assert resp.json() == {"codigo": "acesso_negado", "mensagem": "Acesso negado"}


def test_operacao_credit_sem_permissao_responde_403_e_nao_persiste(
    client: TestClient,
    session: Session,
) -> None:
    usuario = _criar_usuario(session, perfil_nome="Leitor", permissoes=("devedor.ler",))
    carteira_id = _criar_carteira(session, usuario.tenant.id)
    antes = _contar_devedores(session)

    resp = client.post(
        f"/credit/carteiras/{carteira_id}/devedores",
        json=DEVEDOR_PAYLOAD,
        headers={
            **_headers(usuario.token),
            "Idempotency-Key": "imp-092-sem-permissao",
        },
    )

    assert resp.status_code == 403
    assert resp.json()["codigo"] == "acesso_negado"
    assert _contar_devedores(session) == antes


def test_cross_tenant_responde_404_antes_de_avaliar_permissao(
    client: TestClient,
    session: Session,
) -> None:
    usuario = _criar_usuario(session, perfil_nome="SemPermissao")
    outro_tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(outro_tenant)
    session.commit()
    carteira_de_outro_tenant = _criar_carteira(session, outro_tenant.id)

    resp = client.get(
        f"/credit/carteiras/{carteira_de_outro_tenant}/devedores",
        headers=_headers(usuario.token),
    )

    assert resp.status_code == 404
    assert resp.json() == {
        "codigo": "carteira_nao_encontrada",
        "mensagem": "Carteira inexistente",
    }


def test_cross_tenant_criacao_responde_404_e_nao_persiste(
    client: TestClient,
    session: Session,
) -> None:
    usuario = _criar_usuario(session, perfil_nome="Operador", permissoes=("devedor.criar",))
    outro_tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(outro_tenant)
    session.commit()
    carteira_de_outro_tenant = _criar_carteira(session, outro_tenant.id)
    antes = _contar_devedores(session)

    resp = client.post(
        f"/credit/carteiras/{carteira_de_outro_tenant}/devedores",
        json=DEVEDOR_PAYLOAD,
        headers={
            **_headers(usuario.token),
            "Idempotency-Key": "imp-092-cross-tenant",
        },
    )

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "carteira_nao_encontrada"
    assert _contar_devedores(session) == antes
    assert "cross_tenant.negado" in set(session.scalars(select(AuditoriaLogORM.acao)).all())
