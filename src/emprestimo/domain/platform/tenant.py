"""Aggregate Tenant — Aggregate Root do Platform Context (DOMAIN-017).

O Tenant estabelece a fronteira de isolamento entre organizações. Todo
recurso da plataforma pertence exatamente a um Tenant.

Responsabilidades (DOMAIN-017 §2):
- manter a identidade da organização;
- manter seus Usuários, Configurações e Carteiras;
- garantir o isolamento dos dados;
- estabelecer a fronteira transacional do Platform Context.

O Tenant não executa regras financeiras (Credit Context).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class TenantState(StrEnum):
    """Estado operacional do Tenant (PLAN-001 §5)."""

    PROVISAO = "provisao"
    ATIVO = "ativo"
    INATIVO = "inativo"


@dataclass
class Tenant:
    """Aggregate Root do Platform Context.

    Nesta fase (IMP-001) apenas a estrutura é disponibilizada: identidade,
    dados institucionais, estado operacional e vínculos. A validação de
    invariantes pertence à fase de Domínio (IMP-009).
    """

    identificador_institucional: str
    nome: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    estado: TenantState = TenantState.PROVISAO
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
