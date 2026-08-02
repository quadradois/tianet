"""Aggregate Tenant — Aggregate Root do Platform Context (DOMAIN-017).

O Tenant estabelece a fronteira de isolamento entre organizações. Todo
recurso da plataforma pertence exatamente a um Tenant.

Responsabilidades (DOMAIN-017 §2):
- manter a identidade da organização;
- manter seus Usuários, Configurações e Carteiras;
- garantir o isolamento dos dados;
- estabelecer a fronteira transacional do Platform Context;
- proteger as invariantes INV-001..INV-005 (IMP-009).

O Tenant não executa regras financeiras (Credit Context). A criação de
Carteira, Usuário e Configuração ocorre exclusivamente através deste
aggregate (TASK-042), preservando as invariantes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.usuario import Usuario

CARTEIRA_PADRAO_NOME = "Carteira Principal"
"""Nome da Carteira padrão criada no provisionamento (UC-003, IMP-010)."""

PERFIL_ADMINISTRADOR = "administrador"
"""Perfil de acesso do primeiro Usuário do Tenant (UC-004, IMP-011)."""

CONFIGURACOES_PADRAO: tuple[tuple[str, str], ...] = (("moeda", "BRL"),)
"""Parâmetros iniciais do Tenant (UC-005, IMP-012).

Valores de referência para o provisionamento; o catálogo definitivo de
configurações pertence à camada de Aplicação (IMP-013).
"""


class TenantState(StrEnum):
    """Estado operacional do Tenant (PLAN-001 §5)."""

    PROVISAO = "provisao"
    ATIVO = "ativo"
    INATIVO = "inativo"


@dataclass
class Tenant:
    """Aggregate Root do Platform Context.

    INV-001: todo Usuário pertence exatamente a um Tenant;
    INV-002: toda Carteira pertence exatamente a um Tenant;
    INV-003: nenhum Usuário pertence a dois Tenants;
    INV-004: nenhuma Carteira pertence a dois Tenants;
    INV-005: v1 — exatamente uma Carteira por Tenant (DOMAIN-017 §5).
    """

    identificador_institucional: str
    nome: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    estado: TenantState = TenantState.PROVISAO
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    _usuarios: list[Usuario] = field(default_factory=list, init=False, repr=False)
    _carteiras: list[Carteira] = field(default_factory=list, init=False, repr=False)
    _configuracoes: list[Configuracao] = field(default_factory=list, init=False, repr=False)

    # ------------------------------------------------------------------ #
    # Estado interno (somente leitura fora do aggregate)
    # ------------------------------------------------------------------ #

    @property
    def usuarios(self) -> tuple[Usuario, ...]:
        """Usuários vinculados ao Tenant (INV-001/INV-003)."""
        return tuple(self._usuarios)

    @property
    def carteiras(self) -> tuple[Carteira, ...]:
        """Carteiras vinculadas ao Tenant (INV-002/INV-004)."""
        return tuple(self._carteiras)

    @property
    def configuracoes(self) -> tuple[Configuracao, ...]:
        """Configurações vinculadas ao Tenant."""
        return tuple(self._configuracoes)

    # ------------------------------------------------------------------ #
    # Invariantes do Aggregate (IMP-009)
    # ------------------------------------------------------------------ #

    def adicionar_usuario(self, usuario: Usuario) -> None:
        """Vincula um Usuário ao Tenant, protegendo INV-001 e INV-003.

        O Usuário pertence exatamente a um Tenant: o vínculo é o próprio
        ``tenant_id`` do Tenant, e um Usuário já vinculado a outro Tenant
        viola INV-001/INV-003 (nunca será órfão nem compartilhado).
        """
        if usuario.tenant_id != self.id:
            raise ViolacaoInvarianteError(
                "INV-001",
                f"Usuário {usuario.id} vinculado a Tenant {usuario.tenant_id}, "
                f"não ao Tenant {self.id}",
            )
        if any(existente.id == usuario.id for existente in self._usuarios):
            raise ViolacaoInvarianteError(
                "INV-001",
                f"Usuário {usuario.id} já vinculado a este Tenant",
            )
        self._usuarios.append(usuario)

    def adicionar_carteira(self, carteira: Carteira) -> None:
        """Vincula uma Carteira ao Tenant, protegendo INV-002, INV-004 e INV-005."""
        if carteira.tenant_id != self.id:
            raise ViolacaoInvarianteError(
                "INV-002",
                f"Carteira {carteira.id} vinculada a Tenant {carteira.tenant_id}, "
                f"não ao Tenant {self.id}",
            )
        if any(existente.id == carteira.id for existente in self._carteiras):
            raise ViolacaoInvarianteError(
                "INV-002",
                f"Carteira {carteira.id} já vinculada a este Tenant",
            )
        if len(self._carteiras) >= 1:
            raise ViolacaoInvarianteError(
                "INV-005",
                "v1 permite exatamente uma Carteira por Tenant; "
                "mais de uma Carteira será habilitada em versão futura",
            )
        self._carteiras.append(carteira)

    def adicionar_configuracao(self, configuracao: Configuracao) -> None:
        """Vincula uma Configuração ao Tenant, preservando a unicidade de chave."""
        if configuracao.tenant_id != self.id:
            raise ViolacaoInvarianteError(
                "FOUNDATION-002",
                f"Configuração {configuracao.id} vinculada a Tenant "
                f"{configuracao.tenant_id}, não ao Tenant {self.id}",
            )
        if any(existente.chave == configuracao.chave for existente in self._configuracoes):
            raise ViolacaoInvarianteError(
                "FOUNDATION-002",
                f"Configuração de chave {configuracao.chave!r} já existente neste Tenant",
            )
        self._configuracoes.append(configuracao)

    # ------------------------------------------------------------------ #
    # Provisionamento (IMP-010..IMP-012)
    # ------------------------------------------------------------------ #

    def criar_carteira_padrao(self) -> Carteira:
        """Cria e vincula a Carteira padrão do Tenant (UC-003, IMP-010).

        A Carteira é criada com o nome padrão ``CARTEIRA_PADRAO_NOME`` e
        vinculada ao Credit Context (DOMAIN-001, BR-004) dentro do mesmo
        fluxo de provisionamento.
        """
        carteira = Carteira(tenant_id=self.id, nome=CARTEIRA_PADRAO_NOME)
        self._carteiras.append(carteira)
        return carteira

    def criar_usuario_administrador(self, nome: str, email: str) -> Usuario:
        """Cria o primeiro Usuário Administrador do Tenant (UC-004, IMP-011).

        Atende DOMAIN-018 RN-001 (vinculação obrigatória ao Tenant) e RN-002
        (perfil de acesso mínimo de Administrador). Sem fluxo de
        autenticação nesta fase.
        """
        usuario = Usuario(
            tenant_id=self.id,
            nome=nome,
            email=email,
            perfil_acesso=PERFIL_ADMINISTRADOR,
        )
        self._usuarios.append(usuario)
        return usuario

    def inicializar_configuracoes(self) -> tuple[Configuracao, ...]:
        """Provisiona as configurações padrão do Tenant (UC-005, IMP-012).

        Retorna as Configurações criadas; chamadas subsequentes são
        idempotentes no nível do agregado (chaves já existentes não são
        duplicadas).
        """
        existentes = {config.chave for config in self._configuracoes}
        novas = [
            Configuracao(tenant_id=self.id, chave=chave, valor=valor)
            for chave, valor in CONFIGURACOES_PADRAO
            if chave not in existentes
        ]
        self._configuracoes.extend(novas)
        return tuple(novas)
