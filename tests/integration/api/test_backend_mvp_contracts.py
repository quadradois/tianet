"""Recertificacao P4 de OpenAPI, matriz HTTP e docs historicos."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from tests.factories import UsuarioFactory
from tests.integration.api.test_backend_mvp_e2e import AmbienteMVP, ambiente_mvp
from tests.integration.api.test_backend_mvp_security import _devedor_payload

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.usuario import UsuarioState
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCredencialRepository,
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.presentation.api.auth_routes import router as auth_router
from emprestimo.presentation.api.automacao_routes import router as automacao_router
from emprestimo.presentation.api.comercial_routes import router as comercial_router
from emprestimo.presentation.api.configuracoes_financeiras_routes import (
    router as configuracoes_financeiras_router,
)
from emprestimo.presentation.api.contratos_routes import router as contratos_router
from emprestimo.presentation.api.devedores_routes import router as devedores_router
from emprestimo.presentation.api.iam_routes import router as iam_router
from emprestimo.presentation.api.lancamento_routes import router as lancamento_router
from emprestimo.presentation.api.main import create_app
from emprestimo.presentation.api.motor_routes import router as motor_router
from emprestimo.presentation.api.observability_routes import router as observability_router
from emprestimo.presentation.api.operacao_diaria_routes import router as operacao_diaria_router
from emprestimo.presentation.api.routes import router as platform_router

__all__ = ["ambiente_mvp"]

ROOT = Path(__file__).resolve().parents[3]
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
PUBLIC_PREFIXES = ("/auth/",)
PUBLIC_PATHS = {"/health"}
ERRO_RESPONSE_REF = {"$ref": "#/components/schemas/ErroResponse"}
EXPECTED_STATUS_MATRIX = {
    400: {
        ("get", "/credit/carteiras/{carteira_id}/relatorios/pagamentos"),
        ("post", "/credit/automacao/jobs/{job_id}/retry"),
        ("post", "/credit/emprestimos/{emprestimo_id}/pagamentos"),
    },
    401: {("get", "/platform/tenants")},
    403: {("get", "/platform/tenants")},
    404: {
        ("get", "/platform/tenants/{tenant_id}"),
        ("post", "/credit/carteiras/{carteira_id}/devedores"),
        ("post", "/credit/automacao/jobs/{job_id}/retry"),
    },
    409: {
        ("post", "/credit/propostas-comerciais/{proposta_id}/aprovar"),
        ("post", "/credit/contratos/{contrato_id}/liberar-para-motor"),
        ("post", "/credit/emprestimos/{emprestimo_id}/pagamentos"),
        ("post", "/credit/automacao/jobs/{job_id}/retry"),
    },
}


@dataclass(frozen=True)
class HttpMatrixSample:
    status: int
    method: str
    path: str
    kwargs: dict[str, Any]
    codigo: str


def test_imp_269_openapi_cobre_routers_reais_e_contratos_transversais() -> None:
    schema = create_app().openapi()
    operations = _operations(schema)
    router_operations = _router_operations()

    assert len(operations) == 106
    assert operations.keys() == router_operations
    assert schema["components"]["schemas"]["ErroResponse"]["required"] == [
        "codigo",
        "mensagem",
    ]

    for (method, path), operation in operations.items():
        assert "operationId" in operation, (method, path)
        assert operation["operationId"], (method, path)
        if _is_public(path):
            assert "security" not in operation, (method, path)
        else:
            assert operation["security"] == [{"BearerAuth": []}], (method, path)

        responses = operation["responses"]
        assert "500" in responses, (method, path)
        for status, response in responses.items():
            assert "X-Correlation-ID" in response.get("headers", {}), (method, path, status)
            if status in {"400", "401", "403", "404", "409", "422", "500"}:
                _assert_error_response(response, method, path, status)


def test_imp_270_openapi_declara_matriz_http_global() -> None:
    operations = _operations(create_app().openapi())

    for status, expected_operations in EXPECTED_STATUS_MATRIX.items():
        found = {
            (method, path)
            for (method, path), operation in operations.items()
            if str(status) in operation["responses"]
        }
        assert expected_operations <= found, status

    documented_statuses = {
        int(status)
        for operation in operations.values()
        for status in operation["responses"]
        if status.isdigit()
    }
    assert {400, 401, 403, 404, 409} <= documented_statuses


def test_imp_270_http_matrix_runtime_amostra_400_401_403_404_409(
    ambiente_mvp: AmbienteMVP,
    session: Session,
) -> None:
    samples = [
        HttpMatrixSample(
            400,
            "get",
            f"/credit/carteiras/{ambiente_mvp.carteira_id}/relatorios/pagamentos",
            {
                "params": {"inicio": "2026-10-10", "fim": "2026-09-10"},
                "headers": ambiente_mvp.headers,
            },
            "payload_invalido",
        ),
        HttpMatrixSample(401, "get", "/platform/tenants", {}, "autenticacao_recusada"),
        HttpMatrixSample(
            403,
            "get",
            "/platform/tenants",
            {"headers": _headers_sem_permissao(ambiente_mvp, session)},
            "acesso_negado",
        ),
        HttpMatrixSample(
            404,
            "get",
            f"/platform/tenants/{uuid.uuid4()}",
            {"headers": ambiente_mvp.headers},
            "tenant_nao_encontrado",
        ),
    ]
    devedor_path = f"/credit/carteiras/{ambiente_mvp.carteira_id}/devedores"
    key = "plan020-p4-idempotencia"
    original = ambiente_mvp.client.post(
        devedor_path,
        json=_devedor_payload("52998224725"),
        headers={**ambiente_mvp.headers, "Idempotency-Key": key},
    )
    assert original.status_code == 201
    samples.append(
        HttpMatrixSample(
            409,
            "post",
            devedor_path,
            {
                "json": _devedor_payload("15350946056"),
                "headers": {**ambiente_mvp.headers, "Idempotency-Key": key},
            },
            "conflito_idempotencia",
        )
    )

    for sample in samples:
        response = getattr(ambiente_mvp.client, sample.method)(sample.path, **sample.kwargs)
        assert response.status_code == sample.status, sample
        assert response.json()["codigo"] == sample.codigo, sample
        assert response.headers["X-Correlation-ID"], sample


def test_imp_271_documentacao_historica_classificada_sem_pendencia_superada() -> None:
    report = (
        ROOT / "docs/implementation/reports/PLAN-022-p4-contracts-historical-docs-2026-08-12.md"
    )
    text = report.read_text(encoding="utf-8")

    assert "# PLAN-022 - Recertificacao P4 de Contratos HTTP e Documentacao Historica" in text
    assert "Divergencias ativas bloqueantes: nenhuma" in text
    assert "Caveats historicos aceitos" in text
    assert "IMP-269" in text and "IMP-270" in text and "IMP-271" in text
    for path in (
        "docs/audits/audits/vistoria-backend-2026-08-08.md",
        "docs/implementation/reports/PLAN-020-p0-inventory-baseline-2026-08-12.md",
        "docs/implementation/backlogs/PLAN-020-execution-backlog.md",
    ):
        assert path in text


def _operations(schema: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (method, path): operation
        for path, path_item in schema["paths"].items()
        for method, operation in path_item.items()
        if method in HTTP_METHODS
    }


def _router_operations() -> set[tuple[str, str]]:
    return {
        (method.lower(), route.path)
        for route in _api_routes()
        for method in route.methods or set()
        if method.lower() in HTTP_METHODS
    }


def _api_routes() -> Iterable[APIRoute]:
    for api_router in (
        observability_router,
        auth_router,
        iam_router,
        platform_router,
        devedores_router,
        comercial_router,
        contratos_router,
        motor_router,
        lancamento_router,
        operacao_diaria_router,
        configuracoes_financeiras_router,
        automacao_router,
    ):
        yield from (route for route in api_router.routes if isinstance(route, APIRoute))


def _is_public(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def _assert_error_response(
    response: dict[str, Any],
    method: str,
    path: str,
    status: str,
) -> None:
    assert response["content"]["application/json"]["schema"] == ERRO_RESPONSE_REF, (
        method,
        path,
        status,
    )


def _headers_sem_permissao(ambiente_mvp: AmbienteMVP, session: Session) -> dict[str, str]:
    usuario = UsuarioFactory.build(
        tenant_id=ambiente_mvp.tenant_id,
        email=f"sem-permissao-{uuid.uuid4().hex[:8]}@example.com",
        estado=UsuarioState.ATIVO,
        perfil_acesso="Sem Permissao",
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=usuario.id, segredo="senha-sem-permissao")
    )
    perfil = PerfilAcesso(tenant_id=ambiente_mvp.tenant_id, nome="Sem Permissao")
    perfil_repo = SqlAlchemyPerfilAcessoRepository(session)
    perfil_repo.save(perfil)
    perfil_repo.atribuir_usuario(usuario.id, perfil.id)
    session.commit()

    token = HmacAccessTokenService("segredo-plan-020-e2e").emitir(usuario).token
    return {
        "Authorization": f"Bearer {token}",
        "X-Correlation-ID": "plan-020-p4-403",
    }
