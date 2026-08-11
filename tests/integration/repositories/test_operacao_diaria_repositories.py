"""Testes de integracao dos repositories da Operacao Diaria (EPIC-007/P2)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.contrato_credito import ContratoCredito
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.emprestimo import Emprestimo
from emprestimo.domain.credit.motor_financeiro import MotorFinanceiro
from emprestimo.domain.credit.operacao_diaria import (
    AcaoCobranca,
    AgendaItem,
    CanalComunicacao,
    CobrancaCaso,
    EstadoCobranca,
    EstadoCompromisso,
    EstadoLembrete,
    EstadoOperacional,
    Lembrete,
    RegistroComunicacao,
    RelatorioOperacionalCache,
    TipoAcaoCobranca,
)
from emprestimo.domain.credit.ports import (
    AcaoCobrancaFiltros,
    AgendaItemFiltros,
    ApropriacaoPagamentoFiltros,
    CobrancaCasoFiltros,
    RegistroComunicacaoFiltros,
    RelatorioOperacionalCacheFiltros,
)
from emprestimo.domain.credit.promessa import ApropriacaoPagamento, PromessaPagamento
from emprestimo.domain.credit.proposta_aprovada import PropostaAprovadaLogica
from emprestimo.domain.credit.proposta_comercial import PropostaComercial
from emprestimo.infrastructure.repositories import (
    SqlAlchemyAcaoCobrancaRepository,
    SqlAlchemyAgendaItemRepository,
    SqlAlchemyApropriacaoPagamentoRepository,
    SqlAlchemyCarteiraRepository,
    SqlAlchemyCobrancaCasoRepository,
    SqlAlchemyContratoCreditoRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyEmprestimoRepository,
    SqlAlchemyLembreteRepository,
    SqlAlchemyPagamentoRepository,
    SqlAlchemyParcelaRepository,
    SqlAlchemyPromessaPagamentoRepository,
    SqlAlchemyPropostaComercialRepository,
    SqlAlchemyRegistroComunicacaoRepository,
    SqlAlchemyRelatorioOperacionalCacheRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def test_repositories_de_operacao_diaria_expoem_roundtrip(session: Session) -> None:
    contexto = _contexto_operacao(session)
    caso_repo = SqlAlchemyCobrancaCasoRepository(session)
    acao_repo = SqlAlchemyAcaoCobrancaRepository(session)
    promessa_repo = SqlAlchemyPromessaPagamentoRepository(session)
    item_repo = SqlAlchemyAgendaItemRepository(session)

    caso = CobrancaCaso(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        titulo="Cobranca de atrasos",
        origem="teste_integracao",
        estado=EstadoCobranca.PENDENTE,
    )
    caso_repo.save(caso)

    acao = AcaoCobranca(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        cobranca_caso_id=caso.id,
        emprestimo_id=contexto.emprestimo_id,
        criado_por_usuario_id=contexto.usuario_id,
        tipo=TipoAcaoCobranca.TELEFONE,
        resultado="ligacao inicial",
        estado=EstadoOperacional.ATIVO,
        devedor_id=contexto.devedor_id,
    )
    acao_repo.save(acao)

    promessa = PromessaPagamento.criar(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        emprestimo_id=contexto.emprestimo_id,
        valor_declarado=Decimal("100.00"),
        data_promessa=date(2026, 9, 10),
        criado_por_usuario_id=contexto.usuario_id,
        parcela_id=contexto.parcela_id,
    )
    promessa_repo.save(promessa)

    item = AgendaItem(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        emprestimo_id=contexto.emprestimo_id,
        titulo="Ligar cliente",
        previsto_para=datetime.now(UTC) + timedelta(hours=1),
        usuario_solicitante_id=contexto.usuario_id,
        estado=EstadoCompromisso.ABERTO,
    )
    item_repo.save(item)
    session.commit()

    assert caso_repo.find_by_id(caso.id) == caso
    assert acao_repo.find_by_id(acao.id) is not None
    assert promessa_repo.find_by_id(promessa.id) is not None
    assert item_repo.find_by_id(item.id) is not None

    encontrados = acao_repo.listar(AcaoCobrancaFiltros(tenant_id=contexto.tenant_id))
    assert len(encontrados) == 1


def test_repositories_filtram_e_convertem_tipos(session: Session) -> None:
    contexto = _contexto_operacao(session)
    repo_caso = SqlAlchemyCobrancaCasoRepository(session)
    repo_acao = SqlAlchemyAcaoCobrancaRepository(session)
    repo_item = SqlAlchemyAgendaItemRepository(session)
    repo_lembrete = SqlAlchemyLembreteRepository(session)
    repo_registro = SqlAlchemyRegistroComunicacaoRepository(session)
    repo_relatorio = SqlAlchemyRelatorioOperacionalCacheRepository(session)

    caso = CobrancaCaso(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        titulo="Cobranca por e-mail",
        origem="filtro",
        estado=EstadoCobranca.EM_ANDAMENTO,
    )
    repo_caso.save(caso)

    item = AgendaItem(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        emprestimo_id=contexto.emprestimo_id,
        titulo="Ligar cliente",
        previsto_para=datetime.now(UTC) + timedelta(hours=1),
        usuario_solicitante_id=contexto.usuario_id,
        estado=EstadoCompromisso.ABERTO,
    )
    repo_item.save(item)

    acao = AcaoCobranca(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        cobranca_caso_id=caso.id,
        emprestimo_id=contexto.emprestimo_id,
        criado_por_usuario_id=contexto.usuario_id,
        tipo=TipoAcaoCobranca.EMAIL,
        resultado="sem retorno",
        devedor_id=contexto.devedor_id,
    )
    repo_acao.save(acao)

    lembrete = Lembrete(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        agenda_item_id=item.id,
        horario=datetime.now(UTC) + timedelta(hours=2),
        enviado_por_usuario_id=contexto.usuario_id,
        mensagem="Confirmar proposta",
        estado=EstadoLembrete.PROGRAMA,
    )
    repo_lembrete.save(lembrete)

    registro = RegistroComunicacao(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        responsavel_id=contexto.usuario_id,
        canal=CanalComunicacao.EMAIL,
        ocorrido_em=datetime.now(UTC),
        resumo="ligacao de retorno",
        resultado="nada",
        devedor_id=contexto.devedor_id,
        emprestimo_id=contexto.emprestimo_id,
        agenda_item_id=item.id,
    )
    repo_registro.save(registro)

    relatorio = RelatorioOperacionalCache(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        janela_referencia=date(2026, 9, 1),
        familia_relatorio="operacao_diaria",
        payload_json={"total": 10},
    )
    repo_relatorio.save(relatorio)
    session.commit()

    encontrados = repo_caso.listar(
        CobrancaCasoFiltros(
            tenant_id=contexto.tenant_id,
            estado=EstadoCobranca.EM_ANDAMENTO,
        )
    )
    assert len(encontrados) == 1

    encontrados_acoes = repo_acao.listar(AcaoCobrancaFiltros(tenant_id=contexto.tenant_id))
    assert len(encontrados_acoes) == 1
    assert encontrados_acoes[0].tipo.value == "email"

    encontrados_itens = repo_item.listar(
        AgendaItemFiltros(tenant_id=contexto.tenant_id, estado=EstadoCompromisso.ABERTO)
    )
    assert len(encontrados_itens) == 1

    assert repo_lembrete.find_by_agenda_item_id(item.id)[0].estado is EstadoLembrete.PROGRAMA

    registros = repo_registro.listar(RegistroComunicacaoFiltros(tenant_id=contexto.tenant_id))
    assert registros[0] == registro

    filtrados_relatorio = repo_relatorio.listar(
        RelatorioOperacionalCacheFiltros(
            tenant_id=contexto.tenant_id,
            carteira_id=contexto.carteira_id,
            familia_relatorio="operacao_diaria",
        )
    )
    assert filtrados_relatorio[0].familia_relatorio == "operacao_diaria"


def test_apropriacao_pagamento_roundtrip(session: Session) -> None:
    contexto = _contexto_operacao(session)
    promessa_repo = SqlAlchemyPromessaPagamentoRepository(session)
    aprop_repo = SqlAlchemyApropriacaoPagamentoRepository(session)

    promessa = PromessaPagamento.criar(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        devedor_id=contexto.devedor_id,
        emprestimo_id=contexto.emprestimo_id,
        valor_declarado=Decimal("1200.00"),
        data_promessa=date(2026, 9, 10),
        criado_por_usuario_id=contexto.usuario_id,
        parcela_id=contexto.parcela_id,
    )
    promessa_repo.save(promessa)
    session.commit()

    apropriacao = ApropriacaoPagamento(
        promessa_id=promessa.id,
        pagamento_id=contexto.pagamento_id,
        parcela_id=contexto.parcela_id,
        valor=Decimal("100.00"),
        realizado_em=datetime(2026, 9, 15, 12, 30, tzinfo=UTC),
    )
    aprop_repo.save(apropriacao)
    session.commit()

    encontradas = aprop_repo.listar(ApropriacaoPagamentoFiltros(promessa_id=promessa.id))
    assert len(encontradas) == 1
    assert encontradas[0].promessa_id == promessa.id


def test_unit_of_work_expoe_repositories_de_operacao_diaria(
    session_factory: sessionmaker[Session],
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert isinstance(uow.cobranca_caso, SqlAlchemyCobrancaCasoRepository)
        assert isinstance(uow.acao_cobranca, SqlAlchemyAcaoCobrancaRepository)
        assert isinstance(uow.promessa_pagamento, SqlAlchemyPromessaPagamentoRepository)
        assert isinstance(uow.apropriacao_pagamento, SqlAlchemyApropriacaoPagamentoRepository)
        assert isinstance(uow.agenda_item, SqlAlchemyAgendaItemRepository)
        assert isinstance(uow.lembrete, SqlAlchemyLembreteRepository)
        assert isinstance(uow.registro_comunicacao, SqlAlchemyRegistroComunicacaoRepository)
        assert isinstance(
            uow.relatorio_operacional_cache,
            SqlAlchemyRelatorioOperacionalCacheRepository,
        )


class _ContextoOperacao:
    def __init__(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        emprestimo_id: uuid.UUID,
        parcela_id: uuid.UUID,
        pagamento_id: uuid.UUID,
    ) -> None:
        self.tenant_id = tenant_id
        self.carteira_id = carteira_id
        self.devedor_id = devedor_id
        self.usuario_id = usuario_id
        self.emprestimo_id = emprestimo_id
        self.parcela_id = parcela_id
        self.pagamento_id = pagamento_id


def _contexto_operacao(session: Session) -> _ContextoOperacao:
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    usuario = UsuarioFactory.build(tenant_id=tenant.id)
    SqlAlchemyUsuarioRepository(session).save(usuario)

    devedor = Devedor.criar(
        carteira_id=carteira.id,
        documento=Documento.from_str("529.982.247-25"),
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
        parametros={
            "valor_contratado": "1200.00",
            "quantidade_parcelas": 2,
        },
    )
    proposta.enviar_para_analise(usuario_id=usuario.id)
    proposta.aprovar(usuario_id=usuario.id)
    proposta_repository = SqlAlchemyPropostaComercialRepository(session)
    proposta_repository.save(proposta)
    contrato_repository = SqlAlchemyContratoCreditoRepository(session)
    contrato_repository.save(
        ContratoCredito.criar_de_proposta_aprovada(
            proposta=PropostaAprovadaLogica(
                proposta_id=proposta.id,
                tenant_id=tenant.id,
                carteira_id=carteira.id,
                devedor_id=devedor.id,
                parametros_aprovados={
                    "valor_contratado": "1200.00",
                    "moeda": "BRL",
                    "taxa_juros_mensal": "0.0200",
                    "quantidade_parcelas": 2,
                    "primeiro_vencimento": "2026-09-11",
                    "regra_calculo": "juros_simples_periodo_real",
                },
                aprovada_por_usuario_id=usuario.id,
                aprovada_em=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
            ),
            criado_por_usuario_id=usuario.id,
        )
    )

    contrato = contrato_repository.find_by_proposta_id(proposta.id)
    if contrato is None:
        raise AssertionError("contrato nao encontrado no contexto")

    contrato.formalizar(usuario_id=usuario.id)
    contrato.assinar(usuario_id=usuario.id)
    contrato_liberado = contrato.liberar_para_motor(usuario_id=usuario.id)

    emprestimo = Emprestimo.criar_de_contrato_liberado(contrato_liberado)
    SqlAlchemyEmprestimoRepository(session).save(emprestimo)

    motor = MotorFinanceiro()
    plano = motor.gerar_plano_parcelas(
        emprestimo=emprestimo,
        data_referencia=date(2026, 9, 10),
    )
    SqlAlchemyParcelaRepository(session).save_many(plano.parcelas)

    pagamento = motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=plano.parcelas[0].valor_previsto,
        recebido_em=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        chave_idempotencia="op-001",
        usuario_id=usuario.id,
    )
    SqlAlchemyPagamentoRepository(session).save(pagamento.pagamento)

    session.commit()

    return _ContextoOperacao(
        tenant_id=tenant.id,
        carteira_id=carteira.id,
        devedor_id=devedor.id,
        usuario_id=usuario.id,
        emprestimo_id=emprestimo.id,
        parcela_id=plano.parcelas[0].id,
        pagamento_id=pagamento.pagamento.id,
    )
