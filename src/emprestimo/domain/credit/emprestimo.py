"""Emprestimo (IMP-149, EPIC-005)."""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contrato_liberado import ContratoLiberadoLogico
from emprestimo.domain.credit.dia_de_acerto import proximo_acerto, validar_dia_de_acerto

__all__ = [
    "Emprestimo",
    "EmprestimoCriado",
    "EmprestimoEvento",
    "EmprestimoState",
]


class EmprestimoState(Enum):
    """Estados basicos da operacao financeira."""

    ATIVO = "ativo"
    QUITADO = "quitado"
    CANCELADO = "cancelado"


@dataclass(frozen=True)
class EmprestimoCriado:
    """Evento emitido quando o Motor origina um Emprestimo."""

    emprestimo_id: uuid.UUID
    contrato_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    ocorrido_em: datetime
    tipo: str = "emprestimo_criado"

    @property
    def nome_evento(self) -> str:
        return self.__class__.__name__

    def to_audit_dict(self) -> dict[str, object]:
        return {
            "evento": self.nome_evento,
            "tipo": self.tipo,
            "emprestimo_id": str(self.emprestimo_id),
            "contrato_id": str(self.contrato_id),
            "tenant_id": str(self.tenant_id),
            "carteira_id": str(self.carteira_id),
            "devedor_id": str(self.devedor_id),
            "ocorrido_em": self.ocorrido_em.isoformat(),
        }


EmprestimoEvento = EmprestimoCriado | object


@dataclass
class Emprestimo:
    """Aggregate que reflete o estado atual da operacao financeira."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    contrato_id: uuid.UUID
    principal_original: Decimal
    moeda: str
    _parametros_financeiros: dict[str, object]
    estado: EmprestimoState = EmprestimoState.ATIVO
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None
    ultimo_processamento_em: datetime | None = None
    ultimo_pagamento_em: datetime | None = None
    proximo_vencimento_em: datetime | None = None
    quitado_em: datetime | None = None
    _eventos: list[EmprestimoEvento] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        for campo in (
            "tenant_id",
            "carteira_id",
            "devedor_id",
            "contrato_id",
            "id",
        ):
            _validar_uuid(campo, getattr(self, campo))
        if not isinstance(self.estado, EmprestimoState):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                f"estado deve ser EmprestimoState, recebido {self.estado!r}",
            )
        if self.principal_original <= Decimal("0.00"):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "principal_original deve ser maior que zero",
            )
        if not self.moeda:
            raise ViolacaoInvarianteError("EPIC-005", "moeda nao pode ser vazia")
        self._parametros_financeiros = _copiar_parametros(self._parametros_financeiros)

    @classmethod
    def criar_de_contrato_liberado(
        cls,
        contrato: ContratoLiberadoLogico,
    ) -> Emprestimo:
        """Cria Emprestimo a partir da saida logica de Contratos."""

        if not isinstance(contrato, ContratoLiberadoLogico):
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "emprestimo deve nascer de ContratoLiberadoLogico",
            )
        parametros = _copiar_parametros(contrato.parametros_contratados)
        principal_original = _decimal_de_parametros(
            parametros,
            "valor_contratado",
            "principal_original",
        )
        moeda = str(parametros.get("moeda", "BRL"))
        emprestimo = cls(
            tenant_id=contrato.tenant_id,
            carteira_id=contrato.carteira_id,
            devedor_id=contrato.devedor_id,
            contrato_id=contrato.contrato_id,
            principal_original=principal_original,
            moeda=moeda,
            _parametros_financeiros=parametros,
        )
        emprestimo._registrar_evento_criacao()
        return emprestimo

    @classmethod
    def restaurar(
        cls,
        *,
        id: uuid.UUID,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        contrato_id: uuid.UUID,
        principal_original: Decimal,
        moeda: str,
        parametros_financeiros: Mapping[str, object],
        estado: EmprestimoState,
        criado_em: datetime,
        atualizado_em: datetime | None = None,
        ultimo_processamento_em: datetime | None = None,
        ultimo_pagamento_em: datetime | None = None,
        proximo_vencimento_em: datetime | None = None,
        quitado_em: datetime | None = None,
    ) -> Emprestimo:
        """Reconstitui um Emprestimo persistido sem emitir novo evento."""

        return cls(
            id=id,
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            contrato_id=contrato_id,
            principal_original=principal_original,
            moeda=moeda,
            _parametros_financeiros=_copiar_parametros(parametros_financeiros),
            estado=estado,
            criado_em=criado_em,
            atualizado_em=atualizado_em,
            ultimo_processamento_em=ultimo_processamento_em,
            ultimo_pagamento_em=ultimo_pagamento_em,
            proximo_vencimento_em=proximo_vencimento_em,
            quitado_em=quitado_em,
        )

    @property
    def parametros_financeiros(self) -> dict[str, object]:
        """Parametros congelados do contrato, protegidos contra mutacao externa."""

        return copy.deepcopy(self._parametros_financeiros)

    @property
    def dia_de_acerto(self) -> int | None:
        """Dia do mes combinado para o acerto, quando houver (DR-004).

        `None` nos emprestimos anteriores a esta decisao, que nasceram com plano
        de parcelas. Enquanto os dois modelos convivem, a ausencia e um estado
        legitimo e nao um erro.
        """
        bruto = self._parametros_financeiros.get("dia_de_acerto")
        return validar_dia_de_acerto(bruto) if bruto is not None else None  # type: ignore[arg-type]

    def proximo_acerto_em(self, a_partir_de: date) -> date | None:
        """Proxima data de acerto depois de `a_partir_de`."""

        dia = self.dia_de_acerto
        return proximo_acerto(a_partir_de, dia) if dia is not None else None

    def acerto_sem_pagamento_em(self, data_referencia: date) -> date | None:
        """Acerto ja vencido para o qual nao houve pagamento nenhum.

        O nome diz exatamente o que esta camada consegue saber. Julgar se o
        devedor **quitou os juros do periodo** exige o saldo, e saldo e do Motor
        — que Cobranca, Agenda e Relatorios sao proibidos de importar.

        **Limitacao conhecida e deliberada:** um pagamento parcial, menor que os
        juros devidos, faz este metodo devolver `None`. O devedor pagou algo, e
        para esta camada isso basta para sair da fila de "ninguem apareceu". O
        valor exato continua vindo do saldo, quando o operador abrir a operacao.
        Chamar isto de "inadimplente" seria afirmar mais do que se sabe.
        """
        vigente = self.acerto_vigente_em(data_referencia)
        if vigente is None:
            return None
        if self.ultimo_pagamento_em is not None and self.ultimo_pagamento_em.date() >= vigente:
            return None
        return vigente

    def dias_sem_pagamento_em(self, data_referencia: date) -> int:
        """Dias corridos desde o acerto vencido sem pagamento; zero se nao ha."""

        acerto = self.acerto_sem_pagamento_em(data_referencia)
        return (data_referencia - acerto).days if acerto is not None else 0

    def acerto_vigente_em(self, data_referencia: date) -> date | None:
        """Acerto que o devedor ja deveria ter feito em `data_referencia`.

        E a ultima ocorrencia do dia combinado que nao esta no futuro. Serve a
        Cobranca e a Agenda: se existe acerto vigente e o periodo dele nao foi
        quitado, o devedor esta em atraso.
        """
        dia = self.dia_de_acerto
        if dia is None:
            return None
        origem = self.criado_em.date()
        anterior = None
        cursor = origem
        while True:
            seguinte = proximo_acerto(cursor, dia)
            if seguinte > data_referencia:
                return anterior
            anterior = seguinte
            cursor = seguinte

    @property
    def eventos(self) -> tuple[EmprestimoEvento, ...]:
        """Eventos de dominio gerados pelo Emprestimo."""

        return tuple(self._eventos)

    def marcar_quitado(self, *, quitado_em: datetime | None = None) -> None:
        """Atualiza estado apos processamento de quitacao feito pelo Motor."""

        if self.estado is not EmprestimoState.ATIVO:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                f"emprestimo em {self.estado.value} nao pode ser quitado",
            )
        self.estado = EmprestimoState.QUITADO
        self.quitado_em = quitado_em or datetime.now(UTC)
        self._marcar_atualizado()

    def registrar_evento(self, evento: object) -> None:
        """Adiciona evento gerado pelo Motor Financeiro a trilha do aggregate."""

        if not hasattr(evento, "tipo"):
            raise ViolacaoInvarianteError("EPIC-005", "evento financeiro deve expor tipo")
        self._eventos.append(evento)
        self._marcar_atualizado()

    def _registrar_evento_criacao(self) -> None:
        self._eventos.append(
            EmprestimoCriado(
                emprestimo_id=self.id,
                contrato_id=self.contrato_id,
                tenant_id=self.tenant_id,
                carteira_id=self.carteira_id,
                devedor_id=self.devedor_id,
                ocorrido_em=self.criado_em,
            )
        )

    def _marcar_atualizado(self) -> None:
        self.atualizado_em = datetime.now(UTC)


def _validar_uuid(campo: str, valor: object) -> None:
    if not isinstance(valor, uuid.UUID):
        raise ViolacaoInvarianteError(
            "EPIC-005",
            f"{campo} deve ser uuid.UUID, recebido {valor!r}",
        )


def _copiar_parametros(parametros: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(parametros, Mapping):
        raise ViolacaoInvarianteError(
            "EPIC-005",
            f"parametros financeiros devem ser mapeaveis, recebido {parametros!r}",
        )
    if not parametros:
        raise ViolacaoInvarianteError(
            "EPIC-005",
            "parametros financeiros nao podem ser vazios",
        )
    return copy.deepcopy(dict(parametros))


def _decimal_de_parametros(
    parametros: Mapping[str, object],
    *chaves: str,
) -> Decimal:
    for chave in chaves:
        if chave in parametros:
            try:
                return Decimal(str(parametros[chave]))
            except (InvalidOperation, ValueError) as exc:
                raise ViolacaoInvarianteError(
                    "EPIC-005",
                    f"{chave} deve ser Decimal valido",
                ) from exc
    raise ViolacaoInvarianteError(
        "EPIC-005",
        f"parametros devem informar uma das chaves: {', '.join(chaves)}",
    )
