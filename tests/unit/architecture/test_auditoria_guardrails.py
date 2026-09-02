"""Guardrail do IMP-350: o vocabulario auditado tem que caber na coluna.

`audit_log.status` era VARCHAR(20) e o dominio ja produzia
`resultado_desconhecido`, com 22 caracteres. O `comprovante.py` contornava no
call site; o `notifications.py`, escrito depois, copiou o padrao de auditoria e
nao o contorno — e o caminho de resultado desconhecido do aviso de sobra
estourava a coluna com `DataError`, derrubando a entrega em producao.

O defeito nao era o esquecimento: era depender de cada chamador lembrar de um
remendo. Este teste falha no momento em que um vocabulario novo nao couber,
antes de virar erro de banco num caminho pouco exercitado.
"""

from __future__ import annotations

import ast
from pathlib import Path

from sqlalchemy import String

from emprestimo.application.scheduler import ResultadoExecucao
from emprestimo.infrastructure.db.orm import AuditoriaLogORM

# Lido do proprio ORM, nao repetido como numero: alargar a coluna sem alargar o
# guardrail deixaria o teste protegendo um limite que nao existe mais.
_TIPO_STATUS = AuditoriaLogORM.__table__.columns["status"].type
assert isinstance(_TIPO_STATUS, String) and _TIPO_STATUS.length is not None
LIMITE_STATUS: int = _TIPO_STATUS.length


def _status_literais_do_codigo() -> dict[str, str]:
    """Colhe os status do proprio codigo, em vez de confiar numa lista.

    A versao anterior deste guardrail mantinha `STATUS_LITERAIS` a mao — e caiu
    exatamente no defeito que o docstring acima descreve, um nivel acima:
    dependia de cada autor lembrar de acrescentar o status novo. O IMP-367
    introduziu tres, nenhum entrou na lista, e um deles tinha 46 caracteres
    contra uma coluna de 40. O teste passava.

    Agora varre as chamadas de `registrar(...)` na camada de aplicacao e le o
    quarto argumento posicional quando ele e literal. Status construido em
    runtime escapa desta varredura, e por isso o teste do enum continua ao lado.
    """
    encontrados: dict[str, str] = {}
    for arquivo in sorted(Path("src/emprestimo/application").glob("*.py")):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Call) or not isinstance(no.func, ast.Attribute):
                continue
            if no.func.attr != "registrar" or len(no.args) < 4:
                continue
            status = no.args[3]
            if isinstance(status, ast.Constant) and isinstance(status.value, str):
                encontrados[status.value] = arquivo.name
    return encontrados


STATUS_LITERAIS_ESPERADOS_NO_MINIMO = ("iniciado", "falhou", "rollback_aplicado")
"""Ancora da varredura: se ela parar de achar estes, quebrou e ninguem notaria."""


def test_todo_resultado_de_execucao_cabe_no_status_auditado() -> None:
    excedentes = {
        item.value: len(item.value) for item in ResultadoExecucao if len(item.value) > LIMITE_STATUS
    }

    assert (
        not excedentes
    ), f"status maior que VARCHAR({LIMITE_STATUS}) estoura a insercao na trilha: {excedentes}"


def test_status_literais_dos_servicos_cabem_no_status_auditado() -> None:
    literais = _status_literais_do_codigo()

    faltando = [
        esperado for esperado in STATUS_LITERAIS_ESPERADOS_NO_MINIMO if esperado not in literais
    ]
    assert not faltando, (
        f"a varredura nao achou {faltando}: ela quebrou, e um guardrail quebrado "
        "passa em silencio — que e pior que nao existir"
    )

    excedentes = {
        valor: f"{len(valor)} caracteres, em {arquivo}"
        for valor, arquivo in literais.items()
        if len(valor) > LIMITE_STATUS
    }

    assert (
        not excedentes
    ), f"status maior que VARCHAR({LIMITE_STATUS}) estoura a insercao na trilha: {excedentes}"
