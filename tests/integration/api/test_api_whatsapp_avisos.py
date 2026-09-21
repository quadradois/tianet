"""Contrato HTTP do numero que recebe os avisos do sistema (IMP-353).

`GET/PUT /platform/whatsapp/avisos` le e grava a configuracao `credor_whatsapp`
do Tenant — o destino do resumo diario e do aviso de sobra. Antes, esse numero
so existia por SQL direto na tabela `configuracao`.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.db.session import get_session_factory
from emprestimo.infrastructure.repositories import (
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "segredo-api-whatsapp-avisos"
LER = "whatsapp.conexao.ler"
GERIR = "whatsapp.conexao.gerir"
ROTA = "/platform/whatsapp/avisos"
NUMERO = "5511999998888"
OUTRO = "5562988887777"


@dataclass(frozen=True)
class _Autenticado:
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


def _headers(token: str, *, idempotency: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if idempotency is not None:
        headers["Idempotency-Key"] = idempotency
    return headers


def _autenticar(session: Session, *permissoes: str) -> _Autenticado:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(
        tenant_id=tenant.id, estado=UsuarioState.ATIVO, perfil_acesso="OperadorWhatsApp"
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    perfil = PerfilAcesso(tenant_id=tenant.id, nome="OperadorWhatsApp")
    for codigo in permissoes:
        perfil.adicionar_permissao(Permissao(codigo=codigo, descricao=codigo))
    repo = SqlAlchemyPerfilAcessoRepository(session)
    repo.save(perfil)
    repo.atribuir_usuario(usuario.id, perfil.id)
    session.commit()
    return _Autenticado(usuario, tenant, HmacAccessTokenService(JWT_SECRET).emitir(usuario).token)


def test_sem_numero_cadastrado_devolve_nulo(client: TestClient, session: Session) -> None:
    autenticado = _autenticar(session, LER)

    resposta = client.get(ROTA, headers=_headers(autenticado.token))

    assert resposta.status_code == 200
    assert resposta.json() == {"numero": None}


def test_gravar_normaliza_e_a_leitura_devolve_o_numero(
    client: TestClient, session: Session
) -> None:
    autenticado = _autenticar(session, LER, GERIR)

    gravado = client.put(
        ROTA,
        json={"numero": "+55 (11) 99999-8888"},
        headers=_headers(autenticado.token, idempotency=str(uuid.uuid4())),
    )
    lido = client.get(ROTA, headers=_headers(autenticado.token))

    assert gravado.status_code == 200
    assert gravado.json() == {"numero": "5511999998888"}
    assert lido.json() == {"numero": "5511999998888"}
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        configuracoes = uow.configuracao.find_by_tenant_id(autenticado.tenant.id)
        chaves = {c.chave: c.valor for c in configuracoes}
    assert chaves["credor_whatsapp"] == "5511999998888"


def test_gravar_de_novo_substitui_sem_duplicar_a_chave(
    client: TestClient, session: Session
) -> None:
    autenticado = _autenticar(session, LER, GERIR)
    for numero in ("5511999998888", "5562988887777"):
        resposta = client.put(
            ROTA,
            json={"numero": numero},
            headers=_headers(autenticado.token, idempotency=str(uuid.uuid4())),
        )
        assert resposta.status_code == 200

    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        linhas = [
            c
            for c in uow.configuracao.find_by_tenant_id(autenticado.tenant.id)
            if c.chave == "credor_whatsapp"
        ]
    assert [c.valor for c in linhas] == ["5562988887777"]


@pytest.mark.parametrize("numero", ["", "abc", "123", "55119999988881234567"])
def test_numero_invalido_responde_400_e_nao_grava(
    client: TestClient, session: Session, numero: str
) -> None:
    autenticado = _autenticar(session, LER, GERIR)

    resposta = client.put(
        ROTA, json={"numero": numero}, headers=_headers(autenticado.token, idempotency="k-1")
    )

    assert resposta.status_code == 400
    assert client.get(ROTA, headers=_headers(autenticado.token)).json() == {"numero": None}


def test_put_exige_idempotency_key(client: TestClient, session: Session) -> None:
    autenticado = _autenticar(session, LER, GERIR)

    resposta = client.put(ROTA, json={"numero": NUMERO}, headers=_headers(autenticado.token))

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_replay_com_mesma_chave_devolve_o_mesmo_e_chave_com_numero_diferente_conflita(
    client: TestClient, session: Session
) -> None:
    autenticado = _autenticar(session, LER, GERIR)
    chave = str(uuid.uuid4())

    primeira = client.put(
        ROTA, json={"numero": NUMERO}, headers=_headers(autenticado.token, idempotency=chave)
    )
    replay = client.put(
        ROTA, json={"numero": NUMERO}, headers=_headers(autenticado.token, idempotency=chave)
    )
    divergente = client.put(
        ROTA, json={"numero": OUTRO}, headers=_headers(autenticado.token, idempotency=chave)
    )

    assert primeira.status_code == replay.status_code == 200
    assert divergente.status_code == 409


def test_permissao_de_leitura_nao_autoriza_gravar(client: TestClient, session: Session) -> None:
    autenticado = _autenticar(session, LER)

    resposta = client.put(
        ROTA, json={"numero": NUMERO}, headers=_headers(autenticado.token, idempotency="k-2")
    )

    assert resposta.status_code == 403


def test_sem_token_responde_401(client: TestClient) -> None:
    assert client.get(ROTA).status_code == 401
    assert client.put(ROTA, json={"numero": NUMERO}).status_code == 401


def test_as_duas_operacoes_estao_no_contrato() -> None:
    schema = create_app().openapi()

    assert set(schema["paths"][ROTA]) == {"get", "put"}
