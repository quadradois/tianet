"""Eventos de dominio do ciclo de Contratos (EPIC-004)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.domain.credit.decisao_contrato import DecisaoContrato


@dataclass(frozen=True)
class EventoContrato:
    contrato_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    usuario_id: uuid.UUID
    tipo: str
    estado_anterior: ContratoCreditoState
    estado_posterior: ContratoCreditoState
    criado_em: datetime


def evento_from_decisao(
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    devedor_id: uuid.UUID,
    decisao: DecisaoContrato,
) -> EventoContrato:
    return EventoContrato(
        contrato_id=decisao.contrato_id,
        tenant_id=tenant_id,
        carteira_id=carteira_id,
        devedor_id=devedor_id,
        usuario_id=decisao.usuario_id,
        tipo=decisao.tipo,
        estado_anterior=decisao.estado_anterior,
        estado_posterior=decisao.estado_posterior,
        criado_em=decisao.criado_em,
    )
