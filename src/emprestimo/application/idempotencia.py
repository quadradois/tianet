"""Primitivas compartilhadas de idempotencia para casos de uso de escrita.

O registro e concluido pelo proprio caso de uso antes do ``commit`` do
``UnitOfWork``. Assim, chave, efeito de negocio e referencia do resultado ficam
visiveis atomicamente (AD-002).
"""

from __future__ import annotations

import hashlib
import json
import types
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Union, cast, get_args, get_origin, get_type_hints

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import UnitOfWork


def iniciar_idempotencia(
    uow: UnitOfWork,
    *,
    chave: str | None,
    escopo: str,
    solicitacao: Mapping[str, object],
) -> dict[str, object] | None:
    """Registra a solicitacao ou devolve o resultado concluido para replay."""
    if not chave:
        return None
    solicitacao_hash = _hash_solicitacao(solicitacao)
    existente = uow.idempotencia.find_by_chave(chave, escopo)
    if existente is None:
        uow.idempotencia.registrar(chave, escopo, solicitacao_hash)
        return None
    if existente.get("solicitacao_hash") != solicitacao_hash:
        raise IdempotenciaConflitoError(chave, "payload divergente")
    if existente.get("estado") != "finished":
        raise IdempotenciaConflitoError(chave, "operacao em andamento")
    bruto = existente.get("resultado")
    if not isinstance(bruto, str):
        raise IdempotenciaConflitoError(chave, "resultado ausente")
    try:
        resultado = json.loads(bruto)
    except (TypeError, json.JSONDecodeError) as exc:
        raise IdempotenciaConflitoError(chave, "resultado invalido") from exc
    if not isinstance(resultado, dict):
        raise IdempotenciaConflitoError(chave, "resultado invalido")
    return resultado


def concluir_idempotencia(
    uow: UnitOfWork,
    *,
    chave: str | None,
    escopo: str,
    resultado: Mapping[str, object],
) -> None:
    """Conclui a chave na mesma transacao do efeito de negocio."""
    if not chave:
        return
    uow.idempotencia.concluir(
        chave,
        escopo,
        json.dumps(resultado, default=_json_default, sort_keys=True, separators=(",", ":")),
    )


def resultado_de_dataclass(valor: object) -> dict[str, object]:
    """Congela todos os campos de um resultado/aggregate para replay exato."""
    if not is_dataclass(valor) or isinstance(valor, type):
        raise TypeError("resultado de idempotencia deve ser dataclass")
    return {
        "resultado": {campo.name: getattr(valor, campo.name) for campo in fields(cast(Any, valor))}
    }


def dataclass_do_resultado[T](
    resultado: Mapping[str, object],
    tipo: type[T],
    *,
    chave: str | None,
) -> T:
    """Restaura o snapshot persistido sem reler o estado atual do aggregate."""
    bruto = resultado.get("resultado")
    try:
        restaurado = _restaurar_valor(bruto, tipo)
    except (KeyError, TypeError, ValueError) as exc:
        raise IdempotenciaConflitoError(chave or "<ausente>", "resultado invalido") from exc
    if not isinstance(restaurado, tipo):
        raise IdempotenciaConflitoError(chave or "<ausente>", "resultado invalido")
    return restaurado


def _hash_solicitacao(solicitacao: Mapping[str, object]) -> str:
    bruto = json.dumps(
        solicitacao,
        default=_json_default,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _json_default(valor: Any) -> object:
    if isinstance(valor, (uuid.UUID, date, datetime, Decimal, Enum)):
        return str(valor.value if isinstance(valor, Enum) else valor)
    if isinstance(valor, (set, frozenset, tuple)):
        return list(valor)
    if isinstance(valor, Mapping):
        return dict(valor)
    if is_dataclass(valor) and not isinstance(valor, type):
        return {campo.name: getattr(valor, campo.name) for campo in fields(cast(Any, valor))}
    to_dict = getattr(valor, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    raise TypeError(f"tipo nao serializavel para idempotencia: {type(valor).__name__}")


def _restaurar_valor(valor: object, tipo: Any) -> Any:
    if tipo in {Any, object}:
        return valor
    origem = get_origin(tipo)
    argumentos = get_args(tipo)
    if origem in {types.UnionType, Union}:
        if valor is None and type(None) in argumentos:
            return None
        for alternativa in argumentos:
            if alternativa is type(None):
                continue
            try:
                return _restaurar_valor(valor, alternativa)
            except (KeyError, TypeError, ValueError):
                continue
        raise TypeError("nenhuma alternativa do resultado e valida")
    if origem in {list, Sequence}:
        if not isinstance(valor, list):
            raise TypeError("lista esperada")
        subtipo = argumentos[0] if argumentos else Any
        return [_restaurar_valor(item, subtipo) for item in valor]
    if origem is tuple:
        if not isinstance(valor, list):
            raise TypeError("tupla esperada")
        subtipo = argumentos[0] if argumentos else Any
        return tuple(_restaurar_valor(item, subtipo) for item in valor)
    if origem in {dict, Mapping}:
        if not isinstance(valor, dict):
            raise TypeError("mapping esperado")
        tipo_chave, tipo_valor = argumentos if len(argumentos) == 2 else (Any, Any)
        return {
            _restaurar_valor(chave, tipo_chave): _restaurar_valor(item, tipo_valor)
            for chave, item in valor.items()
        }
    if tipo is uuid.UUID:
        return uuid.UUID(str(valor))
    if tipo is datetime:
        return datetime.fromisoformat(str(valor))
    if tipo is date:
        return date.fromisoformat(str(valor))
    if tipo is Decimal:
        return Decimal(str(valor))
    if isinstance(tipo, type) and issubclass(tipo, Enum):
        return tipo(valor)
    if isinstance(tipo, type) and is_dataclass(tipo):
        if not isinstance(valor, dict):
            raise TypeError("dataclass esperada")
        dicas = get_type_hints(tipo)
        kwargs = {
            campo.name: _restaurar_valor(valor[campo.name], dicas.get(campo.name, Any))
            for campo in fields(tipo)
            if campo.init and campo.name in valor
        }
        restaurado = tipo(**kwargs)
        for campo in fields(tipo):
            if not campo.init and campo.name in valor:
                object.__setattr__(
                    restaurado,
                    campo.name,
                    _restaurar_valor(valor[campo.name], dicas.get(campo.name, Any)),
                )
        return restaurado
    if tipo in {str, int, float, bool}:
        return tipo(valor)
    return valor
