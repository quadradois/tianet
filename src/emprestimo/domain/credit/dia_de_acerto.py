"""Regra de calendario do acerto mensal (DR-004, PLAN-030).

O devedor escolhe um dia do mes — "quero pagar todo dia 10" — e o acerto se
repete nesse dia. O primeiro periodo vai da data do emprestimo ate a proxima
ocorrencia do dia escolhido.

Este modulo vive **fora** do Motor de proposito. Saber quando cai o proximo
acerto e pergunta de Cobranca, Agenda e Operacao Diaria, e o guardrail de
exclusividade proibe esses contextos de importarem `motor_financeiro`. E regra
de calendario, nao de dinheiro: nao ha valor, taxa nem saldo aqui.
"""

from __future__ import annotations

import calendar
from datetime import date

from emprestimo.domain.common.errors import ViolacaoInvarianteError

__all__ = ["DIA_MAXIMO", "DIA_MINIMO", "proximo_acerto", "validar_dia_de_acerto"]

DIA_MINIMO = 1
DIA_MAXIMO = 31


def validar_dia_de_acerto(dia: int) -> int:
    if not isinstance(dia, int) or isinstance(dia, bool):
        raise ViolacaoInvarianteError("EPIC-005", "dia_de_acerto deve ser inteiro")
    if not DIA_MINIMO <= dia <= DIA_MAXIMO:
        raise ViolacaoInvarianteError(
            "EPIC-005",
            f"dia_de_acerto deve estar entre {DIA_MINIMO} e {DIA_MAXIMO}",
        )
    return dia


def _no_mes(ano: int, mes: int, dia: int) -> date:
    """O dia escolhido, ou o ultimo do mes quando ele nao existe.

    Quem escolhe dia 31 acerta em 28 de fevereiro, e nao em 3 de marco: o acerto
    nunca escorrega para o mes seguinte, senao um mes ficaria sem acerto.
    """
    return date(ano, mes, min(dia, calendar.monthrange(ano, mes)[1]))


def proximo_acerto(a_partir_de: date, dia: int) -> date:
    """Primeira ocorrencia do dia de acerto **depois** de `a_partir_de`.

    Estritamente depois: um emprestimo feito no proprio dia de acerto acerta no
    mes seguinte, porque um periodo de zero dia nao teria juros a cobrar.
    """
    if not isinstance(a_partir_de, date):
        raise ViolacaoInvarianteError("EPIC-005", "a_partir_de deve ser date")
    validar_dia_de_acerto(dia)

    candidato = _no_mes(a_partir_de.year, a_partir_de.month, dia)
    if candidato > a_partir_de:
        return candidato
    ano, mes = (
        (a_partir_de.year, a_partir_de.month + 1)
        if a_partir_de.month < 12
        else (a_partir_de.year + 1, 1)
    )
    return _no_mes(ano, mes, dia)
