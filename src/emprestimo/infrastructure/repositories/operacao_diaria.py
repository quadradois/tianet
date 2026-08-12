"""Repositories do EPIC-007.

Persistência das entidades de Operação Diária no SQLAlchemy (P3).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

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
    AcaoCobrancaRepository,
    AgendaItemFiltros,
    AgendaItemRepository,
    ApropriacaoPagamentoFiltros,
    ApropriacaoPagamentoRepository,
    CobrancaCasoFiltros,
    CobrancaCasoRepository,
    LembreteRepository,
    PromessaPagamentoFiltros,
    PromessaPagamentoRepository,
    RegistroComunicacaoFiltros,
    RegistroComunicacaoRepository,
    RelatorioOperacionalCacheFiltros,
    RelatorioOperacionalCacheRepository,
)
from emprestimo.domain.credit.promessa import (
    ApropriacaoPagamento,
    PromessaPagamento,
    PromessaPagamentoState,
)
from emprestimo.infrastructure.db.orm import (
    AcaoCobrancaORM,
    AgendaItemORM,
    ApropriacaoPagamentoORM,
    CobrancaCasoORM,
    LembreteORM,
    PromessaPagamentoORM,
    RegistroComunicacaoORM,
    RelatorioOperacionalCacheORM,
)


class SqlAlchemyCobrancaCasoRepository(CobrancaCasoRepository):
    """Persistência de :class:`CobrancaCaso`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, caso: CobrancaCaso) -> None:
        self._session.merge(
            CobrancaCasoORM(
                id=caso.id,
                tenant_id=caso.tenant_id,
                carteira_id=caso.carteira_id,
                devedor_id=caso.devedor_id,
                emprestimo_id=caso.emprestimo_id,
                titulo=caso.titulo,
                estado=caso.estado.value,
                total_pendente=caso.total_pendente,
                origem=caso.origem,
                criado_em=caso.criado_em,
                atualizado_em=caso.atualizado_em,
            )
        )
        self._session.flush()

    def find_by_id(self, caso_id: uuid.UUID) -> CobrancaCaso | None:
        row = self._session.get(CobrancaCasoORM, caso_id)
        return _to_cobranca_caso(row) if row is not None else None

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[CobrancaCaso]:
        rows = self._session.scalars(
            select(CobrancaCasoORM)
            .where(CobrancaCasoORM.tenant_id == tenant_id)
            .order_by(CobrancaCasoORM.tenant_id, CobrancaCasoORM.id)
        ).all()
        return [_to_cobranca_caso(row) for row in rows]

    def listar(self, filtros: CobrancaCasoFiltros) -> list[CobrancaCaso]:
        query = select(CobrancaCasoORM).where(CobrancaCasoORM.tenant_id == filtros.tenant_id)
        if filtros.carteira_id is not None:
            query = query.where(CobrancaCasoORM.carteira_id == filtros.carteira_id)
        if filtros.devedor_id is not None:
            query = query.where(CobrancaCasoORM.devedor_id == filtros.devedor_id)
        if filtros.estado is not None:
            query = query.where(CobrancaCasoORM.estado == filtros.estado.value)
        query = query.order_by(CobrancaCasoORM.criado_em, CobrancaCasoORM.id)
        rows = self._session.scalars(query).all()
        return [_to_cobranca_caso(row) for row in rows]


class SqlAlchemyAcaoCobrancaRepository(AcaoCobrancaRepository):
    """Persistência de :class:`AcaoCobranca`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, acao: AcaoCobranca) -> None:
        self._session.merge(
            AcaoCobrancaORM(
                id=acao.id,
                cobranca_caso_id=acao.cobranca_caso_id,
                tenant_id=acao.tenant_id,
                carteira_id=acao.carteira_id,
                devedor_id=acao.devedor_id,
                emprestimo_id=acao.emprestimo_id,
                criado_por_usuario_id=acao.criado_por_usuario_id,
                tipo=acao.tipo.value,
                resultado=acao.resultado,
                parcela_id=acao.parcela_id,
                estado=acao.estado.value,
                registrada_em=acao.registrada_em,
            )
        )
        self._session.flush()

    def find_by_id(self, acao_id: uuid.UUID) -> AcaoCobranca | None:
        row = self._session.get(AcaoCobrancaORM, acao_id)
        return _to_acao_cobranca(row) if row is not None else None

    def listar(self, filtros: AcaoCobrancaFiltros) -> list[AcaoCobranca]:
        query = select(AcaoCobrancaORM).where(AcaoCobrancaORM.tenant_id == filtros.tenant_id)
        if filtros.carteira_id is not None:
            query = query.where(AcaoCobrancaORM.carteira_id == filtros.carteira_id)
        if filtros.devedor_id is not None:
            query = query.where(AcaoCobrancaORM.devedor_id == filtros.devedor_id)
        if filtros.emprestimo_id is not None:
            query = query.where(AcaoCobrancaORM.emprestimo_id == filtros.emprestimo_id)
        if filtros.cobranca_caso_id is not None:
            query = query.where(AcaoCobrancaORM.cobranca_caso_id == filtros.cobranca_caso_id)
        if filtros.usuario_id is not None:
            query = query.where(AcaoCobrancaORM.criado_por_usuario_id == filtros.usuario_id)
        if filtros.estado is not None:
            query = query.where(AcaoCobrancaORM.estado == filtros.estado.value)
        rows = self._session.scalars(
            query.order_by(AcaoCobrancaORM.registrada_em, AcaoCobrancaORM.id)
        ).all()
        return [_to_acao_cobranca(row) for row in rows]


class SqlAlchemyPromessaPagamentoRepository(PromessaPagamentoRepository):
    """Persistência de :class:`PromessaPagamento`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, promessa: PromessaPagamento) -> None:
        self._session.merge(
            PromessaPagamentoORM(
                id=promessa.id,
                tenant_id=promessa.tenant_id,
                carteira_id=promessa.carteira_id,
                devedor_id=promessa.devedor_id,
                emprestimo_id=promessa.emprestimo_id,
                valor_declarado=promessa.valor_declarado,
                data_promessa=promessa.data_promessa,
                estado=promessa.estado.value,
                observacao=promessa.observacao,
                parcela_id=promessa.parcela_id,
                criado_por_usuario_id=promessa.criado_por_usuario_id,
                criada_em=promessa.criada_em,
                atualizado_em=promessa.atualizado_em,
            )
        )
        self._session.flush()

    def find_by_id(self, promessa_id: uuid.UUID) -> PromessaPagamento | None:
        row = self._session.get(PromessaPagamentoORM, promessa_id)
        return _to_promessa_pagamento(row) if row is not None else None

    def listar(self, filtros: PromessaPagamentoFiltros) -> list[PromessaPagamento]:
        query = select(PromessaPagamentoORM).where(
            PromessaPagamentoORM.tenant_id == filtros.tenant_id
        )
        if filtros.carteira_id is not None:
            query = query.where(PromessaPagamentoORM.carteira_id == filtros.carteira_id)
        if filtros.devedor_id is not None:
            query = query.where(PromessaPagamentoORM.devedor_id == filtros.devedor_id)
        if filtros.emprestimo_id is not None:
            query = query.where(PromessaPagamentoORM.emprestimo_id == filtros.emprestimo_id)
        if filtros.estado is not None:
            query = query.where(PromessaPagamentoORM.estado == filtros.estado.value)
        rows = self._session.scalars(
            query.order_by(PromessaPagamentoORM.criada_em, PromessaPagamentoORM.id)
        ).all()
        return [_to_promessa_pagamento(row) for row in rows]


class SqlAlchemyApropriacaoPagamentoRepository(ApropriacaoPagamentoRepository):
    """Persistência de :class:`ApropriacaoPagamento`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, apropriacao: ApropriacaoPagamento) -> None:
        if apropriacao.parcela_id is None:
            raise ValueError("ApropriacaoPagamento requer parcela_id para persistir")

        self._session.merge(
            ApropriacaoPagamentoORM(
                id=apropriacao.id,
                promessa_id=apropriacao.promessa_id,
                pagamento_id=apropriacao.pagamento_id,
                valor=apropriacao.valor,
                realizado_em=apropriacao.realizado_em,
                parcela_id=apropriacao.parcela_id,
                idempotencia=str(apropriacao.id),
                criada_em=apropriacao.realizado_em,
            )
        )
        self._session.flush()

    def find_by_id(self, apropriacao_id: uuid.UUID) -> ApropriacaoPagamento | None:
        row = self._session.get(ApropriacaoPagamentoORM, apropriacao_id)
        return _to_apropriacao_pagamento(row) if row is not None else None

    def listar(self, filtros: ApropriacaoPagamentoFiltros) -> list[ApropriacaoPagamento]:
        query = select(ApropriacaoPagamentoORM)
        if filtros.promessa_id is not None:
            query = query.where(ApropriacaoPagamentoORM.promessa_id == filtros.promessa_id)
        if filtros.pagamento_id is not None:
            query = query.where(ApropriacaoPagamentoORM.pagamento_id == filtros.pagamento_id)
        rows = self._session.scalars(
            query.order_by(ApropriacaoPagamentoORM.criada_em, ApropriacaoPagamentoORM.id)
        ).all()
        return [_to_apropriacao_pagamento(row) for row in rows]


class SqlAlchemyAgendaItemRepository(AgendaItemRepository):
    """Persistência de :class:`AgendaItem`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, agenda_item: AgendaItem) -> None:
        self._session.merge(
            AgendaItemORM(
                id=agenda_item.id,
                tenant_id=agenda_item.tenant_id,
                carteira_id=agenda_item.carteira_id,
                devedor_id=agenda_item.devedor_id,
                emprestimo_id=agenda_item.emprestimo_id,
                titulo=agenda_item.titulo,
                previsto_para=agenda_item.previsto_para,
                estado=agenda_item.estado.value,
                criado_em=agenda_item.criado_em,
                atualizado_em=agenda_item.atualizado_em,
                usuario_solicitante_id=agenda_item.usuario_solicitante_id,
            )
        )
        self._session.flush()

    def find_by_id(self, agenda_item_id: uuid.UUID) -> AgendaItem | None:
        row = self._session.get(AgendaItemORM, agenda_item_id)
        return _to_agenda_item(row) if row is not None else None

    def listar(self, filtros: AgendaItemFiltros) -> list[AgendaItem]:
        query = select(AgendaItemORM).where(AgendaItemORM.tenant_id == filtros.tenant_id)
        if filtros.carteira_id is not None:
            query = query.where(AgendaItemORM.carteira_id == filtros.carteira_id)
        if filtros.devedor_id is not None:
            query = query.where(AgendaItemORM.devedor_id == filtros.devedor_id)
        if filtros.emprestimo_id is not None:
            query = query.where(AgendaItemORM.emprestimo_id == filtros.emprestimo_id)
        if filtros.estado is not None:
            query = query.where(AgendaItemORM.estado == filtros.estado.value)
        if filtros.janela_inicio is not None:
            query = query.where(AgendaItemORM.previsto_para >= filtros.janela_inicio)
        if filtros.janela_fim is not None:
            query = query.where(AgendaItemORM.previsto_para <= filtros.janela_fim)
        rows = self._session.scalars(
            query.order_by(AgendaItemORM.previsto_para, AgendaItemORM.id)
        ).all()
        return [_to_agenda_item(row) for row in rows]


class SqlAlchemyLembreteRepository(LembreteRepository):
    """Persistência de :class:`Lembrete`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, lembrete: Lembrete) -> None:
        self._session.merge(
            LembreteORM(
                id=lembrete.id,
                tenant_id=lembrete.tenant_id,
                carteira_id=lembrete.carteira_id,
                agenda_item_id=lembrete.agenda_item_id,
                horario=lembrete.horario,
                enviado_por_usuario_id=lembrete.enviado_por_usuario_id,
                mensagem=lembrete.mensagem,
                estado=lembrete.estado.value,
                criado_em=lembrete.criado_em,
            )
        )
        self._session.flush()

    def find_by_id(self, lembrete_id: uuid.UUID) -> Lembrete | None:
        row = self._session.get(LembreteORM, lembrete_id)
        return _to_lembrete(row) if row is not None else None

    def find_by_agenda_item_id(self, agenda_item_id: uuid.UUID) -> list[Lembrete]:
        rows = self._session.scalars(
            select(LembreteORM)
            .where(LembreteORM.agenda_item_id == agenda_item_id)
            .order_by(LembreteORM.horario, LembreteORM.id)
        ).all()
        return [_to_lembrete(row) for row in rows]


class SqlAlchemyRegistroComunicacaoRepository(RegistroComunicacaoRepository):
    """Persistência de :class:`RegistroComunicacao`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, registro: RegistroComunicacao) -> None:
        self._session.merge(
            RegistroComunicacaoORM(
                id=registro.id,
                tenant_id=registro.tenant_id,
                carteira_id=registro.carteira_id,
                devedor_id=registro.devedor_id,
                emprestimo_id=registro.emprestimo_id,
                responsavel_id=registro.responsavel_id,
                ator_tipo=registro.ator_tipo,
                ator_identificador=registro.ator_identificador,
                notification_id=registro.notification_id,
                template_id=registro.template_id,
                template_versao=registro.template_versao,
                provider_message_id=registro.provider_message_id,
                canal=registro.canal.value,
                resumo=registro.resumo,
                resultado=registro.resultado,
                ocorrido_em=registro.ocorrido_em,
                parcela_id=registro.parcela_id,
                cobranca_acao_id=registro.cobranca_acao_id,
                agenda_item_id=registro.agenda_item_id,
            )
        )
        self._session.flush()

    def find_by_id(self, registro_id: uuid.UUID) -> RegistroComunicacao | None:
        row = self._session.get(RegistroComunicacaoORM, registro_id)
        return _to_registro(row) if row is not None else None

    def listar(self, filtros: RegistroComunicacaoFiltros) -> list[RegistroComunicacao]:
        query = select(RegistroComunicacaoORM).where(
            RegistroComunicacaoORM.tenant_id == filtros.tenant_id
        )
        if filtros.carteira_id is not None:
            query = query.where(RegistroComunicacaoORM.carteira_id == filtros.carteira_id)
        if filtros.devedor_id is not None:
            query = query.where(RegistroComunicacaoORM.devedor_id == filtros.devedor_id)
        if filtros.emprestimo_id is not None:
            query = query.where(RegistroComunicacaoORM.emprestimo_id == filtros.emprestimo_id)
        if filtros.cobranca_acao_id is not None:
            query = query.where(RegistroComunicacaoORM.cobranca_acao_id == filtros.cobranca_acao_id)
        if filtros.agenda_item_id is not None:
            query = query.where(RegistroComunicacaoORM.agenda_item_id == filtros.agenda_item_id)
        rows = self._session.scalars(
            query.order_by(RegistroComunicacaoORM.ocorrido_em, RegistroComunicacaoORM.id)
        ).all()
        return [_to_registro(row) for row in rows]


class SqlAlchemyRelatorioOperacionalCacheRepository(RelatorioOperacionalCacheRepository):
    """Persistência de :class:`RelatorioOperacionalCache`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, relatorio: RelatorioOperacionalCache) -> None:
        self._session.merge(
            RelatorioOperacionalCacheORM(
                id=relatorio.id,
                tenant_id=relatorio.tenant_id,
                carteira_id=relatorio.carteira_id,
                janela_referencia=relatorio.janela_referencia,
                familia_relatorio=relatorio.familia_relatorio,
                payload_json=relatorio.payload_json,
                gerado_em=relatorio.gerado_em,
            )
        )
        self._session.flush()

    def find_by_id(self, relatorio_id: uuid.UUID) -> RelatorioOperacionalCache | None:
        row = self._session.get(RelatorioOperacionalCacheORM, relatorio_id)
        return _to_relatorio(row) if row is not None else None

    def listar(self, filtros: RelatorioOperacionalCacheFiltros) -> list[RelatorioOperacionalCache]:
        query = select(RelatorioOperacionalCacheORM).where(
            RelatorioOperacionalCacheORM.tenant_id == filtros.tenant_id,
            RelatorioOperacionalCacheORM.carteira_id == filtros.carteira_id,
        )
        if filtros.familia_relatorio is not None:
            query = query.where(
                RelatorioOperacionalCacheORM.familia_relatorio == filtros.familia_relatorio
            )
        if filtros.janela_inicio is not None:
            query = query.where(
                RelatorioOperacionalCacheORM.janela_referencia >= filtros.janela_inicio
            )
        if filtros.janela_fim is not None:
            query = query.where(
                RelatorioOperacionalCacheORM.janela_referencia <= filtros.janela_fim
            )
        rows = self._session.scalars(
            query.order_by(
                RelatorioOperacionalCacheORM.janela_referencia,
                RelatorioOperacionalCacheORM.id,
            )
        ).all()
        return [_to_relatorio(row) for row in rows]


def _to_cobranca_caso(row: CobrancaCasoORM) -> CobrancaCaso:
    return CobrancaCaso(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        devedor_id=row.devedor_id,
        emprestimo_id=row.emprestimo_id,
        titulo=row.titulo,
        origem=row.origem,
        estado=EstadoCobranca(row.estado),
        total_pendente=row.total_pendente,
        criado_em=row.criado_em,
        atualizado_em=row.atualizado_em,
    )


def _to_acao_cobranca(row: AcaoCobrancaORM) -> AcaoCobranca:
    return AcaoCobranca(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        devedor_id=row.devedor_id,
        cobranca_caso_id=row.cobranca_caso_id,
        emprestimo_id=row.emprestimo_id,
        criado_por_usuario_id=row.criado_por_usuario_id,
        tipo=TipoAcaoCobranca(row.tipo),
        resultado=row.resultado,
        parcela_id=row.parcela_id,
        estado=EstadoOperacional(row.estado),
        registrada_em=row.registrada_em,
    )


def _to_promessa_pagamento(row: PromessaPagamentoORM) -> PromessaPagamento:
    return PromessaPagamento(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        devedor_id=row.devedor_id,
        emprestimo_id=row.emprestimo_id,
        valor_declarado=row.valor_declarado,
        data_promessa=row.data_promessa,
        criado_por_usuario_id=row.criado_por_usuario_id,
        parcela_id=row.parcela_id,
        estado=PromessaPagamentoState(row.estado),
        observacao=row.observacao,
        criada_em=row.criada_em,
        atualizado_em=row.atualizado_em,
    )


def _to_apropriacao_pagamento(row: ApropriacaoPagamentoORM) -> ApropriacaoPagamento:
    if row.pagamento_id is None:
        raise ValueError("apropriacao de pagamento sem pagamento_id persistido")
    return ApropriacaoPagamento(
        promessa_id=row.promessa_id,
        pagamento_id=row.pagamento_id,
        valor=row.valor,
        realizado_em=row.realizado_em,
        parcela_id=row.parcela_id,
        id=row.id,
    )


def _to_agenda_item(row: AgendaItemORM) -> AgendaItem:
    return AgendaItem(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        devedor_id=row.devedor_id,
        emprestimo_id=row.emprestimo_id,
        titulo=row.titulo,
        previsto_para=row.previsto_para,
        usuario_solicitante_id=row.usuario_solicitante_id,
        estado=EstadoCompromisso(row.estado),
        criado_em=row.criado_em,
        atualizado_em=row.atualizado_em,
    )


def _to_lembrete(row: LembreteORM) -> Lembrete:
    return Lembrete(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        agenda_item_id=row.agenda_item_id,
        horario=row.horario,
        enviado_por_usuario_id=row.enviado_por_usuario_id,
        mensagem=row.mensagem,
        estado=EstadoLembrete(row.estado),
        criado_em=row.criado_em,
    )


def _to_registro(row: RegistroComunicacaoORM) -> RegistroComunicacao:
    return RegistroComunicacao(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        responsavel_id=row.responsavel_id,
        ator_tipo=row.ator_tipo,
        ator_identificador=row.ator_identificador,
        notification_id=row.notification_id,
        template_id=row.template_id,
        template_versao=row.template_versao,
        provider_message_id=row.provider_message_id,
        canal=CanalComunicacao(row.canal),
        ocorrido_em=row.ocorrido_em,
        resumo=row.resumo,
        resultado=row.resultado,
        devedor_id=row.devedor_id,
        emprestimo_id=row.emprestimo_id,
        parcela_id=row.parcela_id,
        cobranca_acao_id=row.cobranca_acao_id,
        agenda_item_id=row.agenda_item_id,
    )


def _to_relatorio(row: RelatorioOperacionalCacheORM) -> RelatorioOperacionalCache:
    return RelatorioOperacionalCache(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        janela_referencia=row.janela_referencia,
        familia_relatorio=row.familia_relatorio,
        payload_json=row.payload_json,
        gerado_em=row.gerado_em,
    )
