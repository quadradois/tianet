"""Testes de integracao dos repositories Comercial (IMP-111/IMP-112)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.ports import Paginacao, PropostaComercialFiltros
from emprestimo.domain.credit.proposta_comercial import PropostaComercial
from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState
from emprestimo.domain.credit.simulacao_comercial import SimulacaoComercial
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyPropostaComercialRepository,
    SqlAlchemySimulacaoComercialRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def test_simulacao_comercial_repository_round_trip(session: Session) -> None:
    contexto = _contexto_persistido(session)
    repo = SqlAlchemySimulacaoComercialRepository(session)
    simulacao = SimulacaoComercial.criar(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        criada_por_usuario_id=contexto.usuario_id,
        parametros={"valor": 1000, "parcelas": 10},
    )

    repo.save(simulacao)
    session.commit()

    carregada = repo.find_by_id(simulacao.id)

    assert carregada is not None
    assert carregada.tenant_id == contexto.tenant_id
    assert carregada.parametros == {"valor": 1000, "parcelas": 10}
    assert [s.id for s in repo.find_by_devedor(contexto.devedor_id)] == [simulacao.id]


def test_proposta_comercial_repository_round_trip_com_decisoes(session: Session) -> None:
    contexto = _contexto_persistido(session)
    simulacao_repo = SqlAlchemySimulacaoComercialRepository(session)
    proposta_repo = SqlAlchemyPropostaComercialRepository(session)
    simulacao = SimulacaoComercial.criar(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        criada_por_usuario_id=contexto.usuario_id,
        parametros={"valor": 1000, "parcelas": 10},
    )
    simulacao_repo.save(simulacao)
    proposta = PropostaComercial.criar(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        criada_por_usuario_id=contexto.usuario_id,
        simulacao_id=simulacao.id,
        parametros={"valor": 1000, "parcelas": 10},
    )
    proposta.enviar_para_analise(usuario_id=contexto.usuario_id)
    proposta.aprovar(usuario_id=contexto.usuario_id)

    proposta_repo.save(proposta)
    session.commit()

    carregada = proposta_repo.find_by_id(proposta.id)

    assert carregada is not None
    assert carregada.simulacao_id == simulacao.id
    assert carregada.estado is PropostaComercialState.APROVADA
    assert carregada.aprovada_por_usuario_id == contexto.usuario_id
    assert [d.estado_posterior for d in carregada.decisoes] == [
        PropostaComercialState.EM_ANALISE,
        PropostaComercialState.APROVADA,
    ]
    assert len(carregada.eventos) == 2
    assert carregada.gerar_contrato_logico().proposta_id == proposta.id


def test_proposta_comercial_repository_filtra_por_tenant_estado_e_carteira(
    session: Session,
) -> None:
    contexto_a = _contexto_persistido(session)
    contexto_b = _contexto_persistido(session)
    repo = SqlAlchemyPropostaComercialRepository(session)
    proposta_a = _proposta(contexto_a)
    proposta_b = _proposta(contexto_b)
    proposta_b.enviar_para_analise(usuario_id=contexto_b.usuario_id)
    repo.save(proposta_a)
    repo.save(proposta_b)
    session.commit()

    resultado = repo.listar_paginado(
        PropostaComercialFiltros(
            tenant_id=contexto_b.tenant_id,
            carteira_id=contexto_b.carteira_id,
            estado=PropostaComercialState.EM_ANALISE,
        ),
        Paginacao(1, 20),
    )

    assert resultado.total == 1
    assert resultado.paginas == 1
    assert [p.id for p in resultado.items] == [proposta_b.id]


def test_unit_of_work_expoe_repositories_comerciais(
    session_factory: sessionmaker[Session],
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert isinstance(uow.simulacao_comercial, SqlAlchemySimulacaoComercialRepository)
        assert isinstance(uow.proposta_comercial, SqlAlchemyPropostaComercialRepository)


class _ContextoComercial:
    def __init__(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> None:
        self.tenant_id = tenant_id
        self.carteira_id = carteira_id
        self.devedor_id = devedor_id
        self.usuario_id = usuario_id


def _contexto_persistido(session: Session) -> _ContextoComercial:
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
    return _ContextoComercial(
        tenant_id=tenant.id,
        carteira_id=carteira.id,
        devedor_id=devedor.id,
        usuario_id=usuario.id,
    )


def _proposta(contexto: _ContextoComercial) -> PropostaComercial:
    return PropostaComercial.criar(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        criada_por_usuario_id=contexto.usuario_id,
        parametros={"valor": 1500, "parcelas": 12},
    )
