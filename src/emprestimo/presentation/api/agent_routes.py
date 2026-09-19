"""Operação do agente pelo Credor (S3, somente leitura).

Uma única rota de leitura: resumo + recentes da inbox do Tenant. Inbox vazia
devolve zeros — não 404: ausência de mensagem não é recurso inexistente.
Sem `Idempotency-Key`: GET não escreve (SPEC-004, regra 3).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from emprestimo.application.autorizacao import Principal
from emprestimo.application.inbox_agente import (
    LIMITE_MAXIMO_RECENTES,
    LIMITE_PADRAO_RECENTES,
    ConsultarInboxAgente,
)
from emprestimo.presentation.api.agent_schemas import InboxAgenteResponse
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_consultar_inbox_agente,
    get_principal_atual,
)
from emprestimo.presentation.api.openapi import RESPOSTAS_PROTEGIDAS

router = APIRouter(
    prefix="/platform/agent",
    tags=["Agent"],
    dependencies=[Depends(get_principal_atual)],
    responses=RESPOSTAS_PROTEGIDAS,
)


@router.get("/inbox", response_model=InboxAgenteResponse)
def consultar_inbox(
    principal: Principal = Depends(exigir_permissao("agent.inbox.ler")),
    caso_de_uso: ConsultarInboxAgente = Depends(get_consultar_inbox_agente),
    limite: int = Query(default=LIMITE_PADRAO_RECENTES, ge=1, le=LIMITE_MAXIMO_RECENTES),
) -> InboxAgenteResponse:
    """Resumo por classe + entradas mais recentes, para triagem do operador."""
    return InboxAgenteResponse.de(
        caso_de_uso.executar(tenant_id=principal.tenant_id, limite=limite)
    )
