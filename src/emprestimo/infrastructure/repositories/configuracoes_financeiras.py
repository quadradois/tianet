"""Repositories SQLAlchemy de Configuracoes Financeiras (EPIC-009/P2)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import cast

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from emprestimo.domain.credit.configuracoes_financeiras import (
    CalendarioFinanceiro,
    CodigoModalidadeFinanceira,
    ConfiguracaoFinanceira,
    ConfiguracaoFinanceiraState,
    EventoConfiguracaoFinanceira,
    JanelaVigencia,
    ModalidadeFinanceira,
    ParametroFinanceiroConfigurado,
    PoliticaArredondamento,
    SnapshotConfiguracaoContratualV1,
    TaxaFinanceiraConfigurada,
)
from emprestimo.domain.credit.ports import (
    CalendarioFinanceiroRepository,
    ConfiguracaoFinanceiraFiltros,
    ConfiguracaoFinanceiraRepository,
    ModalidadeFinanceiraRepository,
)
from emprestimo.infrastructure.db.orm import (
    CalendarioFinanceiroORM,
    ConfiguracaoFinanceiraORM,
    EventoConfiguracaoFinanceiraORM,
    ModalidadeFinanceiraORM,
    SnapshotConfiguracaoContratualORM,
)


class SqlAlchemyModalidadeFinanceiraRepository(ModalidadeFinanceiraRepository):
    """Persistencia de :class:`ModalidadeFinanceira`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, modalidade: ModalidadeFinanceira) -> None:
        self._session.merge(
            ModalidadeFinanceiraORM(
                id=modalidade.id,
                tenant_id=modalidade.tenant_id,
                carteira_id=modalidade.carteira_id,
                codigo=modalidade.codigo.valor,
                nome=modalidade.nome,
                ativa=modalidade.ativa,
            )
        )
        self._session.flush()

    def find_by_id(self, modalidade_id: uuid.UUID) -> ModalidadeFinanceira | None:
        row = self._session.get(ModalidadeFinanceiraORM, modalidade_id)
        return _to_modalidade(row) if row is not None else None

    def listar(self, tenant_id: uuid.UUID) -> list[ModalidadeFinanceira]:
        rows = self._session.scalars(
            select(ModalidadeFinanceiraORM)
            .where(ModalidadeFinanceiraORM.tenant_id == tenant_id)
            .order_by(ModalidadeFinanceiraORM.codigo, ModalidadeFinanceiraORM.id)
        ).all()
        return [_to_modalidade(row) for row in rows]


class SqlAlchemyCalendarioFinanceiroRepository(CalendarioFinanceiroRepository):
    """Persistencia de :class:`CalendarioFinanceiro`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, calendario: CalendarioFinanceiro) -> None:
        self._session.merge(
            CalendarioFinanceiroORM(
                id=calendario.id,
                tenant_id=calendario.tenant_id,
                carteira_id=calendario.carteira_id,
                codigo=calendario.codigo,
                nome=calendario.nome,
                feriados=[feriado.isoformat() for feriado in calendario.feriados],
            )
        )
        self._session.flush()

    def find_by_id(self, calendario_id: uuid.UUID) -> CalendarioFinanceiro | None:
        row = self._session.get(CalendarioFinanceiroORM, calendario_id)
        return _to_calendario(row) if row is not None else None

    def listar(self, tenant_id: uuid.UUID) -> list[CalendarioFinanceiro]:
        rows = self._session.scalars(
            select(CalendarioFinanceiroORM)
            .where(CalendarioFinanceiroORM.tenant_id == tenant_id)
            .order_by(CalendarioFinanceiroORM.codigo, CalendarioFinanceiroORM.id)
        ).all()
        return [_to_calendario(row) for row in rows]


class SqlAlchemyConfiguracaoFinanceiraRepository(ConfiguracaoFinanceiraRepository):
    """Persistencia de :class:`ConfiguracaoFinanceira` e snapshots."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, configuracao: ConfiguracaoFinanceira) -> None:
        self._session.merge(_to_configuracao_orm(configuracao))
        for evento in configuracao.eventos:
            self._session.merge(_to_evento_orm(evento))
        self._session.flush()

    def save_snapshot(self, snapshot: SnapshotConfiguracaoContratualV1) -> None:
        parametros = cast(Mapping[str, object], snapshot.to_dict()["parametros"])
        self._session.add(
            SnapshotConfiguracaoContratualORM(
                id=uuid.uuid4(),
                configuracao_id=snapshot.configuracao_id,
                tenant_id=snapshot.tenant_id,
                carteira_id=snapshot.carteira_id,
                modalidade=snapshot.modalidade,
                versao=snapshot.versao,
                parametros=dict(parametros),
                hash_parametros=snapshot.hash_parametros,
                capturado_em=snapshot.capturado_em,
                capturado_por_usuario_id=snapshot.capturado_por_usuario_id,
                motivo=snapshot.motivo,
            )
        )
        self._session.flush()

    def find_by_id(self, configuracao_id: uuid.UUID) -> ConfiguracaoFinanceira | None:
        row = self._session.get(ConfiguracaoFinanceiraORM, configuracao_id)
        if row is None:
            return None
        eventos = self._eventos_de(row.id)
        return _to_configuracao(row, eventos.get(row.id, []))

    def listar(self, filtros: ConfiguracaoFinanceiraFiltros) -> list[ConfiguracaoFinanceira]:
        query = select(ConfiguracaoFinanceiraORM).where(
            ConfiguracaoFinanceiraORM.tenant_id == filtros.tenant_id
        )
        if filtros.carteira_id is not None:
            query = query.where(ConfiguracaoFinanceiraORM.carteira_id == filtros.carteira_id)
        if filtros.modalidade is not None:
            query = query.where(ConfiguracaoFinanceiraORM.modalidade_codigo == filtros.modalidade)
        if filtros.estado is not None:
            query = query.where(ConfiguracaoFinanceiraORM.estado == filtros.estado.value)
        if filtros.data_referencia is not None:
            query = query.where(
                ConfiguracaoFinanceiraORM.vigencia_inicio <= filtros.data_referencia,
                or_(
                    ConfiguracaoFinanceiraORM.vigencia_fim.is_(None),
                    ConfiguracaoFinanceiraORM.vigencia_fim > filtros.data_referencia,
                ),
            )
        rows = self._session.scalars(
            query.order_by(
                ConfiguracaoFinanceiraORM.vigencia_inicio,
                ConfiguracaoFinanceiraORM.versao,
                ConfiguracaoFinanceiraORM.id,
            )
        ).all()
        eventos = self._eventos_de(*(row.id for row in rows))
        return [_to_configuracao(row, eventos.get(row.id, [])) for row in rows]

    def _eventos_de(
        self, *configuracao_ids: uuid.UUID
    ) -> dict[uuid.UUID, list[EventoConfiguracaoFinanceira]]:
        if not configuracao_ids:
            return {}
        rows = self._session.scalars(
            select(EventoConfiguracaoFinanceiraORM)
            .where(EventoConfiguracaoFinanceiraORM.configuracao_id.in_(configuracao_ids))
            .order_by(
                EventoConfiguracaoFinanceiraORM.ocorrido_em,
                EventoConfiguracaoFinanceiraORM.id,
            )
        ).all()
        eventos: dict[uuid.UUID, list[EventoConfiguracaoFinanceira]] = {}
        for row in rows:
            eventos.setdefault(row.configuracao_id, []).append(_to_evento(row))
        return eventos


def _to_modalidade(row: ModalidadeFinanceiraORM) -> ModalidadeFinanceira:
    return ModalidadeFinanceira(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        codigo=CodigoModalidadeFinanceira(row.codigo),
        nome=row.nome,
        ativa=row.ativa,
    )


def _to_calendario(row: CalendarioFinanceiroORM) -> CalendarioFinanceiro:
    return CalendarioFinanceiro(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        codigo=row.codigo,
        nome=row.nome,
        feriados=tuple(date.fromisoformat(valor) for valor in row.feriados),
    )


def _to_configuracao_orm(configuracao: ConfiguracaoFinanceira) -> ConfiguracaoFinanceiraORM:
    return ConfiguracaoFinanceiraORM(
        id=configuracao.id,
        tenant_id=configuracao.tenant_id,
        carteira_id=configuracao.carteira_id,
        modalidade_codigo=configuracao.modalidade.valor,
        calendario_id=configuracao.calendario_id,
        estado=configuracao.estado.value,
        versao=configuracao.versao,
        vigencia_inicio=configuracao.vigencia.inicio,
        vigencia_fim=configuracao.vigencia.fim,
        taxas=[
            {
                "nome": taxa.nome,
                "valor": str(taxa.valor),
                "periodicidade": taxa.periodicidade,
            }
            for taxa in configuracao.taxas
        ],
        parametros=[
            {
                "nome": parametro.nome,
                "valor": _to_json_value(parametro.valor),
            }
            for parametro in configuracao.parametros
        ],
        politica_arredondamento={
            "modo": configuracao.politica_arredondamento.modo,
            "escala": configuracao.politica_arredondamento.escala,
        },
        criada_por_usuario_id=configuracao.criada_por_usuario_id,
        criada_em=configuracao.criada_em,
        atualizada_em=configuracao.atualizada_em,
        aprovada_por_usuario_id=configuracao.aprovada_por_usuario_id,
        aprovada_em=configuracao.aprovada_em,
        programada_para=configuracao.programada_para,
        ativada_em=configuracao.ativada_em,
        substituida_em=configuracao.substituida_em,
        inativada_em=configuracao.inativada_em,
    )


def _to_configuracao(
    row: ConfiguracaoFinanceiraORM,
    eventos: list[EventoConfiguracaoFinanceira] | None = None,
) -> ConfiguracaoFinanceira:
    politica_arredondamento = cast(Mapping[str, object], row.politica_arredondamento)
    configuracao = ConfiguracaoFinanceira(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        modalidade=CodigoModalidadeFinanceira(row.modalidade_codigo),
        calendario_id=row.calendario_id,
        vigencia=JanelaVigencia(row.vigencia_inicio, row.vigencia_fim),
        taxas=tuple(
            TaxaFinanceiraConfigurada(
                nome=str(taxa["nome"]),
                valor=Decimal(str(taxa["valor"])),
                periodicidade=str(taxa["periodicidade"]),
            )
            for taxa in row.taxas
        ),
        parametros=tuple(
            ParametroFinanceiroConfigurado(
                nome=str(parametro["nome"]),
                valor=parametro.get("valor"),
            )
            for parametro in row.parametros
        ),
        politica_arredondamento=PoliticaArredondamento(
            modo=str(politica_arredondamento["modo"]),
            escala=int(cast(str | int, politica_arredondamento["escala"])),
        ),
        criada_por_usuario_id=row.criada_por_usuario_id,
        estado=ConfiguracaoFinanceiraState(row.estado),
        versao=row.versao,
        criada_em=row.criada_em,
        atualizada_em=row.atualizada_em,
        aprovada_por_usuario_id=row.aprovada_por_usuario_id,
        aprovada_em=row.aprovada_em,
        programada_para=row.programada_para,
        ativada_em=row.ativada_em,
        substituida_em=row.substituida_em,
        inativada_em=row.inativada_em,
    )
    configuracao._eventos = eventos if eventos is not None else []
    return configuracao


def _to_evento_orm(evento: EventoConfiguracaoFinanceira) -> EventoConfiguracaoFinanceiraORM:
    return EventoConfiguracaoFinanceiraORM(
        id=evento.id,
        configuracao_id=evento.configuracao_id,
        tenant_id=evento.tenant_id,
        carteira_id=evento.carteira_id,
        usuario_id=evento.usuario_id,
        tipo=evento.tipo,
        motivo=evento.motivo,
        versao_anterior=evento.versao_anterior,
        versao_nova=evento.versao_nova,
        correlation_id=evento.correlation_id,
        ocorrido_em=evento.ocorrido_em,
    )


def _to_evento(row: EventoConfiguracaoFinanceiraORM) -> EventoConfiguracaoFinanceira:
    return EventoConfiguracaoFinanceira(
        id=row.id,
        tipo=row.tipo,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        configuracao_id=row.configuracao_id,
        usuario_id=row.usuario_id,
        motivo=row.motivo,
        versao_anterior=row.versao_anterior,
        versao_nova=row.versao_nova,
        correlation_id=row.correlation_id,
        ocorrido_em=row.ocorrido_em,
    )


def _to_json_value(valor: object) -> object:
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {str(chave): _to_json_value(item) for chave, item in valor.items()}
    if isinstance(valor, tuple | list):
        return [_to_json_value(item) for item in valor]
    return valor
