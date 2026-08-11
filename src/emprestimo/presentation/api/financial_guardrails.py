"""Guardrails compartilhados para payloads financeiros em APIs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

CHAVES_FINANCEIRAS_LIVRES_PROIBIDAS = frozenset(
    {
        "arredondamento",
        "arredondamentos",
        "calculo",
        "componentes_quitacao",
        "distribuicao",
        "encargos",
        "juros",
        "memoria",
        "memoria_calculo",
        "regra",
        "regra_calculo",
        "saldo_devedor",
        "valor_quitacao",
    }
)


def chaves_financeiras_livres(payload: object) -> list[str]:
    """Retorna chaves que tentam declarar regra/resultado financeiro livre."""
    chaves = _coletar_chaves(payload)
    return sorted(chaves & CHAVES_FINANCEIRAS_LIVRES_PROIBIDAS)


def _coletar_chaves(valor: object) -> set[str]:
    if isinstance(valor, Mapping):
        chaves = {str(chave).strip().lower() for chave in valor}
        for item in valor.values():
            chaves |= _coletar_chaves(item)
        return chaves
    if isinstance(valor, Sequence) and not isinstance(valor, str | bytes | bytearray):
        chaves_coletadas: set[str] = set()
        for item in valor:
            chaves_coletadas |= _coletar_chaves(item)
        return chaves_coletadas
    return set()
