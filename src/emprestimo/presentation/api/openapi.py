"""Componentes OpenAPI compartilhados pela API REST."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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
