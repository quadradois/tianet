"""Testes unitários do DevedorCadastroService (IMP-051)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import Mock

import pytest

from emprestimo.application.cadastro_devedor import DevedorCadastroService, DevedorCriado
from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.common.errors import DevedorJaExisteError
from emprestimo.domain.credit.devedor import DevedorState
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

        def uow_factory() -> Mock:
            return uow

        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory, unicidade, auditoria)

        contatos = [
            {"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True},
            {"tipo": "email", "valor": "joao@exemplo.com", "preferencial": False},
        ]

        resultado = service.criar(
            CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY
        )

        assert isinstance(resultado, DevedorCriado)
        assert resultado.carteira_id == CARTEIRA_ID
        assert resultado.documento == DOCUMENTO
        assert resultado.nome == "João da Silva"
        assert resultado.estado == DevedorState.ATIVO
        assert len(resultado.contatos) == 2

        # Verifica chamadas de auditoria
        assert (
            auditoria.registrar.call_count >= 3
        )  # inicio, aggregate_criado, evento_cadastrado, sucesso

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

        def uow_factory_first() -> Mock:
            return uow_first

        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory_first, unicidade, auditoria)

        contatos = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]

        # Primeira chamada
        resultado1 = service.criar(
            CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY
        )

        # Segunda chamada (replay) - configura mock para retornar o resultado
        uow_replay = _mock_uow_factory()
        import json

        # Simula o registro de idempotência já concluído
        uow_replay.idempotencia.find_by_chave.return_value = {
            "solicitacao_hash": (
                uow_first.idempotencia.registrar.call_args[0][2]
                if uow_first.idempotencia.registrar.call_args
                else "hash"
            ),
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

        def uow_factory_replay() -> Mock:
            return uow_replay

        service2 = DevedorCadastroService(uow_factory_replay, unicidade, auditoria)
        resultado2 = service2.criar(
            CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY
        )

        assert resultado2.devedor_id == resultado1.devedor_id
        assert resultado2.documento == resultado1.documento
        assert resultado2.nome == resultado1.nome

        # Auditoria de replay registrada, com a mesma autoria dos demais eventos
        auditoria.registrar.assert_any_call(
            "devedor",
            None,
            "criar.replay",
            "ok",
            detalhes=json.dumps(
                {"idempotency_key": IDEMPOTENCY_KEY, "usuario_id": None}, sort_keys=True
            ),
        )

    def test_criar_devedor_conflito_idempotencia_hash_divergente(self) -> None:
        """Chave com hash divergente deve levantar IdempotenciaConflitoError."""
        uow = _mock_uow_factory()
        uow.idempotencia.find_by_chave.return_value = {
            "solicitacao_hash": "hash_diferente",
            "estado": "finished",
            "resultado": "{}",
        }

        def uow_factory() -> Mock:
            return uow

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

        def uow_factory() -> Mock:
            return uow

        unicidade = _mock_unicidade()
        unicidade.verificar_documento_disponivel.side_effect = DevedorJaExisteError(
            DOCUMENTO, CARTEIRA_ID
        )
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory, unicidade, auditoria)

        contatos = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]

        with pytest.raises(DevedorJaExisteError) as exc_info:
            service.criar(CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY)

        assert exc_info.value.documento == DOCUMENTO
        assert exc_info.value.carteira_id == CARTEIRA_ID
        # Auditoria de falha registra o TIPO do erro, nunca a mensagem: a
        # mensagem de DevedorJaExisteError interpola o documento, e a trilha
        # e append-only — um CPF gravado aqui nao sai mais (IMP-361).
        auditoria.registrar.assert_any_call(
            "devedor",
            None,
            "criar.falha",
            "falhou",
            detalhes=json.dumps(
                {
                    "erro_tipo": "DevedorJaExisteError",
                    "idempotency_key": IDEMPOTENCY_KEY,
                    "usuario_id": None,
                },
                sort_keys=True,
            ),
        )
        auditoria.registrar.assert_any_call(
            "devedor",
            None,
            "criar.rollback",
            "rollback_aplicado",
            detalhes=json.dumps(
                {"idempotency_key": IDEMPOTENCY_KEY, "usuario_id": None}, sort_keys=True
            ),
        )

    def test_criar_devedor_sem_contatos_falha(self) -> None:
        """Criação sem contatos deve falhar (RN-003)."""
        from emprestimo.domain.common.errors import ViolacaoInvarianteError

        def uow_factory() -> Mock:
            return _mock_uow_factory()

        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorCadastroService(uow_factory, unicidade, auditoria)

        with pytest.raises(ViolacaoInvarianteError) as exc_info:
            service.criar(CARTEIRA_ID, DOCUMENTO, "João da Silva", [], IDEMPOTENCY_KEY)

        assert exc_info.value.codigo == "RN-003"

    def test_criar_devedor_contato_duplicado_falha(self) -> None:
        """Contato tipo+valor duplicado deve falhar (DOMAIN-021)."""
        from emprestimo.domain.common.errors import ViolacaoInvarianteError

        def uow_factory() -> Mock:
            return _mock_uow_factory()

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

        def uow_factory() -> Mock:
            return _mock_uow_factory()

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

    def test_conflito_chave_em_andamento(self) -> None:
        """Chave registrada e ainda nao concluida bloqueia (IMP-063).

        Ocorre quando uma requisicao anterior com a mesma chave falhou entre o
        registro e a conclusao: o estado permanece diferente de "finished".
        """
        contatos = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]
        # O estado é avaliado ANTES do hash nos quatro casos de uso, então um hash
        # qualquer basta: "em andamento" prevalece sobre "divergente".
        uow = _mock_uow_factory()
        uow.idempotencia.find_by_chave.return_value = {
            "solicitacao_hash": "hash-qualquer",
            "estado": "running",
            "resultado": None,
        }
        service = DevedorCadastroService(lambda: uow, _mock_unicidade(), _mock_auditoria())

        with pytest.raises(IdempotenciaConflitoError) as exc_info:
            service.criar(CARTEIRA_ID, DOCUMENTO, "Joao da Silva", contatos, IDEMPOTENCY_KEY)

        assert "andamento" in exc_info.value.motivo


USUARIO_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _detalhes_registrados(auditoria: Mock) -> list[tuple[str, dict[str, object]]]:
    """(acao, detalhes decodificados) de cada evento gravado na trilha.

    Evento sem `detalhes` ou com `detalhes` que nao seja JSON aparece como
    dicionario vazio — e assim reprova as asserções de autoria abaixo, que e
    exatamente o que se quer: a trilha nao aceita evento opaco.
    """
    eventos: list[tuple[str, dict[str, object]]] = []
    for chamada in auditoria.registrar.call_args_list:
        acao = chamada.args[2]
        bruto = chamada.kwargs.get("detalhes")
        if not isinstance(bruto, str):
            eventos.append((acao, {}))
            continue
        try:
            eventos.append((acao, json.loads(bruto)))
        except json.JSONDecodeError:
            eventos.append((acao, {}))
    return eventos


class TestAutoriaNaTrilha:
    """IMP-361 — toda escrita identifica o Principal na trilha da ADR-002.

    Guardrail: ferramenta de escrita nova que esqueca a autoria reprova aqui,
    sem depender de alguem lembrar de conferir call site por call site.
    """

    def test_todo_evento_do_caminho_feliz_carrega_o_principal(self) -> None:
        uow = _mock_uow_factory()
        auditoria = _mock_auditoria()
        service = DevedorCadastroService(lambda: uow, _mock_unicidade(), auditoria)
        contatos = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]

        service.criar(
            CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY, USUARIO_ID
        )

        eventos = _detalhes_registrados(auditoria)
        assert eventos, "o cadastro precisa deixar rastro na trilha"
        for acao, detalhes in eventos:
            assert detalhes.get("usuario_id") == str(USUARIO_ID), f"{acao} sem autoria"

    def test_falha_e_rollback_carregam_o_mesmo_principal(self) -> None:
        unicidade = _mock_unicidade()
        unicidade.verificar_documento_disponivel.side_effect = DevedorJaExisteError(
            DOCUMENTO, CARTEIRA_ID
        )
        auditoria = _mock_auditoria()
        service = DevedorCadastroService(lambda: _mock_uow_factory(), unicidade, auditoria)
        contatos = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]

        with pytest.raises(DevedorJaExisteError):
            service.criar(
                CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY, USUARIO_ID
            )

        eventos = dict(_detalhes_registrados(auditoria))
        assert eventos["criar.falha"]["usuario_id"] == str(USUARIO_ID)
        assert eventos["criar.rollback"]["usuario_id"] == str(USUARIO_ID)

    def test_caminho_de_falha_nao_grava_o_documento(self) -> None:
        """A trilha e append-only: um CPF gravado aqui nao sai mais.

        A mensagem de DevedorJaExisteError interpola o documento, entao registrar
        `str(exc)` vazaria PII em todo cadastro duplicado.
        """
        unicidade = _mock_unicidade()
        unicidade.verificar_documento_disponivel.side_effect = DevedorJaExisteError(
            DOCUMENTO, CARTEIRA_ID
        )
        auditoria = _mock_auditoria()
        service = DevedorCadastroService(lambda: _mock_uow_factory(), unicidade, auditoria)
        contatos = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]

        with pytest.raises(DevedorJaExisteError):
            service.criar(
                CARTEIRA_ID, DOCUMENTO, "João da Silva", contatos, IDEMPOTENCY_KEY, USUARIO_ID
            )

        for chamada in auditoria.registrar.call_args_list:
            assert DOCUMENTO not in str(chamada.kwargs.get("detalhes"))
        eventos = dict(_detalhes_registrados(auditoria))
        assert eventos["criar.falha"]["erro_tipo"] == "DevedorJaExisteError"
