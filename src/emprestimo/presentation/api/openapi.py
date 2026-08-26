"""Componentes OpenAPI compartilhados pela API REST."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI

from emprestimo.presentation.api.schemas import ErroResponse

ResponseSpec = dict[int | str, dict[str, Any]]

RESPOSTA_AUTENTICACAO_RECUSADA: ResponseSpec = {
    401: {
        "model": ErroResponse,
        "description": "Autenticacao recusada por token ausente, invalido ou expirado.",
    }
}
RESPOSTA_ACESSO_NEGADO: ResponseSpec = {
    403: {
        "model": ErroResponse,
        "description": "Principal autenticado nao possui permissao para a operacao.",
    }
}
RESPOSTA_RECURSO_NAO_ENCONTRADO: ResponseSpec = {
    404: {
        "model": ErroResponse,
        "description": "Recurso inexistente ou indisponivel para o Tenant autenticado.",
    }
}
RESPOSTA_PAYLOAD_INVALIDO: ResponseSpec = {
    400: {
        "model": ErroResponse,
        "description": "Payload, parametros ou headers invalidos para a operacao.",
    }
}
RESPOSTA_CONFLITO_ESTADO: ResponseSpec = {
    409: {
        "model": ErroResponse,
        "description": "Transicao de estado invalida para o recurso atual.",
    }
}
RESPOSTA_REGRA_VIOLADA: ResponseSpec = {
    422: {
        "model": ErroResponse,
        "description": "Regra ou invariante de dominio violada pelo comando.",
    }
}
RESPOSTA_CONTEXTO_INCOMPLETO: ResponseSpec = {
    409: {
        "model": ErroResponse,
        "description": "Contexto operacional corrente indisponivel.",
    }
}
RESPOSTA_ERRO_INTERNO: ResponseSpec = {
    500: {
        "model": ErroResponse,
        "description": "Erro tecnico inesperado com resposta segura e correlacionavel.",
    }
}

CORRELATION_ID_PARAMETER: dict[str, Any] = {
    "name": "X-Correlation-ID",
    "in": "header",
    "required": False,
    "schema": {"type": "string", "maxLength": 128},
    "description": "Identificador tecnico de correlacao aceito ou gerado pela API.",
}

CORRELATION_ID_RESPONSE_HEADER: dict[str, Any] = {
    "description": "Identificador tecnico de correlacao da requisicao.",
    "schema": {"type": "string"},
}

OPERACOES_REGRA_VIOLADA = frozenset(
    {
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
)

OPERACOES_CONFLITO_ADICIONAIS = frozenset(
    {
        ("post", "/platform/tenants/{tenant_id}/inativar"),
        ("post", "/platform/tenants/{tenant_id}/reativar"),
        ("post", "/iam/usuarios/{usuario_id}/credencial/redefinir"),
        ("post", "/iam/perfis"),
        ("patch", "/iam/perfis/{perfil_id}"),
        ("post", "/iam/perfis/{perfil_id}/inativar"),
        ("put", "/iam/perfis/{perfil_id}/permissoes/{codigo}"),
        ("delete", "/iam/perfis/{perfil_id}/permissoes/{codigo}"),
        ("put", "/iam/usuarios/{usuario_id}/perfil/{perfil_id}"),
        ("delete", "/iam/usuarios/{usuario_id}/perfil"),
        ("post", "/credit/carteiras/{carteira_id}/devedores"),
        ("get", "/credit/configuracoes-financeiras/vigente"),
    }
)

RESPOSTAS_AUTH: ResponseSpec = {**RESPOSTA_AUTENTICACAO_RECUSADA}
RESPOSTAS_PROTEGIDAS: ResponseSpec = {
    **RESPOSTA_AUTENTICACAO_RECUSADA,
    **RESPOSTA_ACESSO_NEGADO,
}
RESPOSTAS_PROTEGIDAS_COM_RECURSO: ResponseSpec = {
    **RESPOSTAS_PROTEGIDAS,
    **RESPOSTA_RECURSO_NAO_ENCONTRADO,
}


def combinar_respostas(*grupos: Mapping[int | str, Mapping[str, Any]]) -> ResponseSpec:
    """Combina mapas de responses evitando mutacao acidental entre rotas."""
    return {codigo: dict(spec) for grupo in grupos for codigo, spec in grupo.items()}


def instalar_openapi_observabilidade(app: FastAPI) -> None:
    """Adiciona contratos transversais de observabilidade ao OpenAPI gerado."""
    original_openapi = app.openapi

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = original_openapi()
        metodos_http = {"get", "post", "put", "patch", "delete"}
        for path, path_item in schema.get("paths", {}).items():
            for metodo, operacao in path_item.items():
                if metodo not in metodos_http:
                    continue
                _normalizar_respostas_validacao(path, metodo, operacao)
                _adicionar_correlation_parameter(operacao)
                responses = operacao.setdefault("responses", {})
                responses.setdefault(
                    "500",
                    {
                        "description": RESPOSTA_ERRO_INTERNO[500]["description"],
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErroResponse"}
                            }
                        },
                    },
                )
                for response in responses.values():
                    response.setdefault("headers", {})[
                        "X-Correlation-ID"
                    ] = CORRELATION_ID_RESPONSE_HEADER
        schemas = schema.get("components", {}).get("schemas", {})
        schemas.pop("HTTPValidationError", None)
        schemas.pop("ValidationError", None)
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]


def _adicionar_correlation_parameter(operacao: dict[str, Any]) -> None:
    parameters = operacao.setdefault("parameters", [])
    if not any(param.get("name") == "X-Correlation-ID" for param in parameters):
        parameters.append(dict(CORRELATION_ID_PARAMETER))


def _normalizar_respostas_validacao(
    path: str,
    metodo: str,
    operacao: dict[str, Any],
) -> None:
    """Espelha a semantica runtime: entrada invalida 400 e regra de comando 422."""
    responses = operacao.setdefault("responses", {})
    response_422 = responses.get("422", {})
    ref_422 = (
        response_422.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref")
    )
    if ref_422 == "#/components/schemas/HTTPValidationError":
        responses.pop("422")

    parametros_validaveis = [
        parametro
        for parametro in operacao.get("parameters", [])
        if parametro.get("name") != "X-Correlation-ID"
    ]
    tem_entrada = bool(operacao.get("requestBody") or parametros_validaveis)
    if tem_entrada:
        responses.setdefault(
            "400",
            _erro_response(RESPOSTA_PAYLOAD_INVALIDO[400]["description"]),
        )
    if (metodo, path) in OPERACOES_REGRA_VIOLADA:
        responses.setdefault(
            "422",
            _erro_response(RESPOSTA_REGRA_VIOLADA[422]["description"]),
        )
    if (metodo, path) in OPERACOES_CONFLITO_ADICIONAIS:
        responses.setdefault(
            "409",
            _erro_response(RESPOSTA_CONFLITO_ESTADO[409]["description"]),
        )
    if (metodo, path) == ("get", "/iam/contexto-atual"):
        responses.pop("403", None)
        responses["409"] = _erro_response(RESPOSTA_CONTEXTO_INCOMPLETO[409]["description"])


def _erro_response(descricao: str) -> dict[str, Any]:
    return {
        "description": descricao,
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErroResponse"}}},
    }
