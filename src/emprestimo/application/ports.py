"""Ports da camada de Aplicação (TASK-043, IMP-014..IMP-016).

A camada de Aplicação depende de contratos (ABCs); a Infrastructure
implementa. Idempotência e Auditoria são preocupações técnicas de
aplicação, não regras de domínio — por isso seus contratos vivem aqui e
não em ``domain``.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from emprestimo.domain.credit.ports import (
    CarteiraRepository,
    ContatoRepository,
    DevedorRepository,
)
from emprestimo.domain.platform.ports import (
    ConfiguracaoRepository,
    TenantRepository,
    UsuarioRepository,
)


class IdempotenciaRegistro(ABC):
    """Registro de Idempotency-Keys com constraint único (AD-002, IMP-015).

    O registro pertence à mesma transação do caso de uso (Unit of Work):
    a chave só fica visível como concluída junto com o resultado persistido.
    """

    @abstractmethod
    def registrar(self, chave: str, escopo: str, solicitacao_hash: str) -> None: ...

    @abstractmethod
    def find_by_chave(self, chave: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def concluir(self, chave: str, resultado: str) -> None: ...


class AuditoriaRegistro(ABC):
    """Trilha append-only e imutável do provisionamento (IMP-016).

    Persiste em sessão independente: os registros de início/falha/rollback
    sobrevivem ao rollback da transação de negócio (AD-001).
    """

    @abstractmethod
    def registrar(
        self,
        entidade: str,
        entidade_id: uuid.UUID | None,
        acao: str,
        status: str,
        detalhes: str | None = None,
    ) -> None: ...


class UnitOfWork(ABC):
    """Fronteira transacional única do caso de uso (AD-001, IMP-014).

    Expõe os repositórios e o registro de idempotência compartilhando a
    mesma sessão/transação. Commit apenas ao final; qualquer exceção
    dispara rollback automático no ``__exit__``. Nenhum repositório
    executa commit.
    """

    tenant: TenantRepository
    usuario: UsuarioRepository
    configuracao: ConfiguracaoRepository
    carteira: CarteiraRepository
    devedor: DevedorRepository
    contato: ContatoRepository
    idempotencia: IdempotenciaRegistro

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            self.rollback()
        self.close()
