"""Entity Configuração — parâmetro específico de um Tenant (FOUNDATION-002 §Configuração).

"Configuração: parâmetro específico de um Tenant que define o comportamento
da plataforma para sua organização."
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Configuracao:
    """Parâmetro de configuração vinculado a exatamente um Tenant.

    Nesta fase (IMP-003) apenas a estrutura é disponibilizada; a
    inicialização de valores padrão pertence à fase de Domínio (IMP-012).
    """

    tenant_id: uuid.UUID
    chave: str
    valor: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
