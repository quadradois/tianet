"""Entity Usuário — entidade filha do Aggregate Tenant (DOMAIN-018).

O Usuário representa uma pessoa autorizada a acessar a plataforma em nome
de um Tenant. Pertence exclusivamente ao Platform Context e nunca ao domínio
financeiro (DOMAIN-018 §1).

Ciclo de vida (DOMAIN-018 §4): Convidado → Ativo → Inativo → Removido.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from emprestimo.domain.common.errors import ViolacaoInvarianteError


class UsuarioState(StrEnum):
    """Ciclo de vida do Usuário (DOMAIN-018 §4)."""

    CONVIDADO = "convidado"
    ATIVO = "ativo"
    INATIVO = "inativo"
    REMOVIDO = "removido"


@dataclass
class Usuario:
    """Entidade Usuário, sempre vinculada a exatamente um Tenant (DOMAIN-018 INV-001).

    Atributos de estrutura disponibilizados na Fase 1 (IMP-002); as regras
    de negócio (RN-001..RN-005) pertencem às fases seguintes. O perfil de
    acesso (RN-002) é preenchido pelo Aggregate Tenant no provisionamento
    (IMP-011) e permanece ``None`` até que um perfil seja atribuído.
    """

    tenant_id: uuid.UUID
    nome: str
    email: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    perfil_acesso: str | None = None
    estado: UsuarioState = UsuarioState.CONVIDADO
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))

    # ------------------------------------------------------------------ #
    # Ciclo de vida (DOMAIN-018 §4)
    # ------------------------------------------------------------------ #

    def _verificar_estado(self, esperado: UsuarioState, regra: str) -> None:
        """Valida o estado atual antes de uma transição (DOMAIN-018 §4)."""
        if self.estado is not esperado:
            raise ViolacaoInvarianteError(
                regra,
                f"transição inválida: esperado '{esperado.value}', " f"atual '{self.estado.value}'",
            )

    def ativar(self) -> None:
        """Transição Convidado → Ativo (DOMAIN-018 §4).

        Ocorre quando o Usuário define sua credencial inicial — sem credencial
        o acesso é bloqueado.
        """
        self._verificar_estado(UsuarioState.CONVIDADO, "DOMAIN-018")
        self.estado = UsuarioState.ATIVO

    def inativar(self) -> None:
        """Transição Ativo → Inativo (DOMAIN-018 §4)."""
        self._verificar_estado(UsuarioState.ATIVO, "DOMAIN-018")
        self.estado = UsuarioState.INATIVO

    def reativar(self) -> None:
        """Transição Inativo → Ativo (DOMAIN-018 §4)."""
        self._verificar_estado(UsuarioState.INATIVO, "DOMAIN-018")
        self.estado = UsuarioState.ATIVO

    def remover(self) -> None:
        """Transição Inativo → Removido (DOMAIN-018 §4).

        A remoção é definitiva: não há retorno de Removido.
        """
        self._verificar_estado(UsuarioState.INATIVO, "DOMAIN-018")
        self.estado = UsuarioState.REMOVIDO

    @property
    def ativo(self) -> bool:
        """Indica se o Usuário está em estado Ativo (pré-requisito de acesso)."""
        return self.estado is UsuarioState.ATIVO
