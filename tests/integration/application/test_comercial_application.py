"""Testes de aplicacao do Comercial (IMP-113..IMP-117)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.comercial import (
    ConsultaComercialService,
    DecisaoComercialService,
    IntegracaoPropostaAprovadaService,
    PropostaComercialService,
    SimulacaoComercialService,
)
from emprestimo.application.errors import (
    PropostaComercialNaoEncontradaError,
    TransicaoEstadoInvalidaError,
    UsuarioNaoEncontradoError,
)
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import (
    AuditoriaLogORM,
    IdempotencyKeyORM,
    SimulacaoComercialORM,
)
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@dataclass(frozen=True)
class _Ambiente:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    usuario_id: uuid.UUID
    uow_factory: sessionmaker[Session]


class _UnitOfWorkComFalhaNoCommit(SqlAlchemyUnitOfWork):
    def commit(self) -> None:
        raise RuntimeError("falha forcada no commit do negocio")


def test_comercial_audita_falha_em_sessao_independente_e_reverte_negocio(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    with session_factory() as session:
        simulacoes_antes = session.scalar(select(func.count()).select_from(SimulacaoComercialORM))
        chaves_antes = session.scalar(select(func.count()).select_from(IdempotencyKeyORM))

    service = SimulacaoComercialService(
        lambda: _UnitOfWorkComFalhaNoCommit(session_factory),
        SqlAlchemyAuditoriaRegistro(session_factory),
    )
    with pytest.raises(RuntimeError, match="falha forcada"):
        service.criar(
            tenant_id=ambiente.tenant_id,
            carteira_id=ambiente.carteira_id,
            devedor_id=ambiente.devedor_id,
            usuario_id=ambiente.usuario_id,
            parametros={"valor": 2000, "parcelas": 8},
            idempotency_key=str(uuid.uuid4()),
        )

    with session_factory() as session:
        simulacoes_depois = session.scalar(select(func.count()).select_from(SimulacaoComercialORM))
        chaves_depois = session.scalar(select(func.count()).select_from(IdempotencyKeyORM))
        acoes = session.scalars(
            select(AuditoriaLogORM.acao)
            .where(AuditoriaLogORM.entidade == "simulacao_comercial")
            .where(AuditoriaLogORM.detalhes.contains(str(ambiente.carteira_id)))
        ).all()
    assert simulacoes_depois == simulacoes_antes
    assert chaves_depois == chaves_antes
    assert set(acoes) == {"criar.inicio", "criar.falha", "criar.rollback"}


def test_fluxo_comercial_cria_aprova_e_gera_contrato_logico(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    simulacoes = SimulacaoComercialService(lambda: SqlAlchemyUnitOfWork(session_factory), auditoria)
    propostas = PropostaComercialService(lambda: SqlAlchemyUnitOfWork(session_factory), auditoria)
    decisoes = DecisaoComercialService(lambda: SqlAlchemyUnitOfWork(session_factory), auditoria)
    integracao = IntegracaoPropostaAprovadaService(lambda: SqlAlchemyUnitOfWork(session_factory))

    simulacao = simulacoes.criar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        devedor_id=ambiente.devedor_id,
        usuario_id=ambiente.usuario_id,
        parametros={"valor": 2000, "parcelas": 8},
    )
    proposta = propostas.criar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        devedor_id=ambiente.devedor_id,
        usuario_id=ambiente.usuario_id,
        simulacao_id=simulacao.simulacao_id,
        parametros=simulacao.parametros,
    )

    enviada = decisoes.enviar_para_analise(
        proposta_id=proposta.proposta_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
    )
    aprovada = decisoes.aprovar(
        proposta_id=proposta.proposta_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
    )
    contrato = integracao.gerar_contrato_logico(
        proposta_id=proposta.proposta_id,
        tenant_id=ambiente.tenant_id,
    )

    assert enviada.estado is PropostaComercialState.EM_ANALISE
    assert aprovada.estado is PropostaComercialState.APROVADA
    assert aprovada.total_decisoes == 2
    assert contrato.proposta_id == proposta.proposta_id
    assert contrato.parametros_aprovados["valor"] == 2000


def test_consulta_comercial_lista_propostas_isoladas_por_tenant(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente_a = _ambiente(session_factory)
    ambiente_b = _ambiente(session_factory)
    propostas = PropostaComercialService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        SqlAlchemyAuditoriaRegistro(session_factory),
    )
    consulta = ConsultaComercialService(lambda: SqlAlchemyUnitOfWork(session_factory))
    proposta_a = propostas.criar(
        tenant_id=ambiente_a.tenant_id,
        carteira_id=ambiente_a.carteira_id,
        devedor_id=ambiente_a.devedor_id,
        usuario_id=ambiente_a.usuario_id,
        parametros={"valor": 1000},
    )
    propostas.criar(
        tenant_id=ambiente_b.tenant_id,
        carteira_id=ambiente_b.carteira_id,
        devedor_id=ambiente_b.devedor_id,
        usuario_id=ambiente_b.usuario_id,
        parametros={"valor": 3000},
    )

    resultado = consulta.listar_propostas(tenant_id=ambiente_a.tenant_id, pagina=1, tamanho=20)

    assert resultado.total == 1
    assert [p.id for p in resultado.items] == [proposta_a.proposta_id]
    with pytest.raises(PropostaComercialNaoEncontradaError):
        consulta.consultar_proposta(
            proposta_id=proposta_a.proposta_id,
            tenant_id=ambiente_b.tenant_id,
        )


def test_decisao_comercial_rejeita_usuario_de_outro_tenant(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente_a = _ambiente(session_factory)
    ambiente_b = _ambiente(session_factory)
    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    propostas = PropostaComercialService(lambda: SqlAlchemyUnitOfWork(session_factory), auditoria)
    decisoes = DecisaoComercialService(lambda: SqlAlchemyUnitOfWork(session_factory), auditoria)
    proposta = propostas.criar(
        tenant_id=ambiente_a.tenant_id,
        carteira_id=ambiente_a.carteira_id,
        devedor_id=ambiente_a.devedor_id,
        usuario_id=ambiente_a.usuario_id,
        parametros={"valor": 1000},
    )

    with pytest.raises(UsuarioNaoEncontradoError):
        decisoes.enviar_para_analise(
            proposta_id=proposta.proposta_id,
            tenant_id=ambiente_a.tenant_id,
            usuario_id=ambiente_b.usuario_id,
        )


def test_servicos_comerciais_rejeitam_devedor_inativo(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    _inativar_devedor(session_factory, ambiente.devedor_id)
    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    simulacoes = SimulacaoComercialService(lambda: SqlAlchemyUnitOfWork(session_factory), auditoria)
    propostas = PropostaComercialService(lambda: SqlAlchemyUnitOfWork(session_factory), auditoria)

    with pytest.raises(ViolacaoInvarianteError, match="Devedor inativo"):
        simulacoes.criar(
            tenant_id=ambiente.tenant_id,
            carteira_id=ambiente.carteira_id,
            devedor_id=ambiente.devedor_id,
            usuario_id=ambiente.usuario_id,
            parametros={"valor": 1000},
        )
    with pytest.raises(ViolacaoInvarianteError, match="Devedor inativo"):
        propostas.criar(
            tenant_id=ambiente.tenant_id,
            carteira_id=ambiente.carteira_id,
            devedor_id=ambiente.devedor_id,
            usuario_id=ambiente.usuario_id,
            parametros={"valor": 1000},
        )


def test_decisao_comercial_traduz_transicao_invalida_para_conflito(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    auditoria = SqlAlchemyAuditoriaRegistro(session_factory)
    propostas = PropostaComercialService(lambda: SqlAlchemyUnitOfWork(session_factory), auditoria)
    decisoes = DecisaoComercialService(lambda: SqlAlchemyUnitOfWork(session_factory), auditoria)
    proposta = propostas.criar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        devedor_id=ambiente.devedor_id,
        usuario_id=ambiente.usuario_id,
        parametros={"valor": 1000},
    )

    with pytest.raises(TransicaoEstadoInvalidaError):
        decisoes.aprovar(
            proposta_id=proposta.proposta_id,
            tenant_id=ambiente.tenant_id,
            usuario_id=ambiente.usuario_id,
        )


def test_contrato_logico_requer_proposta_aprovada(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    propostas = PropostaComercialService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        SqlAlchemyAuditoriaRegistro(session_factory),
    )
    integracao = IntegracaoPropostaAprovadaService(lambda: SqlAlchemyUnitOfWork(session_factory))
    proposta = propostas.criar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        devedor_id=ambiente.devedor_id,
        usuario_id=ambiente.usuario_id,
        parametros={"valor": 1000},
    )

    with pytest.raises(ViolacaoInvarianteError):
        integracao.gerar_contrato_logico(
            proposta_id=proposta.proposta_id,
            tenant_id=ambiente.tenant_id,
        )


def _inativar_devedor(session_factory: sessionmaker[Session], devedor_id: uuid.UUID) -> None:
    with session_factory() as session:
        repo = SqlAlchemyDevedorRepository(session)
        devedor = repo.find_by_id(devedor_id)
        assert devedor is not None
        devedor.inativar()
        repo.save(devedor)
        session.commit()


def _ambiente(session_factory: sessionmaker[Session]) -> _Ambiente:
    with session_factory() as session:
        tenant = TenantFactory.build()
        SqlAlchemyTenantRepository(session).save(tenant)
        carteira = CarteiraFactory.build(tenant_id=tenant.id)
        SqlAlchemyCarteiraRepository(session).save(carteira)
        usuario = UsuarioFactory.build(tenant_id=tenant.id)
        SqlAlchemyUsuarioRepository(session).save(usuario)
        devedor = Devedor.criar(
            carteira_id=carteira.id,
            documento=Documento.from_str("52998224725"),
            nome=f"Devedor {uuid.uuid4()}",
            contatos=(
                Contato(
                    devedor_id=uuid.uuid4(),
                    tipo=TipoContato.EMAIL,
                    valor=f"{uuid.uuid4().hex}@exemplo.com",
                    preferencial=True,
                ),
            ),
        )
        SqlAlchemyDevedorRepository(session).save(devedor)
        session.commit()
        return _Ambiente(
            tenant_id=tenant.id,
            carteira_id=carteira.id,
            devedor_id=devedor.id,
            usuario_id=usuario.id,
            uow_factory=session_factory,
        )
