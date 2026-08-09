"""Testes de integração da API de Devedores (IMP-057..IMP-059) — PostgreSQL real.

Diferente dos testes de contrato em ``tests/unit/presentation``, aqui os casos
de uso são os reais e a persistência acontece de fato: o que se verifica é o
caminho completo requisição → caso de uso → banco → resposta.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory

from emprestimo.application.autorizacao import Principal
from emprestimo.application.cadastro_devedor import DevedorCadastroService
from emprestimo.application.consulta_devedor import (
    DevedorConsultaPorDocumentoService,
    DevedorConsultaService,
    DevedorListagemService,
)
from emprestimo.application.estado_devedor import DevedorEstadoService
from emprestimo.application.historico_devedor import DevedorHistoricoService
from emprestimo.domain.credit.unicidade_devedor import UnicidadeDevedorService
from emprestimo.infrastructure.auditoria import (
    SqlAlchemyAuditoriaConsulta,
    SqlAlchemyAuditoriaRegistro,
)
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyTenantRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

CPF_A = "52998224725"
CPF_B = "11144477735"
PRINCIPAL_TESTE = Principal(
    usuario_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
    tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
    perfil_acesso="Teste",
    access_token_expira_em=datetime.now(UTC) + timedelta(minutes=15),
)

PAYLOAD = {
    "documento": CPF_A,
    "nome": "João da Silva",
    "contatos": [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}],
}


def _carteira_persistida(session: Session) -> str:
    tenant = TenantFactory.build(id=PRINCIPAL_TESTE.tenant_id)
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    session.commit()
    return str(carteira.id)


@pytest.fixture
def carteira_id(session: Session) -> str:
    return _carteira_persistida(session)


@pytest.fixture
def outra_carteira_id(session: Session) -> str:
    """Segunda Carteira real — usada nos testes de pertinência (ADR-018)."""
    return _carteira_persistida(session)


@pytest.fixture
def client(session_factory: sessionmaker[Session], session: Session) -> Iterator[TestClient]:
    app = create_app()

    def _uow() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    def _auditoria() -> SqlAlchemyAuditoriaRegistro:
        return SqlAlchemyAuditoriaRegistro(session_factory)

    app.dependency_overrides[dependencies.get_devedor_cadastro_service] = lambda: (
        DevedorCadastroService(
            uow_factory=_uow,
            unicidade=UnicidadeDevedorService(SqlAlchemyDevedorRepository(session)),
            auditoria=_auditoria(),
        )
    )
    app.dependency_overrides[dependencies.get_devedor_consulta_service] = lambda: (
        DevedorConsultaService(uow_factory=_uow)
    )
    app.dependency_overrides[dependencies.get_devedor_consulta_por_documento_service] = (
        lambda: DevedorConsultaPorDocumentoService(uow_factory=_uow)
    )
    app.dependency_overrides[dependencies.get_devedor_listagem_service] = lambda: (
        DevedorListagemService(uow_factory=_uow)
    )
    app.dependency_overrides[dependencies.get_devedor_estado_service] = lambda: (
        DevedorEstadoService(uow_factory=_uow, auditoria=_auditoria())
    )
    app.dependency_overrides[dependencies.get_devedor_historico_service] = lambda: (
        DevedorHistoricoService(
            uow_factory=_uow,
            auditoria_consulta=SqlAlchemyAuditoriaConsulta(session),
        )
    )
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL_TESTE
    autorizacao = Mock()
    autorizacao.exigir_permissao.return_value = None
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    with TestClient(app) as c:
        yield c


def _criar(client: TestClient, carteira_id: str, chave: str, **campos: object) -> Response:
    return cast(
        Response,
        client.post(
            f"/credit/carteiras/{carteira_id}/devedores",
            json={**PAYLOAD, **campos},
            headers={"Idempotency-Key": chave},
        ),
    )


def test_post_persiste_e_consulta_recupera(client: TestClient, carteira_id: str) -> None:
    resp = _criar(client, carteira_id, "chave-1")

    assert resp.status_code == 201
    devedor_id = resp.json()["id"]

    obtido = client.get(f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}")
    assert obtido.status_code == 200
    assert obtido.json()["documento"] == CPF_A
    assert obtido.json()["estado"] == "ativo"
    assert len(obtido.json()["contatos"]) == 1


def test_post_documento_duplicado_409(client: TestClient, carteira_id: str) -> None:
    """Regressão: a unicidade precisa chegar ao cliente como 409, não 500."""
    assert _criar(client, carteira_id, "chave-1").status_code == 201

    resp = _criar(client, carteira_id, "chave-2", nome="Outro Nome")

    assert resp.status_code == 409
    assert resp.json()["codigo"] == "devedor_ja_existe"


def test_post_cpf_invalido_422(client: TestClient, carteira_id: str) -> None:
    """Dígitos verificadores inválidos são recusados pelo Value Object."""
    resp = _criar(client, carteira_id, "chave-cpf", documento="11111111111")

    assert resp.status_code == 422


def test_replay_mesma_chave_nao_duplica(client: TestClient, carteira_id: str) -> None:
    primeira = _criar(client, carteira_id, "chave-replay")
    segunda = _criar(client, carteira_id, "chave-replay")

    assert primeira.status_code == 201
    assert segunda.status_code == 201
    assert primeira.json()["id"] == segunda.json()["id"]

    listagem = client.get(f"/credit/carteiras/{carteira_id}/devedores")
    assert listagem.json()["total"] == 1


def test_consulta_por_documento(client: TestClient, carteira_id: str) -> None:
    _criar(client, carteira_id, "chave-1")

    resp = client.get(f"/credit/carteiras/{carteira_id}/devedores", params={"documento": CPF_A})

    assert resp.status_code == 200
    assert resp.json()["documento"] == CPF_A


def test_listagem_com_filtro_de_estado(client: TestClient, carteira_id: str) -> None:
    _criar(client, carteira_id, "chave-1")
    segundo = _criar(client, carteira_id, "chave-2", documento=CPF_B, nome="Ana Souza")
    client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{segundo.json()['id']}/inativar",
        headers={"Idempotency-Key": "chave-inativar"},
    )

    resp = client.get(f"/credit/carteiras/{carteira_id}/devedores", params={"estado": "inativo"})

    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["nome"] == "Ana Souza"


def test_inativar_e_reativar_persistem(client: TestClient, carteira_id: str) -> None:
    devedor_id = _criar(client, carteira_id, "chave-1").json()["id"]

    inativado = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar",
        headers={"Idempotency-Key": "chave-inativar"},
    )
    assert inativado.status_code == 200
    assert inativado.json()["estado"] == "inativo"
    assert (
        client.get(f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}").json()["estado"]
        == "inativo"
    )

    reativado = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/reativar",
        headers={"Idempotency-Key": "chave-reativar"},
    )
    assert reativado.status_code == 200
    assert reativado.json()["estado"] == "ativo"
    assert (
        client.get(f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}").json()["estado"]
        == "ativo"
    )


def test_historico_reconstitui_as_alteracoes(client: TestClient, carteira_id: str) -> None:
    """US-027: a trilha gravada pelas escritas é o que a consulta devolve."""
    devedor_id = _criar(client, carteira_id, "chave-1").json()["id"]
    client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar",
        headers={"Idempotency-Key": "chave-inativar"},
    )

    resp = client.get(f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/historico")

    assert resp.status_code == 200
    acoes = [e["acao"] for e in resp.json()["eventos"]]
    assert "criar.aggregate_criado" in acoes
    assert "inativar.estado_alterado" in acoes
    assert "inativar.sucesso" in acoes
    # Ordem cronológica: a criação precede a inativação
    assert acoes.index("criar.aggregate_criado") < acoes.index("inativar.sucesso")
    for evento in resp.json()["eventos"]:
        assert evento["criado_em"]
        assert evento["status"]


def test_historico_devedor_inexistente_404(client: TestClient, carteira_id: str) -> None:
    resp = client.get(f"/credit/carteiras/{carteira_id}/devedores/{uuid.uuid4()}/historico")

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "devedor_nao_encontrado"


def test_historico_isolado_por_devedor(client: TestClient, carteira_id: str) -> None:
    """Cada Devedor só enxerga a própria trilha."""
    primeiro = _criar(client, carteira_id, "chave-1").json()["id"]
    segundo = _criar(client, carteira_id, "chave-2", documento=CPF_B, nome="Ana Souza").json()["id"]
    client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{segundo}/inativar",
        headers={"Idempotency-Key": "chave-inativar"},
    )

    do_primeiro = client.get(
        f"/credit/carteiras/{carteira_id}/devedores/{primeiro}/historico"
    ).json()

    assert do_primeiro["devedor_id"] == primeiro
    assert all("inativar" not in e["acao"] for e in do_primeiro["eventos"])


def test_historico_nao_gera_trilha(client: TestClient, carteira_id: str) -> None:
    """ADR-002: leitura não é auditada — consultar não aumenta a trilha."""
    devedor_id = _criar(client, carteira_id, "chave-1").json()["id"]
    antes = len(
        client.get(f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/historico").json()[
            "eventos"
        ]
    )

    depois = len(
        client.get(f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/historico").json()[
            "eventos"
        ]
    )

    assert depois == antes


# --- ADR-018: pertinência Carteira ↔ Devedor, com duas Carteiras reais ---


@pytest.mark.parametrize(
    ("metodo", "sufixo", "corpo"),
    [
        ("get", "", None),
        ("get", "/historico", None),
        ("patch", "", {"nome": "João Santos"}),
        ("post", "/inativar", None),
        ("post", "/reativar", None),
    ],
)
def test_devedor_de_outra_carteira_404(
    client: TestClient,
    carteira_id: str,
    outra_carteira_id: str,
    metodo: str,
    sufixo: str,
    corpo: dict[str, object] | None,
) -> None:
    """Devedor existente na Carteira A, requisitado sob a Carteira B: 404."""
    devedor_id = _criar(client, carteira_id, "chave-1").json()["id"]

    url = f"/credit/carteiras/{outra_carteira_id}/devedores/{devedor_id}{sufixo}"
    kwargs: dict[str, Any] = {"headers": {"Idempotency-Key": "chave-x"}}
    if corpo is not None:
        kwargs["json"] = corpo

    resp = cast(Response, getattr(client, metodo)(url, **kwargs))

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "devedor_nao_encontrado"


def test_escrita_sob_carteira_errada_nao_altera_o_devedor(
    client: TestClient, carteira_id: str, outra_carteira_id: str
) -> None:
    """A pertinência barra antes do caso de uso: o estado permanece intacto."""
    devedor_id = _criar(client, carteira_id, "chave-1").json()["id"]

    barrada = client.post(
        f"/credit/carteiras/{outra_carteira_id}/devedores/{devedor_id}/inativar",
        headers={"Idempotency-Key": "chave-x"},
    )

    assert barrada.status_code == 404
    atual = client.get(f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}")
    assert atual.json()["estado"] == "ativo"


def test_inativar_duas_vezes_viola_inv005(client: TestClient, carteira_id: str) -> None:
    devedor_id = _criar(client, carteira_id, "chave-1").json()["id"]
    client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar",
        headers={"Idempotency-Key": "chave-inativar"},
    )

    resp = client.post(
        f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar",
        headers={"Idempotency-Key": "chave-inativar-2"},
    )

    assert resp.status_code == 422
    assert resp.json()["codigo"] == "regra_violada"
