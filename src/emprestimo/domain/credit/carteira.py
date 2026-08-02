"""Aggregate Carteira — Aggregate Root do Credit Context (DOMAIN-001).

A Carteira garante a consistência de todas as operações financeiras
pertencentes ao Credor. Toda operação de crédito pertence exatamente a uma
Carteira.

Nesta fase (IMP-007) apenas a estrutura mínima necessária ao vínculo
Tenant→Carteira é disponibilizada (BR-004: FK obrigatória para o Tenant).
O modelo completo do Aggregate Carteira (Devedor, Contrato, Empréstimo,
Parcela, Pagamento) pertence à implementação do domínio de crédito.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Carteira:
    """Aggregate Root do Credit Context, com vínculo obrigatório ao Tenant.

    Nesta fase (IMP-007) apenas a estrutura de persistência é
    disponibilizada; regras financeiras são do Motor Financeiro (DOMAIN-010).
    """

    tenant_id: uuid.UUID
    nome: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
