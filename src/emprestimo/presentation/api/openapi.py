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
        for path_item in schema.get("paths", {}).values():
            for metodo, operacao in path_item.items():
                if metodo not in metodos_http:
                    continue
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
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]


def _adicionar_correlation_parameter(operacao: dict[str, Any]) -> None:
    parameters = operacao.setdefault("parameters", [])
    if not any(param.get("name") == "X-Correlation-ID" for param in parameters):
        parameters.append(dict(CORRELATION_ID_PARAMETER))
