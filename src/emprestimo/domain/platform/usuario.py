"""Entity Usuário — entidade filha do Aggregate Tenant (DOMAIN-018).

O Usuário representa uma pessoa autorizada a acessar a plataforma em nome
de um Tenant. Pertence exclusivamente ao Platform Context e nunca ao domínio
financeiro (DOMAIN-018 §1).

Ciclo de vida (DOMAIN-018 §4): Convidado → Ativo → Inativo → Removido.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class UsuarioState(StrEnum):
    """Ciclo de vida do Usuário (DOMAIN-018 §4)."""

    CONVIDADO = "convidado"
    ATIVO = "ativo"
    INATIVO = "inativo"
    REMOVIDO = "removido"


@dataclass
class Usuario:
    """Entidade Usuário, sempre vinculada a exatamente um Tenant (DOMAIN-018 INV-001).

    Nesta fase (IMP-002) apenas a estrutura é disponibilizada; as regras
    (RN-001..RN-005) pertencem às fases seguintes.
    """

    tenant_id: uuid.UUID
    nome: str
    email: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    estado: UsuarioState = UsuarioState.CONVIDADO
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
