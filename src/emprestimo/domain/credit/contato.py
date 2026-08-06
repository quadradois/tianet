"""Entity Contato — entidade filha do Aggregate Devedor (DOMAIN-021).

O Contato representa um meio de comunicação do Devedor: telefone, e-mail ou
WhatsApp. Possui identidade própria dentro do Devedor e ciclo de vida
independente (adicionado, atualizado, removido).

Regras preservadas nesta entity (IMP-044):
    - RN-002: todo Contato possui um tipo válido (telefone, e-mail, WhatsApp);
    - RN-003: ao menos um Contato válido é obrigatório na criação do Devedor
      (garantido pelo Aggregate Devedor — IMP-045);
    - RN-004: o valor do Contato deve ser válido para o tipo informado;
    - RN-005: apenas um Contato preferencial por tipo por Devedor
      (garantido pelo Aggregate Devedor — IMP-045, que detém a coleção).

RN-003 e RN-005 são invariantes da coleção e portanto responsabilidade do
Aggregate Devedor (IMP-045). Esta entity valida a unidade (tipo, valor,
marcador preferencial) isoladamente.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from emprestimo.domain.common.errors import DomainError


class TipoContato(StrEnum):
    """Canal de comunicação do Devedor (DOMAIN-021 RN-002)."""

    TELEFONE = "telefone"
    EMAIL = "email"
    WHATSAPP = "whatsapp"


class ContatoInvalidoError(DomainError):
    """Valor de Contato inválido para o tipo informado (DOMAIN-021 RN-004)."""

    def __init__(self, tipo: TipoContato, motivo: str) -> None:
        super().__init__(f"Contato {tipo.value} inválido: {motivo}")
        self.tipo = tipo
        self.motivo = motivo


class TipoContatoInvalidoError(DomainError):
    """Tipo de Contato inválido — deve ser um TipoContato válido."""

    def __init__(self, tipo_recebido: type) -> None:
        super().__init__(
            f"Tipo de contato inválido: {tipo_recebido.__name__}. "
            f"Deve ser um TipoContato válido."
        )
        self.tipo_recebido = tipo_recebido


class DevedorIdInvalidoError(DomainError):
    """devedor_id inválido — deve ser um uuid.UUID válido."""

    def __init__(self, devedor_id: object) -> None:
        super().__init__(f"devedor_id inválido: {devedor_id!r} — deve ser uuid.UUID.")
        self.devedor_id = devedor_id


# Máscara de telefone/WhatsApp: dígitos, com espaços, parênteses, hífens, sinal de mais e ponto.
_PADRAO_TELEFONE = re.compile(r"^\+?[0-9\s()\-\./]{8,20}$")
# E-mail: formato básico usuario@dominio (sem validar DNS/MX).
_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _contar_digitos(valor: str) -> int:
    """Conta apenas dígitos no valor."""
    return sum(1 for c in valor if c.isdigit())


def _validar_valor_por_tipo(tipo: TipoContato, valor: str) -> None:
    """Valida o valor do Contato conforme o tipo (DOMAIN-021 RN-004).

    Levanta ``ContatoInvalidoError`` quando o valor não satisfaz o formato
    esperado para o tipo informado.
    """
    valor_limpo = valor.strip()
    if not valor_limpo:
        raise ContatoInvalidoError(tipo, "valor não pode ser vazio")

    if tipo in (TipoContato.TELEFONE, TipoContato.WHATSAPP):
        telefone_invalido = _PADRAO_TELEFONE.match(valor_limpo) is None
        if telefone_invalido:
            raise ContatoInvalidoError(tipo, "formato de telefone/WhatsApp inválido")
        # Mínimo de 10 dígitos para telefone brasileiro (DDD + número)
        if _contar_digitos(valor_limpo) < 10:
            raise ContatoInvalidoError(tipo, "telefone/WhatsApp deve conter pelo menos 10 dígitos")
    elif tipo is TipoContato.EMAIL:
        if _PADRAO_EMAIL.match(valor_limpo) is None:
            raise ContatoInvalidoError(tipo, "formato de e-mail inválido")


@dataclass
class Contato:
    """Entity Contato do Devedor (DOMAIN-021).

    Attributes:
        devedor_id: vínculo obrigatório ao Devedor (RN-001 / INV-001).
        tipo: canal de comunicação (RN-002).
        valor: o valor do canal (RN-004 — validado conforme o tipo).
        preferencial: se este contato é o preferencial do tipo (RN-005).
        id: identidade única do Contato dentro do Devedor (INV-001).
        criado_em/atualizado_em: rastreabilidade cadastral.
    """

    devedor_id: uuid.UUID
    tipo: TipoContato
    valor: str
    preferencial: bool = False
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None

    def __post_init__(self) -> None:
        # Valida tipo
        if not isinstance(self.tipo, TipoContato):
            raise TipoContatoInvalidoError(type(self.tipo))

        # Valida devedor_id
        if not isinstance(self.devedor_id, uuid.UUID):
            raise DevedorIdInvalidoError(self.devedor_id)

        # Normaliza valor antes de validar/armazenar
        self.valor = self.valor.strip()

        # Valida valor por tipo
        _validar_valor_por_tipo(self.tipo, self.valor)
