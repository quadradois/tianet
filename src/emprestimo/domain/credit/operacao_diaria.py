"""Modelos de dominio transacionais da operacao diaria (EPIC-007/P1)."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from emprestimo.domain.common.errors import ViolacaoInvarianteError

__all__ = [
    "AgendaItem",
    "CanalComunicacao",
    "CobrancaCaso",
    "CompromissoAgenda",
    "EstadoCobranca",
    "EstadoCompromisso",
    "EstadoLembrete",
    "EstadoOperacional",
    "HistoricoComunicacao",
    "JanelaAgenda",
    "Lembrete",
    "RegistroComunicacao",
    "RelatorioOperacionalCache",
    "ResumoCarteira",
    "TipoAcaoCobranca",
    "VencimentoOperacional",
]


class TipoAcaoCobranca(StrEnum):
    """Tipos de acao manual de cobranca."""

    CONTATO = "contato"
    TELEFONE = "telefone"
    EMAIL = "email"
    VISITA = "visita"
    OUTRO = "outro"


class EstadoOperacional(StrEnum):
    """Estados base para registros operacionais."""

    ATIVO = "ativo"
    INATIVO = "inativo"


class EstadoCompromisso(StrEnum):
    """Estados do compromisso operacional."""

    ABERTO = "aberto"
    REAGENDADO = "reagendado"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


class EstadoLembrete(StrEnum):
    """Estado de processamento do lembrete."""

    PROGRAMA = "programa"
    ENVIADO = "enviado"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


class EstadoCobranca(StrEnum):
    """Estados do caso de cobranca."""

    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    ENCERRADO = "encerrado"


class CanalComunicacao(StrEnum):
    """Canais operacionais de comunicacao."""

    TELEFONE = "telefone"
    EMAIL = "email"
    CHAT = "chat"
    PRESENCIAL = "presencial"


@dataclass
class CobrancaCaso:
    """Aggregate de acompanhamento principal da cobranca manual."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    titulo: str
    origem: str
    estado: EstadoCobranca = EstadoCobranca.PENDENTE
    emprestimo_id: uuid.UUID | None = None
    total_pendente: Decimal = Decimal("0.00")
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        _validar_uuid("devedor_id", self.devedor_id)
        if self.emprestimo_id is not None:
            _validar_uuid("emprestimo_id", self.emprestimo_id)
        if not isinstance(self.estado, EstadoCobranca):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"estado de cobranca invalido: {self.estado!r}",
            )
        if not self.titulo.strip():
            raise ViolacaoInvarianteError("EPIC-007", "titulo da cobranca e obrigatorio")
        if not self.origem.strip():
            raise ViolacaoInvarianteError("EPIC-007", "origem da cobranca e obrigatoria")
        if not isinstance(self.total_pendente, Decimal):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"total_pendente deve ser Decimal, recebido {self.total_pendente!r}",
            )
        if self.total_pendente < Decimal("0.00"):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "total_pendente nao pode ser negativo",
            )


@dataclass
class AcaoCobranca:
    """Acao de cobranca manual registrada por usuario."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    cobranca_caso_id: uuid.UUID
    emprestimo_id: uuid.UUID
    criado_por_usuario_id: uuid.UUID
    tipo: TipoAcaoCobranca
    resultado: str
    devedor_id: uuid.UUID | None = None
    parcela_id: uuid.UUID | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    registrada_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    estado: EstadoOperacional = EstadoOperacional.ATIVO

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        _validar_uuid("cobranca_caso_id", self.cobranca_caso_id)
        _validar_uuid("emprestimo_id", self.emprestimo_id)
        _validar_uuid("criado_por_usuario_id", self.criado_por_usuario_id)
        if self.devedor_id is not None:
            _validar_uuid("devedor_id", self.devedor_id)
        if self.parcela_id is not None:
            _validar_uuid("parcela_id", self.parcela_id)
        if not isinstance(self.tipo, TipoAcaoCobranca):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"tipo de acao invalido: {self.tipo!r}",
            )
        if not self.resultado.strip():
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "resultado da acao e obrigatorio",
            )

    def atualizar_resultado(self, *, usuario_id: uuid.UUID, resultado: str) -> None:
        """Atualiza o resultado da acao em cadeia de contato."""

        _validar_uuid("usuario_id", usuario_id)
        if self.estado is not EstadoOperacional.ATIVO:
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "acao inativa nao pode ser atualizada",
            )
        if not resultado.strip():
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "resultado nao pode ser vazio",
            )
        self.resultado = resultado
        self.registrada_em = datetime.now(UTC)


@dataclass
class CompromissoAgenda:
    """Compromisso operacional de carteira/agenda."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    usuario_solicitante_id: uuid.UUID
    titulo: str
    previsto_para: datetime
    devedor_id: uuid.UUID | None = None
    emprestimo_id: uuid.UUID | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    estado: EstadoCompromisso = EstadoCompromisso.ABERTO
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        if self.devedor_id is not None:
            _validar_uuid("devedor_id", self.devedor_id)
        _validar_uuid("usuario_solicitante_id", self.usuario_solicitante_id)
        if self.emprestimo_id is not None:
            _validar_uuid("emprestimo_id", self.emprestimo_id)
        if not self.titulo.strip():
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "titulo de compromisso e obrigatorio",
            )
        if self.estado is not EstadoCompromisso.ABERTO:
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"estado inicial invalido: {self.estado.value}",
            )
        if self.previsto_para < datetime.now(UTC):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "data de compromisso deve ser no futuro",
            )

    def reagendar(self, *, novo_horario: datetime) -> None:
        """Reagenda compromisso para novo horario."""

        if self.estado in (EstadoCompromisso.CONCLUIDO, EstadoCompromisso.CANCELADO):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"nao e possivel reagendar compromisso {self.estado.value}",
            )
        if novo_horario < datetime.now(UTC):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "novo horario nao pode ser no passado",
            )
        self.previsto_para = novo_horario
        self.estado = EstadoCompromisso.REAGENDADO
        self.atualizado_em = datetime.now(UTC)

    def concluir(self) -> None:
        """Marca compromisso como concluido."""

        if self.estado is EstadoCompromisso.CANCELADO:
            raise ViolacaoInvarianteError("EPIC-007", "compromisso cancelado")
        self.estado = EstadoCompromisso.CONCLUIDO
        self.atualizado_em = datetime.now(UTC)

    def cancelar(self) -> None:
        """Marca compromisso como cancelado."""

        if self.estado is EstadoCompromisso.CONCLUIDO:
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "compromisso concluido nao pode ser cancelado",
            )
        self.estado = EstadoCompromisso.CANCELADO
        self.atualizado_em = datetime.now(UTC)


@dataclass
class AgendaItem:
    """Alias semantico de item de agenda da operacao diaria."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    usuario_solicitante_id: uuid.UUID
    titulo: str
    previsto_para: datetime
    emprestimo_id: uuid.UUID | None = None
    estado: EstadoCompromisso = EstadoCompromisso.ABERTO
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        _validar_uuid("devedor_id", self.devedor_id)
        _validar_uuid("usuario_solicitante_id", self.usuario_solicitante_id)
        _validar_uuid("id", self.id)
        if self.emprestimo_id is not None:
            _validar_uuid("emprestimo_id", self.emprestimo_id)
        if not self.titulo.strip():
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "titulo de compromisso e obrigatorio",
            )
        if not isinstance(self.estado, EstadoCompromisso):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"estado de compromisso invalido: {self.estado!r}",
            )
        if self.estado is EstadoCompromisso.ABERTO and self.previsto_para < datetime.now(UTC):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "data de compromisso deve ser no futuro",
            )

    def reagendar(self, *, novo_horario: datetime) -> None:
        if self.estado in (EstadoCompromisso.CONCLUIDO, EstadoCompromisso.CANCELADO):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"nao e possivel reagendar compromisso {self.estado.value}",
            )
        if novo_horario < datetime.now(UTC):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "novo horario nao pode ser no passado",
            )
        self.previsto_para = novo_horario
        self.estado = EstadoCompromisso.REAGENDADO
        self.atualizado_em = datetime.now(UTC)

    def concluir(self) -> None:
        if self.estado is EstadoCompromisso.CANCELADO:
            raise ViolacaoInvarianteError("EPIC-007", "compromisso cancelado")
        self.estado = EstadoCompromisso.CONCLUIDO
        self.atualizado_em = datetime.now(UTC)

    def cancelar(self) -> None:
        if self.estado is EstadoCompromisso.CONCLUIDO:
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "compromisso concluido nao pode ser cancelado",
            )
        self.estado = EstadoCompromisso.CANCELADO
        self.atualizado_em = datetime.now(UTC)


@dataclass
class Lembrete:
    """Lembrete associado a compromisso."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    horario: datetime
    enviado_por_usuario_id: uuid.UUID
    mensagem: str
    agenda_item_id: uuid.UUID | None = None
    compromisso_id: uuid.UUID | None = None
    estado: EstadoLembrete = EstadoLembrete.PROGRAMA
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        if self.agenda_item_id is None and self.compromisso_id is not None:
            self.agenda_item_id = self.compromisso_id
        elif self.compromisso_id is None and self.agenda_item_id is not None:
            self.compromisso_id = self.agenda_item_id
        elif self.agenda_item_id != self.compromisso_id:
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "compromisso_id e agenda_item_id devem ser o mesmo identificador",
            )
        if self.compromisso_id is None:
            raise ViolacaoInvarianteError("EPIC-007", "compromisso_id e obrigatorio")
        _validar_uuid("agenda_item_id", self.agenda_item_id)
        _validar_uuid("enviado_por_usuario_id", self.enviado_por_usuario_id)
        if not self.mensagem.strip():
            raise ViolacaoInvarianteError("EPIC-007", "mensagem do lembrete e obrigatoria")

    def enviar(self) -> None:
        """Marca lembrete como enviado."""

        self._exigir_programado("enviado")
        self.estado = EstadoLembrete.ENVIADO

    def concluir(self) -> None:
        """Marca lembrete como concluido sem confundir com envio."""

        self._exigir_programado("concluido")
        self.estado = EstadoLembrete.CONCLUIDO

    def cancelar(self) -> None:
        """Marca lembrete como cancelado."""

        self._exigir_programado("cancelado")
        self.estado = EstadoLembrete.CANCELADO

    def _exigir_programado(self, acao: str) -> None:
        if self.estado is not EstadoLembrete.PROGRAMA:
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"lembrete {self.estado.value} nao pode ser {acao}",
            )


@dataclass(frozen=True)
class RegistroComunicacao:
    """Entrada imutavel de comunicacao manual."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    responsavel_id: uuid.UUID
    canal: CanalComunicacao
    ocorrido_em: datetime
    resumo: str
    resultado: str
    devedor_id: uuid.UUID | None = None
    emprestimo_id: uuid.UUID | None = None
    parcela_id: uuid.UUID | None = None
    cobranca_acao_id: uuid.UUID | None = None
    agenda_item_id: uuid.UUID | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        _validar_uuid("responsavel_id", self.responsavel_id)
        if self.devedor_id is not None:
            _validar_uuid("devedor_id", self.devedor_id)
        if self.emprestimo_id is not None:
            _validar_uuid("emprestimo_id", self.emprestimo_id)
        if self.parcela_id is not None:
            _validar_uuid("parcela_id", self.parcela_id)
        if self.cobranca_acao_id is not None:
            _validar_uuid("cobranca_acao_id", self.cobranca_acao_id)
        if self.agenda_item_id is not None:
            _validar_uuid("agenda_item_id", self.agenda_item_id)
        if not isinstance(self.canal, CanalComunicacao):
            raise ViolacaoInvarianteError(
                "EPIC-007",
                f"canal invalido: {self.canal!r}",
            )
        if not self.resumo.strip():
            raise ViolacaoInvarianteError("EPIC-007", "resumo e obrigatorio")
        if not self.resultado.strip():
            raise ViolacaoInvarianteError("EPIC-007", "resultado e obrigatorio")


@dataclass
class HistoricoComunicacao:
    """Historico de comunicacoes para uma cadeia de relacionamento."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    emprestimo_id: uuid.UUID | None = None
    registros: tuple[RegistroComunicacao, ...] = ()
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        object.__setattr__(self, "registros", tuple(self.registros))
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        _validar_uuid("devedor_id", self.devedor_id)
        if self.emprestimo_id is not None:
            _validar_uuid("emprestimo_id", self.emprestimo_id)

    @property
    def registros_imutaveis(self) -> tuple[RegistroComunicacao, ...]:
        """Retorna registros com isolamento defensivo."""

        return tuple(copy.deepcopy(self.registros))

    def adicionar(self, registro: RegistroComunicacao) -> None:
        """Adiciona comunicacao no historico."""

        if registro.tenant_id != self.tenant_id:
            raise ViolacaoInvarianteError("EPIC-007", "tenant de registro incompativel")
        if registro.carteira_id != self.carteira_id:
            raise ViolacaoInvarianteError("EPIC-007", "carteira de registro incompativel")
        if registro.devedor_id != self.devedor_id:
            raise ViolacaoInvarianteError("EPIC-007", "devedor de registro incompativel")
        if self.emprestimo_id is not None and registro.emprestimo_id != self.emprestimo_id:
            raise ViolacaoInvarianteError("EPIC-007", "emprestimo de registro incompativel")

        object.__setattr__(self, "registros", self.registros + (registro,))


@dataclass(frozen=True)
class ResumoCarteira:
    """Read model de resumo de carteira (previa de relatorio)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    total_operacoes: int
    operacoes_pendentes: int
    vencidas: int
    encerradas: int
    atualizado_em: date


@dataclass(frozen=True)
class VencimentoOperacional:
    """Read model de vencimento operacional."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    data_vencimento: date
    emprestimo_id: uuid.UUID
    parcela_id: uuid.UUID
    valor_esperado: Any
    estado_oficial: str


@dataclass(frozen=True)
class JanelaAgenda:
    """Janela temporal de agenda."""

    inicio: datetime
    fim: datetime

    def __post_init__(self) -> None:
        if self.inicio > self.fim:
            raise ViolacaoInvarianteError(
                "EPIC-007",
                "janela inicial deve ser menor ou igual ao fim",
            )


@dataclass(frozen=True)
class RelatorioOperacionalCache:
    """Representa registro de relatorio de leitura operacional."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    janela_referencia: date
    familia_relatorio: str
    payload_json: dict[str, object]
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    gerado_em: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _validar_uuid("tenant_id", self.tenant_id)
        _validar_uuid("carteira_id", self.carteira_id)
        if not self.familia_relatorio.strip():
            raise ViolacaoInvarianteError("EPIC-007", "familia_relatorio e obrigatoria")
        if not isinstance(self.payload_json, dict):
            raise ViolacaoInvarianteError("EPIC-007", "payload_json deve ser dict")


def _validar_uuid(campo: str, valor: object) -> None:
    if not isinstance(valor, uuid.UUID):
        raise ViolacaoInvarianteError(
            "EPIC-007",
            f"{campo} deve ser uuid.UUID, recebido {valor!r}",
        )
