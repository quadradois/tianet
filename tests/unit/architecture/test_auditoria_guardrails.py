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

from sqlalchemy import String

from emprestimo.application.scheduler import ResultadoExecucao
from emprestimo.infrastructure.db.orm import AuditoriaLogORM

# Lido do proprio ORM, nao repetido como numero: alargar a coluna sem alargar o
# guardrail deixaria o teste protegendo um limite que nao existe mais.
_TIPO_STATUS = AuditoriaLogORM.__table__.columns["status"].type
assert isinstance(_TIPO_STATUS, String) and _TIPO_STATUS.length is not None
LIMITE_STATUS: int = _TIPO_STATUS.length

# Status gravados fora de um enum, colhidos dos servicos de aplicacao.
STATUS_LITERAIS = (
    "iniciado",
    "ok",
    "falhou",
    "rollback_aplicado",
    "nao_configurado",
    "resultado_desconhecido",
)


def test_todo_resultado_de_execucao_cabe_no_status_auditado() -> None:
    excedentes = {
        item.value: len(item.value) for item in ResultadoExecucao if len(item.value) > LIMITE_STATUS
    }

    assert (
        not excedentes
    ), f"status maior que VARCHAR({LIMITE_STATUS}) estoura a insercao na trilha: {excedentes}"


def test_status_literais_dos_servicos_cabem_no_status_auditado() -> None:
    excedentes = {valor: len(valor) for valor in STATUS_LITERAIS if len(valor) > LIMITE_STATUS}

    assert (
        not excedentes
    ), f"status maior que VARCHAR({LIMITE_STATUS}) estoura a insercao na trilha: {excedentes}"
