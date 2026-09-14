"""Adaptador tool_calls → dispatcher (IMP-356-D lote 2, slice 2).

O modelo sugere; este módulo valida antes de qualquer rede: nome fora do
catálogo, JSON ilegível, argumento extra ou data contra o relógio do
servidor viram recusa fechada. Resolução de referência opaca continua no
dispatcher (com o resolvedor injetado); aqui só passa o que o schema
permite.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from emprestimo.agent.catalogo import CATALOGO
from emprestimo.agent.dispatcher import (
    ArgumentoInvalidoError,
    FerramentaDesconhecidaError,
    validar_argumentos,
)
from emprestimo.agent.llm_client import ChamadaFerramenta


@dataclass(frozen=True)
class IntencaoValidada:
    nome: str
    argumentos: dict[str, str]


def interpretar_chamada(chamada: ChamadaFerramenta, hoje: date) -> IntencaoValidada:
    """Parse + schema de um tool_call; nada inválido atravessa."""
    ferramenta = CATALOGO.get(chamada.nome)
    if ferramenta is None:
        raise FerramentaDesconhecidaError(f"ferramenta fora do catalogo: {chamada.nome}")
    try:
        brutos = json.loads(chamada.argumentos)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ArgumentoInvalidoError("argumentos ilegíveis") from exc
    if not isinstance(brutos, dict):
        raise ArgumentoInvalidoError("argumentos devem ser objeto")
    argumentos: dict[str, Any] = {str(k): v for k, v in brutos.items()}
    validados = validar_argumentos(ferramenta, argumentos, hoje)
    return IntencaoValidada(nome=ferramenta.nome, argumentos=validados)
