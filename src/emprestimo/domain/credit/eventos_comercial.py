"""Eventos de dominio do Comercial (IMP-108, EPIC-003)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from emprestimo.domain.credit.decisao_comercial import DecisaoComercial
from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState


@dataclass(frozen=True)
class EventoPropostaComercial:
    """Evento base para transicoes de PropostaComercial."""

    proposta_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    usuario_id: uuid.UUID
    estado_anterior: PropostaComercialState
    estado_posterior: PropostaComercialState
    motivo: str | None
    ocorrido_em: datetime

    @classmethod
    def from_decisao(
        cls,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        decisao: DecisaoComercial,
    ) -> EventoPropostaComercial:
        """Constroi o evento a partir da decisao comercial registrada."""

        return cls(
            proposta_id=decisao.proposta_id,
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            usuario_id=decisao.usuario_id,
            estado_anterior=decisao.estado_anterior,
            estado_posterior=decisao.estado_posterior,
            motivo=decisao.motivo,
            ocorrido_em=decisao.criado_em,
        )

    @property
    def nome_evento(self) -> str:
        return self.__class__.__name__

    def to_audit_dict(self) -> dict[str, object]:
        """Serializa para registro na trilha de auditoria."""

        return {
            "evento": self.nome_evento,
            "proposta_id": str(self.proposta_id),
            "tenant_id": str(self.tenant_id),
            "carteira_id": str(self.carteira_id),
            "devedor_id": str(self.devedor_id),
            "usuario_id": str(self.usuario_id),
            "estado_anterior": self.estado_anterior.value,
            "estado_posterior": self.estado_posterior.value,
            "motivo": self.motivo,
            "ocorrido_em": self.ocorrido_em.isoformat(),
        }


@dataclass(frozen=True)
class PropostaEnviadaParaAnalise(EventoPropostaComercial):
    """Evento emitido quando a proposta sai de rascunho para analise."""


@dataclass(frozen=True)
class PropostaAprovada(EventoPropostaComercial):
    """Evento emitido quando a proposta e aprovada."""


@dataclass(frozen=True)
class PropostaRecusada(EventoPropostaComercial):
    """Evento emitido quando a proposta e recusada."""


@dataclass(frozen=True)
class PropostaCancelada(EventoPropostaComercial):
    """Evento emitido quando a proposta e cancelada."""


@dataclass(frozen=True)
class PropostaExpirada(EventoPropostaComercial):
    """Evento emitido quando a proposta expira."""


EVENTO_POR_ESTADO_POSTERIOR = {
    PropostaComercialState.EM_ANALISE: PropostaEnviadaParaAnalise,
    PropostaComercialState.APROVADA: PropostaAprovada,
    PropostaComercialState.RECUSADA: PropostaRecusada,
    PropostaComercialState.CANCELADA: PropostaCancelada,
    PropostaComercialState.EXPIRADA: PropostaExpirada,
}


def evento_from_decisao(
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    devedor_id: uuid.UUID,
    decisao: DecisaoComercial,
) -> EventoPropostaComercial:
    """Cria o evento correspondente ao estado posterior da decisao."""

    evento_cls = EVENTO_POR_ESTADO_POSTERIOR[decisao.estado_posterior]
    return evento_cls.from_decisao(
        tenant_id=tenant_id,
        carteira_id=carteira_id,
        devedor_id=devedor_id,
        decisao=decisao,
    )
