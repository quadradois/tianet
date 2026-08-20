"""Testes de integracao dos repositories Motor Financeiro (IMP-156)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.contrato_credito import ContratoCredito
from emprestimo.domain.credit.contrato_liberado import ContratoLiberadoLogico
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.emprestimo import Emprestimo, EmprestimoState
from emprestimo.domain.credit.motor_financeiro import MotorFinanceiro
from emprestimo.domain.credit.ports import EmprestimoFiltros, Paginacao
from emprestimo.domain.credit.proposta_aprovada import PropostaAprovadaLogica
from emprestimo.domain.credit.proposta_comercial import PropostaComercial
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyContratoCreditoRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyEmprestimoRepository,
    SqlAlchemyEventoFinanceiroRepository,
    SqlAlchemyMemoriaCalculoRepository,
    SqlAlchemyPagamentoRepository,
    SqlAlchemyPropostaComercialRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def test_motor_financeiro_repositories_round_trip_com_trilha_completa(
    session: Session,
) -> None:
    contexto = _contexto_persistido(session)
    contrato = _contrato_liberado(contexto)
    emprestimo = Emprestimo.criar_de_contrato_liberado(contrato)
    motor = _motor()
    pagamento = motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=Decimal("1000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        chave_idempotencia="pag-001",
        usuario_id=contexto.usuario_id,
    )

    SqlAlchemyEmprestimoRepository(session).save(emprestimo)
    SqlAlchemyPagamentoRepository(session).save(pagamento.pagamento)
    memoria_repo = SqlAlchemyMemoriaCalculoRepository(session)
    memoria_repo.save(pagamento.memoria, emprestimo.id, pagamento.pagamento.id)
    SqlAlchemyEventoFinanceiroRepository(session).save(pagamento.evento)
    session.commit()

    emprestimo_carregado = SqlAlchemyEmprestimoRepository(session).find_by_id(emprestimo.id)
    pagamentos = SqlAlchemyPagamentoRepository(session).find_by_emprestimo_id(emprestimo.id)
    memorias = memoria_repo.find_by_emprestimo_id(emprestimo.id)
    eventos = SqlAlchemyEventoFinanceiroRepository(session).find_by_emprestimo_id(emprestimo.id)

    assert emprestimo_carregado is not None
    assert emprestimo_carregado.principal_original == emprestimo.principal_original
    assert emprestimo_carregado.parametros_financeiros["valor_contratado"] == "10000.00"
    assert pagamentos[0].chave_idempotencia == "pag-001"
    memorias_por_tipo = {memoria.tipo: memoria for memoria in memorias}
    assert memorias_por_tipo["pagamento"].passos[0].nome == "distribuir_juros"
    assert eventos[0].tipo == "pagamento_registrado"
    assert eventos[0].memoria_calculo_id == pagamento.memoria.id
    assert cast(Any, emprestimo_carregado.eventos[0]).tipo == "pagamento_registrado"


def test_emprestimo_repository_filtra_por_tenant_carteira_devedor_e_estado(
    session: Session,
) -> None:
    contexto_a = _contexto_persistido(session)
    contexto_b = _contexto_persistido(session)
    repo = SqlAlchemyEmprestimoRepository(session)
    emprestimo_a = Emprestimo.criar_de_contrato_liberado(_contrato_liberado(contexto_a))
    emprestimo_b = Emprestimo.criar_de_contrato_liberado(_contrato_liberado(contexto_b))
    emprestimo_b.marcar_quitado(quitado_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC))
    repo.save(emprestimo_a)
    repo.save(emprestimo_b)
    session.commit()

    resultado = repo.listar_paginado(
        EmprestimoFiltros(
            tenant_id=contexto_b.tenant_id,
            carteira_id=contexto_b.carteira_id,
            devedor_id=contexto_b.devedor_id,
            estado=EmprestimoState.QUITADO,
        ),
        Paginacao(1, 20),
    )

    assert resultado.total == 1
    assert resultado.paginas == 1
    assert [item.id for item in resultado.items] == [emprestimo_b.id]
    carregado = repo.find_by_contrato_id(contexto_b.contrato_id)
    assert carregado is not None
    assert carregado.id == emprestimo_b.id


def test_pagamento_repository_busca_por_chave_idempotencia(session: Session) -> None:
    contexto = _contexto_persistido(session)
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado(contexto))
    motor = _motor()
    resultado = motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=Decimal("1000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        chave_idempotencia="pag-idem",
        usuario_id=contexto.usuario_id,
    )
    SqlAlchemyEmprestimoRepository(session).save(emprestimo)
    repo = SqlAlchemyPagamentoRepository(session)
    repo.save(resultado.pagamento)
    session.commit()

    carregado = repo.find_by_idempotency_key(emprestimo.id, "pag-idem")

    assert carregado is not None
    assert carregado.id == resultado.pagamento.id


def test_unit_of_work_expoe_repositories_motor_e_preserva_transacao(
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    contexto = _contexto_persistido(session)
    contrato = _contrato_liberado(contexto)
    emprestimo_sem_commit = Emprestimo.criar_de_contrato_liberado(contrato)

    with (
        pytest.raises(RuntimeError, match="falha simulada"),
        SqlAlchemyUnitOfWork(session_factory) as uow,
    ):
        assert isinstance(uow.emprestimo, SqlAlchemyEmprestimoRepository)
        assert isinstance(uow.pagamento, SqlAlchemyPagamentoRepository)
        assert isinstance(uow.memoria_calculo, SqlAlchemyMemoriaCalculoRepository)
        assert isinstance(uow.evento_financeiro, SqlAlchemyEventoFinanceiroRepository)
        uow.emprestimo.save(emprestimo_sem_commit)
        raise RuntimeError("falha simulada")

    assert SqlAlchemyEmprestimoRepository(session).find_by_id(emprestimo_sem_commit.id) is None

    emprestimo_commitado = Emprestimo.criar_de_contrato_liberado(contrato)

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.emprestimo.save(emprestimo_commitado)
        uow.commit()

    carregado = SqlAlchemyEmprestimoRepository(session).find_by_id(emprestimo_commitado.id)

    # O commit atravessa; o rollback acima nao deixou rastro. E o que este teste
    # verifica — a memoria de calculo vinha da geracao de plano, que nao existe.
    assert carregado is not None


class _ContextoMotor:
    def __init__(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        proposta_id: uuid.UUID,
        contrato_id: uuid.UUID,
    ) -> None:
        self.tenant_id = tenant_id
        self.carteira_id = carteira_id
        self.devedor_id = devedor_id
        self.usuario_id = usuario_id
        self.proposta_id = proposta_id
        self.contrato_id = contrato_id


def _contexto_persistido(session: Session) -> _ContextoMotor:
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
        parametros={"valor_contratado": "10000.00", "quantidade_parcelas": 2},
    )
    proposta.enviar_para_analise(usuario_id=usuario.id)
    proposta.aprovar(usuario_id=usuario.id)
    SqlAlchemyPropostaComercialRepository(session).save(proposta)
    contrato = ContratoCredito.criar_de_proposta_aprovada(
        proposta=PropostaAprovadaLogica(
            proposta_id=proposta.id,
            tenant_id=tenant.id,
            carteira_id=carteira.id,
            devedor_id=devedor.id,
            parametros_aprovados={
                "valor_contratado": "10000.00",
                "moeda": "BRL",
                "taxa_juros_mensal": "0.0200",
                "dia_de_acerto": 10,
                "primeiro_vencimento": "2026-09-10",
                "regra_calculo": "juros_simples_periodo_real",
            },
            aprovada_por_usuario_id=usuario.id,
            aprovada_em=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
        ),
        criado_por_usuario_id=usuario.id,
    )
    contrato.formalizar(usuario_id=usuario.id)
    contrato.assinar(usuario_id=usuario.id)
    contrato.liberar_para_motor(usuario_id=usuario.id)
    SqlAlchemyContratoCreditoRepository(session).save(contrato)
    session.commit()
    return _ContextoMotor(
        tenant_id=tenant.id,
        carteira_id=carteira.id,
        devedor_id=devedor.id,
        usuario_id=usuario.id,
        proposta_id=proposta.id,
        contrato_id=contrato.id,
    )


def _contrato_liberado(contexto: _ContextoMotor) -> ContratoLiberadoLogico:
    return ContratoLiberadoLogico(
        contrato_id=contexto.contrato_id,
        proposta_comercial_id=contexto.proposta_id,
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        parametros_contratados={
            "valor_contratado": "10000.00",
            "moeda": "BRL",
            "taxa_juros_mensal": "0.0200",
            "dia_de_acerto": 10,
            "primeiro_vencimento": "2026-09-10",
            "regra_calculo": "juros_simples_periodo_real",
        },
        liberado_por_usuario_id=contexto.usuario_id,
        liberado_em=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
    )


def _motor() -> MotorFinanceiro:
    return MotorFinanceiro()
