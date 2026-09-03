"""Inventario vivo da superficie Backend MVP para o PLAN-020."""

from __future__ import annotations

from typing import Any

from emprestimo.presentation.api.main import create_app

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
PUBLIC_PREFIXES = ("/auth/",)
PUBLIC_PATHS = {"/health"}

EXPECTED_CONTEXTS = {
    "platform": "/platform/tenants",
    "iam": "/iam/",
    "cadastro": "/credit/carteiras/{carteira_id}/devedores",
    "comercial": "/credit/propostas-comerciais",
    "contratos": "/credit/contratos",
    "motor": "/credit/emprestimos",
    "operacao_diaria": "/credit/cobrancas",
    "relatorios": "/credit/carteiras/{carteira_id}/relatorios",
    "configuracoes": "/credit/configuracoes-financeiras",
    "automacao": "/credit/automacao",
    "notificacoes": "/credit/notificacoes",
    "whatsapp": "/platform/whatsapp/conexao",
    "health": "/health",
}


def _operations(schema: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (method, path): operation
        for path, path_item in schema["paths"].items()
        for method, operation in path_item.items()
        if method in HTTP_METHODS
    }


def _is_public(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def test_openapi_inventory_covers_backend_mvp_contexts() -> None:
    schema = create_app().openapi()
    operations = _operations(schema)

    assert len(operations) == 111
    # IMP-351: eram 5 publicas; POST /auth/ativar saiu com o fluxo de ativacao.
    assert sum(1 for _, path in operations if _is_public(path)) == 4
    # IMP-368: 111 no total = 4 publicas + 107 protegidas. Eram 107/103 ate o
    # IMP-362; entraram as quatro de /platform/whatsapp/conexao — consultar,
    # conectar, desconectar e excluir a instancia.
    assert sum(1 for _, path in operations if not _is_public(path)) == 107

    paths = set(schema["paths"])
    for context, expected_fragment in EXPECTED_CONTEXTS.items():
        assert any(path.startswith(expected_fragment) for path in paths), context


def test_openapi_inventory_classifies_public_and_protected_security() -> None:
    schema = create_app().openapi()

    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    for (method, path), operation in _operations(schema).items():
        if _is_public(path):
            assert "security" not in operation, (method, path)
        else:
            assert operation["security"] == [{"BearerAuth": []}], (method, path)


def test_openapi_inventory_declares_correlation_id_on_public_and_protected_routes() -> None:
    schema = create_app().openapi()

    for (method, path), operation in _operations(schema).items():
        responses = operation["responses"]
        for status, response in responses.items():
            assert "X-Correlation-ID" in response.get("headers", {}), (method, path, status)
