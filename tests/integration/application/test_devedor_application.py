"""Testes de integração da camada de Aplicação — Devedor (IMP-061).

PostgreSQL real. Diferente dos testes de API, que exercitam o contrato HTTP,
aqui os casos de uso são chamados diretamente: o que se verifica é a transação
única (AD-001), o replay da Idempotency-Key (AD-002), a constraint UNIQUE, a
trilha de auditoria (ADR-002) e a ausência de estados parciais após falha.

A verificação usa sempre uma sessão independente da usada pelo caso de uso —
ler pela mesma sessão mascararia dados que só existem na transação aberta.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory

from emprestimo.application.atualizacao_devedor import DevedorAtualizacaoService
from emprestimo.application.cadastro_devedor import DevedorCadastroService
from emprestimo.application.consulta_devedor import (
    DevedorConsultaPorDocumentoService,
    DevedorConsultaService,
    DevedorListagemService,
)
from emprestimo.application.errors import (
    DevedorNaoEncontradoError,
    IdempotenciaConflitoError,
)
from emprestimo.application.estado_devedor import DevedorEstadoService
from emprestimo.application.historico_devedor import DevedorHistoricoService
from emprestimo.domain.common.errors import DevedorJaExisteError, ViolacaoInvarianteError
from emprestimo.domain.credit.devedor import DevedorState
from emprestimo.domain.credit.ports import DevedorFiltros
from emprestimo.domain.credit.unicidade_devedor import UnicidadeDevedorService
from emprestimo.infrastructure.auditoria import (
    SqlAlchemyAuditoriaConsulta,
    SqlAlchemyAuditoriaRegistro,
)
from emprestimo.infrastructure.db.orm import (
    AuditoriaLogORM,
    ContatoORM,
    DevedorORM,
    IdempotencyKeyORM,
)
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyTenantRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

CPF_A = "52998224725"
CPF_B = "11144477735"

CONTATOS = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]


@dataclass
class _Ambiente:
    cadastro: DevedorCadastroService
    consulta: DevedorConsultaService
    por_documento: DevedorConsultaPorDocumentoService
    listagem: DevedorListagemService
    atualizacao: DevedorAtualizacaoService
    estado: DevedorEstadoService
    historico: DevedorHistoricoService
    carteira_id: uuid.UUID
    session_factory: sessionmaker[Session]


@pytest.fixture
def ambiente(session_factory: sessionmaker[Session], session: Session) -> _Ambiente:
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    session.commit()

    def uow() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    unicidade = UnicidadeDevedorService(SqlAlchemyDevedorRepository(session))

    return _Ambiente(
        cadastro=DevedorCadastroService(uow, unicidade, auditoria),
        consulta=DevedorConsultaService(uow),
        por_documento=DevedorConsultaPorDocumentoService(uow),
        listagem=DevedorListagemService(uow),
        atualizacao=DevedorAtualizacaoService(uow, unicidade, auditoria),
        estado=DevedorEstadoService(uow, auditoria),
        historico=DevedorHistoricoService(uow, SqlAlchemyAuditoriaConsulta(session)),
        carteira_id=carteira.id,
        session_factory=session_factory,
    )


def _criar(amb: _Ambiente, chave: str = "chave-1", documento: str = CPF_A, **extras):
    return amb.cadastro.criar(
        carteira_id=amb.carteira_id,
        documento=documento,
        nome=extras.get("nome", "João da Silva"),
        contatos=extras.get("contatos", CONTATOS),
        idempotency_key=chave,
    )


def _contar(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


def _acoes(session: Session) -> set[str]:
    return set(session.scalars(select(AuditoriaLogORM.acao)).all())


# --- Transação única (AD-001) ------------------------------------------------


def test_cadastro_persiste_devedor_contatos_e_chave(ambiente: _Ambiente) -> None:
    resultado = _criar(ambiente)

    assert resultado.estado is DevedorState.ATIVO
    with ambiente.session_factory() as s:
        devedor = s.get(DevedorORM, resultado.devedor_id)
        assert devedor is not None
        assert devedor.documento == CPF_A
        assert devedor.estado == "ativo"
        assert _contar(s, ContatoORM) == 1
        chave = s.scalar(select(IdempotencyKeyORM).where(IdempotencyKeyORM.chave == "chave-1"))
        assert chave is not None
        assert chave.estado == "finished"
        assert str(resultado.devedor_id) in chave.resultado


def test_documento_duplicado_nao_deixa_dados_parciais(ambiente: _Ambiente) -> None:
    """A segunda tentativa falha na unicidade e nada dela pode sobrar no banco."""
    _criar(ambiente, chave="chave-1")

    with pytest.raises(DevedorJaExisteError):
        _criar(ambiente, chave="chave-2", nome="Outro Nome")

    with ambiente.session_factory() as s:
        assert _contar(s, DevedorORM) == 1
        assert _contar(s, ContatoORM) == 1


def test_contatos_invalidos_nao_persistem_o_devedor(ambiente: _Ambiente) -> None:
    """RN-005: dois preferenciais do mesmo tipo. O rollback é da transação inteira."""
    contatos = [
        {"tipo": "telefone", "valor": "(11) 1111-1111", "preferencial": True},
        {"tipo": "telefone", "valor": "(11) 2222-2222", "preferencial": True},
    ]

    with pytest.raises(ViolacaoInvarianteError):
        _criar(ambiente, chave="chave-rn005", contatos=contatos)

    with ambiente.session_factory() as s:
        assert _contar(s, DevedorORM) == 0
        assert _contar(s, ContatoORM) == 0


# --- Idempotência (AD-002) ---------------------------------------------------


def test_replay_retorna_mesmo_resultado_sem_duplicar(ambiente: _Ambiente) -> None:
    primeiro = _criar(ambiente, chave="chave-replay")
    segundo = _criar(ambiente, chave="chave-replay")

    assert segundo.devedor_id == primeiro.devedor_id
    with ambiente.session_factory() as s:
        assert _contar(s, DevedorORM) == 1
        assert _contar(s, IdempotencyKeyORM) == 1


def test_chave_reutilizada_com_payload_divergente_gera_conflito(ambiente: _Ambiente) -> None:
    _criar(ambiente, chave="chave-div")

    with pytest.raises(IdempotenciaConflitoError):
        _criar(ambiente, chave="chave-div", documento=CPF_B, nome="Outra Pessoa")

    with ambiente.session_factory() as s:
        assert _contar(s, DevedorORM) == 1


def test_idempotencia_isolada_por_caso_de_uso(ambiente: _Ambiente) -> None:
    """A mesma chave em escopos distintos não colide: o escopo compõe a identidade."""
    criado = _criar(ambiente, chave="chave-compartilhada")

    ambiente.estado.inativar(criado.devedor_id, "chave-compartilhada")

    with ambiente.session_factory() as s:
        assert s.get(DevedorORM, criado.devedor_id).estado == "inativo"
        escopos = set(s.scalars(select(IdempotencyKeyORM.escopo)).all())
        assert {"devedor-cadastro", "devedor-estado"} <= escopos


# --- Trilha de auditoria (ADR-002) -------------------------------------------


def test_auditoria_do_cadastro_gravada_no_sucesso(ambiente: _Ambiente) -> None:
    _criar(ambiente)

    with ambiente.session_factory() as s:
        acoes = _acoes(s)
        assert "criar.inicio" in acoes
        assert "criar.aggregate_criado" in acoes
        assert "criar.evento_cadastrado" in acoes
        assert "criar.sucesso" in acoes


def test_auditoria_sobrevive_ao_rollback(ambiente: _Ambiente) -> None:
    """ADR-002: a trilha usa sessão independente e persiste mesmo quando a
    transação de negócio é desfeita."""
    _criar(ambiente, chave="chave-1")

    with pytest.raises(DevedorJaExisteError):
        _criar(ambiente, chave="chave-2", nome="Outro")

    with ambiente.session_factory() as s:
        acoes = _acoes(s)
        assert "criar.falha" in acoes
        assert "criar.rollback" in acoes
        assert _contar(s, DevedorORM) == 1  # o rollback valeu para o dado


def test_auditoria_das_transicoes_de_estado(ambiente: _Ambiente) -> None:
    criado = _criar(ambiente)
    ambiente.estado.inativar(criado.devedor_id, "k-inativar")
    ambiente.estado.reativar(criado.devedor_id, "k-reativar")

    with ambiente.session_factory() as s:
        acoes = _acoes(s)
        assert {
            "inativar.estado_alterado",
            "inativar.evento_inativado",
            "inativar.sucesso",
        } <= acoes
        assert {
            "reativar.estado_alterado",
            "reativar.evento_reativado",
            "reativar.sucesso",
        } <= acoes


# --- Consultas ---------------------------------------------------------------


def test_consulta_por_id_traz_contatos(ambiente: _Ambiente) -> None:
    criado = _criar(ambiente)

    devedor = ambiente.consulta.consultar_por_id(criado.devedor_id)

    assert devedor is not None
    assert len(devedor.contatos) == 1
    assert devedor.contatos[0].valor == "(11) 1234-5678"


def test_consulta_por_documento_normaliza_a_entrada(ambiente: _Ambiente) -> None:
    """O documento é aceito com máscara e normalizado pelo Value Object."""
    _criar(ambiente)

    devedor = ambiente.por_documento.consultar_por_documento(ambiente.carteira_id, "529.982.247-25")

    assert devedor is not None
    assert devedor.documento.valor == CPF_A


def test_listagem_pagina_e_filtra(ambiente: _Ambiente) -> None:
    _criar(ambiente, chave="k1", nome="Ana Souza")
    segundo = _criar(ambiente, chave="k2", documento=CPF_B, nome="Bruno Lima")
    ambiente.estado.inativar(segundo.devedor_id, "k-inativar")

    todos = ambiente.listagem.listar(ambiente.carteira_id, 1, 20, DevedorFiltros())
    inativos = ambiente.listagem.listar(
        ambiente.carteira_id, 1, 20, DevedorFiltros(estado="inativo")
    )
    pagina2 = ambiente.listagem.listar(ambiente.carteira_id, 2, 1, DevedorFiltros())

    assert todos.total == 2
    assert inativos.total == 1
    assert list(inativos.items)[0].nome == "Bruno Lima"
    assert pagina2.pagina == 2
    assert len(list(pagina2.items)) == 1


# --- Atualização (FEATURE-007) -----------------------------------------------


def test_atualizacao_substitui_contatos_no_banco(ambiente: _Ambiente) -> None:
    criado = _criar(ambiente)

    ambiente.atualizacao.atualizar(
        criado.devedor_id,
        "k-update",
        nome="João Santos",
        contatos=[{"tipo": "email", "valor": "joao@exemplo.com", "preferencial": True}],
    )

    devedor = ambiente.consulta.consultar_por_id(criado.devedor_id)
    assert devedor is not None
    assert devedor.nome == "João Santos"
    assert len(devedor.contatos) == 1
    assert devedor.contatos[0].valor == "joao@exemplo.com"


def test_atualizacao_de_devedor_inexistente(ambiente: _Ambiente) -> None:
    with pytest.raises(DevedorNaoEncontradoError):
        ambiente.atualizacao.atualizar(uuid.uuid4(), "k-404", nome="Fantasma")


def test_documento_permanece_imutavel_apos_atualizacao(ambiente: _Ambiente) -> None:
    """INV-003: nenhum caminho de atualização altera o documento."""
    criado = _criar(ambiente)

    ambiente.atualizacao.atualizar(criado.devedor_id, "k-update", nome="Outro Nome")

    with ambiente.session_factory() as s:
        assert s.get(DevedorORM, criado.devedor_id).documento == CPF_A


# --- Transições de estado (FEATURE-008) --------------------------------------


def test_transicoes_persistem_no_banco(ambiente: _Ambiente) -> None:
    criado = _criar(ambiente)

    ambiente.estado.inativar(criado.devedor_id, "k-inativar")
    with ambiente.session_factory() as s:
        assert s.get(DevedorORM, criado.devedor_id).estado == "inativo"

    ambiente.estado.reativar(criado.devedor_id, "k-reativar")
    with ambiente.session_factory() as s:
        assert s.get(DevedorORM, criado.devedor_id).estado == "ativo"


def test_transicao_invalida_nao_altera_o_estado(ambiente: _Ambiente) -> None:
    """INV-005: inativar duas vezes viola a invariante e o dado não muda."""
    criado = _criar(ambiente)
    ambiente.estado.inativar(criado.devedor_id, "k1")

    with pytest.raises(ViolacaoInvarianteError) as exc:
        ambiente.estado.inativar(criado.devedor_id, "k2")

    assert exc.value.codigo == "INV-005"
    with ambiente.session_factory() as s:
        assert s.get(DevedorORM, criado.devedor_id).estado == "inativo"


def test_reativacao_nao_reabre_documento_para_outro_devedor(ambiente: _Ambiente) -> None:
    """INV-002: o documento continua ocupado mesmo com o Devedor inativo."""
    criado = _criar(ambiente)
    ambiente.estado.inativar(criado.devedor_id, "k-inativar")

    with pytest.raises(DevedorJaExisteError):
        _criar(ambiente, chave="k-outro", nome="Homônimo")


# --- Histórico (US-027) ------------------------------------------------------


def test_historico_reconstitui_a_trilha_do_devedor(ambiente: _Ambiente) -> None:
    criado = _criar(ambiente)
    ambiente.estado.inativar(criado.devedor_id, "k-inativar")

    eventos = ambiente.historico.consultar(criado.devedor_id)

    assert eventos is not None
    acoes = [e.acao for e in eventos]
    assert "criar.aggregate_criado" in acoes
    assert "inativar.sucesso" in acoes
    assert acoes.index("criar.aggregate_criado") < acoes.index("inativar.sucesso")


def test_historico_de_devedor_inexistente_retorna_none(ambiente: _Ambiente) -> None:
    assert ambiente.historico.consultar(uuid.uuid4()) is None
