"""Ports do Platform Context — contratos de persistência (Repository Pattern).

A camada Domain define os contratos; a Infrastructure implementa. O Domain
não conhece SQLAlchemy nem FastAPI (DECISION-001 / ADR-001).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp, EstadoPareamento
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.sessao import Sessao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario


@dataclass(frozen=True)
class TenantFiltro:
    """Filtros para listagem de Tenants (IMP-025)."""

    estado: TenantState | None = None


@dataclass(frozen=True)
class TenantOrdenacao:
    """Ordenação para listagem de Tenants (IMP-025)."""

    campo: Literal["criado_em", "identificador_institucional", "nome", "estado"] = "criado_em"
    direcao: Literal["asc", "desc"] = "asc"


@dataclass(frozen=True)
class TenantPaginado:
    """Resultado paginado de Tenants (IMP-025)."""

    items: list[Tenant]
    total: int
    page: int
    size: int
    pages: int


class TenantRepository(ABC):
    """Persistência do Aggregate Tenant (IMP-004)."""

    @abstractmethod
    def save(self, tenant: Tenant) -> None: ...

    @abstractmethod
    def find_by_id(self, tenant_id: uuid.UUID) -> Tenant | None: ...

    @abstractmethod
    def find_by_identificador_institucional(self, identificador: str) -> Tenant | None: ...

    @abstractmethod
    def find_all(self) -> list[Tenant]: ...

    @abstractmethod
    def find_all_paginated(
        self,
        page: int = 1,
        size: int = 20,
        ordenacao: TenantOrdenacao | None = None,
        filtro: TenantFiltro | None = None,
    ) -> TenantPaginado: ...


class UsuarioRepository(ABC):
    """Persistência da Entity Usuário (IMP-005)."""

    @abstractmethod
    def save(self, usuario: Usuario) -> None: ...

    @abstractmethod
    def find_by_id(self, usuario_id: uuid.UUID) -> Usuario | None: ...

    @abstractmethod
    def find_by_email(self, email: str) -> Usuario | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Usuario]: ...


class ConfiguracaoRepository(ABC):
    """Persistência da Entity Configuração (IMP-006)."""

    @abstractmethod
    def save(self, configuracao: Configuracao) -> None: ...

    @abstractmethod
    def find_by_id(self, configuracao_id: uuid.UUID) -> Configuracao | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Configuracao]: ...


class ConexaoWhatsAppRepository(ABC):
    """Persistencia da Entity ConexaoWhatsApp (IMP-365, PLAN-034).

    O token viaja SEPARADO da entidade, e de proposito: ele e segredo, e a
    entidade nao deve carrega-lo por engano para um log, uma resposta de API ou
    uma trilha de auditoria. Quem quiser o token pede por ele explicitamente, e
    quem quiser o estado da conexao nunca o recebe de brinde.

    A cifragem e responsabilidade da implementacao — o dominio nao conhece
    `cryptography`, nem deveria.
    """

    @abstractmethod
    def save(self, conexao: ConexaoWhatsApp, *, token: str | None = None) -> None:
        """Grava a conexao. `token=None` preserva o token ja guardado.

        Sem esse cuidado, um `save` de pareamento apagaria o token — e a conexao
        continuaria existindo, sem poder enviar nada.
        """

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> ConexaoWhatsApp | None: ...

    @abstractmethod
    def find_token(self, tenant_id: uuid.UUID) -> str | None:
        """Devolve o token decifrado. Unico caminho para obte-lo."""


class ProvedorWhatsApp(ABC):
    """Operacoes de instancia no provedor, sem o protocolo HTTP a tiracolo.

    A Application orquestra criar, conectar, ler estado e desconectar; nao
    conhece rotas, chaves de tenant nem formato de QR. O token entra como
    parametro em vez de virar estado do adapter porque quem sabe qual token usar
    e o repositorio, e ele so entrega o valor a quem pedir explicitamente.
    """

    @abstractmethod
    def criar_instancia(self, nome: str) -> tuple[str, str]:
        """Cria a instancia e devolve `(instancia_id, token)`.

        **O token e gerado por nos**; o provedor apenas o ecoa. Quem procurar um
        identificador emitido pelo servidor nao vai encontrar.
        """

    @abstractmethod
    def conectar(self, token: str) -> None:
        """Inicia o pareamento. Idempotente numa instancia ja conectada."""

    @abstractmethod
    def qrcode(self, token: str) -> str:
        """QR em base64. Levanta `QrCodeIndisponivelError` enquanto gera."""

    @abstractmethod
    def estado(self, token: str) -> EstadoPareamento: ...

    @abstractmethod
    def desconectar(self, token: str) -> None:
        """Desvincula o numero. A instancia permanece."""


class CredencialRepository(ABC):
    """Persistencia da Entity Credencial (IMP-086)."""

    @abstractmethod
    def save(self, credencial: Credencial) -> None: ...

    @abstractmethod
    def find_by_id(self, credencial_id: uuid.UUID) -> Credencial | None: ...

    @abstractmethod
    def find_by_usuario_id(self, usuario_id: uuid.UUID) -> Credencial | None: ...


class SessaoRepository(ABC):
    """Persistencia da Entity Sessao (IMP-086)."""

    @abstractmethod
    def save(self, sessao: Sessao) -> None: ...

    @abstractmethod
    def find_by_id(self, sessao_id: uuid.UUID) -> Sessao | None: ...

    @abstractmethod
    def find_by_usuario_id(self, usuario_id: uuid.UUID) -> list[Sessao]: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Sessao]: ...


class PermissaoRepository(ABC):
    """Persistencia do catalogo de Permissoes (IMP-086)."""

    @abstractmethod
    def save(self, permissao: Permissao) -> None: ...

    @abstractmethod
    def find_by_codigo(self, codigo: str) -> Permissao | None: ...

    @abstractmethod
    def find_all(self) -> list[Permissao]: ...


class PerfilAcessoRepository(ABC):
    """Persistencia do Perfil de Acesso e suas permissoes (IMP-086)."""

    @abstractmethod
    def save(self, perfil: PerfilAcesso) -> None: ...

    @abstractmethod
    def find_by_id(self, perfil_id: uuid.UUID) -> PerfilAcesso | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[PerfilAcesso]: ...

    @abstractmethod
    def find_by_tenant_nome(self, tenant_id: uuid.UUID, nome: str) -> PerfilAcesso | None: ...

    @abstractmethod
    def atribuir_usuario(self, usuario_id: uuid.UUID, perfil_id: uuid.UUID) -> None: ...

    @abstractmethod
    def remover_usuario(self, usuario_id: uuid.UUID) -> None: ...

    @abstractmethod
    def find_by_usuario_id(self, usuario_id: uuid.UUID) -> PerfilAcesso | None: ...

    @abstractmethod
    def exists_with_permission(self, codigo: str) -> bool: ...

    @abstractmethod
    def tenant_has_permission(self, tenant_id: uuid.UUID, codigo: str) -> bool: ...

    @abstractmethod
    def count_usuarios(self, perfil_id: uuid.UUID) -> int: ...
