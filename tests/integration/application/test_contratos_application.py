"""Testes de aplicacao de Contratos (IMP-133..IMP-137)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.comercial import DecisaoComercialService, PropostaComercialService
from emprestimo.application.contratos import (
    AssinaturaContratoService,
    CancelamentoEncerramentoContratoService,
    ConsultaContratoService,
    FormalizacaoContratoService,
    LiberacaoContratoService,
)
from emprestimo.application.errors import (
    ContratoCreditoNaoEncontradoError,
    TransicaoEstadoInvalidaError,
)
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
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


def test_fluxo_contratos_cria_assina_libera_e_gera_saida_logica(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    proposta_id = _proposta_aprovada(session_factory, ambiente)
    formalizacao = FormalizacaoContratoService(lambda: SqlAlchemyUnitOfWork(session_factory))
    assinatura = AssinaturaContratoService(lambda: SqlAlchemyUnitOfWork(session_factory))
    liberacao = LiberacaoContratoService(lambda: SqlAlchemyUnitOfWork(session_factory))

    contrato = formalizacao.criar_de_proposta(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        proposta_comercial_id=proposta_id,
        usuario_id=ambiente.usuario_id,
    )
    formalizado = assinatura.formalizar(
        contrato_id=contrato.contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
    )
    assinado = assinatura.assinar(
        contrato_id=contrato.contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
    )
    saida = liberacao.liberar_para_motor(
        contrato_id=contrato.contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
    )

    assert contrato.estado is ContratoCreditoState.RASCUNHO
    assert formalizado.estado is ContratoCreditoState.FORMALIZADO
    assert assinado.estado is ContratoCreditoState.ASSINADO
    assert saida.contrato_id == contrato.contrato_id
    assert saida.parametros_contratados["valor"] == 1000


def test_consulta_contratos_lista_isolada_por_tenant(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente_a = _ambiente(session_factory)
    ambiente_b = _ambiente(session_factory)
    contrato_a = _contrato_criado(session_factory, ambiente_a)
    _contrato_criado(session_factory, ambiente_b)
    consulta = ConsultaContratoService(lambda: SqlAlchemyUnitOfWork(session_factory))

    resultado = consulta.listar_contratos(tenant_id=ambiente_a.tenant_id, pagina=1, tamanho=20)

    assert resultado.total == 1
    assert [c.id for c in resultado.items] == [contrato_a]
    with pytest.raises(ContratoCreditoNaoEncontradoError):
        consulta.consultar_contrato(contrato_id=contrato_a, tenant_id=ambiente_b.tenant_id)


def test_contrato_rejeita_proposta_nao_aprovada(session_factory: sessionmaker[Session]) -> None:
    ambiente = _ambiente(session_factory)
    proposta_id = (
        PropostaComercialService(lambda: SqlAlchemyUnitOfWork(session_factory))
        .criar(
            tenant_id=ambiente.tenant_id,
            carteira_id=ambiente.carteira_id,
            devedor_id=ambiente.devedor_id,
            usuario_id=ambiente.usuario_id,
            parametros={"valor": 1000},
        )
        .proposta_id
    )
    formalizacao = FormalizacaoContratoService(lambda: SqlAlchemyUnitOfWork(session_factory))

    with pytest.raises(TransicaoEstadoInvalidaError):
        formalizacao.criar_de_proposta(
            tenant_id=ambiente.tenant_id,
            carteira_id=ambiente.carteira_id,
            proposta_comercial_id=proposta_id,
            usuario_id=ambiente.usuario_id,
        )


def test_contrato_rejeita_devedor_inativo(session_factory: sessionmaker[Session]) -> None:
    ambiente = _ambiente(session_factory)
    proposta_id = _proposta_aprovada(session_factory, ambiente)
    _inativar_devedor(session_factory, ambiente.devedor_id)
    formalizacao = FormalizacaoContratoService(lambda: SqlAlchemyUnitOfWork(session_factory))

    with pytest.raises(ViolacaoInvarianteError, match="Devedor inativo"):
        formalizacao.criar_de_proposta(
            tenant_id=ambiente.tenant_id,
            carteira_id=ambiente.carteira_id,
            proposta_comercial_id=proposta_id,
            usuario_id=ambiente.usuario_id,
        )


def test_contrato_rejeita_liberacao_sem_assinatura(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_criado(session_factory, ambiente)
    liberacao = LiberacaoContratoService(lambda: SqlAlchemyUnitOfWork(session_factory))

    with pytest.raises(TransicaoEstadoInvalidaError):
        liberacao.liberar_para_motor(
            contrato_id=contrato_id,
            tenant_id=ambiente.tenant_id,
            usuario_id=ambiente.usuario_id,
        )


def test_cancelar_contrato_nao_liberado(session_factory: sessionmaker[Session]) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_criado(session_factory, ambiente)
    cancelamento = CancelamentoEncerramentoContratoService(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    )

    contrato = cancelamento.cancelar(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        motivo="cliente desistiu",
    )

    assert contrato.estado is ContratoCreditoState.CANCELADO


def _proposta_aprovada(session_factory: sessionmaker[Session], ambiente: _Ambiente) -> uuid.UUID:
    propostas = PropostaComercialService(lambda: SqlAlchemyUnitOfWork(session_factory))
    decisoes = DecisaoComercialService(lambda: SqlAlchemyUnitOfWork(session_factory))
    proposta = propostas.criar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        devedor_id=ambiente.devedor_id,
        usuario_id=ambiente.usuario_id,
        parametros={"valor": 1000, "prazo_meses": 10},
    )
    decisoes.enviar_para_analise(
        proposta_id=proposta.proposta_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
    )
    decisoes.aprovar(
        proposta_id=proposta.proposta_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
    )
    return proposta.proposta_id


def _contrato_criado(session_factory: sessionmaker[Session], ambiente: _Ambiente) -> uuid.UUID:
    proposta_id = _proposta_aprovada(session_factory, ambiente)
    formalizacao = FormalizacaoContratoService(lambda: SqlAlchemyUnitOfWork(session_factory))
    return formalizacao.criar_de_proposta(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        proposta_comercial_id=proposta_id,
        usuario_id=ambiente.usuario_id,
    ).contrato_id


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
        )
