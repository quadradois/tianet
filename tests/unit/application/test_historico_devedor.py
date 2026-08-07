"""Testes unitários do DevedorHistoricoService (US-027)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import Mock

from emprestimo.application.historico_devedor import DevedorHistoricoService
from emprestimo.application.ports import EventoAuditoria, UnitOfWork

DEVEDOR_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _evento(acao: str) -> EventoAuditoria:
    return EventoAuditoria(
        id=uuid.uuid4(),
        entidade="devedor",
        entidade_id=DEVEDOR_ID,
        acao=acao,
        status="ok",
        detalhes=None,
        criado_em=datetime.now(UTC),
    )


def _mock_uow(devedor: object | None) -> Mock:
    uow = Mock(spec=UnitOfWork)
    uow.devedor = Mock()
    uow.devedor.find_by_id.return_value = devedor
    uow.__enter__ = Mock(return_value=uow)
    uow.__exit__ = Mock(return_value=None)
    return uow


def test_consultar_retorna_a_trilha() -> None:
    uow = _mock_uow(Mock())
    consulta = Mock()
    consulta.listar_por_entidade.return_value = [
        _evento("criar.sucesso"),
        _evento("inativar.sucesso"),
    ]

    service = DevedorHistoricoService(lambda: uow, consulta)
    eventos = service.consultar(DEVEDOR_ID)

    assert eventos is not None
    assert [e.acao for e in eventos] == ["criar.sucesso", "inativar.sucesso"]
    consulta.listar_por_entidade.assert_called_once_with("devedor", DEVEDOR_ID)


def test_devedor_inexistente_retorna_none() -> None:
    """Distinguir inexistente de sem-eventos é o que permite o 404 da US-027."""
    uow = _mock_uow(None)
    consulta = Mock()

    service = DevedorHistoricoService(lambda: uow, consulta)

    assert service.consultar(DEVEDOR_ID) is None
    consulta.listar_por_entidade.assert_not_called()


def test_devedor_sem_eventos_retorna_lista_vazia() -> None:
    uow = _mock_uow(Mock())
    consulta = Mock()
    consulta.listar_por_entidade.return_value = []

    service = DevedorHistoricoService(lambda: uow, consulta)

    assert service.consultar(DEVEDOR_ID) == []


def test_consulta_nao_grava_trilha() -> None:
    """ADR-002: somente escrita é auditada — a consulta não registra nada."""
    uow = _mock_uow(Mock())
    consulta = Mock()
    consulta.listar_por_entidade.return_value = []

    service = DevedorHistoricoService(lambda: uow, consulta)
    service.consultar(DEVEDOR_ID)

    assert not hasattr(consulta, "registrar") or not consulta.registrar.called
    uow.commit.assert_not_called()
