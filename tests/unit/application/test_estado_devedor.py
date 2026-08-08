"""Testes unitários do DevedorEstadoService (IMP-055).

Cobrem as transições de estado ``inativar``/``reativar`` (FEATURE-008,
US-025/US-026): sucesso, replay idempotente, conflitos de chave, Devedor
inexistente, violação INV-005 e trilha de auditoria.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from emprestimo.application.errors import (
    DevedorNaoEncontradoError,
    IdempotenciaConflitoError,
)
from emprestimo.application.estado_devedor import (
    DevedorEstadoAlteradoResultado,
    DevedorEstadoService,
    _solicitacao_hash,
)
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento

CARTEIRA_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DEVEDOR_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
TENANT_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
DOCUMENTO = "52998224725"


def _mock_devedor(estado: DevedorState = DevedorState.ATIVO) -> Devedor:
    """Cria um Devedor mock em um estado inicial."""
    contatos = (
        Contato(
            devedor_id=DEVEDOR_ID,
            tipo=TipoContato.TELEFONE,
            valor="(11) 1234-5678",
            preferencial=True,
        ),
    )
    devedor = Devedor.criar(
        carteira_id=CARTEIRA_ID,
        documento=Documento.from_str(DOCUMENTO),
        nome="João da Silva",
        contatos=contatos,
    )
    devedor.id = DEVEDOR_ID
    # Transição para o estado desejado (Inativo) antes do teste
    if estado is DevedorState.INATIVO:
        devedor.inativar()
    return devedor


def _mock_carteira() -> Mock:
    """Cria uma Carteira mock para testes."""
    carteira = Mock()
    carteira.id = CARTEIRA_ID
    carteira.tenant_id = TENANT_ID
    return carteira


def _mock_uow_factory(devedor: Devedor | None = None, carteira: Mock | None = None) -> Mock:
    """Cria um mock do UnitOfWork com DevedorRepository e CarteiraRepository."""
    uow = Mock(spec=UnitOfWork)
    uow.devedor = Mock()
    uow.devedor.find_by_id.return_value = devedor
    uow.devedor.save = Mock()
    uow.carteira = Mock()
    uow.carteira.find_by_id.return_value = carteira or _mock_carteira()
    uow.idempotencia = Mock()
    uow.idempotencia.find_by_chave.return_value = None
    uow.idempotencia.registrar = Mock()
    uow.idempotencia.concluir = Mock()
    uow.commit = Mock()
    uow.rollback = Mock()
    uow.close = Mock()
    uow.__enter__ = Mock(return_value=uow)
    uow.__exit__ = Mock(return_value=None)
    return uow


def _mock_auditoria() -> Mock:
    """Cria um mock do AuditoriaRegistro."""
    return Mock()


def _registro_concluido(
    *,
    hash_: str,
    estado: str,
    estado_anterior: str,
    estado_novo: str,
) -> dict[str, object]:
    """Monta um registro de idempotência concluído para cenários de replay/divergência."""
    return {
        "chave": "idem-key",
        "escopo": "devedor-estado",
        "solicitacao_hash": hash_,
        "estado": estado,
        "resultado": json.dumps(
            {
                "devedor_id": str(DEVEDOR_ID),
                "carteira_id": str(CARTEIRA_ID),
                "documento": DOCUMENTO,
                "nome": "João da Silva",
                "estado_anterior": estado_anterior,
                "estado_novo": estado_novo,
                "atualizado_em": datetime.now().isoformat(),
            }
        ),
        "criado_em": datetime.now().isoformat(),
        "concluido_em": datetime.now().isoformat(),
    }


class TestDevedorEstadoService:
    """Testes do DevedorEstadoService (IMP-055)."""

    def test_inativar_ativa_a_inativo(self) -> None:
        """Deve transicionar Ativo → Inativo e retornar o resultado correto."""
        devedor = _mock_devedor()  # estado ATIVO
        uow = _mock_uow_factory(devedor)
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)
        resultado = service.inativar(DEVEDOR_ID, "idem-key-inativar")

        assert isinstance(resultado, DevedorEstadoAlteradoResultado)
        assert resultado.devedor_id == DEVEDOR_ID
        assert resultado.carteira_id == CARTEIRA_ID
        assert resultado.documento == DOCUMENTO
        assert resultado.nome == "João da Silva"
        assert resultado.estado_anterior is DevedorState.ATIVO
        assert resultado.estado_novo is DevedorState.INATIVO
        assert isinstance(resultado.atualizado_em, datetime)
        assert devedor.estado is DevedorState.INATIVO

        uow.devedor.save.assert_called_once_with(devedor)
        uow.commit.assert_called_once()
        uow.idempotencia.concluir.assert_called_once()
        uow.idempotencia.registrar.assert_called_once()

    def test_reativar_inativo_a_ativo(self) -> None:
        """Transição deve retornar o estado correto Inativo → Ativo."""
        devedor = _mock_devedor(DevedorState.INATIVO)
        uow = _mock_uow_factory(devedor)
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)
        resultado = service.reativar(DEVEDOR_ID, "idem-key-reativar")

        assert resultado.estado_anterior is DevedorState.INATIVO
        assert resultado.estado_novo is DevedorState.ATIVO
        assert devedor.estado is DevedorState.ATIVO
        uow.devedor.save.assert_called_once_with(devedor)
        uow.commit.assert_called_once()

    def test_inativar_devedor_ja_inativo_viola_inv005(self) -> None:
        """Inativar um Devedor já Inativo deve levantar ViolacaoInvarianteError (INV-005)."""
        devedor = _mock_devedor(DevedorState.INATIVO)
        uow = _mock_uow_factory(devedor)
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)

        with pytest.raises(ViolacaoInvarianteError) as exc_info:
            service.inativar(DEVEDOR_ID, "idem-key-inv005")

        assert exc_info.value.codigo == "INV-005"
        uow.devedor.save.assert_not_called()

    def test_reativar_de_al_ativo_viola_inv005(self) -> None:
        """Reativar um Devedor já Ativo deve violar INV-005."""
        devedor = _mock_devedor(DevedorState.ATIVO)
        uow = _mock_uow_factory(devedor)
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)

        with pytest.raises(ViolacaoInvarianteError) as exc_info:
            service.reativar(DEVEDOR_ID, "idem-key-inv005-reativar")

        assert exc_info.value.codigo == "INV-005"
        uow.devedor.save.assert_not_called()

    def test_replay_mesma_chave_mesmo_resultado(self) -> None:
        """Replay com a mesma chave deve retornar o mesmo resultado (AD-002)."""
        uow = _mock_uow_factory(_mock_devedor())
        hash_esperado = _solicitacao_hash(DEVEDOR_ID, "inativar")
        uow.idempotencia.find_by_chave.return_value = _registro_concluido(
            hash_=hash_esperado,
            estado="finished",
            estado_anterior="ativo",
            estado_novo="inativo",
        )
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)
        resultado = service.inativar(DEVEDOR_ID, "idem-key-replay")

        assert resultado.estado_anterior is DevedorState.ATIVO
        assert resultado.estado_novo is DevedorState.INATIVO
        # Replay: não deve salvar novamente
        uow.devedor.save.assert_not_called()
        uow.commit.assert_called_once()
        auditoria.registrar.assert_any_call(
            "devedor",
            None,
            "inativar.replay",
            "ok",
            detalhes=json.dumps({"idempotency_key": "idem-key-replay"}),
        )

    def test_conflito_payload_divergente(self) -> None:
        """Chave com hash divergente deve levantar IdempotenciaConflitoError."""
        uow = _mock_uow_factory(_mock_devedor())
        uow.idempotencia.find_by_chave.return_value = _registro_concluido(
            hash_="b" * 64,  # hash diferente
            estado="finished",
            estado_anterior="ativo",
            estado_novo="inativo",
        )
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)

        with pytest.raises(IdempotenciaConflitoError) as exc_info:
            service.inativar(DEVEDOR_ID, "idem-key-conflito")

        assert exc_info.value.idempotency_key == "idem-key-conflito"
        assert "divergente" in exc_info.value.motivo

    def test_conflito_em_andamento(self) -> None:
        """Chave em andamento deve bloquear independentemente do hash."""
        uow = _mock_uow_factory(_mock_devedor())
        uow.idempotencia.find_by_chave.return_value = _registro_concluido(
            hash_=_solicitacao_hash(DEVEDOR_ID, "inativar"),
            estado="started",  # ainda em andamento
            estado_anterior="ativo",
            estado_novo="inativo",
        )
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)

        with pytest.raises(IdempotenciaConflitoError) as exc_info:
            service.inativar(DEVEDOR_ID, "idem-key-andamento")

        assert "andamento" in exc_info.value.motivo

    def test_devedor_nao_encontrado(self) -> None:
        """Devedor inexistente deve levantar DevedorNaoEncontradoError."""
        uow = _mock_uow_factory(None)  # devedor = None
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)

        with pytest.raises(DevedorNaoEncontradoError) as exc_info:
            service.inativar(DEVEDOR_ID, "idem-key-404")

        assert exc_info.value.devedor_id == DEVEDOR_ID

    def test_auditoria_registra_trilha_inativar(self) -> None:
        """Trilha do inativar: inicio → estado_alterado → evento_inativado → sucesso."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)
        service.inativar(DEVEDOR_ID, "idem-key-auditoria")

        calls = auditoria.registrar.call_args_list
        assert calls[0][0][2] == "inativar.inicio"
        assert calls[0][0][3] == "iniciado"
        assert calls[1][0][2] == "inativar.estado_alterado"
        assert calls[1][0][3] == "ok"
        assert calls[2][0][2] == "inativar.evento_inativado"
        assert calls[2][0][3] == "ok"
        assert calls[3][0][2] == "inativar.sucesso"
        assert calls[3][0][3] == "ok"

    def test_auditoria_registra_evento_reativado(self) -> None:
        """A chave do evento de reativação deve ser reativar.evento_reativado."""
        devedor = _mock_devedor(DevedorState.INATIVO)
        uow = _mock_uow_factory(devedor)
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)
        service.reativar(DEVEDOR_ID, "idem-key-evento-reativar")

        eventos = [c[0][2] for c in auditoria.registrar.call_args_list]
        assert "reativar.evento_reativado" in eventos
        assert "inativar.evento_inativado" not in eventos

    def test_auditoria_falha_e_rollback_em_excecao(self) -> None:
        """Exceção no save deve registrar falha e rollback, sem sucesso."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow.devedor.save.side_effect = Exception("DB error")
        auditoria = _mock_auditoria()

        service = DevedorEstadoService(lambda: uow, auditoria)

        with pytest.raises(Exception, match="DB error"):
            service.inativar(DEVEDOR_ID, "idem-key-falha")

        eventos = [c[0][2] for c in auditoria.registrar.call_args_list]
        assert "inativar.falha" in eventos
        assert "inativar.rollback" in eventos
        assert "inativar.sucesso" not in eventos
