"""Testes unitários do DevedorCadastroService (IMP-051)."""

from __future__ import annotations

import uuid
from unittest.mock import Mock

import pytest

from emprestimo.application.cadastro_devedor import DevedorCadastroService, DevedorCriado
from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.unicidade_devedor import UnicidadeDevedorService

CARTEIRA_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
DEVEDOR_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DOCUMENTO = "52998224725"
IDEMPOTENCY_KEY = "idem-key-123"


def _mock_uow_factory() -> Mock:
    """Cria um mock do UnitOfWork com repositórios e idempotência."""
    uow = Mock(spec=UnitOfWork)
    uow.devedor = Mock()
    uow.contato = Mock()
    uow.carteira = Mock()
    uow.tenant = Mock()
    uow.idempotencia = Mock()
    uow.idempotencia.find_by_chave.return_value = None  # Novo: sem chave existente
    uow.commit = Mock()
    uow.rollback = Mock()
    uow.close = Mock()
    uow.__enter__ = Mock(return_value=uow)
    uow.__exit__ = Mock(return_value=None)

    # Carteira mock para buscar tenant_id
    carteira_mock = Mock()
    carteira_mock.tenant_id = TENANT_ID
    uow.carteira.find_by_id.return_value = carteira_mock

    return uow


def _mock_unicidade() -> Mock:
    """Mock do UnicidadeDevedorService."""
    mock = Mock(spec=UnicidadeDevedorService)
    mock.verificar_documento_disponivel = Mock()
    return mock


def _mock_auditoria() -> Mock:
    """Mock do AuditoriaRegistro."""
    return Mock(spec=AuditoriaRegistro)


class TestDevedorCadastroService:
    """Testes do DevedorCadastroService (IMP-051)."""

    def test_criar_devedor_sucesso(self) -> None:
        """Deve criar Devedor com sucesso e retornar DevedorCriado."""
        uow = _mock_uow_factory()
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory, unicidade, auditoria)

        contatos = [
            {"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True},
            {"tipo": "email", "valor": "joao@exemplo.com", "preferencial": False},
        ]

        resultado = service.criar(CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY)

        assert isinstance(resultado, DevedorCriado)
        assert resultado.carteira_id == CARTEIRA_ID
        assert resultado.documento == DOCUMENTO
        assert resultado.nome == "João da Silva"
        assert resultado.estado == DevedorState.ATIVO
        assert len(resultado.contatos) == 2

        # Verifica chamadas de auditoria
        assert auditoria.registrar.call_count >= 3  # inicio, aggregate_criado, evento_cadastrado, sucesso

        # Verifica unicidade chamada
        unicidade.verificar_documento_disponivel.assert_called_once()

        # Verifica persistência
        uow.devedor.save.assert_called_once()
        uow.idempotencia.registrar.assert_called_once()
        uow.idempotencia.concluir.assert_called_once()
        uow.commit.assert_called_once()

    def test_criar_devedor_replay_mesma_chave(self) -> None:
        """Replay com mesma Idempotency-Key deve retornar resultado original."""
        # Primeiro cria um service com factory que retorna None na idempotência
        uow_first = _mock_uow_factory()
        uow_factory_first = lambda: uow_first
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory_first, unicidade, auditoria)

        contatos = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]

        # Primeira chamada
        resultado1 = service.criar(CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY)

        # Segunda chamada (replay) - configura mock para retornar o resultado
        uow_replay = _mock_uow_factory()
        import json

        # Simula o registro de idempotência já concluído
        uow_replay.idempotencia.find_by_chave.return_value = {
            "solicitacao_hash": uow_first.idempotencia.registrar.call_args[0][2] if uow_first.idempotencia.registrar.call_args else "hash",
            "estado": "finished",
            "resultado": json.dumps(
                {
                    "devedor_id": str(resultado1.devedor_id),
                    "carteira_id": str(resultado1.carteira_id),
                    "documento": resultado1.documento,
                    "nome": resultado1.nome,
                    "contatos": list(resultado1.contatos),
                    "estado": resultado1.estado.value,
                    "criado_em": resultado1.criado_em.isoformat(),
                }
            ),
        }

        def uow_factory_replay():
            return uow_replay

        service2 = DevedorCadastroService(uow_factory_replay, unicidade, auditoria)
        resultado2 = service2.criar(CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY)

        assert resultado2.devedor_id == resultado1.devedor_id
        assert resultado2.documento == resultado1.documento
        assert resultado2.nome == resultado1.nome

        # Auditoria de replay registrada
        auditoria.registrar.assert_any_call(
            "devedor", None, "criar.replay", "ok",
            detalhes=json.dumps({"idempotency_key": IDEMPOTENCY_KEY})
        )

    def test_criar_devedor_conflito_idempotencia_hash_divergente(self) -> None:
        """Chave com hash divergente deve levantar IdempotenciaConflitoError."""
        uow = _mock_uow_factory()
        uow.idempotencia.find_by_chave.return_value = {
            "solicitacao_hash": "hash_diferente",
            "estado": "finished",
            "resultado": "{}",
        }
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory, unicidade, auditoria)

        contatos = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]

        with pytest.raises(IdempotenciaConflitoError) as exc_info:
            service.criar(CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY)

        assert exc_info.value.idempotency_key == IDEMPOTENCY_KEY
        assert "divergente" in exc_info.value.motivo.lower()

    def test_criar_devedor_unicidade_falha(self) -> None:
        """Violação de unicidade deve propagar erro do domínio."""
        from emprestimo.domain.common.errors import DevedorJaExisteError

        uow = _mock_uow_factory()
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        unicidade.verificar_documento_disponivel.side_effect = DevedorJaExisteError(DOCUMENTO, CARTEIRA_ID)
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory, unicidade, auditoria)

        contatos = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]

        with pytest.raises(DevedorJaExisteError) as exc_info:
            service.criar(CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY)

        assert exc_info.value.documento == DOCUMENTO
        assert exc_info.value.carteira_id == CARTEIRA_ID
        # Auditoria de falha registrada
        auditoria.registrar.assert_any_call(
            "devedor", None, "criar.falha", "falhou",
            detalhes=f"DevedorJaExisteError: Devedor com documento {DOCUMENTO!r} já existente na Carteira {CARTEIRA_ID}"
        )
        auditoria.registrar.assert_any_call("devedor", None, "criar.rollback", "rollback_aplicado")

    def test_criar_devedor_sem_contatos_falha(self) -> None:
        """Criação sem contatos deve falhar (RN-003)."""
        from emprestimo.domain.common.errors import ViolacaoInvarianteError

        uow_factory = lambda: _mock_uow_factory()
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory, unicidade, auditoria)

        with pytest.raises(ViolacaoInvarianteError) as exc_info:
            service.criar(CARTEIRA_ID, DOCUMENTO, "João da Silva", [], IDEMPOTENCY_KEY)

        assert exc_info.value.codigo == "RN-003"

    def test_criar_devedor_contato_duplicado_falha(self) -> None:
        """Contato tipo+valor duplicado deve falhar (DOMAIN-021)."""
        from emprestimo.domain.common.errors import ViolacaoInvarianteError

        uow_factory = lambda: _mock_uow_factory()
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory, unicidade, auditoria)

        contatos = [
            {"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True},
            {"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": False},
        ]

        with pytest.raises(ViolacaoInvarianteError) as exc_info:
            service.criar(CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY)

        assert exc_info.value.codigo == "DOMAIN-021"

    def test_criar_devedor_dois_preferenciais_mesmo_tipo_falha(self) -> None:
        """Dois preferenciais do mesmo tipo deve falhar (RN-005)."""
        from emprestimo.domain.common.errors import ViolacaoInvarianteError

        uow_factory = lambda: _mock_uow_factory()
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory, unicidade, auditoria)

        contatos = [
            {"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True},
            {"tipo": "telefone", "valor": "(21) 98765-4321", "preferencial": True},
        ]

        with pytest.raises(ViolacaoInvarianteError) as exc_info:
            service.criar(CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY)

        assert exc_info.value.codigo == "RN-005"