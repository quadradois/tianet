"""Proposta Comercial (IMP-107, EPIC-003)."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.decisao_comercial import DecisaoComercial
from emprestimo.domain.credit.eventos_comercial import (
    EventoPropostaComercial,
    evento_from_decisao,
)
from emprestimo.domain.credit.proposta_aprovada import PropostaAprovadaLogica
from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState

__all__ = ["PropostaAprovadaLogica", "PropostaComercial", "PropostaComercialState"]

ESTADOS_TERMINAIS = frozenset(
    {
        PropostaComercialState.APROVADA,
        PropostaComercialState.RECUSADA,
        PropostaComercialState.CANCELADA,
        PropostaComercialState.EXPIRADA,
    }
)


@dataclass
class PropostaComercial:
    """Aggregate Root do contexto Comercial."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    criada_por_usuario_id: uuid.UUID
    _parametros: dict[str, object]
    simulacao_id: uuid.UUID | None = None
    estado: PropostaComercialState = PropostaComercialState.RASCUNHO
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None
    aprovada_por_usuario_id: uuid.UUID | None = None
    aprovada_em: datetime | None = None
    _decisoes: list[DecisaoComercial] = field(default_factory=list, init=False, repr=False)
    _eventos: list[EventoPropostaComercial] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        _validar_uuid("devedor_id", self.devedor_id)
        _validar_uuid("criada_por_usuario_id", self.criada_por_usuario_id)
        if self.simulacao_id is not None:
            _validar_uuid("simulacao_id", self.simulacao_id)
        if not isinstance(self.estado, PropostaComercialState):
            raise ViolacaoInvarianteError(
                "EPIC-003",
                f"estado deve ser PropostaComercialState, recebido {self.estado!r}",
            )
        if not isinstance(self.id, uuid.UUID):
            raise ViolacaoInvarianteError(
                "EPIC-003",
                f"id deve ser uuid.UUID, recebido {self.id!r}",
            )
        self._parametros = _copiar_parametros(self._parametros)

    @classmethod
    def criar(
        cls,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        criada_por_usuario_id: uuid.UUID,
        parametros: Mapping[str, object],
        simulacao_id: uuid.UUID | None = None,
    ) -> PropostaComercial:
        """Cria uma proposta comercial em rascunho."""

        return cls(
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            criada_por_usuario_id=criada_por_usuario_id,
            simulacao_id=simulacao_id,
            _parametros=_copiar_parametros(parametros),
        )

    @classmethod
    def restaurar(
        cls,
        *,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        criada_por_usuario_id: uuid.UUID,
        parametros: Mapping[str, object],
        simulacao_id: uuid.UUID | None,
        estado: PropostaComercialState,
        criado_em: datetime,
        atualizado_em: datetime | None,
        aprovada_por_usuario_id: uuid.UUID | None,
        aprovada_em: datetime | None,
        decisoes: list[DecisaoComercial] | None = None,
    ) -> PropostaComercial:
        """Reconstitui uma proposta comercial persistida sem nova transicao."""

        proposta = cls(
            id=id,
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            criada_por_usuario_id=criada_por_usuario_id,
            simulacao_id=simulacao_id,
            estado=estado,
            _parametros=_copiar_parametros(parametros),
            criado_em=criado_em,
            atualizado_em=atualizado_em,
            aprovada_por_usuario_id=aprovada_por_usuario_id,
            aprovada_em=aprovada_em,
        )
        proposta._decisoes = list(decisoes or [])
        proposta._eventos = [
            evento_from_decisao(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                devedor_id=devedor_id,
                decisao=decisao,
            )
            for decisao in proposta._decisoes
        ]
        return proposta

    @property
    def parametros(self) -> dict[str, object]:
        """Parametros comerciais atuais, protegidos contra mutacao externa."""

        return copy.deepcopy(self._parametros)

    @property
    def decisoes(self) -> tuple[DecisaoComercial, ...]:
        """Trilha imutavel de decisoes comerciais."""

        return tuple(self._decisoes)

    @property
    def eventos(self) -> tuple[EventoPropostaComercial, ...]:
        """Eventos de dominio gerados pelas decisoes comerciais."""

        return tuple(self._eventos)

    def enviar_para_analise(self, *, usuario_id: uuid.UUID) -> None:
        self._transicionar(
            usuario_id=usuario_id,
            estado_esperado=PropostaComercialState.RASCUNHO,
            proximo_estado=PropostaComercialState.EM_ANALISE,
        )

    def aprovar(self, *, usuario_id: uuid.UUID) -> None:
        self._transicionar(
            usuario_id=usuario_id,
            estado_esperado=PropostaComercialState.EM_ANALISE,
            proximo_estado=PropostaComercialState.APROVADA,
        )
        self.aprovada_por_usuario_id = usuario_id
        self.aprovada_em = datetime.now(UTC)

    def recusar(self, *, usuario_id: uuid.UUID, motivo: str | None = None) -> None:
        self._transicionar(
            usuario_id=usuario_id,
            estado_esperado=PropostaComercialState.EM_ANALISE,
            proximo_estado=PropostaComercialState.RECUSADA,
            motivo=motivo,
        )

    def cancelar(self, *, usuario_id: uuid.UUID, motivo: str | None = None) -> None:
        if self.estado not in {
            PropostaComercialState.RASCUNHO,
            PropostaComercialState.EM_ANALISE,
        }:
            self._falhar_transicao(PropostaComercialState.CANCELADA)
        self._registrar_decisao(
            usuario_id=usuario_id,
            proximo_estado=PropostaComercialState.CANCELADA,
            motivo=motivo,
        )

    def expirar(self, *, usuario_id: uuid.UUID) -> None:
        self._transicionar(
            usuario_id=usuario_id,
            estado_esperado=PropostaComercialState.EM_ANALISE,
            proximo_estado=PropostaComercialState.EXPIRADA,
        )

    def atualizar_parametros(self, parametros: Mapping[str, object]) -> None:
        if self.estado in ESTADOS_TERMINAIS:
            raise ViolacaoInvarianteError(
                "EPIC-003",
                f"proposta terminal nao permite alterar parametros ({self.estado.value})",
            )
        self._parametros = _copiar_parametros(parametros)
        self._marcar_atualizado()

    def gerar_contrato_logico(self) -> PropostaAprovadaLogica:
        if self.estado is not PropostaComercialState.APROVADA:
            raise ViolacaoInvarianteError(
                "EPIC-003",
                f"apenas proposta aprovada gera saida logica ({self.estado.value})",
            )
        if self.aprovada_por_usuario_id is None or self.aprovada_em is None:
            raise ViolacaoInvarianteError(
                "EPIC-003",
                "proposta aprovada deve possuir usuario e instante de aprovacao",
            )
        return PropostaAprovadaLogica(
            proposta_id=self.id,
            tenant_id=self.tenant_id,
            carteira_id=self.carteira_id,
            devedor_id=self.devedor_id,
            parametros_aprovados=self._parametros,
            aprovada_por_usuario_id=self.aprovada_por_usuario_id,
            aprovada_em=self.aprovada_em,
        )

    def _transicionar(
        self,
        *,
        usuario_id: uuid.UUID,
        estado_esperado: PropostaComercialState,
        proximo_estado: PropostaComercialState,
        motivo: str | None = None,
    ) -> None:
        if self.estado is not estado_esperado:
            self._falhar_transicao(proximo_estado)
        self._registrar_decisao(
            usuario_id=usuario_id,
            proximo_estado=proximo_estado,
            motivo=motivo,
        )

    def _registrar_decisao(
        self,
        *,
        usuario_id: uuid.UUID,
        proximo_estado: PropostaComercialState,
        motivo: str | None = None,
    ) -> None:
        _validar_uuid("usuario_id", usuario_id)
        estado_anterior = self.estado
        self.estado = proximo_estado
        decisao = DecisaoComercial(
            proposta_id=self.id,
            usuario_id=usuario_id,
            estado_anterior=estado_anterior,
            estado_posterior=proximo_estado,
            motivo=motivo,
        )
        self._decisoes.append(decisao)
        self._eventos.append(
            evento_from_decisao(
                tenant_id=self.tenant_id,
                carteira_id=self.carteira_id,
                devedor_id=self.devedor_id,
                decisao=decisao,
            )
        )
        self._marcar_atualizado()

    def _falhar_transicao(self, proximo_estado: PropostaComercialState) -> None:
        raise ViolacaoInvarianteError(
            "EPIC-003",
            f"nao e possivel transicionar proposta de {self.estado.value} "
            f"para {proximo_estado.value}",
        )

    def _marcar_atualizado(self) -> None:
        self.atualizado_em = datetime.now(UTC)


def _validar_uuid(campo: str, valor: object) -> None:
    if not isinstance(valor, uuid.UUID):
        raise ViolacaoInvarianteError(
            "EPIC-003",
            f"{campo} deve ser uuid.UUID, recebido {valor!r}",
        )


def _copiar_parametros(parametros: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(parametros, Mapping):
        raise ViolacaoInvarianteError(
            "EPIC-003",
            f"parametros deve ser mapeavel, recebido {parametros!r}",
        )
    if not parametros:
        raise ViolacaoInvarianteError(
            "EPIC-003",
            "parametros comerciais nao podem ser vazios",
        )
    return copy.deepcopy(dict(parametros))
