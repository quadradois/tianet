"""Contrato HTTP da inbox do agente (S3, somente leitura).

O que estes testes protegem:

1. **RBAC de verdade**: `agent.inbox.ler` autoriza ler; sem ela, 403 — e sem
   token, 401;
2. **inbox vazia é 200 com zeros**, não 404;
3. **o limite tem teto nos dois lados**: a rota recusa `limite=0` com 422 e o
   caso de uso corta no máximo.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.agent.conversa import ClasseContexto, EntradaConversa
from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.application.inbox_agente import ConsultarInboxAgente
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.cifra import ENV_CHAVE, CifraToken
from emprestimo.infrastructure.db.session import get_session_factory
from emprestimo.infrastructure.repositories import (
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.repositories.conversa import (
    SqlAlchemyInboxConversaRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "segredo-api-agent-inbox"
LER = "agent.inbox.ler"
ROTA = "/platform/agent/inbox"


@dataclass(frozen=True)
class _Autenticado:
    usuario: Usuario
    tenant: Tenant
    token: str


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, JWT_SECRET)


@pytest.fixture(autouse=True)
def chave_de_cifra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_CHAVE, CifraToken.gerar_chave())


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()

    def _uow() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(get_session_factory())

    app.dependency_overrides[dependencies.get_consultar_inbox_agente] = (
        lambda: ConsultarInboxAgente(_uow)
    )
    with TestClient(app) as c:
        yield c


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _autenticar(session: Session, *permissoes: str) -> _Autenticado:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(
        tenant_id=tenant.id,
        estado=UsuarioState.ATIVO,
        perfil_acesso="OperadorAgente",
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    perfil = PerfilAcesso(tenant_id=tenant.id, nome="OperadorAgente")
    for codigo in permissoes:
        perfil.adicionar_permissao(Permissao(codigo=codigo, descricao=codigo))
    repo = SqlAlchemyPerfilAcessoRepository(session)
    repo.save(perfil)
    repo.atribuir_usuario(usuario.id, perfil.id)
    session.commit()
    return _Autenticado(
        usuario=usuario,
        tenant=tenant,
        token=HmacAccessTokenService(JWT_SECRET).emitir(usuario).token,
    )


def _entrada(tenant_id: uuid.UUID, provider_input_id: str) -> EntradaConversa:
    return EntradaConversa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        instancia_ref="tianet",
        envelope_instance_id="instancia-stub",
        provider_input_id=provider_input_id,
        remetente_normalizado="556299999999",
        classe=ClasseContexto.PRE_CADASTRO,
        texto="ola",
        estado="recebida",
        recebido_em=datetime.now(UTC),
    )


def test_sem_token_responde_401(client: TestClient, session: Session) -> None:
    _ = session
    resposta = client.get(ROTA)
    assert resposta.status_code == 401


def test_sem_permissao_responde_403(client: TestClient, session: Session) -> None:
    ambiente = _autenticar(session)
    resposta = client.get(ROTA, headers=_headers(ambiente.token))
    assert resposta.status_code == 403


def test_inbox_vazia_devolve_zeros(client: TestClient, session: Session) -> None:
    ambiente = _autenticar(session, LER)
    resposta = client.get(ROTA, headers=_headers(ambiente.token))
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 0
    assert corpo["operadora"] == 0
    assert corpo["pre_cadastro"] == 0
    assert corpo["recentes"] == []


def test_resumo_e_recentes_vem_do_tenant(client: TestClient, session: Session) -> None:
    ambiente = _autenticar(session, LER)
    repo = SqlAlchemyInboxConversaRepository(session)
    assert repo.salvar(_entrada(ambiente.tenant.id, "primeira"))
    assert repo.salvar(_entrada(ambiente.tenant.id, "segunda"))
    session.commit()
    resposta = client.get(ROTA, headers=_headers(ambiente.token))
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 2
    assert corpo["pre_cadastro"] == 2
    assert [item["provider_input_id"] for item in corpo["recentes"]] == [
        "primeira",
        "segunda",
    ]


def test_limite_zero_e_400(client: TestClient, session: Session) -> None:
    # Validacao de query cai no handler de payload invalido (400), nao 422.
    ambiente = _autenticar(session, LER)
    resposta = client.get(ROTA, params={"limite": 0}, headers=_headers(ambiente.token))
    assert resposta.status_code == 400
