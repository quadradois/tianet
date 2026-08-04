"""Erros da camada de Aplicação (TASK-043).

Conflitos de idempotência são erros de uso do serviço (AD-002): herdam de
``DomainError`` para que a API os traduza como 409, no mesmo caminho da
violação de unicidade.
"""

from __future__ import annotations

from emprestimo.domain.common.errors import DomainError


class IdempotenciaConflitoError(DomainError):
    """A Idempotency-Key já foi utilizada com resultado diferente (AD-002).

    Levantada quando a mesma chave é reenviada com payload divergente
    (``solicitacao_hash`` diferente) ou enquanto um provisionamento com a
    mesma chave ainda está em andamento.
    """

    def __init__(self, idempotency_key: str, motivo: str) -> None:
        super().__init__(f"Conflito de Idempotency-Key {idempotency_key!r}: {motivo}")
        self.idempotency_key = idempotency_key
        self.motivo = motivo


class TransicaoEstadoInvalidaError(DomainError):
    """Transição de estado operacional rejeitada pelo Aggregate (FEATURE-004).

    A regra de negócio é avaliada no Domain (``inativar()``/``reativar()``,
    DOMAIN-017) e lança ``ViolacaoInvarianteError``; a Aplicação a traduz para
    este erro de conflito para que a API responda 409 (estado divergente —
    IMP-036). Não é regra de negócio duplicada: apenas re-enquadramento do
    erro já decidido pelo Aggregate.
    """

    def __init__(self, tenant_id: object, acao: str, motivo: str) -> None:
        super().__init__(f"Transição de estado inválida em {tenant_id} ({acao}): {motivo}")
        self.tenant_id = tenant_id
        self.acao = acao
        self.motivo = motivo
