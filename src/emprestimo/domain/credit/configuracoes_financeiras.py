"""Dominio de Configuracoes Financeiras e Calendario Operacional (EPIC-009)."""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from types import MappingProxyType

from emprestimo.domain.common.errors import ViolacaoInvarianteError

__all__ = [
    "CalendarioFinanceiro",
    "CodigoModalidadeFinanceira",
    "ConfiguracaoFinanceira",
    "ConfiguracaoFinanceiraState",
    "ConfiguracaoFinanceiraVigenteV1",
    "EventoConfiguracaoFinanceira",
    "JanelaVigencia",
    "ModalidadeFinanceira",
    "ParametroFinanceiroConfigurado",
    "PoliticaArredondamento",
    "SnapshotConfiguracaoContratualV1",
    "TaxaFinanceiraConfigurada",
]

EPIC = "EPIC-009"


class ConfiguracaoFinanceiraState(Enum):
    """Estados governados de uma configuracao financeira."""

    RASCUNHO = "rascunho"
    APROVADA = "aprovada"
    PROGRAMADA = "programada"
    ATIVA = "ativa"
    SUBSTITUIDA = "substituida"
    INATIVA = "inativa"


@dataclass(frozen=True)
class CodigoModalidadeFinanceira:
    """Codigo canonico de modalidade financeira."""

    valor: str

    def __post_init__(self) -> None:
        valor = self.valor.strip().lower().replace("-", "_")
        if not valor:
            raise ViolacaoInvarianteError(EPIC, "codigo de modalidade nao pode ser vazio")
        if not valor.replace("_", "").isalnum():
            raise ViolacaoInvarianteError(
                EPIC,
                "codigo de modalidade deve conter apenas letras, numeros ou underscore",
            )
        object.__setattr__(self, "valor", valor)


@dataclass(frozen=True)
class JanelaVigencia:
    """Janela de vigencia sem retroatividade implicita."""

    inicio: date
    fim: date | None = None

    def __post_init__(self) -> None:
        _validar_data("inicio", self.inicio)
        if self.fim is not None:
            _validar_data("fim", self.fim)
            if self.fim <= self.inicio:
                raise ViolacaoInvarianteError(
                    EPIC,
                    "fim da vigencia deve ser posterior ao inicio",
                )

    def contem(self, data_referencia: date) -> bool:
        _validar_data("data_referencia", data_referencia)
        return self.inicio <= data_referencia and (self.fim is None or data_referencia < self.fim)


@dataclass(frozen=True)
class TaxaFinanceiraConfigurada:
    """Taxa permitida para o Motor consumir posteriormente."""

    nome: str
    valor: Decimal
    periodicidade: str

    def __post_init__(self) -> None:
        nome = self.nome.strip().lower()
        periodicidade = self.periodicidade.strip().lower()
        if not nome:
            raise ViolacaoInvarianteError(EPIC, "nome da taxa nao pode ser vazio")
        _validar_decimal("valor", self.valor)
        if self.valor < Decimal("0.00"):
            raise ViolacaoInvarianteError(EPIC, "valor da taxa nao pode ser negativo")
        if not periodicidade:
            raise ViolacaoInvarianteError(EPIC, "periodicidade da taxa nao pode ser vazia")
        object.__setattr__(self, "nome", nome)
        object.__setattr__(self, "periodicidade", periodicidade)


@dataclass(frozen=True)
class ParametroFinanceiroConfigurado:
    """Parametro financeiro governado, sem formula livre."""

    nome: str
    valor: object

    def __post_init__(self) -> None:
        nome = self.nome.strip().lower()
        if not nome:
            raise ViolacaoInvarianteError(EPIC, "nome do parametro nao pode ser vazio")
        if isinstance(self.valor, float):
            raise ViolacaoInvarianteError(EPIC, "parametro financeiro nao aceita float")
        _normalizar_valor(self.valor)
        object.__setattr__(self, "nome", nome)


@dataclass(frozen=True)
class PoliticaArredondamento:
    """Politica declarativa de arredondamento consumivel pelo Motor."""

    modo: str
    escala: int

    def __post_init__(self) -> None:
        modo = self.modo.strip().lower()
        if modo not in {"half_up", "half_even", "down"}:
            raise ViolacaoInvarianteError(EPIC, f"modo de arredondamento invalido: {modo!r}")
        if not isinstance(self.escala, int) or self.escala < 0:
            raise ViolacaoInvarianteError(EPIC, "escala de arredondamento deve ser inteira")
        object.__setattr__(self, "modo", modo)


@dataclass(frozen=True)
class ModalidadeFinanceira:
    """Modalidade disponivel para um tenant/carteira."""

    tenant_id: uuid.UUID
    codigo: CodigoModalidadeFinanceira
    nome: str
    carteira_id: uuid.UUID | None = None
    ativa: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("id", self.id)
        if self.carteira_id is not None:
            _validar_uuid("carteira_id", self.carteira_id)
        if not self.nome.strip():
            raise ViolacaoInvarianteError(EPIC, "nome da modalidade nao pode ser vazio")


@dataclass(frozen=True)
class CalendarioFinanceiro:
    """Calendario operacional para datas de referencia."""

    tenant_id: uuid.UUID
    codigo: str
    nome: str
    feriados: tuple[date, ...] = ()
    carteira_id: uuid.UUID | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("id", self.id)
        if self.carteira_id is not None:
            _validar_uuid("carteira_id", self.carteira_id)
        if not self.codigo.strip():
            raise ViolacaoInvarianteError(EPIC, "codigo do calendario nao pode ser vazio")
        if not self.nome.strip():
            raise ViolacaoInvarianteError(EPIC, "nome do calendario nao pode ser vazio")
        for feriado in self.feriados:
            _validar_data("feriado", feriado)

    def resolver_periodo(self, data_referencia: date) -> dict[str, object]:
        _validar_data("data_referencia", data_referencia)
        return {
            "calendario_id": str(self.id),
            "data_referencia": data_referencia.isoformat(),
            "eh_feriado": data_referencia in self.feriados,
        }


@dataclass(frozen=True)
class EventoConfiguracaoFinanceira:
    """Evento de auditoria da configuracao financeira."""

    tipo: str
    tenant_id: uuid.UUID
    configuracao_id: uuid.UUID
    usuario_id: uuid.UUID
    ocorrido_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    carteira_id: uuid.UUID | None = None
    motivo: str | None = None
    versao_anterior: int | None = None
    versao_nova: int | None = None
    correlation_id: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        for campo in ("tenant_id", "configuracao_id", "usuario_id", "id"):
            _validar_uuid(campo, getattr(self, campo))
        if self.carteira_id is not None:
            _validar_uuid("carteira_id", self.carteira_id)
        if not self.tipo.strip():
            raise ViolacaoInvarianteError(EPIC, "tipo do evento nao pode ser vazio")
        if self.versao_nova is not None and self.versao_nova < 1:
            raise ViolacaoInvarianteError(EPIC, "versao nova deve ser positiva")


@dataclass(frozen=True)
class ConfiguracaoFinanceiraVigenteV1:
    """Contrato de leitura da configuracao vigente."""

    configuracao_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None
    modalidade: str
    versao: int
    vigencia: JanelaVigencia
    parametros: Mapping[str, object]
    consultada_em: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "parametros", _congelar_mapping(self.parametros))


@dataclass(frozen=True)
class SnapshotConfiguracaoContratualV1:
    """Snapshot imutavel que Contratos congela para o Motor consumir."""

    configuracao_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None
    modalidade: str
    versao: int
    parametros: Mapping[str, object]
    hash_parametros: str
    capturado_em: datetime
    capturado_por_usuario_id: uuid.UUID
    motivo: str | None = None

    def __post_init__(self) -> None:
        _validar_uuid("configuracao_id", self.configuracao_id)
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("capturado_por_usuario_id", self.capturado_por_usuario_id)
        if self.carteira_id is not None:
            _validar_uuid("carteira_id", self.carteira_id)
        parametros = _congelar_mapping(self.parametros)
        hash_parametros = _hash_parametros(parametros)
        if self.hash_parametros != hash_parametros:
            raise ViolacaoInvarianteError(EPIC, "hash do snapshot nao confere")
        object.__setattr__(self, "parametros", parametros)

    def to_dict(self) -> dict[str, object]:
        return {
            "configuracao_id": str(self.configuracao_id),
            "tenant_id": str(self.tenant_id),
            "carteira_id": str(self.carteira_id) if self.carteira_id else None,
            "modalidade": self.modalidade,
            "versao": self.versao,
            "parametros": _descongelar(self.parametros),
            "hash_parametros": self.hash_parametros,
            "capturado_em": self.capturado_em.isoformat(),
            "capturado_por_usuario_id": str(self.capturado_por_usuario_id),
            "motivo": self.motivo,
        }


@dataclass
class ConfiguracaoFinanceira:
    """Aggregate de configuracao financeira versionada."""

    tenant_id: uuid.UUID
    modalidade: CodigoModalidadeFinanceira
    calendario_id: uuid.UUID
    vigencia: JanelaVigencia
    taxas: tuple[TaxaFinanceiraConfigurada, ...]
    parametros: tuple[ParametroFinanceiroConfigurado, ...]
    politica_arredondamento: PoliticaArredondamento
    criada_por_usuario_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    estado: ConfiguracaoFinanceiraState = ConfiguracaoFinanceiraState.RASCUNHO
    versao: int = 1
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criada_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizada_em: datetime | None = None
    aprovada_por_usuario_id: uuid.UUID | None = None
    aprovada_em: datetime | None = None
    programada_para: date | None = None
    ativada_em: datetime | None = None
    substituida_em: datetime | None = None
    inativada_em: datetime | None = None
    _eventos: list[EventoConfiguracaoFinanceira] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        for campo in ("tenant_id", "calendario_id", "criada_por_usuario_id", "id"):
            _validar_uuid(campo, getattr(self, campo))
        if self.carteira_id is not None:
            _validar_uuid("carteira_id", self.carteira_id)
        if not isinstance(self.estado, ConfiguracaoFinanceiraState):
            raise ViolacaoInvarianteError(EPIC, "estado de configuracao invalido")
        if self.versao < 1:
            raise ViolacaoInvarianteError(EPIC, "versao deve ser positiva")
        if not self.taxas:
            raise ViolacaoInvarianteError(EPIC, "configuracao deve possuir ao menos uma taxa")
        if not self.parametros:
            raise ViolacaoInvarianteError(
                EPIC,
                "configuracao deve possuir ao menos um parametro financeiro",
            )

    @classmethod
    def criar_rascunho(
        cls,
        *,
        tenant_id: uuid.UUID,
        modalidade: CodigoModalidadeFinanceira,
        calendario_id: uuid.UUID,
        vigencia: JanelaVigencia,
        taxas: tuple[TaxaFinanceiraConfigurada, ...],
        parametros: tuple[ParametroFinanceiroConfigurado, ...],
        politica_arredondamento: PoliticaArredondamento,
        criada_por_usuario_id: uuid.UUID,
        carteira_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
    ) -> ConfiguracaoFinanceira:
        configuracao = cls(
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            modalidade=modalidade,
            calendario_id=calendario_id,
            vigencia=vigencia,
            taxas=taxas,
            parametros=parametros,
            politica_arredondamento=politica_arredondamento,
            criada_por_usuario_id=criada_por_usuario_id,
        )
        configuracao._registrar_evento(
            tipo="configuracao_financeira.criada",
            usuario_id=criada_por_usuario_id,
            versao_nova=configuracao.versao,
            correlation_id=correlation_id,
        )
        return configuracao

    @property
    def eventos(self) -> tuple[EventoConfiguracaoFinanceira, ...]:
        return tuple(self._eventos)

    @property
    def parametros_normalizados(self) -> dict[str, object]:
        dados = {
            parametro.nome: _normalizar_valor(parametro.valor) for parametro in self.parametros
        }
        for taxa in self.taxas:
            dados[taxa.nome] = {
                "valor": str(taxa.valor),
                "periodicidade": taxa.periodicidade,
            }
        dados["politica_arredondamento"] = {
            "modo": self.politica_arredondamento.modo,
            "escala": self.politica_arredondamento.escala,
        }
        dados["calendario_id"] = str(self.calendario_id)
        return copy.deepcopy(dados)

    def aprovar(
        self,
        *,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self._exigir_estado(ConfiguracaoFinanceiraState.RASCUNHO)
        self.estado = ConfiguracaoFinanceiraState.APROVADA
        self.aprovada_por_usuario_id = usuario_id
        self.aprovada_em = datetime.now(UTC)
        self._marcar_atualizado()
        self._registrar_evento(
            tipo="configuracao_financeira.aprovada",
            usuario_id=usuario_id,
            motivo=motivo,
            versao_anterior=self.versao,
            versao_nova=self.versao,
            correlation_id=correlation_id,
        )

    def programar(
        self,
        *,
        usuario_id: uuid.UUID,
        data_ativacao: date,
        motivo: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self._exigir_estado(ConfiguracaoFinanceiraState.APROVADA)
        if data_ativacao < self.vigencia.inicio:
            raise ViolacaoInvarianteError(EPIC, "ativacao nao pode anteceder a vigencia")
        self.estado = ConfiguracaoFinanceiraState.PROGRAMADA
        self.programada_para = data_ativacao
        self._marcar_atualizado()
        self._registrar_evento(
            tipo="configuracao_financeira.programada",
            usuario_id=usuario_id,
            motivo=motivo,
            versao_anterior=self.versao,
            versao_nova=self.versao,
            correlation_id=correlation_id,
        )

    def ativar(
        self,
        *,
        usuario_id: uuid.UUID,
        ativada_em: datetime | None = None,
        motivo: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        if self.estado not in {
            ConfiguracaoFinanceiraState.APROVADA,
            ConfiguracaoFinanceiraState.PROGRAMADA,
        }:
            self._falhar_transicao(ConfiguracaoFinanceiraState.ATIVA)
        self.estado = ConfiguracaoFinanceiraState.ATIVA
        self.ativada_em = ativada_em or datetime.now(UTC)
        self._marcar_atualizado()
        self._registrar_evento(
            tipo="configuracao_financeira.ativada",
            usuario_id=usuario_id,
            motivo=motivo,
            versao_anterior=self.versao,
            versao_nova=self.versao,
            correlation_id=correlation_id,
        )

    def substituir(
        self,
        *,
        usuario_id: uuid.UUID,
        substituida_em: datetime | None = None,
        motivo: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self._exigir_estado(ConfiguracaoFinanceiraState.ATIVA)
        self.estado = ConfiguracaoFinanceiraState.SUBSTITUIDA
        self.substituida_em = substituida_em or datetime.now(UTC)
        self._marcar_atualizado()
        self._registrar_evento(
            tipo="configuracao_financeira.substituida",
            usuario_id=usuario_id,
            motivo=motivo,
            versao_anterior=self.versao,
            versao_nova=self.versao,
            correlation_id=correlation_id,
        )

    def inativar(
        self,
        *,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        if self.estado not in {
            ConfiguracaoFinanceiraState.APROVADA,
            ConfiguracaoFinanceiraState.PROGRAMADA,
            ConfiguracaoFinanceiraState.ATIVA,
        }:
            self._falhar_transicao(ConfiguracaoFinanceiraState.INATIVA)
        self.estado = ConfiguracaoFinanceiraState.INATIVA
        self.inativada_em = datetime.now(UTC)
        self._marcar_atualizado()
        self._registrar_evento(
            tipo="configuracao_financeira.inativada",
            usuario_id=usuario_id,
            motivo=motivo,
            versao_anterior=self.versao,
            versao_nova=self.versao,
            correlation_id=correlation_id,
        )

    def esta_vigente(self, data_referencia: date) -> bool:
        return self.estado is ConfiguracaoFinanceiraState.ATIVA and self.vigencia.contem(
            data_referencia
        )

    def gerar_vigente(
        self, *, consultada_em: datetime | None = None
    ) -> ConfiguracaoFinanceiraVigenteV1:
        self._exigir_estado(ConfiguracaoFinanceiraState.ATIVA)
        return ConfiguracaoFinanceiraVigenteV1(
            configuracao_id=self.id,
            tenant_id=self.tenant_id,
            carteira_id=self.carteira_id,
            modalidade=self.modalidade.valor,
            versao=self.versao,
            vigencia=self.vigencia,
            parametros=self.parametros_normalizados,
            consultada_em=consultada_em or datetime.now(UTC),
        )

    def capturar_snapshot(
        self,
        *,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        capturado_em: datetime | None = None,
        correlation_id: str | None = None,
    ) -> SnapshotConfiguracaoContratualV1:
        self._exigir_estado(ConfiguracaoFinanceiraState.ATIVA)
        parametros = self.parametros_normalizados
        snapshot = SnapshotConfiguracaoContratualV1(
            configuracao_id=self.id,
            tenant_id=self.tenant_id,
            carteira_id=self.carteira_id,
            modalidade=self.modalidade.valor,
            versao=self.versao,
            parametros=parametros,
            hash_parametros=_hash_parametros(parametros),
            capturado_em=capturado_em or datetime.now(UTC),
            capturado_por_usuario_id=usuario_id,
            motivo=motivo,
        )
        self._registrar_evento(
            tipo="configuracao_financeira.snapshot_capturado",
            usuario_id=usuario_id,
            motivo=motivo,
            versao_anterior=self.versao,
            versao_nova=self.versao,
            correlation_id=correlation_id,
        )
        return snapshot

    def _exigir_estado(self, estado: ConfiguracaoFinanceiraState) -> None:
        if self.estado is not estado:
            self._falhar_transicao(estado)

    def _falhar_transicao(self, proximo_estado: ConfiguracaoFinanceiraState) -> None:
        raise ViolacaoInvarianteError(
            EPIC,
            f"nao e possivel transicionar configuracao de {self.estado.value} "
            f"para {proximo_estado.value}",
        )

    def _registrar_evento(
        self,
        *,
        tipo: str,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        versao_anterior: int | None = None,
        versao_nova: int | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self._eventos.append(
            EventoConfiguracaoFinanceira(
                tipo=tipo,
                tenant_id=self.tenant_id,
                carteira_id=self.carteira_id,
                configuracao_id=self.id,
                usuario_id=usuario_id,
                motivo=motivo,
                versao_anterior=versao_anterior,
                versao_nova=versao_nova,
                correlation_id=correlation_id,
            )
        )

    def _marcar_atualizado(self) -> None:
        self.atualizada_em = datetime.now(UTC)


def _validar_uuid(campo: str, valor: object) -> None:
    if not isinstance(valor, uuid.UUID):
        raise ViolacaoInvarianteError(EPIC, f"{campo} deve ser uuid.UUID, recebido {valor!r}")


def _validar_data(campo: str, valor: object) -> None:
    if not isinstance(valor, date):
        raise ViolacaoInvarianteError(EPIC, f"{campo} deve ser date, recebido {valor!r}")


def _validar_decimal(campo: str, valor: object) -> None:
    if not isinstance(valor, Decimal):
        raise ViolacaoInvarianteError(EPIC, f"{campo} deve ser Decimal, recebido {valor!r}")


def _normalizar_valor(valor: object) -> object:
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, Mapping):
        return {str(chave): _normalizar_valor(item) for chave, item in valor.items()}
    if isinstance(valor, tuple | list):
        return [_normalizar_valor(item) for item in valor]
    if isinstance(valor, str | int | bool) or valor is None:
        return valor
    raise ViolacaoInvarianteError(
        EPIC,
        f"tipo de parametro financeiro nao suportado: {type(valor).__name__}",
    )


def _congelar_mapping(parametros: Mapping[str, object]) -> Mapping[str, object]:
    normalizados = {
        str(chave): _congelar(_normalizar_valor(valor)) for chave, valor in parametros.items()
    }
    return MappingProxyType(normalizados)


def _congelar(valor: object) -> object:
    if isinstance(valor, Mapping):
        return _congelar_mapping(valor)
    if isinstance(valor, list | tuple):
        return tuple(_congelar(item) for item in valor)
    return copy.deepcopy(valor)


def _descongelar(valor: object) -> object:
    if isinstance(valor, Mapping):
        return {str(chave): _descongelar(item) for chave, item in valor.items()}
    if isinstance(valor, tuple):
        return [_descongelar(item) for item in valor]
    return copy.deepcopy(valor)


def _hash_parametros(parametros: Mapping[str, object]) -> str:
    payload = json.dumps(_descongelar(parametros), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
