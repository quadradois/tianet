"""Instrumentacao comum de escritas com a trilha append-only da ADR-002."""

from __future__ import annotations

import inspect
import json
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any, Concatenate, ParamSpec, Protocol, TypeVar, cast

from emprestimo.application.ports import AuditoriaRegistro

_P = ParamSpec("_P")
_R = TypeVar("_R")
_S = TypeVar("_S", bound="_ServicoAuditado")


class _ServicoAuditado(Protocol):
    _auditoria: AuditoriaRegistro


def auditar_escrita(
    entidade: str,
    acao: str,
    *,
    identificador: str | None = None,
) -> Callable[
    [Callable[Concatenate[_S, _P], _R]],
    Callable[Concatenate[_S, _P], _R],
]:
    """Registra inicio, sucesso, falha e rollback fora da transacao de negocio."""

    def decorator(
        func: Callable[Concatenate[_S, _P], _R],
    ) -> Callable[Concatenate[_S, _P], _R]:
        assinatura = inspect.signature(func)

        @wraps(func)
        def wrapper(self: _S, *args: _P.args, **kwargs: _P.kwargs) -> _R:
            argumentos = assinatura.bind(self, *args, **kwargs).arguments
            entidade_id = argumentos.get(identificador) if identificador else None
            if not isinstance(entidade_id, uuid.UUID):
                entidade_id = uuid.uuid4()
            detalhes_base = _detalhes_seguros(argumentos, entidade_id)
            self._auditoria.registrar(
                entidade,
                entidade_id,
                f"{acao}.inicio",
                "iniciado",
                detalhes=json.dumps(detalhes_base, sort_keys=True),
            )
            try:
                resultado = func(self, *args, **kwargs)
            except Exception as exc:
                self._auditoria.registrar(
                    entidade,
                    entidade_id,
                    f"{acao}.falha",
                    "falhou",
                    detalhes=json.dumps(
                        {**detalhes_base, "erro_tipo": type(exc).__name__},
                        sort_keys=True,
                    ),
                )
                self._auditoria.registrar(
                    entidade,
                    entidade_id,
                    f"{acao}.rollback",
                    "rollback_aplicado",
                    detalhes=json.dumps(detalhes_base, sort_keys=True),
                )
                raise
            self._auditoria.registrar(
                entidade,
                entidade_id,
                f"{acao}.sucesso",
                "ok",
                detalhes=json.dumps(detalhes_base, sort_keys=True),
            )
            return resultado

        return cast(Callable[Concatenate[_S, _P], _R], wrapper)

    return decorator


def _detalhes_seguros(argumentos: dict[str, Any], execucao_id: uuid.UUID) -> dict[str, str]:
    detalhes = {"execucao_id": str(execucao_id)}
    for nome, valor in argumentos.items():
        if nome != "self" and nome.endswith("_id") and isinstance(valor, uuid.UUID):
            detalhes[nome] = str(valor)
    return detalhes
