"""Catálogo Operadora contra a API real (IMP-356-D, T4).

Nada mockado abaixo da borda HTTP, exceto a identidade: o app é o
`create_app()` de produção, os serviços e o PostgreSQL são os reais, o
transporte é ASGI em-processo. Só `get_principal_atual` e a autorização
são substituídas — a matriz de permissões em si já é coberta por
`test_api_authorization.py`; aqui se prova contrato, mascaramento e
fail-closed das seis rotas do catálogo, de ponta a ponta
(dispatcher → HTTP → serviço → banco → apresentador).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.orm import Session
from starlette.testclient import TestClient
from tests.factories import CarteiraFactory, TenantFactory

from emprestimo.agent.api_client import ApiAusenciaError, ClienteApi
from emprestimo.agent.apresentadores import renderizar
from emprestimo.agent.dispatcher import ContextoFerramentas, executar_ferramenta
from emprestimo.application.autorizacao import Principal
from emprestimo.application.errors import AcessoNegadoError
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyTenantRepository,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

HOJE = date(2026, 9, 14)
CPF = "52998224725"
NOME = "Maria da Conceição Silva"

PRINCIPAL = Principal(
    usuario_id=uuid.uuid4(),
    tenant_id=uuid.uuid4(),
    perfil_acesso="Operadora",
    access_token_expira_em=datetime.now(UTC) + timedelta(minutes=15),
)


@pytest.fixture
def base(session: Session) -> dict[str, Any]:
    tenant = TenantFactory.build(id=PRINCIPAL.tenant_id)
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    devedor = Devedor.criar(
        carteira_id=carteira.id,
        documento=Documento.from_str(CPF),
        nome=NOME,
        contatos=[
            Contato(
                devedor_id=uuid.uuid4(),
                tipo=TipoContato.TELEFONE,
                valor="(11) 1234-5678",
                preferencial=True,
            )
        ],
    )
    SqlAlchemyDevedorRepository(session).save(devedor)
    session.commit()
    return {"carteira": carteira, "devedor": devedor}


def _app_liberado(carteira: Carteira) -> FastAPI:
    app = create_app()
    autorizacao = Mock()
    autorizacao.exigir_permissao.return_value = None
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    app.dependency_overrides[dependencies.get_carteira_do_principal] = lambda: carteira
    return app


def _contexto(carteira_id: uuid.UUID, refs: dict[str, str]) -> ContextoFerramentas:
    return ContextoFerramentas(
        carteira_id=str(carteira_id),
        resolvedor_devedor=lambda ref: refs.get(ref),
        hoje=HOJE,
    )


def test_ponta_a_ponta_localizar_mascara_e_resolve(base: dict[str, Any]) -> None:
    carteira: Carteira = base["carteira"]
    devedor: Devedor = base["devedor"]
    app = _app_liberado(carteira)
    transporte = httpx.ASGITransport(app=app)
    cliente = ClienteApi("https://api.exemplo", lambda: "token", transporte=transporte)

    async def _cenario() -> dict[str, Any]:
        return await executar_ferramenta(
            cliente, _contexto(carteira.id, {}), "localizar_devedor", {"nome": "Conceição"}
        )

    dto = asyncio.run(_cenario())
    asyncio.run(cliente.close())
    assert dto["total"] >= 1
    item = next(i for i in dto["items"] if i["id"] == str(devedor.id))
    assert item["nome"] == NOME
    texto = renderizar("localizar_devedor", dto, {str(devedor.id): "ref-1"})
    assert "Maria D. C. S." in texto
    assert CPF not in texto and "***25" in texto
    assert "(11)" not in texto


def test_ponta_a_ponta_saldo_zerado_resumo_e_relatorios_vazios(base: dict[str, Any]) -> None:
    carteira: Carteira = base["carteira"]
    devedor: Devedor = base["devedor"]
    app = _app_liberado(carteira)
    transporte = httpx.ASGITransport(app=app)
    cliente = ClienteApi("https://api.exemplo", lambda: "token", transporte=transporte)
    ctx = _contexto(carteira.id, {"ref-1": str(devedor.id)})

    async def _cenario() -> dict[str, dict[str, Any]]:
        return {
            "saldo": await executar_ferramenta(
                cliente, ctx, "consultar_saldo_devedor", {"devedor_ref": "ref-1"}
            ),
            "resumo": await executar_ferramenta(cliente, ctx, "consultar_resumo_carteira", {}),
            "acertos": await executar_ferramenta(cliente, ctx, "consultar_acertos", {}),
            "pagamentos": await executar_ferramenta(
                cliente,
                ctx,
                "consultar_pagamentos_periodo",
                {"inicio": "2026-09-01", "fim": "2026-09-14"},
            ),
            "fluxo": await executar_ferramenta(
                cliente,
                ctx,
                "consultar_fluxo_realizado",
                {"inicio": "2026-09-01", "fim": "2026-09-14"},
            ),
        }

    saidas = asyncio.run(_cenario())
    asyncio.run(cliente.close())
    assert saidas["saldo"]["total"] == "0.00"
    assert "Sem empréstimos ativos" in renderizar("consultar_saldo_devedor", saidas["saldo"])
    assert saidas["resumo"]["principal_a_receber"] == "0.00"
    assert "999999" not in renderizar("consultar_resumo_carteira", saidas["resumo"])
    assert saidas["acertos"]["itens"] == []
    assert saidas["pagamentos"]["pagamentos"] == []
    assert saidas["fluxo"]["itens"] == []


def test_saldo_de_devedor_inexistente_e_404_neutro(base: dict[str, Any]) -> None:
    carteira: Carteira = base["carteira"]
    app = _app_liberado(carteira)
    transporte = httpx.ASGITransport(app=app)
    cliente = ClienteApi("https://api.exemplo", lambda: "token", transporte=transporte)
    ctx = _contexto(carteira.id, {"ref-x": str(uuid.uuid4())})

    async def _cenario() -> None:
        with pytest.raises(ApiAusenciaError):
            await executar_ferramenta(
                cliente, ctx, "consultar_saldo_devedor", {"devedor_ref": "ref-x"}
            )

    asyncio.run(_cenario())
    asyncio.run(cliente.close())


def test_negacao_de_permissao_fecha_as_seis_rotas_sem_detalhe(base: dict[str, Any]) -> None:
    carteira: Carteira = base["carteira"]
    app = create_app()
    autorizacao = Mock()
    autorizacao.exigir_permissao.side_effect = AcessoNegadoError("sem acesso")
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    app.dependency_overrides[dependencies.get_carteira_do_principal] = lambda: carteira
    cid = str(carteira.id)
    rotas = [
        f"/credit/carteiras/{cid}/devedores?nome=x",
        f"/credit/devedores/{uuid.uuid4()}/saldo?data_referencia=2026-09-14",
        f"/credit/carteiras/{cid}/relatorios/resumo?data_referencia=2026-09-14",
        f"/credit/carteiras/{cid}/relatorios/vencimentos?data_referencia=2026-09-14",
        f"/credit/carteiras/{cid}/relatorios/pagamentos?inicio=2026-09-01&fim=2026-09-14",
        f"/credit/carteiras/{cid}/relatorios/fluxo?inicio=2026-09-01&fim=2026-09-14",
    ]
    with TestClient(app) as client:
        for rota in rotas:
            resposta = client.get(rota)
            assert resposta.status_code == 403, rota
            corpo = resposta.text.lower()
            assert "traceback" not in corpo and "sql" not in corpo


def test_sem_bearer_as_rotas_exigem_autenticacao(
    base: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Cadeia real até o serviço (só o segredo é de teste): sem Bearer, 401.
    monkeypatch.setenv("JWT_SECRET_KEY", "segredo-de-teste-com-48-caracteres-0123456789ab")
    app = create_app()
    cid = str(base["carteira"].id)
    with TestClient(app) as client:
        resposta = client.get(f"/credit/carteiras/{cid}/devedores?nome=x")
        assert resposta.status_code == 401
        assert resposta.json()["codigo"] == "autenticacao_recusada"
