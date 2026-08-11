"""App FastAPI — camada Presentation da FEATURE-001 (IMP-017/018).

Responsabilidades: montar o app, registrar rotas e traduzir exceções de
domínio/aplicação em respostas HTTP padronizadas:
- 400 — payload inválido (RequestValidationError) ou header ausente;
- 409 — organização já existente / conflito de Idempotency-Key;
- 422 — violação de regra de domínio (invariante);
- 500 — erro inesperado (sem vazamento de detalhes internos).

Os handlers tipam o segundo argumento como ``Exception`` por contravariância
das assinaturas esperadas por ``add_exception_handler`` (mypy strict).
"""

from __future__ import annotations

import logging
from typing import cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from emprestimo.application.autorizacao import RecursoDeOutroTenantError
from emprestimo.application.errors import (
    AcessoNegadoError,
    AgendaItemNaoEncontradoError,
    AutenticacaoRecusadaError,
    CarteiraNaoEncontradaError,
    CobrancaCasoNaoEncontradoError,
    ContratoCreditoNaoEncontradoError,
    CredencialInvalidaError,
    DevedorNaoEncontradoError,
    EmprestimoNaoEncontradoError,
    IdempotenciaConflitoError,
    LembreteNaoEncontradoError,
    PagamentoNaoEncontradoError,
    PerfilConflitoError,
    PerfilNaoEncontradoError,
    PromessaPagamentoNaoEncontradaError,
    PropostaComercialNaoEncontradaError,
    RegistroComunicacaoNaoEncontradoError,
    SimulacaoComercialNaoEncontradaError,
    TransicaoEstadoInvalidaError,
    UsuarioNaoEncontradoError,
)
from emprestimo.domain.common.errors import (
    DevedorJaExisteError,
    DocumentoInvalidoError,
    PerfilJaExisteError,
    TenantJaExisteError,
    ViolacaoInvarianteError,
)
from emprestimo.domain.credit.contato import ContatoInvalidoError
from emprestimo.presentation.api.auth_routes import router as auth_router
from emprestimo.presentation.api.comercial_routes import router as comercial_router
from emprestimo.presentation.api.contratos_routes import router as contratos_router
from emprestimo.presentation.api.devedores_routes import router as devedores_router
from emprestimo.presentation.api.iam_routes import router as iam_router
from emprestimo.presentation.api.motor_routes import router as motor_router
from emprestimo.presentation.api.operacao_diaria_routes import router as operacao_diaria_router
from emprestimo.presentation.api.routes import router

logger = logging.getLogger(__name__)

TITLE = "TiaNet — API"
VERSION = "0.1.0"


def create_app() -> FastAPI:
    """Factory do app — permite instâncias isoladas em testes."""
    app = FastAPI(title=TITLE, version=VERSION)
    app.include_router(auth_router)
    app.include_router(iam_router)
    app.include_router(router)
    app.include_router(devedores_router)
    app.include_router(comercial_router)
    app.include_router(contratos_router)
    app.include_router(motor_router)
    app.include_router(operacao_diaria_router)
    app.add_exception_handler(RequestValidationError, _payload_invalido)
    app.add_exception_handler(AutenticacaoRecusadaError, _autenticacao_recusada)
    app.add_exception_handler(AcessoNegadoError, _acesso_negado)
    app.add_exception_handler(CredencialInvalidaError, _autenticacao_recusada)
    app.add_exception_handler(CarteiraNaoEncontradaError, _recurso_nao_encontrado)
    app.add_exception_handler(UsuarioNaoEncontradoError, _recurso_nao_encontrado)
    app.add_exception_handler(PerfilNaoEncontradoError, _recurso_nao_encontrado)
    app.add_exception_handler(SimulacaoComercialNaoEncontradaError, _recurso_nao_encontrado)
    app.add_exception_handler(PropostaComercialNaoEncontradaError, _recurso_nao_encontrado)
    app.add_exception_handler(ContratoCreditoNaoEncontradoError, _recurso_nao_encontrado)
    app.add_exception_handler(EmprestimoNaoEncontradoError, _recurso_nao_encontrado)
    app.add_exception_handler(CobrancaCasoNaoEncontradoError, _recurso_nao_encontrado)
    app.add_exception_handler(PromessaPagamentoNaoEncontradaError, _recurso_nao_encontrado)
    app.add_exception_handler(PagamentoNaoEncontradoError, _recurso_nao_encontrado)
    app.add_exception_handler(AgendaItemNaoEncontradoError, _recurso_nao_encontrado)
    app.add_exception_handler(LembreteNaoEncontradoError, _recurso_nao_encontrado)
    app.add_exception_handler(RegistroComunicacaoNaoEncontradoError, _recurso_nao_encontrado)
    app.add_exception_handler(RecursoDeOutroTenantError, _recurso_nao_encontrado)
    app.add_exception_handler(PerfilConflitoError, _perfil_conflito)
    app.add_exception_handler(PerfilJaExisteError, _perfil_conflito)
    app.add_exception_handler(TenantJaExisteError, _tenant_ja_existe)
    app.add_exception_handler(DevedorJaExisteError, _devedor_ja_existe)
    app.add_exception_handler(DevedorNaoEncontradoError, _devedor_nao_encontrado)
    app.add_exception_handler(IdempotenciaConflitoError, _conflito_idempotencia)
    app.add_exception_handler(TransicaoEstadoInvalidaError, _conflito_estado)
    app.add_exception_handler(ViolacaoInvarianteError, _regra_violada)
    app.add_exception_handler(DocumentoInvalidoError, _regra_violada)
    app.add_exception_handler(ContatoInvalidoError, _regra_violada)
    app.add_exception_handler(HTTPException, _http_exception)
    app.add_exception_handler(Exception, _erro_inesperado)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Healthcheck do serviço."""
        return {"status": "ok"}

    return app


def _corpo(codigo: str, mensagem: str) -> dict[str, str]:
    return {"codigo": codigo, "mensagem": mensagem}


async def _payload_invalido(request: Request, exc: Exception) -> JSONResponse:
    if request.url.path.startswith("/auth/"):
        return _corpo_autenticacao_recusada()
    erros = cast(RequestValidationError, exc)
    return JSONResponse(
        status_code=400,
        content=_corpo("payload_invalido", str(erros.errors()[:3])),
    )


async def _autenticacao_recusada(_: Request, exc: Exception) -> JSONResponse:
    del exc
    return _corpo_autenticacao_recusada()


async def _acesso_negado(_: Request, exc: Exception) -> JSONResponse:
    del exc
    return JSONResponse(
        status_code=403,
        content=_corpo("acesso_negado", "Acesso negado"),
    )


async def _recurso_nao_encontrado(_: Request, exc: Exception) -> JSONResponse:
    del exc
    return JSONResponse(
        status_code=404,
        content=_corpo("recurso_nao_encontrado", "Recurso nao encontrado"),
    )


async def _perfil_conflito(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content=_corpo("perfil_conflito", str(exc)))


def _corpo_autenticacao_recusada() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=_corpo("autenticacao_recusada", "Autenticacao recusada"),
    )


async def _tenant_ja_existe(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content=_corpo("tenant_ja_existe", str(exc)))


async def _devedor_ja_existe(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content=_corpo("devedor_ja_existe", str(exc)))


async def _devedor_nao_encontrado(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content=_corpo("devedor_nao_encontrado", str(exc)))


async def _conflito_idempotencia(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content=_corpo("conflito_idempotencia", str(exc)))


async def _conflito_estado(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=409, content=_corpo("conflito_estado", str(exc)))


async def _regra_violada(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content=_corpo("regra_violada", str(exc)))


async def _http_exception(_: Request, exc: Exception) -> JSONResponse:
    erro = cast(HTTPException, exc)
    detalhes = erro.detail if isinstance(erro.detail, dict) else _corpo("erro", str(erro.detail))
    return JSONResponse(status_code=erro.status_code, content=detalhes)


async def _erro_inesperado(request: Request, exc: Exception) -> JSONResponse:
    del exc
    logger.exception("Erro inesperado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_corpo("erro_interno", "erro inesperado no servidor"),
    )


app = create_app()
