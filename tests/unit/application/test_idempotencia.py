import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import cast
from unittest.mock import MagicMock

import pytest

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.idempotencia import (
    concluir_idempotencia,
    dataclass_do_resultado,
    iniciar_idempotencia,
    resultado_de_dataclass,
)
from emprestimo.application.ports import UnitOfWork


class _EstadoProva(StrEnum):
    ORIGINAL = "original"
    ALTERADO = "alterado"


@dataclass
class _ResultadoProva:
    recurso_id: uuid.UUID
    estado: _EstadoProva
    ocorrido_em: datetime
    parametros: dict[str, object]


def _uow() -> tuple[UnitOfWork, MagicMock]:
    uow = MagicMock(spec=UnitOfWork)
    idempotencia = MagicMock()
    uow.idempotencia = idempotencia
    return cast(UnitOfWork, uow), idempotencia


def test_idempotencia_registra_e_conclui_no_mesmo_unit_of_work() -> None:
    uow, idempotencia = _uow()
    idempotencia.find_by_chave.return_value = None

    replay = iniciar_idempotencia(
        uow,
        chave="imp-333-chave",
        escopo="imp333:prova",
        solicitacao={"valor": 10, "ordem": ["a", "b"]},
    )
    concluir_idempotencia(
        uow,
        chave="imp-333-chave",
        escopo="imp333:prova",
        resultado={"recurso_id": "original"},
    )

    assert replay is None
    idempotencia.registrar.assert_called_once()
    idempotencia.concluir.assert_called_once_with(
        "imp-333-chave",
        "imp333:prova",
        '{"recurso_id":"original"}',
    )


def test_idempotencia_replay_devolve_resultado_original() -> None:
    uow, idempotencia = _uow()
    idempotencia.find_by_chave.return_value = None
    solicitacao = {"valor": 10}
    iniciar_idempotencia(
        uow,
        chave="imp-333-replay",
        escopo="imp333:prova",
        solicitacao=solicitacao,
    )
    solicitacao_hash = idempotencia.registrar.call_args.args[2]
    idempotencia.find_by_chave.return_value = {
        "solicitacao_hash": solicitacao_hash,
        "estado": "finished",
        "resultado": '{"recurso_id":"original"}',
    }

    replay = iniciar_idempotencia(
        uow,
        chave="imp-333-replay",
        escopo="imp333:prova",
        solicitacao=solicitacao,
    )

    assert replay == {"recurso_id": "original"}


def test_idempotencia_rejeita_payload_divergente() -> None:
    uow, idempotencia = _uow()
    idempotencia.find_by_chave.return_value = None
    iniciar_idempotencia(
        uow,
        chave="imp-333-conflito",
        escopo="imp333:prova",
        solicitacao={"valor": 10},
    )
    solicitacao_hash = idempotencia.registrar.call_args.args[2]
    idempotencia.find_by_chave.return_value = {
        "solicitacao_hash": solicitacao_hash,
        "estado": "finished",
        "resultado": '{"recurso_id":"original"}',
    }

    with pytest.raises(IdempotenciaConflitoError, match="payload divergente"):
        iniciar_idempotencia(
            uow,
            chave="imp-333-conflito",
            escopo="imp333:prova",
            solicitacao={"valor": 11},
        )


def test_idempotencia_replay_restaura_snapshot_completo_e_nao_estado_posterior() -> None:
    uow, idempotencia = _uow()
    original = _ResultadoProva(
        recurso_id=uuid.uuid4(),
        estado=_EstadoProva.ORIGINAL,
        ocorrido_em=datetime(2026, 8, 22, 12, 30, tzinfo=UTC),
        parametros={"produto": "livre"},
    )
    concluir_idempotencia(
        uow,
        chave="imp-333-snapshot",
        escopo="imp333:prova",
        resultado=resultado_de_dataclass(original),
    )
    original.estado = _EstadoProva.ALTERADO
    persistido = json.loads(idempotencia.concluir.call_args.args[2])

    replay = dataclass_do_resultado(
        persistido,
        _ResultadoProva,
        chave="imp-333-snapshot",
    )

    assert replay.estado is _EstadoProva.ORIGINAL
    assert replay.ocorrido_em == datetime(2026, 8, 22, 12, 30, tzinfo=UTC)
    assert replay.parametros == {"produto": "livre"}
