"""DTOs da API REST (RA-012 — Presentation nunca expõe Aggregates).

Contratos de entrada e saída de IMP-017/018/026/027/032, desacoplados das
entidades de domínio. Nenhuma regra de negócio vive aqui; apenas validação
de entrada e serialização.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from emprestimo.domain.platform.perfil import PerfilState
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.domain.platform.usuario import UsuarioState


class TenantResponse(BaseModel):
    """Representação pública de um Tenant (POST 201 e GET 200).

    Exposição mínima: identidade, dados institucionais, estado e criação.
    Nenhum dado interno de infraestrutura é exposto.
    """

    id: uuid.UUID
    identificador_institucional: str
    nome: str
    estado: TenantState
    criado_em: datetime


class TenantListagemParams(BaseModel):
    """Parâmetros de query para listagem paginada de Tenants (IMP-027, US-011)."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    sort: str = Field(
        default="criado_em:asc",
        pattern=r"^(criado_em|identificador_institucional|nome|estado):(asc|desc)$",
    )
    estado: TenantState | None = None


class TenantListagemResponse(BaseModel):
    """Resposta paginada de listagem de Tenants (IMP-027)."""

    items: list[TenantResponse]
    total: int
    page: int
    size: int
    pages: int


class TenantUpdateRequest(BaseModel):
    """Payload de atualização parcial do Tenant (IMP-032, US-012, DA-205).

    Apenas o nome é atualizável no MVP (FEATURE-003). Regras de domínio
    (não vazio, <= 200 caracteres) permanecem no Aggregate (IMP-029) —
    a violação responde 422 ``regra_violada`` pelo handler do main.py.
    """

    model_config = ConfigDict(extra="forbid")

    nome: str

    @field_validator("nome", mode="before")
    @classmethod
    def _normalizar_texto(cls, valor: Any) -> Any:
        if isinstance(valor, str):
            return valor.strip()
        return valor


class ErroResponse(BaseModel):
    """Corpo padronizado de erro da API."""

    codigo: str
    mensagem: str


class HealthResponse(BaseModel):
    """Resposta publica minima do healthcheck operacional."""

    status: Literal["healthy", "degraded", "unhealthy"]
    service: str
    checks: dict[str, Literal["healthy", "degraded", "unhealthy"]]


class AuthLoginRequest(BaseModel):
    """Payload de login por Tenant, e-mail e credencial (IMP-090)."""

    model_config = ConfigDict(extra="forbid")

    identificador_institucional: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    segredo: str = Field(min_length=1)

    @field_validator("identificador_institucional", "email", "segredo", mode="before")
    @classmethod
    def _normalizar_texto(cls, valor: Any) -> Any:
        if isinstance(valor, str):
            return valor.strip()
        return valor


class AuthRefreshRequest(BaseModel):
    """Payload para renovar access token ou encerrar sessao via refresh token."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)

    @field_validator("refresh_token", mode="before")
    @classmethod
    def _normalizar_refresh(cls, valor: Any) -> Any:
        if isinstance(valor, str):
            return valor.strip()
        return valor


class AuthLoginResponse(BaseModel):
    """Resposta de login com access token curto e refresh token persistido."""

    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    token_type: str = "bearer"
    access_token: str
    access_token_expira_em: datetime
    refresh_token: str
    refresh_token_expira_em: datetime


class AuthRefreshResponse(BaseModel):
    """Resposta da renovacao contendo apenas novo access token."""

    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    token_type: str = "bearer"
    access_token: str
    access_token_expira_em: datetime


class AuthLogoutResponse(BaseModel):
    """Resposta simples do encerramento de sessao."""

    status: str


class UsuarioCreateRequest(BaseModel):
    """Payload de criacao de Usuario (IMP-355)."""

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=254)
    segredo: str = Field(min_length=1)

    @field_validator("nome", "email", mode="before")
    @classmethod
    def _normalizar(cls, valor: Any) -> Any:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("email")
    @classmethod
    def _email_basico(cls, valor: str) -> str:
        if "@" not in valor or valor.startswith("@") or valor.endswith("@"):
            raise ValueError("e-mail invalido")
        return valor


class UsuarioResponse(BaseModel):
    """DTO unico de Usuario (RA-012). Nunca expoe segredo nem hash."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    email: str
    estado: UsuarioState
    perfil_acesso: str | None = None
    criado_em: datetime


class AlterarCredencialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    segredo_atual: str = Field(min_length=1)
    novo_segredo: str = Field(min_length=1)


class RedefinirCredencialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    novo_segredo: str = Field(min_length=1)


class CredencialResponse(BaseModel):
    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    estado: UsuarioState


class PerfilCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(min_length=1, max_length=120)


class PerfilUpdateRequest(PerfilCreateRequest):
    pass


class PerfilResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    estado: PerfilState
    permissoes: list[str]


class PermissoesEfetivasResponse(BaseModel):
    usuario_id: uuid.UUID
    perfil_id: uuid.UUID | None
    perfil_nome: str | None
    permissoes: list[str]


class ContextoUsuarioResponse(BaseModel):
    id: uuid.UUID
    nome: str
    email: str


class ContextoTenantResponse(BaseModel):
    id: uuid.UUID
    nome: str
    identificador_institucional: str


class ContextoCarteiraResponse(BaseModel):
    id: uuid.UUID
    nome: str


class ContextoPerfilResponse(BaseModel):
    id: uuid.UUID
    nome: str


class ContextoOperacionalResponse(BaseModel):
    usuario: ContextoUsuarioResponse
    tenant: ContextoTenantResponse
    carteira_padrao: ContextoCarteiraResponse
    perfil: ContextoPerfilResponse | None
    permissoes: list[str]


class PermissaoCatalogoItemResponse(BaseModel):
    codigo: str
    descricao: str
    grupo: str


class PermissoesCatalogoResponse(BaseModel):
    versao: str
    itens: list[PermissaoCatalogoItemResponse]
