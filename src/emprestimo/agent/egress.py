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
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from emprestimo.domain.credit.automacao_ports import NotificationChannel
from emprestimo.domain.credit.notifications import ResultadoCanal

VERSAO_CHAVE_EGRESS = "egress/v1"

_DIGITOS = re.compile(r"\D+")


class DestinoInvalidoError(ValueError):
    """Destinatário fora do formato discável — nunca sai para o fio."""


class TokenEgressError(Exception):
    """Token ausente ou de outro dono — falha fechada, sem envio."""


class ConflitoEgressError(Exception):
    """Mesma chave (entrada+índice) com conteúdo ou contexto divergente."""


def normalizar_destino(remetente: str) -> str:
    """Normaliza o destino pelo servidor.

    Aceita dígitos discáveis (10–15) e JIDs individuais (`@s.whatsapp.net`,
    `@lid`) com parte local discável — repassados como estão. Recusa
    grupo (`@g.us`), vazio, curto/longo e LID convertido em telefone:
    identidade não resolvida nunca ganha egress.
    """
    texto = remetente.strip()
    if "@g.us" in texto:
        raise DestinoInvalidoError("grupo nunca é destino")
    if "@" in texto:
        local, _, dominio = texto.partition("@")
        if dominio not in ("s.whatsapp.net", "lid"):
            raise DestinoInvalidoError("domínio desconhecido")
        digitos = _DIGITOS.sub("", local)
        if not 10 <= len(digitos) <= 15:
            raise DestinoInvalidoError("destinatário fora do formato discável")
        return texto
    digitos = _DIGITOS.sub("", texto)
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
    principal_id: UUID | None
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


@dataclass(frozen=True)
class ContextoEnvio:
    inbox_id: UUID
    sessao_id: UUID
    tenant_id: UUID
    carteira_id: UUID | None
    instancia_ref: str
    classe: str
    principal_id: UUID | None
    remetente: str
    provider_input_id: str
    correlation_id: str = ""
    indice: int = 0
    ferramenta: str | None = None
    call_id: str | None = None


class AvisadorQuota:
    """No máximo 1 aviso por remetente a cada 60s (processo-local)."""

    JANELA_SEGUNDOS = 60

    def __init__(self, relogio: Callable[[], datetime] | None = None) -> None:
        self._relogio = relogio or (lambda: datetime.now(UTC))
        self._ultimos: dict[str, datetime] = {}

    def deve_avis_ar(self, remetente: str) -> bool:
        agora = self._relogio()
        ultimo = self._ultimos.get(remetente)
        if ultimo is not None and (agora - ultimo).total_seconds() < self.JANELA_SEGUNDOS:
            return False
        self._ultimos[remetente] = agora
        return True


def _para_intencao(contexto: ContextoEnvio, destinatario: str, texto: str) -> IntencaoEgress:
    return IntencaoEgress(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        instancia_ref=contexto.instancia_ref,
        classe=contexto.classe,
        principal_id=contexto.principal_id,
        destinatario=destinatario,
        provider_input_id=contexto.provider_input_id,
        indice=contexto.indice,
        ferramenta=contexto.ferramenta,
        call_id=contexto.call_id,
        texto=texto,
    )


def enviar_texto(
    repositorio: EgressRepository,
    canal: NotificationChannel,
    contexto: ContextoEnvio,
    texto: str,
    prazo_restante_s: float | None = None,
) -> EgressConversa:
    """Persiste a intenção, transmite e persiste o desfecho.

    Replay encontra a linha terminal sem nova chamada; divergência é
    conflito; desconhecido e falha sem prova nunca repetem sozinhos.
    No máximo 2 transmissões (tentativa + 1 retry temporário), sempre
    dentro do prazo quando informado.
    """
    import hashlib

    destinatario = normalizar_destino(contexto.remetente)
    intencao = _para_intencao(contexto, destinatario, texto)
    chave = derivar_chave(intencao)
    payload = payload_canonico(
        {
            "texto": texto,
            "destinatario": destinatario,
            "indice": contexto.indice,
            "classe": contexto.classe,
            "ferramenta": intencao.ferramenta or "",
            "call_id": intencao.call_id or "",
        }
    )
    novo = EgressConversa(
        id=uuid.uuid4(),
        inbox_id=contexto.inbox_id,
        sessao_id=contexto.sessao_id,
        indice=contexto.indice,
        chave=chave,
        payload_canonico=payload,
        payload_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        instancia_ref=contexto.instancia_ref,
        classe=contexto.classe,
        principal_id=contexto.principal_id,
        destinatario=destinatario,
        ferramenta=intencao.ferramenta,
        call_id=intencao.call_id,
        estado=EstadoEgress.PREPARADO,
        tentativas=0,
    )
    existente = repositorio.preparar(novo)
    if existente.estado != EstadoEgress.PREPARADO:
        return existente
    for _ in range(2):
        if existente.tentativas >= 2:
            return existente
        if prazo_restante_s is not None and prazo_restante_s <= 0:
            return repositorio.marcar_estado(existente.id, EstadoEgress.FALHA, codigo="deadline")
        existente = repositorio.marcar_estado(existente.id, EstadoEgress.EM_ENVIO)
        try:
            resultado = canal.enviar(
                destinatario=destinatario,
                assunto="conversa",
                corpo=texto,
                chave_idempotente=chave,
            )
        except Exception:
            return repositorio.marcar_estado(
                existente.id, EstadoEgress.DESCONHECIDO, codigo="excecao_envio"
            )
        if resultado.resultado == ResultadoCanal.ACEITA:
            return repositorio.marcar_estado(
                existente.id,
                EstadoEgress.ACEITO,
                provider_id=resultado.provider_message_id,
                codigo=resultado.codigo,
            )
        if resultado.resultado == ResultadoCanal.FALHA_PERMANENTE:
            return repositorio.marcar_estado(
                existente.id, EstadoEgress.FALHA, codigo=resultado.codigo
            )
        if resultado.resultado == ResultadoCanal.DESCONHECIDO:
            return repositorio.marcar_estado(
                existente.id, EstadoEgress.DESCONHECIDO, codigo=resultado.codigo
            )
        repositorio.marcar_estado(existente.id, EstadoEgress.FALHA, codigo=resultado.codigo)
        recarregado = repositorio.buscar_por_chave(chave)
        assert recarregado is not None
        existente = recarregado
    return existente


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
    principal_id: UUID | None
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
