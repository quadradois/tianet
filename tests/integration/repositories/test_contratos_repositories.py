"""Testes de integracao dos repositories Contratos (IMP-131/IMP-132)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.contrato_credito import ContratoCredito
from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.ports import ContratoCreditoFiltros, Paginacao
from emprestimo.domain.credit.proposta_aprovada import PropostaAprovadaLogica
from emprestimo.domain.credit.proposta_comercial import PropostaComercial
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyContratoCreditoRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyPropostaComercialRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def test_contrato_credito_repository_round_trip_com_eventos(session: Session) -> None:
    contexto = _contexto_persistido(session)
    repo = SqlAlchemyContratoCreditoRepository(session)
    contrato = _contrato(contexto)
    contrato.formalizar(usuario_id=contexto.usuario_id)
    contrato.assinar(usuario_id=contexto.usuario_id)
    contrato.liberar_para_motor(usuario_id=contexto.usuario_id)

    repo.save(contrato)
    session.commit()

    carregado = repo.find_by_id(contrato.id)

    assert carregado is not None
    assert carregado.estado is ContratoCreditoState.LIBERADO_PARA_MOTOR
    assert carregado.proposta_comercial_id == contexto.proposta_id
    assert [d.tipo for d in carregado.decisoes] == [
        "criado",
        "formalizado",
        "assinado",
        "liberado_para_motor",
    ]
    assert [d.estado_posterior for d in carregado.decisoes] == [
        ContratoCreditoState.RASCUNHO,
        ContratoCreditoState.FORMALIZADO,
        ContratoCreditoState.ASSINADO,
        ContratoCreditoState.LIBERADO_PARA_MOTOR,
    ]
    assert carregado.gerar_saida_logica().contrato_id == contrato.id


def test_contrato_credito_repository_filtra_por_tenant_estado_e_carteira(
    session: Session,
) -> None:
    contexto_a = _contexto_persistido(session)
    contexto_b = _contexto_persistido(session)
    repo = SqlAlchemyContratoCreditoRepository(session)
    contrato_a = _contrato(contexto_a)
    contrato_b = _contrato(contexto_b)
    contrato_b.formalizar(usuario_id=contexto_b.usuario_id)
    repo.save(contrato_a)
    repo.save(contrato_b)
    session.commit()

    resultado = repo.listar_paginado(
        ContratoCreditoFiltros(
            tenant_id=contexto_b.tenant_id,
            carteira_id=contexto_b.carteira_id,
            estado=ContratoCreditoState.FORMALIZADO,
        ),
        Paginacao(1, 20),
    )

    assert resultado.total == 1
    assert resultado.paginas == 1
    assert [c.id for c in resultado.items] == [contrato_b.id]


def test_contrato_credito_repository_busca_por_proposta(session: Session) -> None:
    contexto = _contexto_persistido(session)
    repo = SqlAlchemyContratoCreditoRepository(session)
    contrato = _contrato(contexto)
    repo.save(contrato)
    session.commit()

    carregado = repo.find_by_proposta_id(contexto.proposta_id)

    assert carregado is not None
    assert carregado.id == contrato.id


def test_unit_of_work_expoe_repository_contratos(
    session_factory: sessionmaker[Session],
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert isinstance(uow.contrato_credito, SqlAlchemyContratoCreditoRepository)


class _ContextoContratos:
    def __init__(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        proposta_id: uuid.UUID,
    ) -> None:
        self.tenant_id = tenant_id
        self.carteira_id = carteira_id
        self.devedor_id = devedor_id
        self.usuario_id = usuario_id
        self.proposta_id = proposta_id


def _contexto_persistido(session: Session) -> _ContextoContratos:
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
    proposta = PropostaComercial.criar(
        tenant_id=tenant.id,
        carteira_id=carteira.id,
        devedor_id=devedor.id,
        criada_por_usuario_id=usuario.id,
        parametros={"valor_contratado": "1000.00", "prazo_meses": 10},
    )
    proposta.enviar_para_analise(usuario_id=usuario.id)
    proposta.aprovar(usuario_id=usuario.id)
    SqlAlchemyPropostaComercialRepository(session).save(proposta)
    session.commit()
    return _ContextoContratos(
        tenant_id=tenant.id,
        carteira_id=carteira.id,
        devedor_id=devedor.id,
        usuario_id=usuario.id,
        proposta_id=proposta.id,
    )


def _contrato(contexto: _ContextoContratos) -> ContratoCredito:
    proposta = PropostaAprovadaLogica(
        proposta_id=contexto.proposta_id,
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        parametros_aprovados={"valor_contratado": "1000.00", "prazo_meses": 10},
        aprovada_por_usuario_id=contexto.usuario_id,
        aprovada_em=datetime.now(UTC),
    )
    return ContratoCredito.criar_de_proposta_aprovada(
        proposta=proposta,
        criado_por_usuario_id=contexto.usuario_id,
    )
