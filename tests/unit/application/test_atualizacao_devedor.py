"""Testes unitários do DevedorAtualizacaoService (IMP-054)."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from emprestimo.application.atualizacao_devedor import (
    DevedorAtualizacaoService,
    DevedorAtualizadoResultado,
)
from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.eventos_devedor import DevedorAtualizado as DevedorAtualizadoEvento
from emprestimo.domain.credit.unicidade_devedor import UnicidadeDevedorService
from emprestimo.domain.common.errors import ViolacaoInvarianteError

CARTEIRA_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DEVEDOR_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
TENANT_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
DOCUMENTO = "52998224725"


def _mock_devedor() -> Devedor:
    """Cria um Devedor mock para testes."""
    contatos = (
        Contato(
            devedor_id=DEVEDOR_ID,
            tipo=TipoContato.TELEFONE,
            valor="(11) 1234-5678",
            preferencial=True,
        ),
        Contato(
            devedor_id=DEVEDOR_ID,
            tipo=TipoContato.EMAIL,
            valor="joao@exemplo.com",
            preferencial=False,
        ),
    )
    devedor = Devedor.criar(
        carteira_id=CARTEIRA_ID,
        documento=Documento.from_str(DOCUMENTO),
        nome="João da Silva",
        contatos=contatos,
    )
    # Força o ID para controle nos testes
    devedor.id = DEVEDOR_ID
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
    uow.contato = Mock()
    uow.contato.save = Mock()
    # TASK-099: a atualização reconcilia a coleção com o banco. Sem contatos
    # previamente persistidos, nada há para remover.
    uow.contato.find_by_devedor.return_value = []
    uow.contato.remove = Mock()
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


def _mock_unicidade() -> Mock:
    """Cria um mock do UnicidadeDevedorService."""
    return Mock(spec=UnicidadeDevedorService)


def _mock_auditoria() -> Mock:
    """Cria um mock do AuditoriaRegistro."""
    return Mock()


class TestDevedorAtualizacaoService:
    """Testes do DevedorAtualizacaoService (IMP-054)."""

    def test_atualizar_apenas_nome(self) -> None:
        """Deve atualizar apenas o nome do Devedor."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)
        resultado = service.atualizar(
            DEVEDOR_ID,
            "idem-key-123",
            nome="João Santos",
        )

        assert isinstance(resultado, DevedorAtualizadoResultado)
        assert resultado.devedor_id == DEVEDOR_ID
        assert resultado.carteira_id == CARTEIRA_ID
        assert resultado.documento == DOCUMENTO
        assert resultado.nome == "João Santos"
        assert resultado.estado == DevedorState.ATIVO
        assert len(resultado.contatos) == 2  # contatos originais mantidos
        assert isinstance(resultado.atualizado_em, datetime)

        # Verifica que o devedor foi salvo com o novo nome
        uow.devedor.save.assert_called_once_with(devedor)
        uow.commit.assert_called_once()
        uow.idempotencia.concluir.assert_called_once()

    def test_atualizar_apenas_contatos(self) -> None:
        """Deve substituir todos os contatos do Devedor."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        novos_contatos = [
            {"tipo": "telefone", "valor": "(11) 99999-9999", "preferencial": True},
            {"tipo": "email", "valor": "novo@exemplo.com", "preferencial": False},
        ]
        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)
        resultado = service.atualizar(
            DEVEDOR_ID,
            "idem-key-456",
            contatos=novos_contatos,
        )

        assert resultado.nome == "João da Silva"  # nome original mantido
        assert len(resultado.contatos) == 2
        assert resultado.contatos[0]["tipo"] == "telefone"
        assert resultado.contatos[0]["valor"] == "(11) 99999-9999"
        assert resultado.contatos[0]["preferencial"] is True
        assert resultado.contatos[1]["tipo"] == "email"
        assert resultado.contatos[1]["valor"] == "novo@exemplo.com"
        assert resultado.contatos[1]["preferencial"] is False
        uow.devedor.save.assert_called_once_with(devedor)
        uow.commit.assert_called_once()

    def test_atualizar_nome_e_contatos_juntos(self) -> None:
        """Deve atualizar nome e contatos em uma única operação."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        novos_contatos = [
            {"tipo": "whatsapp", "valor": "(11) 98765-4321", "preferencial": True},
        ]
        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)
        resultado = service.atualizar(
            DEVEDOR_ID,
            "idem-key-789",
            nome="João da Silva Atualizado",
            contatos=novos_contatos,
        )

        assert resultado.nome == "João da Silva Atualizado"
        assert len(resultado.contatos) == 1
        assert resultado.contatos[0]["tipo"] == "whatsapp"
        assert resultado.contatos[0]["valor"] == "(11) 98765-4321"
        assert resultado.contatos[0]["preferencial"] is True
        uow.devedor.save.assert_called_once_with(devedor)
        uow.commit.assert_called_once()

    def test_replay_idempotencia_mesma_chave_mesmo_resultado(self) -> None:
        """Replay com a mesma Idempotency-Key deve retornar o mesmo resultado (AD-002)."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        import json

        # O hash deve ser calculado da mesma forma que o service: nome.strip() e contatos ordenados
        from emprestimo.application.atualizacao_devedor import _solicitacao_hash

        hash_esperado = _solicitacao_hash(
            DEVEDOR_ID,
            nome="João da Silva Atualizado",
            contatos=[{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}],
        )
        uow.idempotencia.find_by_chave.return_value = {
            "chave": "idem-key-replay",
            "escopo": "devedor-atualizacao",
            "solicitacao_hash": hash_esperado,  # hash calculado consistentemente
            "estado": "finished",
            "resultado": json.dumps(
                {
                    "devedor_id": str(DEVEDOR_ID),
                    "carteira_id": str(CARTEIRA_ID),
                    "documento": DOCUMENTO,
                    "nome": "João da Silva Atualizado",
                    "contatos": [
                        {"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}
                    ],
                    "estado": "ativo",
                    "atualizado_em": datetime.now().isoformat(),
                }
            ),
            "criado_em": datetime.now().isoformat(),
            "concluido_em": datetime.now().isoformat(),
        }
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)
        resultado = service.atualizar(
            DEVEDOR_ID,
            "idem-key-replay",
            nome="João da Silva Atualizado",
            contatos=[{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}],
        )

        assert resultado.nome == "João da Silva Atualizado"
        # Não deve chamar save novamente (replay)
        uow.devedor.save.assert_not_called()
        uow.commit.assert_called_once()
        auditoria.registrar.assert_any_call(
            "devedor",
            None,
            "atualizar.replay",
            "ok",
            detalhes=json.dumps({"idempotency_key": "idem-key-replay"}),
        )

    def test_conflito_idempotencia_payload_divergente(self) -> None:
        """Reutilizar chave com payload diferente deve lançar IdempotenciaConflitoError (AD-002)."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        # Hash diferente do payload atual
        uow.idempotencia.find_by_chave.return_value = {
            "chave": "idem-key-conflito",
            "escopo": "devedor-atualizacao",
            "solicitacao_hash": "b" * 64,  # hash diferente
            "estado": "finished",
            "resultado": '{"devedor_id": "...", "nome": "Outro"}',
            "criado_em": datetime.now().isoformat(),
            "concluido_em": datetime.now().isoformat(),
        }
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)

        with pytest.raises(IdempotenciaConflitoError) as exc_info:
            service.atualizar(
                DEVEDOR_ID,
                "idem-key-conflito",
                nome="João Santos",
            )

        assert exc_info.value.idempotency_key == "idem-key-conflito"
        assert "divergente" in exc_info.value.motivo

    def test_conflito_idempotencia_em_andamento(self) -> None:
        """Reutilizar chave enquanto atualização anterior ainda em andamento deve lançar IdempotenciaConflitoError."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow.idempotencia.find_by_chave.return_value = {
            "chave": "idem-key-andamento",
            "escopo": "devedor-atualizacao",
            "solicitacao_hash": "c" * 64,
            "estado": "started",  # ainda em andamento
            "resultado": None,
            "criado_em": datetime.now().isoformat(),
            "concluido_em": None,
        }
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)

        with pytest.raises(IdempotenciaConflitoError) as exc_info:
            service.atualizar(
                DEVEDOR_ID,
                "idem-key-andamento",
                nome="João Santos",
            )

        assert "andamento" in exc_info.value.motivo

    def test_devedor_nao_encontrado(self) -> None:
        """Deve lançar DevedorNaoEncontradoError quando Devedor não existe."""
        uow = _mock_uow_factory(None)  # devedor = None
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)

        with pytest.raises(Exception) as exc_info:
            service.atualizar(
                DEVEDOR_ID,
                "idem-key-404",
                nome="João Santos",
            )

        # Verifica se é DevedorNaoEncontradoError (importado localmente no service)
        assert "Devedor não encontrado" in str(exc_info.value)

    def test_contatos_lista_vazia_viola_rn003(self) -> None:
        """Deve lançar ViolacaoInvarianteError RN-003 quando lista de contatos vazia."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)

        with pytest.raises(ViolacaoInvarianteError) as exc_info:
            service.atualizar(
                DEVEDOR_ID,
                "idem-key-rn003",
                contatos=[],  # lista vazia
            )

        assert exc_info.value.codigo == "RN-003"
        assert "pelo menos um contato" in str(exc_info.value)

    def test_dois_preferenciais_mesmo_tipo_viola_rn005(self) -> None:
        """Deve lançar ViolacaoInvarianteError RN-005 ao tentar dois preferenciais do mesmo tipo."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        # Dois telefones preferenciais
        contatos = [
            {"tipo": "telefone", "valor": "(11) 99999-9999", "preferencial": True},
            {"tipo": "telefone", "valor": "(11) 88888-8888", "preferencial": True},
        ]
        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)

        with pytest.raises(ViolacaoInvarianteError) as exc_info:
            service.atualizar(
                DEVEDOR_ID,
                "idem-key-rn005",
                contatos=contatos,
            )

        assert exc_info.value.codigo == "RN-005"
        assert "preferencial" in str(exc_info.value).lower()

    def test_contato_duplicado_tipo_valor_viola_domain021(self) -> None:
        """Deve lançar ViolacaoInvarianteError DOMAIN-021 ao tentar contatos duplicados."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        # Mesmo telefone duas vezes
        contatos = [
            {"tipo": "telefone", "valor": "(11) 99999-9999", "preferencial": True},
            {"tipo": "telefone", "valor": "(11) 99999-9999", "preferencial": False},
        ]
        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)

        with pytest.raises(ViolacaoInvarianteError) as exc_info:
            service.atualizar(
                DEVEDOR_ID,
                "idem-key-domain021",
                contatos=contatos,
            )

        assert exc_info.value.codigo == "DOMAIN-021"
        assert "já existente" in str(exc_info.value).lower()

    def test_auditoria_registra_eventos_corretos(self) -> None:
        """Deve registrar trilha completa de auditoria (inicio, aggregate_atualizado, evento_atualizado, sucesso)."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)
        service.atualizar(
            DEVEDOR_ID,
            "idem-key-auditoria",
            nome="João Atualizado",
        )

        # Verifica chamadas de auditoria na ordem
        calls = auditoria.registrar.call_args_list
        # 1. inicio
        assert calls[0][0][2] == "atualizar.inicio"
        assert calls[0][0][3] == "iniciado"
        # 2. aggregate_atualizado
        assert calls[1][0][2] == "atualizar.aggregate_atualizado"
        assert calls[1][0][3] == "ok"
        # 3. evento_atualizado
        assert calls[2][0][2] == "atualizar.evento_atualizado"
        assert calls[2][0][3] == "ok"
        # 4. sucesso (fora do with, após commit)
        assert calls[3][0][2] == "atualizar.sucesso"
        assert calls[3][0][3] == "ok"

    def test_auditoria_registra_falha_e_rollback_em_excecao(self) -> None:
        """Deve registrar falha e rollback quando ocorre exceção durante atualização."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        # Força erro no save
        uow.devedor.save.side_effect = Exception("DB error")
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)

        with pytest.raises(Exception):
            service.atualizar(
                DEVEDOR_ID,
                "idem-key-falha",
                nome="João Santos",
            )

        # Verifica que registrou falha e rollback
        calls = auditoria.registrar.call_args_list
        # Deve ter: inicio, falha, rollback
        eventos = [c[0][2] for c in calls]
        assert "atualizar.falha" in eventos
        assert "atualizar.rollback" in eventos
        # Não deve ter sucesso
        assert "atualizar.sucesso" not in eventos

    def test_normaliza_nome_strip(self) -> None:
        """Deve normalizar nome aplicando strip()."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)
        resultado = service.atualizar(
            DEVEDOR_ID,
            "idem-key-strip",
            nome="  João Santos  ",
        )

        assert resultado.nome == "João Santos"

    def test_contatos_valor_strip_e_tipo_enum(self) -> None:
        """Deve aplicar strip no valor dos contatos e converter tipo para Enum."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)
        uow_factory = lambda: uow
        unicidade = _mock_unicidade()
        auditoria = _mock_auditoria()

        service = DevedorAtualizacaoService(uow_factory, unicidade, auditoria)
        resultado = service.atualizar(
            DEVEDOR_ID,
            "idem-key-contato-strip",
            contatos=[{"tipo": "TELEFONE", "valor": "  (11) 99999-9999  ", "preferencial": True}],
        )

        # Verifica que o resultado final tem o contato com valor stripado e tipo convertido
        assert len(resultado.contatos) == 1
        assert resultado.contatos[0]["tipo"] == "telefone"
        assert resultado.contatos[0]["valor"] == "(11) 99999-9999"
        assert resultado.contatos[0]["preferencial"] is True
