"""Egress conversacional — identidade e idempotência (IMP-356-E slice 1).

Antes de qualquer envio: destino normalizado pelo servidor (nunca
LID→fone, grupo ou vazio), chave idempotente derivada do vínculo
completo e payload canônico versionado. Single-tenant por processo: o
resolvedor só conhece O tenant e instância configurados; qualquer
divergência recusa sem enviar. Puro — sem rede, sem banco, sem segredo.
"""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

VERSAO_CHAVE_EGRESS = "egress/v1"

_DIGITOS = re.compile(r"\D+")


class DestinoInvalidoError(ValueError):
    """Destinatário fora do formato discável — nunca sai para o fio."""


class TokenEgressError(Exception):
    """Token ausente ou de outro dono — falha fechada, sem envio."""


class ConflitoEgressError(Exception):
    """Mesma chave (entrada+índice) com conteúdo ou contexto divergente."""


def normalizar_destino(remetente: str) -> str:
    """Reduz a dígitos e exige discável (10–15 dígitos).

    Recusa grupo, LID, vazio e curto/longo: identidade não resolvida
    nunca ganha egress, e LID nunca vira telefone.
    """
    if "@" in remetente:
        raise DestinoInvalidoError("identidade com domínio não é discável")
    digitos = _DIGITOS.sub("", remetente)
    if not 10 <= len(digitos) <= 15:
        raise DestinoInvalidoError("destinatário fora do formato discável")
    return digitos


def payload_canonico(campos: Mapping[str, Any]) -> str:
    """Serialização canônica versionada para hash e comparação."""
    return json.dumps(campos, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class IntencaoEgress:
    tenant_id: UUID
    carteira_id: UUID | None
    instancia_ref: str
    classe: str
    principal_id: UUID
    destinatario: str
    provider_input_id: str
    indice: int
    ferramenta: str | None
    call_id: str | None
    texto: str


def derivar_chave(intencao: IntencaoEgress) -> str:
    """Chave estável por entrada+índice; conteúdo divergente muda a chave."""
    material = payload_canonico(
        {
            "versao": VERSAO_CHAVE_EGRESS,
            "tenant_id": str(intencao.tenant_id),
            "carteira_id": str(intencao.carteira_id) if intencao.carteira_id else "",
            "instancia_ref": intencao.instancia_ref,
            "classe": intencao.classe,
            "principal_id": str(intencao.principal_id),
            "destinatario": intencao.destinatario,
            "provider_input_id": intencao.provider_input_id,
            "indice": intencao.indice,
            "ferramenta": intencao.ferramenta or "",
            "call_id": intencao.call_id or "",
            "texto": intencao.texto,
        }
    )
    return f"egress/v1/{hashlib.sha256(material.encode('utf-8')).hexdigest()}"


def chaves_conflitam(chave: str, payload_novo: str, payload_guardado: str) -> bool:
    """Mesma chave com payload diferente = conflito terminal, sem envio."""
    del chave
    return payload_novo != payload_guardado


class ResolvedorTokenEgress:
    """Token do tenant+instância configurados — e de mais ninguém.

    `carregar` lê o token cifrado do store (Fernet via ambiente na
    fiação real); `decifrar` abre. Divergência de tenant/instância ou
    ausência recusa com erro nomeado, sem logar segredo.
    """

    def __init__(
        self,
        tenant_id: UUID,
        instancia_ref: str,
        carregar: Callable[[UUID, str], bytes | None],
        decifrar: Callable[[bytes], str],
    ) -> None:
        self._tenant_id = tenant_id
        self._instancia_ref = instancia_ref
        self._carregar = carregar
        self._decifrar = decifrar

    def resolver(self, tenant_id: UUID, instancia_ref: str) -> str:
        if tenant_id != self._tenant_id or instancia_ref != self._instancia_ref:
            raise TokenEgressError("token de outro dono")
        cifrado = self._carregar(tenant_id, instancia_ref)
        if cifrado is None:
            raise TokenEgressError("conexão ausente")
        return self._decifrar(cifrado)


class EstadoEgress(StrEnum):
    """Máquina de estados da intenção de envio (slice 2)."""

    PREPARADO = "preparado"
    EM_ENVIO = "em_envio"
    ACEITO = "aceito"
    FALHA = "falha"
    DESCONHECIDO = "desconhecido"


_TRANSICOES_EGRESS: dict[EstadoEgress, frozenset[EstadoEgress]] = {
    EstadoEgress.PREPARADO: frozenset({EstadoEgress.EM_ENVIO, EstadoEgress.FALHA}),
    EstadoEgress.EM_ENVIO: frozenset(
        {EstadoEgress.ACEITO, EstadoEgress.FALHA, EstadoEgress.DESCONHECIDO}
    ),
    EstadoEgress.FALHA: frozenset({EstadoEgress.EM_ENVIO}),
    EstadoEgress.ACEITO: frozenset(),
    EstadoEgress.DESCONHECIDO: frozenset(),
}


def transicao_permitida(de: EstadoEgress, para: EstadoEgress) -> bool:
    """Aceito e desconhecido são terminais: nunca reenviam sozinhos."""
    return para in _TRANSICOES_EGRESS[de]


@dataclass(frozen=True)
class EgressConversa:
    """Intenção de envio persistida antes de transmitir."""

    id: UUID
    inbox_id: UUID
    sessao_id: UUID
    indice: int
    chave: str
    payload_canonico: str
    payload_hash: str
    tenant_id: UUID
    carteira_id: UUID | None
    instancia_ref: str
    classe: str
    principal_id: UUID
    destinatario: str
    ferramenta: str | None
    call_id: str | None
    estado: EstadoEgress
    tentativas: int
    provider_id: str | None = None
    codigo: str | None = None
    conciliacao_chave: str | None = None
    criado_em: datetime | None = None


class EgressRepository(ABC):
    """Porta da intenção durável de envio."""

    @abstractmethod
    def preparar(self, egresso: EgressConversa) -> EgressConversa:
        """Insere; chave/inbox+índice repetidos com mesmo payload devolvem
        o existente (replay); com payload divergente, conflito terminal."""

    @abstractmethod
    def buscar_por_chave(self, chave: str) -> EgressConversa | None: ...

    @abstractmethod
    def marcar_estado(
        self,
        egresso_id: UUID,
        para: EstadoEgress,
        provider_id: str | None = None,
        codigo: str | None = None,
    ) -> EgressConversa:
        """Transição validada; terminal não sai do lugar."""
