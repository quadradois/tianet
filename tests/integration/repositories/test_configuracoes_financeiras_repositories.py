"""Testes de integracao dos repositories de Configuracoes Financeiras."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.domain.credit.configuracoes_financeiras import (
    CalendarioFinanceiro,
    CodigoModalidadeFinanceira,
    ConfiguracaoFinanceira,
    ConfiguracaoFinanceiraState,
    JanelaVigencia,
    ModalidadeFinanceira,
    ParametroFinanceiroConfigurado,
    PoliticaArredondamento,
    TaxaFinanceiraConfigurada,
)
from emprestimo.domain.credit.ports import ConfiguracaoFinanceiraFiltros
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCalendarioFinanceiroRepository,
    SqlAlchemyCarteiraRepository,
    SqlAlchemyConfiguracaoFinanceiraRepository,
    SqlAlchemyModalidadeFinanceiraRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def test_repositories_configuracoes_financeiras_roundtrip(session: Session) -> None:
    contexto = _contexto(session)
    modalidade_repo = SqlAlchemyModalidadeFinanceiraRepository(session)
    calendario_repo = SqlAlchemyCalendarioFinanceiroRepository(session)
    configuracao_repo = SqlAlchemyConfiguracaoFinanceiraRepository(session)

    modalidade = ModalidadeFinanceira(
        tenant_id=contexto["tenant_id"],
        carteira_id=contexto["carteira_id"],
        codigo=CodigoModalidadeFinanceira("prazo-fixo"),
        nome="Prazo fixo",
    )
    calendario = CalendarioFinanceiro(
        tenant_id=contexto["tenant_id"],
        carteira_id=contexto["carteira_id"],
        codigo="br_padrao",
        nome="Brasil padrao",
        feriados=(date(2026, 9, 7),),
    )
    modalidade_repo.save(modalidade)
    calendario_repo.save(calendario)

    configuracao = _configuracao(
        tenant_id=contexto["tenant_id"],
        carteira_id=contexto["carteira_id"],
        calendario_id=calendario.id,
        usuario_id=contexto["usuario_id"],
    )
    configuracao.aprovar(usuario_id=contexto["usuario_id"])
    configuracao.ativar(usuario_id=contexto["usuario_id"])
    snapshot = configuracao.capturar_snapshot(usuario_id=contexto["usuario_id"])
    configuracao_repo.save(configuracao)
    configuracao_repo.save_snapshot(snapshot)
    session.commit()

    assert modalidade_repo.find_by_id(modalidade.id) == modalidade
    assert calendario_repo.find_by_id(calendario.id) == calendario

    restaurada = configuracao_repo.find_by_id(configuracao.id)
    assert restaurada is not None
    assert restaurada.estado is ConfiguracaoFinanceiraState.ATIVA
    assert restaurada.parametros_normalizados["valor_minimo"] == "100.00"
    assert len(restaurada.eventos) == 4

    vigentes = configuracao_repo.listar(
        ConfiguracaoFinanceiraFiltros(
            tenant_id=contexto["tenant_id"],
            carteira_id=contexto["carteira_id"],
            modalidade="prazo_fixo",
            estado=ConfiguracaoFinanceiraState.ATIVA,
            data_referencia=date(2026, 9, 10),
        )
    )
    assert [item.id for item in vigentes] == [configuracao.id]


def test_unit_of_work_expoe_repositories_configuracoes_financeiras(
    session_factory: sessionmaker[Session],
) -> None:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert isinstance(uow.modalidade_financeira, SqlAlchemyModalidadeFinanceiraRepository)
        assert isinstance(uow.calendario_financeiro, SqlAlchemyCalendarioFinanceiroRepository)
        assert isinstance(uow.configuracao_financeira, SqlAlchemyConfiguracaoFinanceiraRepository)


def _contexto(session: Session) -> dict[str, uuid.UUID]:
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    usuario = UsuarioFactory.build(tenant_id=tenant.id)
    SqlAlchemyUsuarioRepository(session).save(usuario)
    session.commit()
    return {
        "tenant_id": tenant.id,
        "carteira_id": carteira.id,
        "usuario_id": usuario.id,
    }


def _configuracao(
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    calendario_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> ConfiguracaoFinanceira:
    return ConfiguracaoFinanceira.criar_rascunho(
        tenant_id=tenant_id,
        carteira_id=carteira_id,
        modalidade=CodigoModalidadeFinanceira("prazo-fixo"),
        calendario_id=calendario_id,
        vigencia=JanelaVigencia(date(2026, 9, 1)),
        taxas=(
            TaxaFinanceiraConfigurada(
                nome="taxa_juros_mensal",
                valor=Decimal("0.0200"),
                periodicidade="mensal",
            ),
        ),
        parametros=(
            ParametroFinanceiroConfigurado("valor_minimo", Decimal("100.00")),
            ParametroFinanceiroConfigurado("moeda", "BRL"),
        ),
        politica_arredondamento=PoliticaArredondamento("half_up", 2),
        criada_por_usuario_id=usuario_id,
    )
