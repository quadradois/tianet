"""Erros de domínio — falhas expressas na linguagem do negócio (IMP-008).

A camada Domain comunica violações de regras através de exceções próprias,
nunca de exceções de infraestrutura (ADR-001): a aplicação traduz
DomainError em respostas HTTP sem conhecer detalhes de persistência.
"""

from __future__ import annotations


class DomainError(Exception):
    """Falha de regra de negócio do domínio."""


class ViolacaoInvarianteError(DomainError):
    """Estado inválido bloqueado por uma invariante do Aggregate (IMP-009).

    Args:
        codigo: identificador da invariante violada (ex.: ``INV-005``).
        mensagem: descrição legível da violação.
    """

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(f"Invariante {codigo} violada: {mensagem}")
        self.codigo = codigo
        self.mensagem = mensagem


class TenantJaExisteError(DomainError):
    """A organização já está provisionada na plataforma (IMP-008, UC-002).

    Levantada tanto pela consulta de unicidade quanto pela tradução da
    violação de constraint em corrida (AD-002) — conflito explícito, sem
    exceção genérica de persistência.
    """

    def __init__(self, identificador_institucional: str) -> None:
        super().__init__(f"Organização já existente: {identificador_institucional!r}")
        self.identificador_institucional = identificador_institucional
