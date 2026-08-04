"""DTOs da API REST (RA-012 — Presentation nunca expõe Aggregates).

Contratos de entrada e saída de IMP-017/018/026/027/032, desacoplados das
entidades de domínio. Nenhuma regra de negócio vive aqui; apenas validação
de entrada e serialização.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from emprestimo.domain.platform.tenant import TenantState


class TenantCreateRequest(BaseModel):
    """Payload de criação de Tenant (US-001 — dados obrigatórios)."""

    model_config = ConfigDict(extra="forbid")

    identificador_institucional: str = Field(min_length=1, max_length=120)
    nome: str = Field(min_length=1, max_length=200)
    nome_administrador: str = Field(min_length=1, max_length=200)
    email_administrador: str = Field(min_length=3, max_length=254)

    @field_validator("*", mode="before")
    @classmethod
    def _normalizar_texto(cls, valor: Any) -> Any:
        if isinstance(valor, str):
            return valor.strip()
        return valor

    @field_validator("identificador_institucional", "nome", "nome_administrador")
    @classmethod
    def _nao_vazio(cls, valor: str) -> str:
        if not valor:
            raise ValueError("campo obrigatório não pode ser vazio")
        return valor

    @field_validator("email_administrador")
    @classmethod
    def _email_basico(cls, valor: str) -> str:
        if "@" not in valor or valor.startswith("@") or valor.endswith("@"):
            raise ValueError("e-mail inválido")
        return valor


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
