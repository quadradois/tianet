"""Entity PerfilAcesso - conjunto de permissoes RBAC (IMP-084)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.permissao import Permissao, normalizar_codigo_permissao


class PerfilState(StrEnum):
    """Estado operacional do Perfil de Acesso."""

    ATIVO = "ativo"
    INATIVO = "inativo"


@dataclass
class PerfilAcesso:
    """Perfil de Acesso de um Tenant, usado para autorizacao RBAC."""

    tenant_id: uuid.UUID
    nome: str
    estado: PerfilState = PerfilState.ATIVO
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None
    _permissoes: list[Permissao] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, uuid.UUID):
            raise ViolacaoInvarianteError(
                "FEATURE-011",
                f"tenant_id deve ser uuid.UUID, recebido {self.tenant_id!r}",
            )
        nome = self.nome.strip()
        if not nome:
            raise ViolacaoInvarianteError(
                "FEATURE-011",
                "nome do Perfil de Acesso nao pode ser vazio",
            )
        if len(nome) > 120:
            raise ViolacaoInvarianteError(
                "FEATURE-011",
                "nome do Perfil de Acesso deve possuir no maximo 120 caracteres",
            )
        if not isinstance(self.estado, PerfilState):
            raise ViolacaoInvarianteError(
                "FEATURE-011",
                f"estado deve ser PerfilState, recebido {self.estado!r}",
            )
        self.nome = nome

    @property
    def permissoes(self) -> tuple[Permissao, ...]:
        return tuple(self._permissoes)

    def adicionar_permissao(self, permissao: Permissao) -> None:
        if self.estado is not PerfilState.ATIVO:
            raise ViolacaoInvarianteError("FEATURE-011", "Perfil de Acesso inativo")
        if any(existente.codigo == permissao.codigo for existente in self._permissoes):
            return
        self._permissoes.append(permissao)
        self._marcar_atualizado()

    def remover_permissao(self, codigo: str) -> None:
        if self.estado is not PerfilState.ATIVO:
            raise ViolacaoInvarianteError("FEATURE-011", "Perfil de Acesso inativo")
        codigo_normalizado = normalizar_codigo_permissao(codigo)
        self._permissoes = [
            permissao for permissao in self._permissoes if permissao.codigo != codigo_normalizado
        ]
        self._marcar_atualizado()

    def renomear(self, nome: str) -> None:
        novo_nome = nome.strip()
        if not novo_nome or len(novo_nome) > 120:
            raise ViolacaoInvarianteError(
                "FEATURE-011", "nome do Perfil de Acesso deve possuir entre 1 e 120 caracteres"
            )
        self.nome = novo_nome
        self._marcar_atualizado()

    def permite(self, codigo: str) -> bool:
        if self.estado is not PerfilState.ATIVO:
            return False
        codigo_normalizado = normalizar_codigo_permissao(codigo)
        return any(permissao.codigo == codigo_normalizado for permissao in self._permissoes)

    def inativar(self) -> None:
        if self.estado is PerfilState.INATIVO:
            raise ViolacaoInvarianteError(
                "FEATURE-011",
                "Perfil de Acesso ja esta inativo",
            )
        self.estado = PerfilState.INATIVO
        self._marcar_atualizado()

    def reativar(self) -> None:
        if self.estado is PerfilState.ATIVO:
            raise ViolacaoInvarianteError(
                "FEATURE-011",
                "Perfil de Acesso ja esta ativo",
            )
        self.estado = PerfilState.ATIVO
        self._marcar_atualizado()

    def _marcar_atualizado(self) -> None:
        self.atualizado_em = datetime.now(UTC)
