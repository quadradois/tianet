"""Contrato de Credito (EPIC-004)."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.domain.credit.contrato_liberado import ContratoLiberadoLogico
from emprestimo.domain.credit.decisao_contrato import DecisaoContrato
from emprestimo.domain.credit.eventos_contrato import EventoContrato, evento_from_decisao
from emprestimo.domain.credit.proposta_aprovada import PropostaAprovadaLogica

__all__ = ["ContratoCredito", "ContratoCreditoState", "ContratoLiberadoLogico"]

ESTADOS_IMUTAVEIS = frozenset(
    {
        ContratoCreditoState.FORMALIZADO,
        ContratoCreditoState.ASSINADO,
        ContratoCreditoState.LIBERADO_PARA_MOTOR,
        ContratoCreditoState.CANCELADO,
        ContratoCreditoState.ENCERRADO,
    }
)


@dataclass
class ContratoCredito:
    """Aggregate Root do contexto Contratos."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    proposta_comercial_id: uuid.UUID
    criado_por_usuario_id: uuid.UUID
    _parametros: dict[str, object]
    estado: ContratoCreditoState = ContratoCreditoState.RASCUNHO
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None
    formalizado_por_usuario_id: uuid.UUID | None = None
    formalizado_em: datetime | None = None
    assinado_por_usuario_id: uuid.UUID | None = None
    assinado_em: datetime | None = None
    liberado_por_usuario_id: uuid.UUID | None = None
    liberado_em: datetime | None = None
    motivo_encerramento: str | None = None
    _decisoes: list[DecisaoContrato] = field(default_factory=list, init=False, repr=False)
    _eventos: list[EventoContrato] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        for campo in (
            "tenant_id",
            "carteira_id",
            "devedor_id",
            "proposta_comercial_id",
            "criado_por_usuario_id",
            "id",
        ):
            _validar_uuid(campo, getattr(self, campo))
        if not isinstance(self.estado, ContratoCreditoState):
            raise ViolacaoInvarianteError(
                "EPIC-004",
                f"estado deve ser ContratoCreditoState, recebido {self.estado!r}",
            )
        self._parametros = _copiar_parametros(self._parametros)

    @classmethod
    def criar_de_proposta_aprovada(
        cls,
        *,
        proposta: PropostaAprovadaLogica,
        criado_por_usuario_id: uuid.UUID,
    ) -> ContratoCredito:
        contrato = cls(
            tenant_id=proposta.tenant_id,
            carteira_id=proposta.carteira_id,
            devedor_id=proposta.devedor_id,
            proposta_comercial_id=proposta.proposta_id,
            criado_por_usuario_id=criado_por_usuario_id,
            _parametros=_copiar_parametros(proposta.parametros_aprovados),
        )
        contrato._registrar_decisao(
            usuario_id=criado_por_usuario_id,
            tipo="criado",
            estado_anterior=ContratoCreditoState.RASCUNHO,
            estado_posterior=ContratoCreditoState.RASCUNHO,
        )
        return contrato

    @classmethod
    def restaurar(
        cls,
        *,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        proposta_comercial_id: uuid.UUID,
        criado_por_usuario_id: uuid.UUID,
        parametros: Mapping[str, object],
        estado: ContratoCreditoState,
        criado_em: datetime,
        atualizado_em: datetime | None,
        formalizado_por_usuario_id: uuid.UUID | None,
        formalizado_em: datetime | None,
        assinado_por_usuario_id: uuid.UUID | None,
        assinado_em: datetime | None,
        liberado_por_usuario_id: uuid.UUID | None,
        liberado_em: datetime | None,
        motivo_encerramento: str | None,
        decisoes: list[DecisaoContrato] | None = None,
    ) -> ContratoCredito:
        contrato = cls(
            id=id,
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            proposta_comercial_id=proposta_comercial_id,
            criado_por_usuario_id=criado_por_usuario_id,
            _parametros=_copiar_parametros(parametros),
            estado=estado,
            criado_em=criado_em,
            atualizado_em=atualizado_em,
            formalizado_por_usuario_id=formalizado_por_usuario_id,
            formalizado_em=formalizado_em,
            assinado_por_usuario_id=assinado_por_usuario_id,
            assinado_em=assinado_em,
            liberado_por_usuario_id=liberado_por_usuario_id,
            liberado_em=liberado_em,
            motivo_encerramento=motivo_encerramento,
        )
        contrato._decisoes = list(decisoes or [])
        contrato._eventos = [
            evento_from_decisao(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                devedor_id=devedor_id,
                decisao=decisao,
            )
            for decisao in contrato._decisoes
        ]
        return contrato

    @property
    def parametros(self) -> dict[str, object]:
        return copy.deepcopy(self._parametros)

    @property
    def decisoes(self) -> tuple[DecisaoContrato, ...]:
        return tuple(self._decisoes)

    @property
    def eventos(self) -> tuple[EventoContrato, ...]:
        return tuple(self._eventos)

    def atualizar_parametros(self, parametros: Mapping[str, object]) -> None:
        if self.estado in ESTADOS_IMUTAVEIS:
            raise ViolacaoInvarianteError(
                "EPIC-004",
                f"contrato nao permite alterar parametros em {self.estado.value}",
            )
        self._parametros = _copiar_parametros(parametros)
        self._marcar_atualizado()

    def formalizar(self, *, usuario_id: uuid.UUID) -> None:
        self._transicionar(
            usuario_id=usuario_id,
            permitido={ContratoCreditoState.RASCUNHO},
            proximo_estado=ContratoCreditoState.FORMALIZADO,
        )
        self.formalizado_por_usuario_id = usuario_id
        self.formalizado_em = datetime.now(UTC)

    def assinar(self, *, usuario_id: uuid.UUID) -> None:
        self._transicionar(
            usuario_id=usuario_id,
            permitido={ContratoCreditoState.FORMALIZADO},
            proximo_estado=ContratoCreditoState.ASSINADO,
        )
        self.assinado_por_usuario_id = usuario_id
        self.assinado_em = datetime.now(UTC)

    def liberar_para_motor(self, *, usuario_id: uuid.UUID) -> ContratoLiberadoLogico:
        self._transicionar(
            usuario_id=usuario_id,
            permitido={ContratoCreditoState.ASSINADO},
            proximo_estado=ContratoCreditoState.LIBERADO_PARA_MOTOR,
        )
        self.liberado_por_usuario_id = usuario_id
        self.liberado_em = datetime.now(UTC)
        return self.gerar_saida_logica()

    def cancelar(self, *, usuario_id: uuid.UUID, motivo: str | None = None) -> None:
        self._transicionar(
            usuario_id=usuario_id,
            permitido={ContratoCreditoState.RASCUNHO, ContratoCreditoState.FORMALIZADO},
            proximo_estado=ContratoCreditoState.CANCELADO,
            motivo=motivo,
        )
        self.motivo_encerramento = motivo

    def encerrar(self, *, usuario_id: uuid.UUID, motivo: str | None = None) -> None:
        self._transicionar(
            usuario_id=usuario_id,
            permitido={ContratoCreditoState.ASSINADO, ContratoCreditoState.LIBERADO_PARA_MOTOR},
            proximo_estado=ContratoCreditoState.ENCERRADO,
            motivo=motivo,
        )
        self.motivo_encerramento = motivo

    def gerar_saida_logica(self) -> ContratoLiberadoLogico:
        if self.estado is not ContratoCreditoState.LIBERADO_PARA_MOTOR:
            raise ViolacaoInvarianteError(
                "EPIC-004",
                f"apenas contrato liberado gera saida logica ({self.estado.value})",
            )
        if self.liberado_por_usuario_id is None or self.liberado_em is None:
            raise ViolacaoInvarianteError(
                "EPIC-004",
                "contrato liberado deve possuir usuario e instante de liberacao",
            )
        return ContratoLiberadoLogico(
            contrato_id=self.id,
            proposta_comercial_id=self.proposta_comercial_id,
            tenant_id=self.tenant_id,
            carteira_id=self.carteira_id,
            devedor_id=self.devedor_id,
            parametros_contratados=self._parametros,
            liberado_por_usuario_id=self.liberado_por_usuario_id,
            liberado_em=self.liberado_em,
        )

    def _transicionar(
        self,
        *,
        usuario_id: uuid.UUID,
        permitido: set[ContratoCreditoState],
        proximo_estado: ContratoCreditoState,
        motivo: str | None = None,
    ) -> None:
        _validar_uuid("usuario_id", usuario_id)
        if self.estado not in permitido:
            raise ViolacaoInvarianteError(
                "EPIC-004",
                f"nao e possivel transicionar contrato de {self.estado.value} "
                f"para {proximo_estado.value}",
            )
        estado_anterior = self.estado
        self.estado = proximo_estado
        self._registrar_decisao(
            usuario_id=usuario_id,
            tipo=proximo_estado.value,
            estado_anterior=estado_anterior,
            estado_posterior=proximo_estado,
            motivo=motivo,
        )
        self._marcar_atualizado()

    def _registrar_decisao(
        self,
        *,
        usuario_id: uuid.UUID,
        tipo: str,
        estado_anterior: ContratoCreditoState,
        estado_posterior: ContratoCreditoState,
        motivo: str | None = None,
    ) -> None:
        decisao = DecisaoContrato(
            contrato_id=self.id,
            usuario_id=usuario_id,
            tipo=tipo,
            estado_anterior=estado_anterior,
            estado_posterior=estado_posterior,
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

    def _marcar_atualizado(self) -> None:
        self.atualizado_em = datetime.now(UTC)


def _validar_uuid(campo: str, valor: object) -> None:
    if not isinstance(valor, uuid.UUID):
        raise ViolacaoInvarianteError(
            "EPIC-004",
            f"{campo} deve ser uuid.UUID, recebido {valor!r}",
        )


def _copiar_parametros(parametros: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(parametros, Mapping):
        raise ViolacaoInvarianteError(
            "EPIC-004",
            f"parametros deve ser mapeavel, recebido {parametros!r}",
        )
    if not parametros:
        raise ViolacaoInvarianteError("EPIC-004", "parametros contratuais nao podem ser vazios")
    return copy.deepcopy(dict(parametros))
