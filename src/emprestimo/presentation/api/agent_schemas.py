"""DTOs da operação do agente (S3, somente leitura).

Um DTO por recurso (RA-012): a Presentation nunca devolve o Aggregate.
Sem paginação por cursor no v1 — `limite` com teto no caso de uso basta para
triagem, e a inbox real de um Tenant single-tenant é pequena.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from emprestimo.agent.conversa import ClasseContexto
from emprestimo.application.inbox_agente import ResumoInboxAgente


class EntradaInboxResponse(BaseModel):
    provider_input_id: str = Field(description="ID do provedor (dedupe replay).")
    remetente_normalizado: str = Field(description="Remetente normalizado.")
    classe: str = Field(description="operadora, devedor ou pre_cadastro.")
    texto: str | None = Field(default=None, description="Texto, quando houver.")
    estado: str = Field(description="Estado da entrada na inbox.")
    recebido_em: datetime


class InboxAgenteResponse(BaseModel):
    """Resumo + recentes da inbox do Tenant."""

    total: int
    operadora: int = 0
    devedor: int = 0
    pre_cadastro: int = 0
    recentes: list[EntradaInboxResponse] = Field(default_factory=list)

    @classmethod
    def de(cls, resumo: ResumoInboxAgente) -> InboxAgenteResponse:
        return cls(
            total=resumo.total,
            operadora=resumo.por_classe.get(ClasseContexto.OPERADORA, 0),
            devedor=resumo.por_classe.get(ClasseContexto.DEVEDOR, 0),
            pre_cadastro=resumo.por_classe.get(ClasseContexto.PRE_CADASTRO, 0),
            recentes=[
                EntradaInboxResponse(
                    provider_input_id=entrada.provider_input_id,
                    remetente_normalizado=entrada.remetente_normalizado,
                    classe=entrada.classe.value,
                    texto=entrada.texto,
                    estado=entrada.estado,
                    recebido_em=entrada.recebido_em,
                )
                for entrada in resumo.recentes
            ],
        )
