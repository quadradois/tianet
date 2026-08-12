"""DTOs da API REST do Credit Context — Devedor (IMP-056).

Contratos de entrada e saída dos endpoints de Devedor (FEATURE-005..FEATURE-008),
desacoplados do Aggregate (RA-012 — a Presentation nunca expõe Aggregates).

Nenhuma regra de negócio vive aqui: a validação é de fronteira (formato,
tamanho, presença). As invariantes (RN-003 ao menos um contato, RN-005 um
preferencial por tipo, DOMAIN-021 unicidade tipo+valor, validação dos dígitos
do CPF) permanecem no Domain e respondem 422 ``regra_violada``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from emprestimo.domain.credit.contato import TipoContato
from emprestimo.domain.credit.devedor import DevedorState


class ContatoPayload(BaseModel):
    """Contato informado na criação/atualização de um Devedor (DOMAIN-021)."""

    model_config = ConfigDict(extra="forbid")

    tipo: TipoContato
    valor: str = Field(min_length=1, max_length=254)
    preferencial: bool = False
    notificacao_estado: str | None = Field(default=None, pattern="^(permitido|opt_out)$")
    notificacao_evidencia: str | None = Field(default=None, min_length=1, max_length=500)
    notificacao_origem: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("valor", mode="before")
    @classmethod
    def _normalizar(cls, valor: Any) -> Any:
        if isinstance(valor, str):
            return valor.strip()
        return valor

    @model_validator(mode="after")
    def _grupo_notificacao_indivisivel(self) -> ContatoPayload:
        grupo = (
            self.notificacao_estado,
            self.notificacao_evidencia,
            self.notificacao_origem,
        )
        if any(item is not None for item in grupo) and not all(item is not None for item in grupo):
            raise ValueError("campos de consentimento devem ser informados em conjunto")
        return self


class ContatoResponse(BaseModel):
    """Representação pública de um Contato do Devedor."""

    tipo: TipoContato
    valor: str
    preferencial: bool


class DevedorCreateRequest(BaseModel):
    """Payload de cadastro de Devedor (US-015..US-020).

    O documento é aceito como informado (com ou sem máscara) e normalizado
    pelo Value Object Documento no Domain; a validação dos dígitos
    verificadores acontece lá, não aqui.
    """

    model_config = ConfigDict(extra="forbid")

    documento: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=1, max_length=200)
    contatos: list[ContatoPayload] = Field(min_length=1)

    @field_validator("documento", "nome", mode="before")
    @classmethod
    def _normalizar(cls, valor: Any) -> Any:
        if isinstance(valor, str):
            return valor.strip()
        return valor


class DevedorUpdateRequest(BaseModel):
    """Payload de atualização parcial de Devedor (US-024).

    Ambos os campos são opcionais; ``contatos``, quando informado, substitui
    a coleção inteira. O documento é imutável (INV-003) e por isso ausente.
    """

    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=1, max_length=200)
    contatos: list[ContatoPayload] | None = None

    @field_validator("nome", mode="before")
    @classmethod
    def _normalizar(cls, valor: Any) -> Any:
        if isinstance(valor, str):
            return valor.strip()
        return valor


class DevedorResponse(BaseModel):
    """DTO único do Devedor (RA-012) — usado em todas as respostas de sucesso."""

    id: uuid.UUID
    carteira_id: uuid.UUID
    documento: str
    nome: str
    contatos: list[ContatoResponse]
    estado: DevedorState
    criado_em: datetime
    atualizado_em: datetime | None = None


class DevedorListagemParams(BaseModel):
    """Parâmetros de query da listagem paginada de Devedores (US-023)."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    estado: DevedorState | None = None


class DevedorListagemResponse(BaseModel):
    """Resposta paginada da listagem de Devedores (US-023)."""

    items: list[DevedorResponse]
    total: int
    page: int
    size: int
    pages: int


class EventoHistoricoResponse(BaseModel):
    """Um evento da trilha de auditoria do Devedor (US-027).

    ``acao`` identifica a origem (ex.: ``criar.sucesso``, ``inativar.sucesso``),
    ``status`` o desfecho e ``criado_em`` o momento — os três dados que a
    US-027 exige de cada evento.
    """

    acao: str
    status: str
    detalhes: str | None = None
    criado_em: datetime


class DevedorHistoricoResponse(BaseModel):
    """Histórico cadastral do Devedor em ordem cronológica (US-027)."""

    devedor_id: uuid.UUID
    eventos: list[EventoHistoricoResponse]
