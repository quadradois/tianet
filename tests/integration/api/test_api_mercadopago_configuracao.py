"""Contrato HTTP do interruptor do Mercado Pago (IMP-388).

O que o arquivo protege: o segredo nunca volta na resposta, ligar exige
credencial testada, e desligado e um estado nomeado (422
`mercadopago_desabilitado`), nao um 500 nem um 403.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.cifra import CifraToken
from emprestimo.infrastructure.mercadopago import ResultadoVerificacao
from emprestimo.infrastructure.repositories import (
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "segredo-api-mercadopago"
PERMISSAO = "mercadopago.configurar"
ROTA = "/platform/mercadopago/configuracao"
TOKEN = "APP_USR-token-de-producao"
SECRET = "segredo-do-webhook-mp"


@dataclass(frozen=True)
class _Autenticado:
    usuario: Usuario
    tenant: Tenant
    token: str


@pytest.fixture(autouse=True)
def ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, JWT_SECRET)
    monkeypatch.setenv("WHATSAPP_TOKEN_ENCRYPTION_KEY", CifraToken.gerar_chave())


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Provedor sempre aceita, salvo quando o teste trocar o transporte."""
    monkeypatch.setattr(
        "emprestimo.application.configuracao_mercadopago.verificar_credencial",
        lambda _token: ResultadoVerificacao(valido=True, detalhe="ok"),
    )
    with TestClient(create_app()) as c:
        yield c


def _headers(token: str, *, idempotency: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if idempotency is not None:
        headers["Idempotency-Key"] = idempotency
    return headers


def _autenticar(session: Session, *permissoes: str) -> _Autenticado:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(
        tenant_id=tenant.id, estado=UsuarioState.ATIVO, perfil_acesso="AdminMP"
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    perfil = PerfilAcesso(tenant_id=tenant.id, nome="AdminMP")
    for codigo in permissoes:
        perfil.adicionar_permissao(Permissao(codigo=codigo, descricao=codigo))
    repo = SqlAlchemyPerfilAcessoRepository(session)
    repo.save(perfil)
    repo.atribuir_usuario(usuario.id, perfil.id)
    session.commit()
    return _Autenticado(usuario, tenant, HmacAccessTokenService(JWT_SECRET).emitir(usuario).token)


def _configurar(client: TestClient, token: str) -> httpx.Response:
    resposta: httpx.Response = client.put(
        ROTA,
        json={"access_token": TOKEN, "webhook_secret": SECRET},
        headers=_headers(token, idempotency=str(uuid.uuid4())),
    )
    return resposta


def test_tenant_novo_responde_desligado_e_sem_credencial(
    client: TestClient, session: Session
) -> None:
    autenticado = _autenticar(session, PERMISSAO)

    resposta = client.get(ROTA, headers=_headers(autenticado.token))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["habilitado"] is False
    assert corpo["credencial_configurada"] is False
    assert corpo["testado_em"] is None


def test_resposta_nunca_carrega_o_segredo(client: TestClient, session: Session) -> None:
    autenticado = _autenticar(session, PERMISSAO)

    gravado = _configurar(client, autenticado.token)
    lido = client.get(ROTA, headers=_headers(autenticado.token))

    assert gravado.status_code == 200
    for resposta in (gravado, lido):
        assert TOKEN not in resposta.text
        assert SECRET not in resposta.text
    assert lido.json()["credencial_configurada"] is True


def test_habilitar_sem_teste_e_recusado_com_422(client: TestClient, session: Session) -> None:
    autenticado = _autenticar(session, PERMISSAO)
    _configurar(client, autenticado.token)

    resposta = client.post(
        f"{ROTA}/habilitar", headers=_headers(autenticado.token, idempotency=str(uuid.uuid4()))
    )

    assert resposta.status_code == 422
    assert client.get(ROTA, headers=_headers(autenticado.token)).json()["habilitado"] is False


def test_ciclo_completo_liga_e_desliga(client: TestClient, session: Session) -> None:
    autenticado = _autenticar(session, PERMISSAO)
    _configurar(client, autenticado.token)

    testado = client.post(
        f"{ROTA}/testar", headers=_headers(autenticado.token, idempotency=str(uuid.uuid4()))
    )
    ligado = client.post(
        f"{ROTA}/habilitar", headers=_headers(autenticado.token, idempotency=str(uuid.uuid4()))
    )
    desligado = client.post(
        f"{ROTA}/desabilitar", headers=_headers(autenticado.token, idempotency=str(uuid.uuid4()))
    )

    assert testado.status_code == 200
    assert testado.json()["testado_em"] is not None
    assert ligado.json()["habilitado"] is True
    assert desligado.json()["habilitado"] is False
    # Desligar preserva a credencial: religar nao exige redigitar.
    assert desligado.json()["credencial_configurada"] is True


def test_sem_permissao_recebe_403(client: TestClient, session: Session) -> None:
    autenticado = _autenticar(session, "whatsapp.conexao.ler")

    resposta = client.get(ROTA, headers=_headers(autenticado.token))

    assert resposta.status_code == 403


def test_escrita_exige_idempotency_key(client: TestClient, session: Session) -> None:
    autenticado = _autenticar(session, PERMISSAO)

    resposta = client.put(
        ROTA,
        json={"access_token": TOKEN, "webhook_secret": SECRET},
        headers=_headers(autenticado.token),
    )

    assert resposta.status_code == 400
