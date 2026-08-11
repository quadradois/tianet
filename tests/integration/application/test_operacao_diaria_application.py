"""Testes de aplicacao da Operacao Diaria (IMP-177..IMP-178)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
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
from emprestimo.application.errors import CobrancaCasoNaoEncontradoError
from emprestimo.application.motor_financeiro import (
    CriacaoEmprestimoService,
    PagamentoResultado,
    PagamentoService,
    PlanoParcelasService,
)
from emprestimo.application.operacao_diaria import (
    ApropriarPagamentoPromessa,
    ConsultarAgendaOperacional,
    ConsultarFilaCobranca,
    ConsultarHistoricoComunicacao,
    CriarCompromissoAgenda,
    CriarLembreteAgenda,
    ManterCompromissoAgenda,
    ManterLembreteAgenda,
    RegistrarAcaoCobranca,
    RegistrarComunicacaoManual,
    RegistrarPromessa,
)
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.operacao_diaria import (
    CanalComunicacao,
    CobrancaCaso,
    EstadoCobranca,
    EstadoCompromisso,
    EstadoLembrete,
    TipoAcaoCobranca,
)
from emprestimo.domain.credit.promessa import PromessaPagamentoState
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import (
    AcaoCobrancaORM,
    AgendaItemORM,
    ApropriacaoPagamentoORM,
    IdempotencyKeyORM,
    LembreteORM,
    PromessaPagamentoORM,
    RegistroComunicacaoORM,
)
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.repositories.operacao_diaria import (
    SqlAlchemyCobrancaCasoRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@dataclass(frozen=True)
class _Ambiente:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    usuario_id: uuid.UUID


@dataclass(frozen=True)
class _ContextoMotor:
    ambiente: _Ambiente
    emprestimo_id: uuid.UUID
    parcela_id: uuid.UUID
    pagamento: PagamentoResultado


def test_cobranca_manual_registra_acao_promessa_apropriacao_e_replay(
    session_factory: sessionmaker[Session],
) -> None:
    contexto = _contexto_motor(session_factory)
    caso_id = _caso_cobranca(session_factory, contexto)

    fila = ConsultarFilaCobranca(lambda: SqlAlchemyUnitOfWork(session_factory)).listar(
        tenant_id=contexto.ambiente.tenant_id,
        carteira_id=contexto.ambiente.carteira_id,
    )
    assert [item.caso_id for item in fila.items] == [caso_id]

    acoes = RegistrarAcaoCobranca(lambda: SqlAlchemyUnitOfWork(session_factory))
    acao = acoes.registrar(
        tenant_id=contexto.ambiente.tenant_id,
        cobranca_caso_id=caso_id,
        usuario_id=contexto.ambiente.usuario_id,
        tipo=TipoAcaoCobranca.TELEFONE,
        resultado="cliente prometeu pagar",
        idempotency_key="od-acao-1",
        parcela_id=contexto.parcela_id,
    )
    replay_acao = acoes.registrar(
        tenant_id=contexto.ambiente.tenant_id,
        cobranca_caso_id=caso_id,
        usuario_id=contexto.ambiente.usuario_id,
        tipo=TipoAcaoCobranca.TELEFONE,
        resultado="cliente prometeu pagar",
        idempotency_key="od-acao-1",
        parcela_id=contexto.parcela_id,
    )

    promessas = RegistrarPromessa(lambda: SqlAlchemyUnitOfWork(session_factory))
    promessa = promessas.registrar(
        tenant_id=contexto.ambiente.tenant_id,
        cobranca_caso_id=caso_id,
        usuario_id=contexto.ambiente.usuario_id,
        valor_declarado=Decimal("100.00"),
        data_promessa=date(2026, 9, 10),
        idempotency_key="od-promessa-1",
        parcela_id=contexto.parcela_id,
        pagamento_informado=True,
    )
    apropriacao = ApropriarPagamentoPromessa(
        lambda: SqlAlchemyUnitOfWork(session_factory)
    ).apropriar(
        tenant_id=contexto.ambiente.tenant_id,
        promessa_id=promessa.promessa_id,
        pagamento_id=contexto.pagamento.pagamento_id,
        usuario_id=contexto.ambiente.usuario_id,
        idempotency_key="od-apropriacao-1",
    )

    assert replay_acao == acao
    assert promessa.estado is PromessaPagamentoState.PAGAMENTO_INFORMADO
    assert apropriacao.estado_promessa is PromessaPagamentoState.CUMPRIDA
    assert apropriacao.valor == contexto.pagamento.valor_recebido
    with session_factory() as session:
        total_acoes = session.scalar(select(func.count()).select_from(AcaoCobrancaORM))
        total_promessas = session.scalar(select(func.count()).select_from(PromessaPagamentoORM))
        total_apropriacoes = session.scalar(
            select(func.count()).select_from(ApropriacaoPagamentoORM)
        )
        total_chaves = session.scalar(
            select(func.count())
            .select_from(IdempotencyKeyORM)
            .where(IdempotencyKeyORM.chave.in_(["od-acao-1", "od-promessa-1", "od-apropriacao-1"]))
        )
        assert total_acoes == 1
        assert total_promessas == 1
        assert total_apropriacoes == 1
        assert total_chaves == 3


def test_agenda_operacional_cria_lembrete_consulta_e_transiciona(
    session_factory: sessionmaker[Session],
) -> None:
    contexto = _contexto_motor(session_factory)
    previsto_para = datetime.now(UTC) + timedelta(days=2)
    compromissos = CriarCompromissoAgenda(lambda: SqlAlchemyUnitOfWork(session_factory))
    lembretes = CriarLembreteAgenda(lambda: SqlAlchemyUnitOfWork(session_factory))
    manter_compromisso = ManterCompromissoAgenda(lambda: SqlAlchemyUnitOfWork(session_factory))
    manter_lembrete = ManterLembreteAgenda(lambda: SqlAlchemyUnitOfWork(session_factory))

    compromisso = compromissos.criar(
        tenant_id=contexto.ambiente.tenant_id,
        carteira_id=contexto.ambiente.carteira_id,
        devedor_id=contexto.ambiente.devedor_id,
        usuario_id=contexto.ambiente.usuario_id,
        titulo="Retornar cliente",
        previsto_para=previsto_para,
        idempotency_key="od-agenda-1",
        emprestimo_id=contexto.emprestimo_id,
    )
    replay_compromisso = compromissos.criar(
        tenant_id=contexto.ambiente.tenant_id,
        carteira_id=contexto.ambiente.carteira_id,
        devedor_id=contexto.ambiente.devedor_id,
        usuario_id=contexto.ambiente.usuario_id,
        titulo="Retornar cliente",
        previsto_para=previsto_para,
        idempotency_key="od-agenda-1",
        emprestimo_id=contexto.emprestimo_id,
    )
    lembrete = lembretes.criar(
        tenant_id=contexto.ambiente.tenant_id,
        agenda_item_id=compromisso.agenda_item_id,
        usuario_id=contexto.ambiente.usuario_id,
        horario=previsto_para - timedelta(hours=1),
        mensagem="Confirmar retorno",
        idempotency_key="od-lembrete-1",
    )
    agenda = ConsultarAgendaOperacional(lambda: SqlAlchemyUnitOfWork(session_factory)).listar(
        tenant_id=contexto.ambiente.tenant_id,
        carteira_id=contexto.ambiente.carteira_id,
        janela_inicio=previsto_para - timedelta(days=1),
        janela_fim=previsto_para + timedelta(days=1),
    )
    reagendado = manter_compromisso.reagendar(
        tenant_id=contexto.ambiente.tenant_id,
        agenda_item_id=compromisso.agenda_item_id,
        usuario_id=contexto.ambiente.usuario_id,
        novo_horario=previsto_para + timedelta(days=1),
        idempotency_key="od-agenda-reagendar-1",
    )
    concluido = manter_compromisso.concluir(
        tenant_id=contexto.ambiente.tenant_id,
        agenda_item_id=compromisso.agenda_item_id,
        usuario_id=contexto.ambiente.usuario_id,
        idempotency_key="od-agenda-concluir-1",
    )
    lembrete_enviado = manter_lembrete.enviar(
        tenant_id=contexto.ambiente.tenant_id,
        lembrete_id=lembrete.lembrete_id,
        usuario_id=contexto.ambiente.usuario_id,
        idempotency_key="od-lembrete-enviar-1",
    )
    replay_pos_transicao = compromissos.criar(
        tenant_id=contexto.ambiente.tenant_id,
        carteira_id=contexto.ambiente.carteira_id,
        devedor_id=contexto.ambiente.devedor_id,
        usuario_id=contexto.ambiente.usuario_id,
        titulo="Retornar cliente",
        previsto_para=previsto_para,
        idempotency_key="od-agenda-1",
        emprestimo_id=contexto.emprestimo_id,
    )

    assert replay_compromisso == compromisso
    assert replay_pos_transicao == compromisso
    assert replay_pos_transicao.estado is EstadoCompromisso.ABERTO
    assert [item.agenda_item_id for item in agenda.compromissos] == [compromisso.agenda_item_id]
    assert [item.lembrete_id for item in agenda.lembretes] == [lembrete.lembrete_id]
    assert reagendado.estado is EstadoCompromisso.REAGENDADO
    assert concluido.estado is EstadoCompromisso.CONCLUIDO
    assert lembrete_enviado.estado is EstadoLembrete.ENVIADO
    with session_factory() as session:
        total_agenda = session.scalar(select(func.count()).select_from(AgendaItemORM))
        total_lembretes = session.scalar(select(func.count()).select_from(LembreteORM))
        total_chaves = session.scalar(
            select(func.count())
            .select_from(IdempotencyKeyORM)
            .where(
                IdempotencyKeyORM.chave.in_(
                    [
                        "od-agenda-1",
                        "od-lembrete-1",
                        "od-agenda-reagendar-1",
                        "od-agenda-concluir-1",
                        "od-lembrete-enviar-1",
                    ]
                )
            )
        )
        assert total_agenda == 1
        assert total_lembretes == 1
        assert total_chaves == 5


def test_comunicacao_manual_registra_replay_e_consulta_historico(
    session_factory: sessionmaker[Session],
) -> None:
    contexto = _contexto_motor(session_factory)
    comunicacoes = RegistrarComunicacaoManual(lambda: SqlAlchemyUnitOfWork(session_factory))
    ocorrido_em = datetime(2026, 9, 10, 13, 0, tzinfo=UTC)

    registro = comunicacoes.registrar(
        tenant_id=contexto.ambiente.tenant_id,
        carteira_id=contexto.ambiente.carteira_id,
        devedor_id=contexto.ambiente.devedor_id,
        usuario_id=contexto.ambiente.usuario_id,
        canal=CanalComunicacao.TELEFONE,
        ocorrido_em=ocorrido_em,
        resumo="Ligacao de cobranca",
        resultado="Cliente pediu segunda via",
        idempotency_key="od-comunicacao-1",
        emprestimo_id=contexto.emprestimo_id,
        parcela_id=contexto.parcela_id,
    )
    replay = comunicacoes.registrar(
        tenant_id=contexto.ambiente.tenant_id,
        carteira_id=contexto.ambiente.carteira_id,
        devedor_id=contexto.ambiente.devedor_id,
        usuario_id=contexto.ambiente.usuario_id,
        canal=CanalComunicacao.TELEFONE,
        ocorrido_em=ocorrido_em,
        resumo="Ligacao de cobranca",
        resultado="Cliente pediu segunda via",
        idempotency_key="od-comunicacao-1",
        emprestimo_id=contexto.emprestimo_id,
        parcela_id=contexto.parcela_id,
    )
    historico = ConsultarHistoricoComunicacao(lambda: SqlAlchemyUnitOfWork(session_factory)).listar(
        tenant_id=contexto.ambiente.tenant_id,
        carteira_id=contexto.ambiente.carteira_id,
        devedor_id=contexto.ambiente.devedor_id,
        emprestimo_id=contexto.emprestimo_id,
    )

    assert replay == registro
    assert historico.total == 1
    assert historico.registros[0].registro_id == registro.registro_id
    with session_factory() as session:
        total_registros = session.scalar(select(func.count()).select_from(RegistroComunicacaoORM))
        chave = session.scalar(
            select(IdempotencyKeyORM).where(IdempotencyKeyORM.chave == "od-comunicacao-1")
        )
        assert total_registros == 1
        assert chave is not None
        assert chave.estado == "finished"


def test_registrar_acao_cobranca_cross_tenant_preserva_404_logico(
    session_factory: sessionmaker[Session],
) -> None:
    contexto_a = _contexto_motor(session_factory)
    contexto_b = _contexto_motor(session_factory)
    caso_id = _caso_cobranca(session_factory, contexto_a)

    with pytest.raises(CobrancaCasoNaoEncontradoError):
        RegistrarAcaoCobranca(lambda: SqlAlchemyUnitOfWork(session_factory)).registrar(
            tenant_id=contexto_b.ambiente.tenant_id,
            cobranca_caso_id=caso_id,
            usuario_id=contexto_b.ambiente.usuario_id,
            tipo=TipoAcaoCobranca.EMAIL,
            resultado="tentativa cross tenant",
            idempotency_key="od-cross-tenant",
        )

    with session_factory() as session:
        total_acoes = session.scalar(
            select(func.count())
            .select_from(AcaoCobrancaORM)
            .where(AcaoCobrancaORM.cobranca_caso_id == caso_id)
        )
        assert total_acoes == 0


def _contexto_motor(session_factory: sessionmaker[Session]) -> _ContextoMotor:
    ambiente = _ambiente(session_factory)
    contrato_id = _contrato_liberado(session_factory, ambiente)
    emprestimo = CriacaoEmprestimoService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        SqlAlchemyAuditoriaRegistro(session_factory),
    ).criar_de_contrato(
        contrato_id=contrato_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        idempotency_key=f"od-emp-{uuid.uuid4()}",
    )
    plano = PlanoParcelasService(lambda: SqlAlchemyUnitOfWork(session_factory)).gerar(
        emprestimo_id=emprestimo.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        data_referencia=date(2026, 8, 10),
    )
    pagamento = PagamentoService(lambda: SqlAlchemyUnitOfWork(session_factory)).registrar(
        emprestimo_id=emprestimo.emprestimo_id,
        tenant_id=ambiente.tenant_id,
        usuario_id=ambiente.usuario_id,
        valor=plano.parcelas[0].valor_previsto,
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key=f"od-pag-{uuid.uuid4()}",
    )
    return _ContextoMotor(
        ambiente=ambiente,
        emprestimo_id=emprestimo.emprestimo_id,
        parcela_id=plano.parcelas[0].parcela_id,
        pagamento=pagamento,
    )


def _caso_cobranca(
    session_factory: sessionmaker[Session],
    contexto: _ContextoMotor,
) -> uuid.UUID:
    with session_factory() as session:
        caso = CobrancaCaso(
            tenant_id=contexto.ambiente.tenant_id,
            carteira_id=contexto.ambiente.carteira_id,
            devedor_id=contexto.ambiente.devedor_id,
            emprestimo_id=contexto.emprestimo_id,
            titulo="Cobranca de parcela",
            origem="teste_integracao",
            estado=EstadoCobranca.PENDENTE,
        )
        SqlAlchemyCobrancaCasoRepository(session).save(caso)
        session.commit()
        return caso.id


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
        )
