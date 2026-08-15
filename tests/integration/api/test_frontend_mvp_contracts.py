"""Contratos de hardening que desbloqueiam o Frontend MVP (PLAN-025)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.testclient import TestClient
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.application.iam_catalogo import CATALOGO_PERMISSOES, CATALOGO_POR_CODIGO
from emprestimo.domain.platform.perfil import PerfilAcesso, PerfilState
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "segredo-frontend-mvp-contracts"
ROOT = Path(__file__).resolve().parents[3]
OPENAPI_SNAPSHOT = ROOT / "docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json"


@dataclass(frozen=True)
class AmbienteContexto:
    usuario: Usuario
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None
    perfil_id: uuid.UUID | None
    token: str


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, JWT_SECRET)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _criar_contexto(
    session: Session,
    *,
    com_carteira: bool = True,
    com_perfil: bool = True,
    permissoes: tuple[str, ...] = ("devedor.ler",),
    perfil_estado: PerfilState = PerfilState.ATIVO,
) -> AmbienteContexto:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    usuario = UsuarioFactory.build(tenant_id=tenant.id, estado=UsuarioState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    SqlAlchemyUsuarioRepository(session).save(usuario)

    carteira_id: uuid.UUID | None = None
    if com_carteira:
        carteira = CarteiraFactory.build(tenant_id=tenant.id, nome="Carteira Principal")
        SqlAlchemyCarteiraRepository(session).save(carteira)
        carteira_id = carteira.id

    perfil_id: uuid.UUID | None = None
    if com_perfil:
        perfil = PerfilAcesso(tenant_id=tenant.id, nome="operador")
        for codigo in permissoes:
            perfil.adicionar_permissao(CATALOGO_POR_CODIGO[codigo])
        if perfil_estado is PerfilState.INATIVO:
            perfil.inativar()
        repo_perfil = SqlAlchemyPerfilAcessoRepository(session)
        repo_perfil.save(perfil)
        repo_perfil.atribuir_usuario(usuario.id, perfil.id)
        perfil_id = perfil.id

    session.commit()
    return AmbienteContexto(
        usuario=usuario,
        tenant_id=tenant.id,
        carteira_id=carteira_id,
        perfil_id=perfil_id,
        token=HmacAccessTokenService(JWT_SECRET).emitir(usuario).token,
    )


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_imp_276_openapi_publica_contexto_corrente_sem_ids_arbitrarios() -> None:
    operacao = create_app().openapi()["paths"]["/iam/contexto-atual"]["get"]

    parametros = {
        (parametro["in"], parametro["name"]) for parametro in operacao.get("parameters", [])
    }
    assert (
        not {
            ("path", "usuario_id"),
            ("query", "usuario_id"),
            ("query", "tenant_id"),
            ("query", "carteira_id"),
        }
        & parametros
    )
    schema = operacao["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/ContextoOperacionalResponse"}


def test_imp_276_contexto_retorna_exclusivamente_o_principal(
    client: TestClient,
    session: Session,
) -> None:
    ambiente = _criar_contexto(session)

    resposta = client.get(
        "/iam/contexto-atual",
        params={
            "usuario_id": str(uuid.uuid4()),
            "tenant_id": str(uuid.uuid4()),
            "carteira_id": str(uuid.uuid4()),
        },
        headers=_headers(ambiente.token),
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["usuario"]["id"] == str(ambiente.usuario.id)
    assert corpo["tenant"]["id"] == str(ambiente.tenant_id)
    assert corpo["carteira_padrao"]["id"] == str(ambiente.carteira_id)
    assert corpo["perfil"]["id"] == str(ambiente.perfil_id)
    assert corpo["permissoes"] == ["devedor.ler"]


def test_imp_276_contexto_sem_perfil_nao_concede_permissao(
    client: TestClient,
    session: Session,
) -> None:
    ambiente = _criar_contexto(session, com_perfil=False)

    resposta = client.get("/iam/contexto-atual", headers=_headers(ambiente.token))

    assert resposta.status_code == 200
    assert resposta.json()["perfil"] is None
    assert resposta.json()["permissoes"] == []


def test_imp_276_contexto_com_perfil_inativo_falha_fechado(
    client: TestClient,
    session: Session,
) -> None:
    ambiente = _criar_contexto(session, perfil_estado=PerfilState.INATIVO)

    resposta = client.get("/iam/contexto-atual", headers=_headers(ambiente.token))

    assert resposta.status_code == 200
    assert resposta.json()["perfil"]["id"] == str(ambiente.perfil_id)
    assert resposta.json()["permissoes"] == []


def test_imp_276_contexto_sem_carteira_padrao_e_conflito_seguro(
    client: TestClient,
    session: Session,
) -> None:
    ambiente = _criar_contexto(session, com_carteira=False)

    resposta = client.get("/iam/contexto-atual", headers=_headers(ambiente.token))

    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "contexto_operacional_incompleto",
        "mensagem": "Contexto operacional corrente indisponivel",
    }


def test_imp_276_contexto_exige_autenticacao(client: TestClient) -> None:
    resposta = client.get("/iam/contexto-atual")

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "autenticacao_recusada"


def test_imp_278_openapi_publica_catalogo_tipado_e_protegido() -> None:
    operacao = create_app().openapi()["paths"]["/iam/permissoes"]["get"]

    schema = operacao["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/PermissoesCatalogoResponse"}
    assert {"401", "403"} <= set(operacao["responses"])


def test_imp_278_catalogo_reflete_fonte_canonica_versionada(
    client: TestClient,
    session: Session,
) -> None:
    ambiente = _criar_contexto(session, permissoes=("perfil.ler",))

    resposta = client.get("/iam/permissoes", headers=_headers(ambiente.token))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["versao"] == "1.0.0"
    assert [item["codigo"] for item in corpo["itens"]] == sorted(
        permissao.codigo for permissao in CATALOGO_PERMISSOES
    )
    assert len(corpo["itens"]) == len(CATALOGO_PERMISSOES) == 55
    assert all(item["grupo"] == item["codigo"].split(".", maxsplit=1)[0] for item in corpo["itens"])


def test_imp_278_catalogo_exige_perfil_ler(
    client: TestClient,
    session: Session,
) -> None:
    ambiente = _criar_contexto(session)

    negado = client.get("/iam/permissoes", headers=_headers(ambiente.token))
    sem_token = client.get("/iam/permissoes")

    assert negado.status_code == 403
    assert negado.json()["codigo"] == "acesso_negado"
    assert sem_token.status_code == 401
    assert sem_token.json()["codigo"] == "autenticacao_recusada"


@pytest.mark.parametrize(
    ("path", "schema_name"),
    (
        ("/auth/ativar", "AtivacaoRequest"),
        ("/auth/login", "AuthLoginRequest"),
        ("/auth/refresh", "AuthRefreshRequest"),
        ("/auth/logout", "AuthRefreshRequest"),
    ),
)
def test_imp_280_auth_publica_request_body_especifico(
    path: str,
    schema_name: str,
) -> None:
    operacao = create_app().openapi()["paths"][path]["post"]

    assert operacao["requestBody"]["required"] is True
    schema = operacao["requestBody"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": f"#/components/schemas/{schema_name}"}
    assert _response_ref(operacao, "400") == "#/components/schemas/ErroResponse"


def test_imp_281_idempotency_key_runtime_e_openapi_sao_obrigatorios() -> None:
    app = create_app()
    contrato = app.openapi()
    inventario: list[tuple[str, str, bool]] = []

    for inclusao in app.routes:
        router = getattr(inclusao, "original_router", None)
        if router is None:
            continue
        for rota in router.routes:
            if not isinstance(rota, APIRoute):
                continue
            campos = [
                campo for campo in rota.dependant.header_params if campo.alias == "Idempotency-Key"
            ]
            for campo in campos:
                assert rota.methods is not None
                for metodo in rota.methods:
                    inventario.append((rota.path, metodo.lower(), campo.field_info.is_required()))

    assert len(inventario) == 30
    assert all(required for _, _, required in inventario)
    for path, metodo, _ in inventario:
        parametros = contrato["paths"][path][metodo]["parameters"]
        header = next(
            parametro
            for parametro in parametros
            if parametro["in"] == "header" and parametro["name"] == "Idempotency-Key"
        )
        assert header["required"] is True
        assert header["schema"]["minLength"] == 1
        assert header["schema"]["maxLength"] == 255


def _response_ref(operacao: dict[str, object], status: str) -> str | None:
    responses = operacao.get("responses", {})
    assert isinstance(responses, dict)
    response = responses.get(status)
    if not isinstance(response, dict):
        return None
    content = response.get("content", {})
    if not isinstance(content, dict):
        return None
    media = content.get("application/json", {})
    if not isinstance(media, dict):
        return None
    schema = media.get("schema", {})
    return schema.get("$ref") if isinstance(schema, dict) else None


def test_imp_282_openapi_alinha_validacao_400_e_regra_422() -> None:
    contrato = create_app().openapi()
    metodos = {"get", "post", "put", "patch", "delete"}
    automaticos_422: list[str] = []
    sem_400: list[str] = []

    for path, path_item in contrato["paths"].items():
        for metodo, operacao in path_item.items():
            if metodo not in metodos:
                continue
            ref_422 = _response_ref(operacao, "422")
            if ref_422 == "#/components/schemas/HTTPValidationError":
                automaticos_422.append(f"{metodo.upper()} {path}")
            parametros_validaveis = [
                parametro
                for parametro in operacao.get("parameters", [])
                if parametro.get("name") != "X-Correlation-ID"
            ]
            tem_entrada = bool(operacao.get("requestBody") or parametros_validaveis)
            if (
                tem_entrada
                and _response_ref(operacao, "400") != "#/components/schemas/ErroResponse"
            ):
                sem_400.append(f"{metodo.upper()} {path}")
            for status in ("400", "422"):
                if status in operacao["responses"]:
                    assert _response_ref(operacao, status) == ("#/components/schemas/ErroResponse")

    assert automaticos_422 == []
    assert sem_400 == []
    assert "HTTPValidationError" not in contrato["components"]["schemas"]
    assert "ValidationError" not in contrato["components"]["schemas"]
    comando = contrato["paths"]["/platform/tenants/{tenant_id}"]["patch"]
    assert _response_ref(comando, "422") == "#/components/schemas/ErroResponse"
    for acao in ("inativar", "reativar"):
        transicao = contrato["paths"][f"/platform/tenants/{{tenant_id}}/{acao}"]["post"]
        assert "422" not in transicao["responses"]
        assert _response_ref(transicao, "409") == "#/components/schemas/ErroResponse"
    contexto = contrato["paths"]["/iam/contexto-atual"]["get"]
    assert "403" not in contexto["responses"]
    assert _response_ref(contexto, "409") == "#/components/schemas/ErroResponse"
    operacoes_422 = {
        (metodo, path)
        for path, path_item in contrato["paths"].items()
        for metodo, operacao in path_item.items()
        if metodo in metodos and "422" in operacao["responses"]
    }
    assert operacoes_422 == {
        ("post", "/auth/ativar"),
        ("patch", "/platform/tenants/{tenant_id}"),
        ("patch", "/iam/credencial"),
        ("post", "/iam/usuarios/{usuario_id}/credencial/redefinir"),
        ("post", "/iam/perfis"),
        ("patch", "/iam/perfis/{perfil_id}"),
        ("post", "/iam/perfis/{perfil_id}/inativar"),
        ("put", "/iam/perfis/{perfil_id}/permissoes/{codigo}"),
        ("delete", "/iam/perfis/{perfil_id}/permissoes/{codigo}"),
        ("post", "/credit/configuracoes-financeiras/modalidades"),
        ("post", "/credit/configuracoes-financeiras/calendarios"),
        ("post", "/credit/configuracoes-financeiras"),
        ("get", "/credit/configuracoes-financeiras"),
        ("get", "/credit/configuracoes-financeiras/vigente"),
        ("post", "/credit/notificacoes/templates"),
        ("post", "/credit/carteiras/{carteira_id}/devedores"),
        ("patch", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}"),
        ("post", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar"),
        ("post", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/reativar"),
        (
            "post",
            "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais",
        ),
        (
            "post",
            "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
        ),
        ("patch", "/credit/propostas-comerciais/{proposta_id}"),
        ("get", "/credit/propostas-comerciais/{proposta_id}/contrato-logico"),
        ("post", "/credit/carteiras/{carteira_id}/contratos"),
    }
    credencial_propria = contrato["paths"]["/iam/credencial"]["patch"]
    assert "409" not in credencial_propria["responses"]
    vigente = contrato["paths"]["/credit/configuracoes-financeiras/vigente"]["get"]
    assert _response_ref(vigente, "409") == "#/components/schemas/ErroResponse"


def test_imp_283_snapshot_openapi_e_deterministico() -> None:
    esperado = (
        json.dumps(
            create_app().openapi(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    assert OPENAPI_SNAPSHOT.read_bytes() == esperado
