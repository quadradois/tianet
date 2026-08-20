"""Domain objects de promessa de pagamento (EPIC-007, DA-709/DA-718)."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from emprestimo.domain.common.errors import ViolacaoInvarianteError

__all__ = [
    "ApropriacaoPagamento",
    "PromessaPagamento",
    "PromessaPagamentoState",
    "PromessaPagamentoCumprimentoInvalidado",
]


class PromessaPagamentoState(StrEnum):
    """Estados validos da promessa operacional."""

    PENDENTE = "pendente"
    PAGAMENTO_INFORMADO = "pagamento_informado"
    CUMPRIDA = "cumprida"
    DESCUMPRIDA = "descumprida"


@dataclass(frozen=True)
class ApropriacaoPagamento:
    """Representa alocacao explicita de um pagamento para a promessa."""

    promessa_id: uuid.UUID
    pagamento_id: uuid.UUID
    valor: Decimal
    realizado_em: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        _validar_uuid("promessa_id", self.promessa_id)
        _validar_uuid("pagamento_id", self.pagamento_id)
        if not isinstance(self.valor, Decimal):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"valor deve ser Decimal, recebido {self.valor!r}",
            )
        if self.valor <= Decimal("0.00"):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "valor apropriado deve ser positivo",
            )


@dataclass(frozen=True)
class PromessaPagamentoCumprimentoInvalidado:
    """Evento de reversao de cumprimento por estorno financeiro."""

    promessa_id: uuid.UUID
    pagamento_id: uuid.UUID
    estorno_id: uuid.UUID
    estado_anterior: PromessaPagamentoState
    estado_novo: PromessaPagamentoState
    motivo: str
    ocorrencia_em: datetime


@dataclass
class PromessaPagamento:
    """Aggregate operacional da promessa de pagamento (sem calculo financeiro)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    emprestimo_id: uuid.UUID
    valor_declarado: Decimal
    data_promessa: date
    criado_por_usuario_id: uuid.UUID
    estado: PromessaPagamentoState = PromessaPagamentoState.PENDENTE
    observacao: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criada_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None
    _invalidacoes: list[PromessaPagamentoCumprimentoInvalidado] = field(
        default_factory=list,
        init=False,
        repr=False,
    )
    _valor_adequado: Decimal = field(default=Decimal("0.00"), init=False, repr=False)
    _apropriacoes: dict[uuid.UUID, ApropriacaoPagamento] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        _validar_uuid("devedor_id", self.devedor_id)
        _validar_uuid("emprestimo_id", self.emprestimo_id)
        _validar_uuid("criado_por_usuario_id", self.criado_por_usuario_id)
        _validar_uuid("id", self.id)
        if not isinstance(self.estado, PromessaPagamentoState):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"estado invalido, recebido {self.estado!r}",
            )
        if not isinstance(self.data_promessa, date):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"data_promessa deve ser date, recebido {self.data_promessa!r}",
            )
        if not isinstance(self.valor_declarado, Decimal):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"valor_declarado deve ser Decimal, recebido {self.valor_declarado!r}",
            )
        if self.valor_declarado <= Decimal("0.00"):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "valor_declarado deve ser maior que zero",
            )

    @classmethod
    def criar(
        cls,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        emprestimo_id: uuid.UUID,
        criado_por_usuario_id: uuid.UUID,
        valor_declarado: Decimal,
        data_promessa: date,
        observacao: str | None = None,
    ) -> PromessaPagamento:
        """Cria promessa em estado inicial ``pendente``."""

        return cls(
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            emprestimo_id=emprestimo_id,
            valor_declarado=valor_declarado,
            data_promessa=data_promessa,
            criado_por_usuario_id=criado_por_usuario_id,
            observacao=observacao,
        )

    @property
    def valor_adequado(self) -> Decimal:
        """Total apropriado contra a promessa sem mutacao externa."""

        return self._valor_adequado

    @property
    def apropriacoes(self) -> tuple[ApropriacaoPagamento, ...]:
        """Apropriacoes registradas, com vista imutavel."""

        return tuple(self._apropriacoes.values())

    @property
    def invalidacoes(self) -> tuple[PromessaPagamentoCumprimentoInvalidado, ...]:
        """Eventos de invalidacao gerados por rollback de pagamento."""

        return tuple(self._invalidacoes)

    def informar_pagamento(self) -> None:
        """Registra entrada operacional para a promessa."""

        if self.estado is not PromessaPagamentoState.PENDENTE:
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"pagamento_informado nao permitido no estado {self.estado.value}",
            )
        self.estado = PromessaPagamentoState.PAGAMENTO_INFORMADO
        self.atualizado_em = datetime.now(UTC)

    def apropriar_pagamento(self, apropriacao: ApropriacaoPagamento) -> None:
        """Associa um pagamento oficial a esta promessa."""

        if self.estado not in {
            PromessaPagamentoState.PENDENTE,
            PromessaPagamentoState.PAGAMENTO_INFORMADO,
            PromessaPagamentoState.DESCUMPRIDA,
        }:
            return

        if apropriacao.promessa_id != self.id:
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "apropriacao incompativel com a promessa",
            )

        if apropriacao.pagamento_id in self._apropriacoes:
            registro_existente = self._apropriacoes[apropriacao.pagamento_id]
            if registro_existente != apropriacao:
                raise ViolacaoInvarianteError(
                    "EPIC-007",
                    "mesma apropriacao com payload divergente",
                )
            return

        self._apropriacoes[apropriacao.pagamento_id] = copy.deepcopy(apropriacao)
        self._valor_adequado += apropriacao.valor

        if self._valor_adequado >= self.valor_declarado:
            self.estado = PromessaPagamentoState.CUMPRIDA

        self.atualizado_em = apropriacao.realizado_em

    def reavaliar_por_referencia(self, *, data_referencia: date) -> bool:
        """Reavalia estado da promessa conforme janela de promessa e adequacao.

        Retorna True quando a promessa sai de ``cumprida`` para ``pendente``/``descumprida``.
        """

        if self.estado is not PromessaPagamentoState.CUMPRIDA:
            if (
                self.estado
                in {
                    PromessaPagamentoState.PENDENTE,
                    PromessaPagamentoState.PAGAMENTO_INFORMADO,
                }
                and data_referencia > self.data_promessa
                and self._saldo_faltante() > Decimal("0.00")
            ):
                self.estado = PromessaPagamentoState.DESCUMPRIDA
                self.atualizado_em = datetime.now(UTC)
                return True
            return False

        if self._saldo_faltante() > Decimal("0.00"):
            novo_estado = (
                PromessaPagamentoState.PENDENTE
                if data_referencia <= self.data_promessa
                else PromessaPagamentoState.DESCUMPRIDA
            )
            if novo_estado is not self.estado:
                self._invalidacoes.append(
                    PromessaPagamentoCumprimentoInvalidado(
                        promessa_id=self.id,
                        pagamento_id=self._ultima_chave_pagamento(),
                        estorno_id=uuid.uuid4(),
                        estado_anterior=PromessaPagamentoState.CUMPRIDA,
                        estado_novo=novo_estado,
                        motivo="saldo_adequado_invalido",
                        ocorrencia_em=datetime.now(UTC),
                    )
                )
                self.estado = novo_estado
                self.atualizado_em = datetime.now(UTC)
                return True
        return False

    def desfazer_apropriacao(
        self,
        *,
        pagamento_id: uuid.UUID,
        estorno_id: uuid.UUID,
        data_referencia: date,
        motivo: str = "pagamento_estornado",
    ) -> bool:
        """Remove apropiacao de pagamento e reavalia estado."""

        apropriacao = self._apropriacoes.pop(pagamento_id, None)
        if apropriacao is None:
            return False

        self._valor_adequado -= apropriacao.valor
        if self._valor_adequado < Decimal("0.00"):
            self._valor_adequado = Decimal("0.00")

        estado_anterior = self.estado
        se_recalculou = self._reavaliar_apos_estorno(
            data_referencia=data_referencia,
            motivo=motivo,
            pag_id=pagamento_id,
            estorno_id=estorno_id,
        )
        return se_recalculou or estado_anterior is not self.estado

    def _reavaliar_apos_estorno(
        self,
        *,
        data_referencia: date,
        motivo: str,
        pag_id: uuid.UUID,
        estorno_id: uuid.UUID,
    ) -> bool:
        if self.estado is not PromessaPagamentoState.CUMPRIDA:
            if (
                self.estado
                in {
                    PromessaPagamentoState.PENDENTE,
                    PromessaPagamentoState.PAGAMENTO_INFORMADO,
                }
                and data_referencia > self.data_promessa
            ):
                self.estado = PromessaPagamentoState.DESCUMPRIDA
                self.atualizado_em = datetime.now(UTC)
                return True
            return False

        if self._saldo_faltante() > Decimal("0.00"):
            novo = (
                PromessaPagamentoState.PENDENTE
                if data_referencia <= self.data_promessa
                else PromessaPagamentoState.DESCUMPRIDA
            )
            if novo != self.estado:
                self.estado = novo
                self._invalidacoes.append(
                    PromessaPagamentoCumprimentoInvalidado(
                        promessa_id=self.id,
                        pagamento_id=pag_id,
                        estorno_id=estorno_id,
                        estado_anterior=PromessaPagamentoState.CUMPRIDA,
                        estado_novo=novo,
                        motivo=motivo,
                        ocorrencia_em=datetime.now(UTC),
                    )
                )
                self.atualizado_em = datetime.now(UTC)
                return True
            return False
        return False

    def _saldo_faltante(self) -> Decimal:
        return max(self.valor_declarado - self._valor_adequado, Decimal("0.00"))

    def _ultima_chave_pagamento(self) -> uuid.UUID:
        if not self._apropriacoes:
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "nenhum pagamento apropriado para evento de transicao",
            )
        return next(reversed(self._apropriacoes.keys()))


def _validar_uuid(campo: str, valor: object) -> None:
    if not isinstance(valor, uuid.UUID):
        raise ViolacaoInvarianteError(
            "EPIC-007",
            f"{campo} deve ser uuid.UUID, recebido {valor!r}",
        )
