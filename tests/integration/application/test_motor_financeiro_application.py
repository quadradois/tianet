"""Testes de aplicacao do Motor Financeiro (IMP-158)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.comercial import DecisaoComercialService, PropostaComercialService
from emprestimo.application.contratos import (
    AssinaturaContratoService,
    FormalizacaoContratoService,
    LiberacaoContratoService,
)
from emprestimo.application.errors import (
    ContratoCreditoNaoEncontradoError,
    IdempotenciaConflitoError,
    TransicaoEstadoInvalidaError,
)
from emprestimo.application.motor_financeiro import (
    ConsultaSaldoService,
    CriacaoEmprestimoService,
    PagamentoService,
    QuitacaoRenegociacaoService,
)
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.emprestimo import EmprestimoState
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import (
    AuditoriaLogORM,
    EmprestimoORM,
    EventoFinanceiroORM,
    IdempotencyKeyORM,
    MemoriaCalculoORM,
    PagamentoORM,
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
    session_factory: sessionmaker[Session]


def test_criacao_emprestimo_persiste_operacao_chave_e_auditoria(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente)
    service = _service(session_factory)

    resultado = service.criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key="emp-integracao-1",
    )

    assert resultado.estado is EmprestimoState.ATIVO
    assert resultado.principal_original > 0
    with session_factory() as session:
        emprestimo = session.get(EmprestimoORM, resultado.emprestimo_id)
        assert emprestimo is not None
        assert emprestimo.contrato_id == contrato_id
        assert emprestimo.tenant_id == ambiente.tenant_id
        chave = session.scalar(
            select(IdempotencyKeyORM).where(IdempotencyKeyORM.chave == "emp-integracao-1")
        )
        assert chave is not None
        assert chave.estado == "finished"
        assert str(resultado.emprestimo_id) in (chave.resultado or "")
        acoes = set(session.scalars(select(AuditoriaLogORM.acao)).all())
        assert {
            "criar.inicio",
            "criar.aggregate_criado",
            "criar.evento_criado",
            "criar.sucesso",
        } <= acoes


def test_criacao_emprestimo_replay_nao_duplica_operacao(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente)
    service = _service(session_factory)

    primeiro = service.criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key="emp-replay-real",
    )
    segundo = service.criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key="emp-replay-real",
    )

    assert segundo == primeiro
    with session_factory() as session:
        total = session.scalar(
            select(func.count())
            .select_from(EmprestimoORM)
            .where(EmprestimoORM.contrato_id == contrato_id)
        )
        assert total == 1


def test_criacao_emprestimo_contrato_cross_tenant_responde_404(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente_a = _ambiente(session_factory)
    ambiente_b = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente_a)
    service = _service(session_factory)

    with pytest.raises(ContratoCreditoNaoEncontradoError):
        service.criar_de_contrato(
            contrato_id=contrato_id,
            tenant_id=ambiente_b.tenant_id,
            usuario_id=ambiente_b.usuario_id,
            idempotency_key="emp-cross-tenant",
        )

    with session_factory() as session:
        total = session.scalar(
            select(func.count())
            .select_from(EmprestimoORM)
            .where(EmprestimoORM.contrato_id == contrato_id)
        )
        assert total == 0


def test_criacao_emprestimo_duplicada_com_nova_chave_responde_409(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente)
    service = _service(session_factory)
    service.criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key="emp-original",
    )

    with pytest.raises(TransicaoEstadoInvalidaError):
        service.criar_de_contrato(
            contrato_id=contrato_id,
            tenant_id=ambiente.tenant_id,
            usuario_id=ambiente.usuario_id,
            idempotency_key="emp-duplicado",
        )

    with session_factory() as session:
        total = session.scalar(
            select(func.count())
            .select_from(EmprestimoORM)
            .where(EmprestimoORM.contrato_id == contrato_id)
        )
        assert total == 1


def test_criacao_emprestimo_chave_divergente_responde_409(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente)
    service = _service(session_factory)
    service.criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key="emp-divergente",
    )

    with pytest.raises(IdempotenciaConflitoError):
        service.criar_de_contrato(
            contrato_id=contrato_id,
            tenant_id=ambiente.tenant_id,
            usuario_id=uuid.uuid4(),
            idempotency_key="emp-divergente",
        )


def test_pagamento_registra_distribuicao_memoria_evento_e_replay(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente)
    emprestimo = _service(session_factory).criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key="emp-para-pagamento",
    )
    pagamentos = PagamentoService(lambda: SqlAlchemyUnitOfWork(session_factory))

    primeiro = pagamentos.registrar(
        emprestimo_id=emprestimo.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        valor=Decimal("1000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key="pag-integracao-1",
    )
    replay = pagamentos.registrar(
        emprestimo_id=emprestimo.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        valor=Decimal("1000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key="pag-integracao-1",
    )

    assert replay.pagamento_id == primeiro.pagamento_id
    assert replay.valor_recebido == primeiro.valor_recebido
    assert primeiro.memoria is not None
    assert primeiro.memoria.tipo == "pagamento"
    with session_factory() as session:
        total_pagamentos = session.scalar(
            select(func.count())
            .select_from(PagamentoORM)
            .where(PagamentoORM.emprestimo_id == emprestimo.emprestimo_id)
        )
        total_memorias_pagamento = session.scalar(
            select(func.count())
            .select_from(MemoriaCalculoORM)
            .where(
                MemoriaCalculoORM.emprestimo_id == emprestimo.emprestimo_id,
                MemoriaCalculoORM.tipo == "pagamento",
            )
        )
        total_eventos = session.scalar(
            select(func.count())
            .select_from(EventoFinanceiroORM)
            .where(
                EventoFinanceiroORM.emprestimo_id == emprestimo.emprestimo_id,
                EventoFinanceiroORM.tipo == "pagamento_registrado",
            )
        )
        emprestimo_row = session.get(EmprestimoORM, emprestimo.emprestimo_id)
        assert total_pagamentos == 1
        assert total_memorias_pagamento == 1
        assert total_eventos == 1
        assert emprestimo_row is not None
        assert emprestimo_row.ultimo_pagamento_em is not None


def test_pagamento_valor_invalido_nao_persiste_fatos(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente)
    emprestimo = _service(session_factory).criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key="emp-valor-invalido",
    )

    with pytest.raises(TransicaoEstadoInvalidaError):
        PagamentoService(lambda: SqlAlchemyUnitOfWork(session_factory)).registrar(
            emprestimo_id=emprestimo.emprestimo_id,
            tenant_id=ambiente.tenant_id,
            usuario_id=ambiente.usuario_id,
            valor=Decimal("0.00"),
            recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            idempotency_key="pag-zero-real",
        )

    with session_factory() as session:
        total_pagamentos = session.scalar(
            select(func.count())
            .select_from(PagamentoORM)
            .where(PagamentoORM.emprestimo_id == emprestimo.emprestimo_id)
        )
        assert total_pagamentos == 0


def test_consulta_saldo_retorna_componentes_memoria_e_nao_persiste_consulta(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente)
    emprestimo = _service(session_factory).criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key="emp-para-saldo",
    )
    PagamentoService(lambda: SqlAlchemyUnitOfWork(session_factory)).registrar(
        emprestimo_id=emprestimo.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        valor=Decimal("1000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key="pag-antes-consulta-saldo",
    )
    with session_factory() as session:
        memorias_antes = session.scalar(
            select(func.count())
            .select_from(MemoriaCalculoORM)
            .where(MemoriaCalculoORM.emprestimo_id == emprestimo.emprestimo_id)
        )

    saldo = ConsultaSaldoService(lambda: SqlAlchemyUnitOfWork(session_factory)).consultar(
        emprestimo_id=emprestimo.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        data_referencia=date(2026, 10, 10),
    )

    assert saldo.principal >= Decimal("0.00")
    assert saldo.juros >= Decimal("0.00")
    assert saldo.encargos == Decimal("0.00")
    assert saldo.total == saldo.principal + saldo.juros + saldo.encargos
    assert saldo.memoria.tipo == "saldo"
    assert saldo.memoria.entradas["data_referencia"] == "2026-10-10"
    with session_factory() as session:
        memorias_depois = session.scalar(
            select(func.count())
            .select_from(MemoriaCalculoORM)
            .where(MemoriaCalculoORM.emprestimo_id == emprestimo.emprestimo_id)
        )
        assert memorias_depois == memorias_antes


def test_quitacao_quita_emprestimo_e_preserva_memorias_eventos(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente)
    emprestimo = _service(session_factory).criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key="emp-para-quitacao",
    )
    service = QuitacaoRenegociacaoService(lambda: SqlAlchemyUnitOfWork(session_factory))

    quitado = service.quitar(
        emprestimo_id=emprestimo.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        recebido_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        idempotency_key="quit-integracao-1",
    )
    replay = service.quitar(
        emprestimo_id=emprestimo.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        recebido_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        idempotency_key="quit-integracao-1",
    )

    assert quitado.estado is EmprestimoState.QUITADO
    assert replay.pagamento.pagamento_id == quitado.pagamento.pagamento_id
    assert replay.memoria_quitacao.tipo == "quitacao"
    with session_factory() as session:
        emprestimo_row = session.get(EmprestimoORM, emprestimo.emprestimo_id)
        total_pagamentos = session.scalar(
            select(func.count())
            .select_from(PagamentoORM)
            .where(PagamentoORM.emprestimo_id == emprestimo.emprestimo_id)
        )
        tipos_memoria = set(
            session.scalars(
                select(MemoriaCalculoORM.tipo).where(
                    MemoriaCalculoORM.emprestimo_id == emprestimo.emprestimo_id
                )
            ).all()
        )
        tipos_evento = set(
            session.scalars(
                select(EventoFinanceiroORM.tipo).where(
                    EventoFinanceiroORM.emprestimo_id == emprestimo.emprestimo_id
                )
            ).all()
        )
        assert emprestimo_row is not None
        assert emprestimo_row.estado == "quitado"
        assert total_pagamentos == 1
        assert {"quitacao", "pagamento"} <= tipos_memoria
        assert {"pagamento_registrado", "emprestimo_quitado"} <= tipos_evento


def test_renegociacao_registra_memoria_evento_e_preserva_estado_ativo(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente)
    emprestimo = _service(session_factory).criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key="emp-para-renegociacao",
    )

    resultado = QuitacaoRenegociacaoService(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    ).renegociar(
        emprestimo_id=emprestimo.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        novos_parametros={"taxa_juros_mensal": "0.0150"},
        renegociado_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        idempotency_key="ren-integracao-1",
    )

    assert resultado.memoria.tipo == "renegociacao"
    assert resultado.novos_parametros["taxa_juros_mensal"] == "0.0150"
    with session_factory() as session:
        emprestimo_row = session.get(EmprestimoORM, emprestimo.emprestimo_id)
        memoria = session.scalar(
            select(MemoriaCalculoORM).where(
                MemoriaCalculoORM.emprestimo_id == emprestimo.emprestimo_id,
                MemoriaCalculoORM.tipo == "renegociacao",
            )
        )
        evento = session.scalar(
            select(EventoFinanceiroORM).where(
                EventoFinanceiroORM.emprestimo_id == emprestimo.emprestimo_id,
                EventoFinanceiroORM.tipo == "emprestimo_renegociado",
            )
        )
        assert emprestimo_row is not None
        assert emprestimo_row.estado == "ativo"
        assert memoria is not None
        assert evento is not None


def _service(session_factory: sessionmaker[Session]) -> CriacaoEmprestimoService:
    return CriacaoEmprestimoService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        SqlAlchemyAuditoriaRegistro(session_factory),
    )


def _contrato_liberado(
    session_factory: sessionmaker[Session],
    ambiente: _Ambiente,
) -> uuid.UUID:
    proposta = PropostaComercialService(lambda: SqlAlchemyUnitOfWork(session_factory)).criar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        devedor_id=ambiente.devedor_id,
        usuario_id=ambiente.usuario_id,
        parametros={
            "valor_contratado": "10000.00",
            "prazo_meses": 10,
            "quantidade_parcelas": 2,
            "primeiro_vencimento": "2026-09-10",
            "taxa_juros_mensal": "0.0200",
        },
    )
    decisoes = DecisaoComercialService(lambda: SqlAlchemyUnitOfWork(session_factory))
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
    contrato = FormalizacaoContratoService(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    ).criar_de_proposta(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        proposta_comercial_id=proposta.proposta_id,
        usuario_id=ambiente.usuario_id,
    )
    assinatura = AssinaturaContratoService(lambda: SqlAlchemyUnitOfWork(session_factory))
    assinatura.formalizar(
        contrato_id=contrato.contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
    )
    assinatura.assinar(
        contrato_id=contrato.contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
    )
    LiberacaoContratoService(lambda: SqlAlchemyUnitOfWork(session_factory)).liberar_para_motor(
        contrato_id=contrato.contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
    )
    return contrato.contrato_id


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
            session_factory=session_factory,
        )
