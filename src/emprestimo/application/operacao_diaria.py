"""Servicos de aplicacao da Operacao Diaria (EPIC-007/P3)."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import cast

from emprestimo.application.errors import (
    AgendaItemNaoEncontradoError,
    CarteiraNaoEncontradaError,
    CobrancaCasoNaoEncontradoError,
    DevedorNaoEncontradoError,
    EmprestimoNaoEncontradoError,
    IdempotenciaConflitoError,
    LembreteNaoEncontradoError,
    PagamentoNaoEncontradoError,
    PromessaPagamentoNaoEncontradaError,
    RegistroComunicacaoNaoEncontradoError,
    TransicaoEstadoInvalidaError,
    UsuarioNaoEncontradoError,
)
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.operacao_diaria import (
    AcaoCobranca,
    AgendaItem,
    CanalComunicacao,
    CobrancaCaso,
    EstadoCobranca,
    EstadoCompromisso,
    EstadoLembrete,
    Lembrete,
    RegistroComunicacao,
    TipoAcaoCobranca,
)
from emprestimo.domain.credit.pagamento import Pagamento
from emprestimo.domain.credit.ports import (
    AgendaItemFiltros,
    ApropriacaoPagamentoFiltros,
    CobrancaCasoFiltros,
    RegistroComunicacaoFiltros,
)
from emprestimo.domain.credit.promessa import (
    ApropriacaoPagamento,
    PromessaPagamento,
    PromessaPagamentoState,
)
from emprestimo.domain.credit.scheduler import JobAgendado

ESCOPO_IDEMPOTENCIA_ACAO_COBRANCA = "operacao-diaria-acao-cobranca"
ESCOPO_IDEMPOTENCIA_PROMESSA = "operacao-diaria-promessa"
ESCOPO_IDEMPOTENCIA_APROPRIACAO = "operacao-diaria-apropriacao-promessa"
ESCOPO_IDEMPOTENCIA_AGENDA_ITEM = "operacao-diaria-agenda-item"
ESCOPO_IDEMPOTENCIA_LEMBRETE = "operacao-diaria-lembrete"
ESCOPO_IDEMPOTENCIA_AGENDA_REAGENDAR = "operacao-diaria-agenda-reagendar"
ESCOPO_IDEMPOTENCIA_AGENDA_CONCLUIR = "operacao-diaria-agenda-concluir"
ESCOPO_IDEMPOTENCIA_AGENDA_CANCELAR = "operacao-diaria-agenda-cancelar"
ESCOPO_IDEMPOTENCIA_LEMBRETE_REAGENDAR = "operacao-diaria-lembrete-reagendar"
ESCOPO_IDEMPOTENCIA_LEMBRETE_ENVIAR = "operacao-diaria-lembrete-enviar"
ESCOPO_IDEMPOTENCIA_LEMBRETE_CONCLUIR = "operacao-diaria-lembrete-concluir"
ESCOPO_IDEMPOTENCIA_LEMBRETE_CANCELAR = "operacao-diaria-lembrete-cancelar"
ESCOPO_IDEMPOTENCIA_REGISTRO_COMUNICACAO = "operacao-diaria-registro-comunicacao"


@dataclass(frozen=True)
class CobrancaCasoResultado:
    caso_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    emprestimo_id: uuid.UUID | None
    titulo: str
    origem: str
    estado: EstadoCobranca
    total_pendente: Decimal
    criado_em: datetime


@dataclass(frozen=True)
class FilaCobrancaResultado:
    items: tuple[CobrancaCasoResultado, ...]

    @property
    def total(self) -> int:
        return len(self.items)


@dataclass(frozen=True)
class AcaoCobrancaResultado:
    acao_id: uuid.UUID
    caso_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID | None
    emprestimo_id: uuid.UUID
    usuario_id: uuid.UUID
    tipo: TipoAcaoCobranca
    resultado: str
    registrada_em: datetime


@dataclass(frozen=True)
class PromessaPagamentoResultado:
    promessa_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    emprestimo_id: uuid.UUID
    valor_declarado: Decimal
    data_promessa: date
    estado: PromessaPagamentoState
    parcela_id: uuid.UUID | None


@dataclass(frozen=True)
class ApropriacaoPagamentoResultado:
    apropriacao_id: uuid.UUID
    promessa_id: uuid.UUID
    pagamento_id: uuid.UUID
    parcela_id: uuid.UUID | None
    valor: Decimal
    realizado_em: datetime
    estado_promessa: PromessaPagamentoState


@dataclass(frozen=True)
class AgendaItemResultado:
    agenda_item_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    usuario_solicitante_id: uuid.UUID
    titulo: str
    previsto_para: datetime
    emprestimo_id: uuid.UUID | None
    estado: EstadoCompromisso
    atualizado_em: datetime | None


@dataclass(frozen=True)
class LembreteResultado:
    lembrete_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    agenda_item_id: uuid.UUID
    horario: datetime
    enviado_por_usuario_id: uuid.UUID
    mensagem: str
    estado: EstadoLembrete


@dataclass(frozen=True)
class AgendaOperacionalResultado:
    compromissos: tuple[AgendaItemResultado, ...]
    lembretes: tuple[LembreteResultado, ...]
    items: tuple[AgendaItemResultado | LembreteResultado, ...] = ()

    @property
    def total(self) -> int:
        return len(self.items) if self.items else len(self.compromissos) + len(self.lembretes)


@dataclass(frozen=True)
class RegistroComunicacaoResultado:
    registro_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    responsavel_id: uuid.UUID | None
    canal: CanalComunicacao
    ocorrido_em: datetime
    resumo: str
    resultado: str
    devedor_id: uuid.UUID | None
    emprestimo_id: uuid.UUID | None
    parcela_id: uuid.UUID | None
    cobranca_acao_id: uuid.UUID | None
    agenda_item_id: uuid.UUID | None


@dataclass(frozen=True)
class HistoricoComunicacaoResultado:
    registros: tuple[RegistroComunicacaoResultado, ...]

    @property
    def total(self) -> int:
        return len(self.registros)


class ConsultarFilaCobranca:
    """Consulta a fila operacional sem alterar estado."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def listar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID | None = None,
        devedor_id: uuid.UUID | None = None,
        estado: EstadoCobranca | None = None,
    ) -> FilaCobrancaResultado:
        with self._uow_factory() as uow:
            if carteira_id is not None:
                _validar_carteira_do_tenant(uow, carteira_id=carteira_id, tenant_id=tenant_id)
            if devedor_id is not None:
                _validar_devedor_da_carteira(
                    uow,
                    devedor_id=devedor_id,
                    carteira_id=carteira_id,
                )
            casos = uow.cobranca_caso.listar(
                CobrancaCasoFiltros(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    estado=estado,
                )
            )
            if estado is None:
                casos = [caso for caso in casos if caso.estado is not EstadoCobranca.ENCERRADO]
            return FilaCobrancaResultado(tuple(_caso_resultado(caso) for caso in casos))


class ConsultarAgendaOperacional:
    """Consulta compromissos e lembretes operacionais sem alterar estado."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def listar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID | None = None,
        devedor_id: uuid.UUID | None = None,
        emprestimo_id: uuid.UUID | None = None,
        estado: EstadoCompromisso | None = None,
        janela_inicio: datetime | None = None,
        janela_fim: datetime | None = None,
        incluir_lembretes: bool = True,
    ) -> AgendaOperacionalResultado:
        with self._uow_factory() as uow:
            if carteira_id is not None:
                _validar_carteira_do_tenant(uow, carteira_id=carteira_id, tenant_id=tenant_id)
            if devedor_id is not None:
                _validar_devedor_da_carteira(
                    uow,
                    devedor_id=devedor_id,
                    carteira_id=carteira_id,
                )
            compromissos = uow.agenda_item.listar(
                AgendaItemFiltros(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    emprestimo_id=emprestimo_id,
                    estado=estado,
                    janela_inicio=janela_inicio,
                    janela_fim=janela_fim,
                )
            )
            lembretes: list[Lembrete] = []
            if incluir_lembretes:
                for compromisso in compromissos:
                    lembretes.extend(uow.lembrete.find_by_agenda_item_id(compromisso.id))
            return AgendaOperacionalResultado(
                compromissos=tuple(_agenda_item_resultado(item) for item in compromissos),
                lembretes=tuple(_lembrete_resultado(lembrete) for lembrete in lembretes),
                items=_ordenar_agenda(
                    tuple(_agenda_item_resultado(item) for item in compromissos),
                    tuple(_lembrete_resultado(lembrete) for lembrete in lembretes),
                ),
            )


class RegistrarAcaoCobranca:
    """Registra uma acao manual de cobranca na cadeia canonica do caso."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def registrar(
        self,
        *,
        tenant_id: uuid.UUID,
        cobranca_caso_id: uuid.UUID,
        usuario_id: uuid.UUID,
        tipo: TipoAcaoCobranca,
        resultado: str,
        idempotency_key: str,
        parcela_id: uuid.UUID | None = None,
    ) -> AcaoCobrancaResultado:
        solicitacao_hash = _hash_operacao(
            tenant_id=tenant_id,
            cobranca_caso_id=cobranca_caso_id,
            usuario_id=usuario_id,
            tipo=tipo.value,
            resultado=resultado,
            parcela_id=parcela_id,
        )
        with self._uow_factory() as uow:
            caso = _caso_do_tenant(uow, caso_id=cobranca_caso_id, tenant_id=tenant_id)
            _validar_usuario_do_tenant(uow, usuario_id=usuario_id, tenant_id=tenant_id)
            _validar_caso_operavel(caso, "registrar_acao_cobranca")
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=ESCOPO_IDEMPOTENCIA_ACAO_COBRANCA,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento="acao de cobranca em andamento",
            )
            if replay:
                return _acao_replay(uow, idempotency_key=idempotency_key)

            try:
                acao = AcaoCobranca(
                    tenant_id=caso.tenant_id,
                    carteira_id=caso.carteira_id,
                    devedor_id=caso.devedor_id,
                    cobranca_caso_id=caso.id,
                    emprestimo_id=_emprestimo_id_obrigatorio(caso),
                    criado_por_usuario_id=usuario_id,
                    tipo=tipo,
                    resultado=resultado,
                    parcela_id=parcela_id,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    caso.id,
                    "registrar_acao_cobranca",
                    str(exc),
                ) from exc
            uow.acao_cobranca.save(acao)
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA_ACAO_COBRANCA,
                _idempotencia_resultado_json("acao_id", acao.id),
            )
            uow.commit()
            return _acao_resultado(acao)


class RegistrarPromessa:
    """Registra promessa operacional, sem calcular efeito financeiro."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def registrar(
        self,
        *,
        tenant_id: uuid.UUID,
        cobranca_caso_id: uuid.UUID,
        usuario_id: uuid.UUID,
        valor_declarado: Decimal,
        data_promessa: date,
        idempotency_key: str,
        parcela_id: uuid.UUID | None = None,
        observacao: str | None = None,
        pagamento_informado: bool = False,
    ) -> PromessaPagamentoResultado:
        solicitacao_hash = _hash_operacao(
            tenant_id=tenant_id,
            cobranca_caso_id=cobranca_caso_id,
            usuario_id=usuario_id,
            valor_declarado=valor_declarado,
            data_promessa=data_promessa,
            parcela_id=parcela_id,
            observacao=observacao,
            pagamento_informado=pagamento_informado,
        )
        with self._uow_factory() as uow:
            caso = _caso_do_tenant(uow, caso_id=cobranca_caso_id, tenant_id=tenant_id)
            _validar_usuario_do_tenant(uow, usuario_id=usuario_id, tenant_id=tenant_id)
            _validar_caso_operavel(caso, "registrar_promessa")
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=ESCOPO_IDEMPOTENCIA_PROMESSA,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento="promessa em andamento",
            )
            if replay:
                return _promessa_replay(uow, idempotency_key=idempotency_key)

            try:
                promessa = PromessaPagamento.criar(
                    tenant_id=caso.tenant_id,
                    carteira_id=caso.carteira_id,
                    devedor_id=caso.devedor_id,
                    emprestimo_id=_emprestimo_id_obrigatorio(caso),
                    criado_por_usuario_id=usuario_id,
                    valor_declarado=valor_declarado,
                    data_promessa=data_promessa,
                    parcela_id=parcela_id,
                    observacao=observacao,
                )
                if pagamento_informado:
                    promessa.informar_pagamento()
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    caso.id,
                    "registrar_promessa",
                    str(exc),
                ) from exc
            uow.promessa_pagamento.save(promessa)
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA_PROMESSA,
                _idempotencia_resultado_json("promessa_id", promessa.id),
            )
            uow.commit()
            return _promessa_resultado(promessa)


class ApropriarPagamentoPromessa:
    """Associa pagamento oficial do Motor a uma promessa operacional."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def apropriar(
        self,
        *,
        tenant_id: uuid.UUID,
        promessa_id: uuid.UUID,
        pagamento_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
        parcela_id: uuid.UUID | None = None,
        data_referencia: date | None = None,
    ) -> ApropriacaoPagamentoResultado:
        solicitacao_hash = _hash_operacao(
            tenant_id=tenant_id,
            promessa_id=promessa_id,
            pagamento_id=pagamento_id,
            usuario_id=usuario_id,
            parcela_id=parcela_id,
            data_referencia=data_referencia,
        )
        with self._uow_factory() as uow:
            promessa = _promessa_do_tenant(uow, promessa_id=promessa_id, tenant_id=tenant_id)
            _validar_usuario_do_tenant(uow, usuario_id=usuario_id, tenant_id=tenant_id)
            pagamento = uow.pagamento.find_by_id(pagamento_id)
            if pagamento is None or pagamento.emprestimo_id != promessa.emprestimo_id:
                raise PagamentoNaoEncontradoError(pagamento_id)
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=ESCOPO_IDEMPOTENCIA_APROPRIACAO,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento="apropriacao de promessa em andamento",
            )
            if replay:
                return _apropriacao_replay(uow, idempotency_key=idempotency_key)

            _hidratar_apropriacoes(uow, promessa)
            parcela_apropriada = _parcela_da_apropriacao(promessa, pagamento, parcela_id)
            try:
                apropriacao = ApropriacaoPagamento(
                    promessa_id=promessa.id,
                    pagamento_id=pagamento.id,
                    valor=pagamento.valor_recebido,
                    realizado_em=pagamento.recebido_em,
                    parcela_id=parcela_apropriada,
                )
                promessa.apropriar_pagamento(apropriacao)
                promessa.reavaliar_por_referencia(
                    data_referencia=data_referencia or pagamento.recebido_em.date()
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    promessa.id,
                    "apropriar_pagamento",
                    str(exc),
                ) from exc
            uow.apropriacao_pagamento.save(apropriacao)
            uow.promessa_pagamento.save(promessa)
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA_APROPRIACAO,
                _idempotencia_resultado_json("apropriacao_id", apropriacao.id),
            )
            uow.commit()
            return _apropriacao_resultado(apropriacao, promessa)


class CriarCompromissoAgenda:
    """Cria compromisso operacional idempotente."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def criar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        titulo: str,
        previsto_para: datetime,
        idempotency_key: str,
        emprestimo_id: uuid.UUID | None = None,
    ) -> AgendaItemResultado:
        solicitacao_hash = _hash_operacao(
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            usuario_id=usuario_id,
            titulo=titulo,
            previsto_para=previsto_para,
            emprestimo_id=emprestimo_id,
        )
        with self._uow_factory() as uow:
            _validar_carteira_do_tenant(uow, carteira_id=carteira_id, tenant_id=tenant_id)
            _validar_devedor_da_carteira(uow, devedor_id=devedor_id, carteira_id=carteira_id)
            _validar_usuario_do_tenant(uow, usuario_id=usuario_id, tenant_id=tenant_id)
            if emprestimo_id is not None:
                _validar_emprestimo_da_cadeia(
                    uow,
                    emprestimo_id=emprestimo_id,
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                )
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=ESCOPO_IDEMPOTENCIA_AGENDA_ITEM,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento="compromisso de agenda em andamento",
            )
            if replay:
                return _agenda_item_replay(uow, idempotency_key=idempotency_key)

            try:
                agenda_item = AgendaItem(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    usuario_solicitante_id=usuario_id,
                    titulo=titulo,
                    previsto_para=previsto_para,
                    emprestimo_id=emprestimo_id,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    tenant_id,
                    "criar_compromisso_agenda",
                    str(exc),
                ) from exc
            uow.agenda_item.save(agenda_item)
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA_AGENDA_ITEM,
                _serializar_agenda_item_resultado(_agenda_item_resultado(agenda_item)),
            )
            uow.commit()
            return _agenda_item_resultado(agenda_item)


class CriarLembreteAgenda:
    """Cria lembrete associado a um compromisso de agenda."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def criar(
        self,
        *,
        tenant_id: uuid.UUID,
        agenda_item_id: uuid.UUID,
        usuario_id: uuid.UUID,
        horario: datetime,
        mensagem: str,
        idempotency_key: str,
        correlation_id: str | None = None,
    ) -> LembreteResultado:
        solicitacao_hash = _hash_operacao(
            tenant_id=tenant_id,
            agenda_item_id=agenda_item_id,
            usuario_id=usuario_id,
            horario=horario,
            mensagem=mensagem,
        )
        with self._uow_factory() as uow:
            agenda_item = _agenda_item_do_tenant(
                uow,
                agenda_item_id=agenda_item_id,
                tenant_id=tenant_id,
            )
            _validar_usuario_do_tenant(uow, usuario_id=usuario_id, tenant_id=tenant_id)
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=ESCOPO_IDEMPOTENCIA_LEMBRETE,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento="lembrete em andamento",
            )
            if replay:
                return _lembrete_replay(
                    uow,
                    idempotency_key=idempotency_key,
                    escopo=ESCOPO_IDEMPOTENCIA_LEMBRETE,
                )
            try:
                lembrete = Lembrete(
                    tenant_id=agenda_item.tenant_id,
                    carteira_id=agenda_item.carteira_id,
                    agenda_item_id=agenda_item.id,
                    horario=horario,
                    enviado_por_usuario_id=usuario_id,
                    mensagem=mensagem,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    agenda_item.id,
                    "criar_lembrete_agenda",
                    str(exc),
                ) from exc
            uow.lembrete.save(lembrete)
            job = JobAgendado(
                tenant_id=lembrete.tenant_id,
                carteira_id=lembrete.carteira_id,
                tipo="enviar_lembrete",
                executar_em=lembrete.horario,
                correlation_id=correlation_id or str(uuid.uuid4()),
                payload={"lembrete_id": str(lembrete.id)},
                origem_tipo="lembrete",
                origem_id=lembrete.id,
            )
            uow.job_agendado.save(job)
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA_LEMBRETE,
                _serializar_lembrete_resultado(_lembrete_resultado(lembrete)),
            )
            uow.commit()
            return _lembrete_resultado(lembrete)


class ManterCompromissoAgenda:
    """Executa transicoes de estado do compromisso operacional."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def reagendar(
        self,
        *,
        tenant_id: uuid.UUID,
        agenda_item_id: uuid.UUID,
        usuario_id: uuid.UUID,
        novo_horario: datetime,
        idempotency_key: str,
    ) -> AgendaItemResultado:
        return self._transicionar(
            tenant_id=tenant_id,
            agenda_item_id=agenda_item_id,
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            escopo=ESCOPO_IDEMPOTENCIA_AGENDA_REAGENDAR,
            operacao="reagendar_compromisso_agenda",
            payload={"novo_horario": novo_horario},
            aplicar=lambda item: item.reagendar(novo_horario=novo_horario),
        )

    def concluir(
        self,
        *,
        tenant_id: uuid.UUID,
        agenda_item_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
    ) -> AgendaItemResultado:
        return self._transicionar(
            tenant_id=tenant_id,
            agenda_item_id=agenda_item_id,
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            escopo=ESCOPO_IDEMPOTENCIA_AGENDA_CONCLUIR,
            operacao="concluir_compromisso_agenda",
            payload={},
            aplicar=lambda item: item.concluir(),
        )

    def cancelar(
        self,
        *,
        tenant_id: uuid.UUID,
        agenda_item_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
    ) -> AgendaItemResultado:
        return self._transicionar(
            tenant_id=tenant_id,
            agenda_item_id=agenda_item_id,
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            escopo=ESCOPO_IDEMPOTENCIA_AGENDA_CANCELAR,
            operacao="cancelar_compromisso_agenda",
            payload={},
            aplicar=lambda item: item.cancelar(),
        )

    def _transicionar(
        self,
        *,
        tenant_id: uuid.UUID,
        agenda_item_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
        escopo: str,
        operacao: str,
        payload: Mapping[str, object],
        aplicar: Callable[[AgendaItem], None],
    ) -> AgendaItemResultado:
        solicitacao_hash = _hash_operacao(
            tenant_id=tenant_id,
            agenda_item_id=agenda_item_id,
            usuario_id=usuario_id,
            operacao=operacao,
            payload=payload,
        )
        with self._uow_factory() as uow:
            agenda_item = _agenda_item_do_tenant(
                uow,
                agenda_item_id=agenda_item_id,
                tenant_id=tenant_id,
            )
            _validar_usuario_do_tenant(uow, usuario_id=usuario_id, tenant_id=tenant_id)
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=escopo,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento=f"{operacao} em andamento",
            )
            if replay:
                return _agenda_item_replay(uow, idempotency_key=idempotency_key, escopo=escopo)
            try:
                aplicar(agenda_item)
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(agenda_item.id, operacao, str(exc)) from exc
            uow.agenda_item.save(agenda_item)
            uow.idempotencia.concluir(
                idempotency_key,
                escopo,
                _serializar_agenda_item_resultado(_agenda_item_resultado(agenda_item)),
            )
            uow.commit()
            return _agenda_item_resultado(agenda_item)


class ManterLembreteAgenda:
    """Executa transicoes de lembrete sem notificacao externa."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def enviar(
        self,
        *,
        tenant_id: uuid.UUID,
        lembrete_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
    ) -> LembreteResultado:
        return self._transicionar(
            tenant_id=tenant_id,
            lembrete_id=lembrete_id,
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            escopo=ESCOPO_IDEMPOTENCIA_LEMBRETE_ENVIAR,
            operacao="enviar_lembrete_agenda",
            aplicar=lambda lembrete: lembrete.enviar(),
        )

    def concluir(
        self,
        *,
        tenant_id: uuid.UUID,
        lembrete_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
    ) -> LembreteResultado:
        return self._transicionar(
            tenant_id=tenant_id,
            lembrete_id=lembrete_id,
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            escopo=ESCOPO_IDEMPOTENCIA_LEMBRETE_CONCLUIR,
            operacao="concluir_lembrete_agenda",
            payload={},
            aplicar=lambda lembrete: lembrete.concluir(),
        )

    def reagendar(
        self,
        *,
        tenant_id: uuid.UUID,
        lembrete_id: uuid.UUID,
        usuario_id: uuid.UUID,
        novo_horario: datetime,
        idempotency_key: str,
    ) -> LembreteResultado:
        return self._transicionar(
            tenant_id=tenant_id,
            lembrete_id=lembrete_id,
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            escopo=ESCOPO_IDEMPOTENCIA_LEMBRETE_REAGENDAR,
            operacao="reagendar_lembrete_agenda",
            payload={"novo_horario": novo_horario},
            aplicar=lambda lembrete: _reagendar_lembrete(lembrete, novo_horario),
        )

    def cancelar(
        self,
        *,
        tenant_id: uuid.UUID,
        lembrete_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
    ) -> LembreteResultado:
        return self._transicionar(
            tenant_id=tenant_id,
            lembrete_id=lembrete_id,
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            escopo=ESCOPO_IDEMPOTENCIA_LEMBRETE_CANCELAR,
            operacao="cancelar_lembrete_agenda",
            aplicar=_cancelar_lembrete,
        )

    def _transicionar(
        self,
        *,
        tenant_id: uuid.UUID,
        lembrete_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
        escopo: str,
        operacao: str,
        aplicar: Callable[[Lembrete], None],
        payload: Mapping[str, object] | None = None,
    ) -> LembreteResultado:
        solicitacao_hash = _hash_operacao(
            tenant_id=tenant_id,
            lembrete_id=lembrete_id,
            usuario_id=usuario_id,
            operacao=operacao,
            payload=payload or {},
        )
        with self._uow_factory() as uow:
            lembrete = _lembrete_do_tenant(uow, lembrete_id=lembrete_id, tenant_id=tenant_id)
            _validar_usuario_do_tenant(uow, usuario_id=usuario_id, tenant_id=tenant_id)
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=escopo,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento=f"{operacao} em andamento",
            )
            if replay:
                return _lembrete_replay(uow, idempotency_key=idempotency_key, escopo=escopo)
            try:
                aplicar(lembrete)
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(lembrete.id, operacao, str(exc)) from exc
            uow.lembrete.save(lembrete)
            uow.idempotencia.concluir(
                idempotency_key,
                escopo,
                _serializar_lembrete_resultado(_lembrete_resultado(lembrete)),
            )
            uow.commit()
            return _lembrete_resultado(lembrete)


class RegistrarComunicacaoManual:
    """Registra comunicacao manual imutavel na cadeia operacional."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def registrar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        canal: CanalComunicacao,
        ocorrido_em: datetime,
        resumo: str,
        resultado: str,
        idempotency_key: str,
        emprestimo_id: uuid.UUID | None = None,
        parcela_id: uuid.UUID | None = None,
        cobranca_acao_id: uuid.UUID | None = None,
        agenda_item_id: uuid.UUID | None = None,
    ) -> RegistroComunicacaoResultado:
        solicitacao_hash = _hash_operacao(
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            usuario_id=usuario_id,
            canal=canal.value,
            ocorrido_em=ocorrido_em,
            resumo=resumo,
            resultado=resultado,
            emprestimo_id=emprestimo_id,
            parcela_id=parcela_id,
            cobranca_acao_id=cobranca_acao_id,
            agenda_item_id=agenda_item_id,
        )
        with self._uow_factory() as uow:
            _validar_carteira_do_tenant(uow, carteira_id=carteira_id, tenant_id=tenant_id)
            _validar_devedor_da_carteira(uow, devedor_id=devedor_id, carteira_id=carteira_id)
            _validar_usuario_do_tenant(uow, usuario_id=usuario_id, tenant_id=tenant_id)
            if emprestimo_id is not None:
                _validar_emprestimo_da_cadeia(
                    uow,
                    emprestimo_id=emprestimo_id,
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                )
            if parcela_id is not None:
                _validar_parcela_do_emprestimo(
                    uow,
                    parcela_id=parcela_id,
                    emprestimo_id=emprestimo_id,
                )
            if cobranca_acao_id is not None:
                _validar_acao_cobranca_da_cadeia(
                    uow,
                    acao_id=cobranca_acao_id,
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    emprestimo_id=emprestimo_id,
                )
            if agenda_item_id is not None:
                _validar_agenda_item_da_cadeia(
                    uow,
                    agenda_item_id=agenda_item_id,
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    emprestimo_id=emprestimo_id,
                )
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=ESCOPO_IDEMPOTENCIA_REGISTRO_COMUNICACAO,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento="registro de comunicacao em andamento",
            )
            if replay:
                return _registro_comunicacao_replay(uow, idempotency_key=idempotency_key)
            try:
                registro = RegistroComunicacao(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    emprestimo_id=emprestimo_id,
                    responsavel_id=usuario_id,
                    canal=canal,
                    ocorrido_em=ocorrido_em,
                    resumo=resumo,
                    resultado=resultado,
                    parcela_id=parcela_id,
                    cobranca_acao_id=cobranca_acao_id,
                    agenda_item_id=agenda_item_id,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    tenant_id,
                    "registrar_comunicacao_manual",
                    str(exc),
                ) from exc
            resultado_registro = _registro_comunicacao_resultado(registro)
            uow.registro_comunicacao.save(registro)
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA_REGISTRO_COMUNICACAO,
                _serializar_registro_comunicacao_resultado(resultado_registro),
            )
            uow.commit()
            return resultado_registro


class ConsultarHistoricoComunicacao:
    """Consulta historico imutavel de comunicacao manual."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def listar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID | None = None,
        devedor_id: uuid.UUID | None = None,
        emprestimo_id: uuid.UUID | None = None,
        cobranca_acao_id: uuid.UUID | None = None,
        agenda_item_id: uuid.UUID | None = None,
    ) -> HistoricoComunicacaoResultado:
        with self._uow_factory() as uow:
            if carteira_id is not None:
                _validar_carteira_do_tenant(uow, carteira_id=carteira_id, tenant_id=tenant_id)
            if devedor_id is not None:
                _validar_devedor_da_carteira(
                    uow,
                    devedor_id=devedor_id,
                    carteira_id=carteira_id,
                )
            if emprestimo_id is not None and carteira_id is not None and devedor_id is not None:
                _validar_emprestimo_da_cadeia(
                    uow,
                    emprestimo_id=emprestimo_id,
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                )
            registros = uow.registro_comunicacao.listar(
                RegistroComunicacaoFiltros(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    emprestimo_id=emprestimo_id,
                    cobranca_acao_id=cobranca_acao_id,
                    agenda_item_id=agenda_item_id,
                )
            )
            return HistoricoComunicacaoResultado(
                registros=tuple(_registro_comunicacao_resultado(item) for item in registros)
            )


def _caso_do_tenant(
    uow: UnitOfWork,
    *,
    caso_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> CobrancaCaso:
    caso = uow.cobranca_caso.find_by_id(caso_id)
    if caso is None or caso.tenant_id != tenant_id:
        raise CobrancaCasoNaoEncontradoError(caso_id)
    return caso


def _promessa_do_tenant(
    uow: UnitOfWork,
    *,
    promessa_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> PromessaPagamento:
    promessa = uow.promessa_pagamento.find_by_id(promessa_id)
    if promessa is None or promessa.tenant_id != tenant_id:
        raise PromessaPagamentoNaoEncontradaError(promessa_id)
    return promessa


def _agenda_item_do_tenant(
    uow: UnitOfWork,
    *,
    agenda_item_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> AgendaItem:
    agenda_item = uow.agenda_item.find_by_id(agenda_item_id)
    if agenda_item is None or agenda_item.tenant_id != tenant_id:
        raise AgendaItemNaoEncontradoError(agenda_item_id)
    return agenda_item


def _lembrete_do_tenant(
    uow: UnitOfWork,
    *,
    lembrete_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> Lembrete:
    lembrete = uow.lembrete.find_by_id(lembrete_id)
    if lembrete is None or lembrete.tenant_id != tenant_id:
        raise LembreteNaoEncontradoError(lembrete_id)
    return lembrete


def _validar_carteira_do_tenant(
    uow: UnitOfWork,
    *,
    carteira_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    carteira = uow.carteira.find_by_id(carteira_id)
    if carteira is None or carteira.tenant_id != tenant_id:
        raise CarteiraNaoEncontradaError(carteira_id)


def _validar_devedor_da_carteira(
    uow: UnitOfWork,
    *,
    devedor_id: uuid.UUID,
    carteira_id: uuid.UUID | None,
) -> None:
    devedor = uow.devedor.find_by_id(devedor_id)
    if devedor is None or (carteira_id is not None and devedor.carteira_id != carteira_id):
        raise DevedorNaoEncontradoError(devedor_id)


def _validar_usuario_do_tenant(
    uow: UnitOfWork,
    *,
    usuario_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    usuario = uow.usuario.find_by_id(usuario_id)
    if usuario is None or usuario.tenant_id != tenant_id:
        raise UsuarioNaoEncontradoError(usuario_id)


def _validar_emprestimo_da_cadeia(
    uow: UnitOfWork,
    *,
    emprestimo_id: uuid.UUID,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    devedor_id: uuid.UUID,
) -> None:
    emprestimo = uow.emprestimo.find_by_id(emprestimo_id)
    if (
        emprestimo is None
        or emprestimo.tenant_id != tenant_id
        or emprestimo.carteira_id != carteira_id
        or emprestimo.devedor_id != devedor_id
    ):
        raise EmprestimoNaoEncontradoError(emprestimo_id)


def _validar_parcela_do_emprestimo(
    uow: UnitOfWork,
    *,
    parcela_id: uuid.UUID,
    emprestimo_id: uuid.UUID | None,
) -> None:
    if emprestimo_id is None:
        raise TransicaoEstadoInvalidaError(
            parcela_id,
            "validar_parcela_comunicacao",
            "parcela exige emprestimo_id na cadeia",
        )
    parcelas = uow.parcela.find_by_emprestimo_id(emprestimo_id)
    if not any(parcela.id == parcela_id for parcela in parcelas):
        raise TransicaoEstadoInvalidaError(
            parcela_id,
            "validar_parcela_comunicacao",
            "parcela nao pertence ao emprestimo informado",
        )


def _validar_acao_cobranca_da_cadeia(
    uow: UnitOfWork,
    *,
    acao_id: uuid.UUID,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    devedor_id: uuid.UUID,
    emprestimo_id: uuid.UUID | None,
) -> None:
    acao = uow.acao_cobranca.find_by_id(acao_id)
    if (
        acao is None
        or acao.tenant_id != tenant_id
        or acao.carteira_id != carteira_id
        or acao.devedor_id != devedor_id
        or (emprestimo_id is not None and acao.emprestimo_id != emprestimo_id)
    ):
        raise CobrancaCasoNaoEncontradoError(acao_id)


def _validar_agenda_item_da_cadeia(
    uow: UnitOfWork,
    *,
    agenda_item_id: uuid.UUID,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    devedor_id: uuid.UUID,
    emprestimo_id: uuid.UUID | None,
) -> None:
    agenda_item = uow.agenda_item.find_by_id(agenda_item_id)
    if (
        agenda_item is None
        or agenda_item.tenant_id != tenant_id
        or agenda_item.carteira_id != carteira_id
        or agenda_item.devedor_id != devedor_id
        or (emprestimo_id is not None and agenda_item.emprestimo_id != emprestimo_id)
    ):
        raise AgendaItemNaoEncontradoError(agenda_item_id)


def _validar_caso_operavel(caso: CobrancaCaso, acao: str) -> None:
    if caso.estado is EstadoCobranca.ENCERRADO:
        raise TransicaoEstadoInvalidaError(caso.id, acao, "caso de cobranca encerrado")
    if caso.emprestimo_id is None:
        raise EmprestimoNaoEncontradoError(caso.id)


def _emprestimo_id_obrigatorio(caso: CobrancaCaso) -> uuid.UUID:
    if caso.emprestimo_id is None:
        raise EmprestimoNaoEncontradoError(caso.id)
    return caso.emprestimo_id


def _replay_ou_registrar_chave(
    uow: UnitOfWork,
    *,
    idempotency_key: str,
    escopo: str,
    solicitacao_hash: str,
    motivo_em_andamento: str,
) -> bool:
    existente = uow.idempotencia.find_by_chave(idempotency_key, escopo)
    if existente is None:
        uow.idempotencia.registrar(idempotency_key, escopo, solicitacao_hash)
        return False
    if existente["estado"] != "finished":
        raise IdempotenciaConflitoError(idempotency_key, motivo_em_andamento)
    if existente["solicitacao_hash"] != solicitacao_hash:
        raise IdempotenciaConflitoError(idempotency_key, "payload divergente")
    return True


def _hash_operacao(**dados: object) -> str:
    bruto = json.dumps(_normalizar_json(dados), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _normalizar_json(valor: object) -> object:
    if isinstance(valor, Decimal):
        return str(valor.quantize(Decimal("0.01")))
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if isinstance(valor, date | datetime):
        return valor.isoformat()
    if isinstance(valor, Mapping):
        return {
            str(chave): _normalizar_json(item)
            for chave, item in sorted(valor.items(), key=lambda item: str(item[0]))
        }
    if isinstance(valor, tuple | list):
        return [_normalizar_json(item) for item in valor]
    return valor


def _idempotencia_resultado_json(campo: str, valor: uuid.UUID) -> str:
    return json.dumps({campo: str(valor)})


def _resultado_id(
    existente: dict[str, object],
    campo: str,
    idempotency_key: str,
) -> uuid.UUID:
    conteudo = existente.get("resultado")
    if not isinstance(conteudo, str) or not conteudo:
        raise IdempotenciaConflitoError(idempotency_key, "resultado ausente")
    dados = json.loads(conteudo)
    return uuid.UUID(cast(str, dados[campo]))


def _acao_replay(uow: UnitOfWork, *, idempotency_key: str) -> AcaoCobrancaResultado:
    existente = uow.idempotencia.find_by_chave(
        idempotency_key,
        ESCOPO_IDEMPOTENCIA_ACAO_COBRANCA,
    )
    if existente is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado ausente")
    acao = uow.acao_cobranca.find_by_id(_resultado_id(existente, "acao_id", idempotency_key))
    if acao is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado de acao ausente")
    return _acao_resultado(acao)


def _agenda_item_replay(
    uow: UnitOfWork,
    *,
    idempotency_key: str,
    escopo: str = ESCOPO_IDEMPOTENCIA_AGENDA_ITEM,
) -> AgendaItemResultado:
    existente = uow.idempotencia.find_by_chave(idempotency_key, escopo)
    if existente is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado ausente")
    if _resultado_tem_snapshot(existente.get("resultado"), "agenda_item_id", "estado"):
        return _desserializar_agenda_item_resultado(
            cast(str, existente["resultado"]),
            idempotency_key,
        )
    agenda_item = uow.agenda_item.find_by_id(
        _resultado_id(existente, "agenda_item_id", idempotency_key)
    )
    if agenda_item is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado de agenda ausente")
    return _agenda_item_resultado(agenda_item)


def _lembrete_replay(
    uow: UnitOfWork,
    *,
    idempotency_key: str,
    escopo: str,
) -> LembreteResultado:
    existente = uow.idempotencia.find_by_chave(idempotency_key, escopo)
    if existente is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado ausente")
    if _resultado_tem_snapshot(existente.get("resultado"), "lembrete_id", "estado"):
        return _desserializar_lembrete_resultado(
            cast(str, existente["resultado"]),
            idempotency_key,
        )
    lembrete = uow.lembrete.find_by_id(_resultado_id(existente, "lembrete_id", idempotency_key))
    if lembrete is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado de lembrete ausente")
    return _lembrete_resultado(lembrete)


def _registro_comunicacao_replay(
    uow: UnitOfWork,
    *,
    idempotency_key: str,
) -> RegistroComunicacaoResultado:
    existente = uow.idempotencia.find_by_chave(
        idempotency_key,
        ESCOPO_IDEMPOTENCIA_REGISTRO_COMUNICACAO,
    )
    if existente is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado ausente")
    if _resultado_tem_snapshot(existente.get("resultado"), "registro_id", "canal"):
        return _desserializar_registro_comunicacao_resultado(
            cast(str, existente["resultado"]),
            idempotency_key,
        )
    registro = uow.registro_comunicacao.find_by_id(
        _resultado_id(existente, "registro_id", idempotency_key)
    )
    if registro is None:
        raise RegistroComunicacaoNaoEncontradoError(
            _resultado_id(existente, "registro_id", idempotency_key)
        )
    return _registro_comunicacao_resultado(registro)


def _promessa_replay(uow: UnitOfWork, *, idempotency_key: str) -> PromessaPagamentoResultado:
    existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA_PROMESSA)
    if existente is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado ausente")
    promessa = uow.promessa_pagamento.find_by_id(
        _resultado_id(existente, "promessa_id", idempotency_key)
    )
    if promessa is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado de promessa ausente")
    return _promessa_resultado(promessa)


def _apropriacao_replay(
    uow: UnitOfWork,
    *,
    idempotency_key: str,
) -> ApropriacaoPagamentoResultado:
    existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA_APROPRIACAO)
    if existente is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado ausente")
    apropriacao = uow.apropriacao_pagamento.find_by_id(
        _resultado_id(existente, "apropriacao_id", idempotency_key)
    )
    if apropriacao is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado de apropriacao ausente")
    promessa = uow.promessa_pagamento.find_by_id(apropriacao.promessa_id)
    if promessa is None:
        raise IdempotenciaConflitoError(idempotency_key, "promessa de apropriacao ausente")
    return _apropriacao_resultado(apropriacao, promessa)


def _hidratar_apropriacoes(uow: UnitOfWork, promessa: PromessaPagamento) -> None:
    apropriacoes = uow.apropriacao_pagamento.listar(
        ApropriacaoPagamentoFiltros(promessa_id=promessa.id)
    )
    for apropriacao in apropriacoes:
        promessa.apropriar_pagamento(apropriacao)


def _parcela_da_apropriacao(
    promessa: PromessaPagamento,
    pagamento: Pagamento,
    parcela_id: uuid.UUID | None,
) -> uuid.UUID | None:
    """Parcela a que a apropriacao se refere, quando houver uma.

    Deixou de ser obrigatoria com a DR-004: no emprestimo livre nao existe
    parcela, e a apropriacao liga um pagamento a uma promessa — o vinculo que
    importa. Antes, a ausencia derrubava a operacao com "parcela oficial da
    apropriacao nao encontrada", o que impediria apropriar qualquer pagamento.
    A entidade sempre aceitou o campo nulo; era este resolvedor que exigia.
    """
    if parcela_id is not None:
        return parcela_id
    parcelas_liquidadas: tuple[uuid.UUID, ...] = pagamento.parcelas_liquidadas
    if parcelas_liquidadas:
        return parcelas_liquidadas[0]
    return promessa.parcela_id


def _caso_resultado(caso: CobrancaCaso) -> CobrancaCasoResultado:
    return CobrancaCasoResultado(
        caso_id=caso.id,
        tenant_id=caso.tenant_id,
        carteira_id=caso.carteira_id,
        devedor_id=caso.devedor_id,
        emprestimo_id=caso.emprestimo_id,
        titulo=caso.titulo,
        origem=caso.origem,
        estado=caso.estado,
        total_pendente=caso.total_pendente,
        criado_em=caso.criado_em,
    )


def _acao_resultado(acao: AcaoCobranca) -> AcaoCobrancaResultado:
    return AcaoCobrancaResultado(
        acao_id=acao.id,
        caso_id=acao.cobranca_caso_id,
        tenant_id=acao.tenant_id,
        carteira_id=acao.carteira_id,
        devedor_id=acao.devedor_id,
        emprestimo_id=acao.emprestimo_id,
        usuario_id=acao.criado_por_usuario_id,
        tipo=acao.tipo,
        resultado=acao.resultado,
        registrada_em=acao.registrada_em,
    )


def _promessa_resultado(promessa: PromessaPagamento) -> PromessaPagamentoResultado:
    return PromessaPagamentoResultado(
        promessa_id=promessa.id,
        tenant_id=promessa.tenant_id,
        carteira_id=promessa.carteira_id,
        devedor_id=promessa.devedor_id,
        emprestimo_id=promessa.emprestimo_id,
        valor_declarado=promessa.valor_declarado,
        data_promessa=promessa.data_promessa,
        estado=promessa.estado,
        parcela_id=promessa.parcela_id,
    )


def _apropriacao_resultado(
    apropriacao: ApropriacaoPagamento,
    promessa: PromessaPagamento,
) -> ApropriacaoPagamentoResultado:
    if apropriacao.parcela_id is None:
        raise TransicaoEstadoInvalidaError(
            promessa.id,
            "apropriar_pagamento",
            "parcela oficial da apropriacao nao encontrada",
        )
    return ApropriacaoPagamentoResultado(
        apropriacao_id=apropriacao.id,
        promessa_id=apropriacao.promessa_id,
        pagamento_id=apropriacao.pagamento_id,
        parcela_id=apropriacao.parcela_id,
        valor=apropriacao.valor,
        realizado_em=apropriacao.realizado_em,
        estado_promessa=promessa.estado,
    )


def _agenda_item_resultado(item: AgendaItem) -> AgendaItemResultado:
    return AgendaItemResultado(
        agenda_item_id=item.id,
        tenant_id=item.tenant_id,
        carteira_id=item.carteira_id,
        devedor_id=item.devedor_id,
        usuario_solicitante_id=item.usuario_solicitante_id,
        titulo=item.titulo,
        previsto_para=item.previsto_para,
        emprestimo_id=item.emprestimo_id,
        estado=item.estado,
        atualizado_em=item.atualizado_em,
    )


def _lembrete_resultado(lembrete: Lembrete) -> LembreteResultado:
    if lembrete.agenda_item_id is None:
        raise TransicaoEstadoInvalidaError(
            lembrete.id,
            "lembrete_resultado",
            "lembrete sem agenda_item_id",
        )
    return LembreteResultado(
        lembrete_id=lembrete.id,
        tenant_id=lembrete.tenant_id,
        carteira_id=lembrete.carteira_id,
        agenda_item_id=lembrete.agenda_item_id,
        horario=lembrete.horario,
        enviado_por_usuario_id=lembrete.enviado_por_usuario_id,
        mensagem=lembrete.mensagem,
        estado=lembrete.estado,
    )


def _registro_comunicacao_resultado(
    registro: RegistroComunicacao,
) -> RegistroComunicacaoResultado:
    return RegistroComunicacaoResultado(
        registro_id=registro.id,
        tenant_id=registro.tenant_id,
        carteira_id=registro.carteira_id,
        responsavel_id=registro.responsavel_id,
        canal=registro.canal,
        ocorrido_em=registro.ocorrido_em,
        resumo=registro.resumo,
        resultado=registro.resultado,
        devedor_id=registro.devedor_id,
        emprestimo_id=registro.emprestimo_id,
        parcela_id=registro.parcela_id,
        cobranca_acao_id=registro.cobranca_acao_id,
        agenda_item_id=registro.agenda_item_id,
    )


def _serializar_agenda_item_resultado(resultado: AgendaItemResultado) -> str:
    return json.dumps(
        {
            "agenda_item_id": str(resultado.agenda_item_id),
            "tenant_id": str(resultado.tenant_id),
            "carteira_id": str(resultado.carteira_id),
            "devedor_id": str(resultado.devedor_id),
            "usuario_solicitante_id": str(resultado.usuario_solicitante_id),
            "titulo": resultado.titulo,
            "previsto_para": resultado.previsto_para.isoformat(),
            "emprestimo_id": (
                str(resultado.emprestimo_id) if resultado.emprestimo_id is not None else None
            ),
            "estado": resultado.estado.value,
            "atualizado_em": (
                resultado.atualizado_em.isoformat() if resultado.atualizado_em is not None else None
            ),
        }
    )


def _desserializar_agenda_item_resultado(
    conteudo: str,
    idempotency_key: str,
) -> AgendaItemResultado:
    try:
        dados = json.loads(conteudo)
        return AgendaItemResultado(
            agenda_item_id=uuid.UUID(dados["agenda_item_id"]),
            tenant_id=uuid.UUID(dados["tenant_id"]),
            carteira_id=uuid.UUID(dados["carteira_id"]),
            devedor_id=uuid.UUID(dados["devedor_id"]),
            usuario_solicitante_id=uuid.UUID(dados["usuario_solicitante_id"]),
            titulo=dados["titulo"],
            previsto_para=datetime.fromisoformat(dados["previsto_para"]),
            emprestimo_id=(
                uuid.UUID(dados["emprestimo_id"]) if dados["emprestimo_id"] is not None else None
            ),
            estado=EstadoCompromisso(dados["estado"]),
            atualizado_em=(
                datetime.fromisoformat(dados["atualizado_em"])
                if dados["atualizado_em"] is not None
                else None
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise IdempotenciaConflitoError(idempotency_key, "resultado de agenda invalido") from exc


def _serializar_lembrete_resultado(resultado: LembreteResultado) -> str:
    return json.dumps(
        {
            "lembrete_id": str(resultado.lembrete_id),
            "tenant_id": str(resultado.tenant_id),
            "carteira_id": str(resultado.carteira_id),
            "agenda_item_id": str(resultado.agenda_item_id),
            "horario": resultado.horario.isoformat(),
            "enviado_por_usuario_id": str(resultado.enviado_por_usuario_id),
            "mensagem": resultado.mensagem,
            "estado": resultado.estado.value,
        }
    )


def _desserializar_lembrete_resultado(
    conteudo: str,
    idempotency_key: str,
) -> LembreteResultado:
    try:
        dados = json.loads(conteudo)
        return LembreteResultado(
            lembrete_id=uuid.UUID(dados["lembrete_id"]),
            tenant_id=uuid.UUID(dados["tenant_id"]),
            carteira_id=uuid.UUID(dados["carteira_id"]),
            agenda_item_id=uuid.UUID(dados["agenda_item_id"]),
            horario=datetime.fromisoformat(dados["horario"]),
            enviado_por_usuario_id=uuid.UUID(dados["enviado_por_usuario_id"]),
            mensagem=dados["mensagem"],
            estado=EstadoLembrete(dados["estado"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise IdempotenciaConflitoError(idempotency_key, "resultado de lembrete invalido") from exc


def _serializar_registro_comunicacao_resultado(
    resultado: RegistroComunicacaoResultado,
) -> str:
    return json.dumps(
        {
            "registro_id": str(resultado.registro_id),
            "tenant_id": str(resultado.tenant_id),
            "carteira_id": str(resultado.carteira_id),
            "responsavel_id": str(resultado.responsavel_id),
            "canal": resultado.canal.value,
            "ocorrido_em": resultado.ocorrido_em.isoformat(),
            "resumo": resultado.resumo,
            "resultado": resultado.resultado,
            "devedor_id": str(resultado.devedor_id) if resultado.devedor_id is not None else None,
            "emprestimo_id": (
                str(resultado.emprestimo_id) if resultado.emprestimo_id is not None else None
            ),
            "parcela_id": str(resultado.parcela_id) if resultado.parcela_id is not None else None,
            "cobranca_acao_id": (
                str(resultado.cobranca_acao_id) if resultado.cobranca_acao_id is not None else None
            ),
            "agenda_item_id": (
                str(resultado.agenda_item_id) if resultado.agenda_item_id is not None else None
            ),
        }
    )


def _desserializar_registro_comunicacao_resultado(
    conteudo: str,
    idempotency_key: str,
) -> RegistroComunicacaoResultado:
    try:
        dados = json.loads(conteudo)
        return RegistroComunicacaoResultado(
            registro_id=uuid.UUID(dados["registro_id"]),
            tenant_id=uuid.UUID(dados["tenant_id"]),
            carteira_id=uuid.UUID(dados["carteira_id"]),
            responsavel_id=uuid.UUID(dados["responsavel_id"]),
            canal=CanalComunicacao(dados["canal"]),
            ocorrido_em=datetime.fromisoformat(dados["ocorrido_em"]),
            resumo=dados["resumo"],
            resultado=dados["resultado"],
            devedor_id=uuid.UUID(dados["devedor_id"]) if dados["devedor_id"] is not None else None,
            emprestimo_id=(
                uuid.UUID(dados["emprestimo_id"]) if dados["emprestimo_id"] is not None else None
            ),
            parcela_id=uuid.UUID(dados["parcela_id"]) if dados["parcela_id"] is not None else None,
            cobranca_acao_id=(
                uuid.UUID(dados["cobranca_acao_id"])
                if dados["cobranca_acao_id"] is not None
                else None
            ),
            agenda_item_id=(
                uuid.UUID(dados["agenda_item_id"]) if dados["agenda_item_id"] is not None else None
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise IdempotenciaConflitoError(
            idempotency_key,
            "resultado de comunicacao invalido",
        ) from exc


def _resultado_tem_snapshot(
    conteudo: object,
    id_campo: str,
    campo_snapshot: str,
) -> bool:
    if not isinstance(conteudo, str) or not conteudo:
        return False
    try:
        dados = json.loads(conteudo)
    except json.JSONDecodeError:
        return False
    return id_campo in dados and campo_snapshot in dados


def _ordenar_agenda(
    compromissos: tuple[AgendaItemResultado, ...],
    lembretes: tuple[LembreteResultado, ...],
) -> tuple[AgendaItemResultado | LembreteResultado, ...]:
    itens: list[AgendaItemResultado | LembreteResultado] = [*compromissos, *lembretes]
    return tuple(
        sorted(
            itens,
            key=lambda item: (
                item.previsto_para if isinstance(item, AgendaItemResultado) else item.horario,
                "compromisso" if isinstance(item, AgendaItemResultado) else "lembrete",
                str(
                    item.agenda_item_id
                    if isinstance(item, AgendaItemResultado)
                    else item.lembrete_id
                ),
            ),
        )
    )


def _reagendar_lembrete(lembrete: Lembrete, novo_horario: datetime) -> None:
    if lembrete.estado is not EstadoLembrete.PROGRAMA:
        raise ViolacaoInvarianteError(
            "EPIC-007",
            f"lembrete {lembrete.estado.value} nao pode ser reagendado",
        )
    lembrete.horario = novo_horario


def _cancelar_lembrete(lembrete: Lembrete) -> None:
    lembrete.cancelar()
