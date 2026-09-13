"""Conversa do agente — classificação e sessão (IMP-356-A).

Todo o contexto Operadora/PreCadastro vive aqui, separado da `Sessao` do IAM
e do `RegistroComunicacao`: o modelo nunca escolhe escopo, e remetente
desconhecido tem zero leitura de carteira. Funções puras para classificação;
persistência mora no store próprio.
"""

from __future__ import annotations

import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ClasseContexto(StrEnum):
    """As duas classes do plano — nunca uma terceira por telefone cadastrado."""

    OPERADORA = "operadora"
    PRE_CADASTRO = "pre_cadastro"


class MotivoDescarte(StrEnum):
    """Códigos fixos e seguros de descarte — nunca ecoam conteúdo."""

    SEM_ID = "sem-id"
    GRUPO = "grupo"
    PROPRIA = "propria"
    EVENTO_NAO_SUPORTADO = "evento-nao-suportado"
    INSTANCIA_DESCONHECIDA = "instancia-desconhecida"
    DUPLICADA = "duplicada"


_DIGITOS = re.compile(r"\D+")
_DOMINIO_GRUPO = "@g.us"
_DOMINIO_LID = "@lid"


def normalizar_remetente(sender: str) -> str:
    """Reduz o remetente a dígitos para comparação com a allowlist.

    JIDs (`@s.whatsapp.net`, `@lid`) viram só dígitos; LID não vira telefone
    — a identidade continua sendo o que o resolvedor autenticou, e grupo nunca
    chega aqui (descartado antes por `IsGroup`/sufixo).
    """
    local = sender.split("@", 1)[0]
    return _DIGITOS.sub("", local)


def eh_remetente_de_grupo(sender: str) -> bool:
    return sender.endswith(_DOMINIO_GRUPO)


def eh_identidade_lid(sender: str) -> bool:
    """LID não resolve Operadora: sem vínculo cadastral comprovado, é desconhecido."""
    return _DOMINIO_LID in sender


@dataclass(frozen=True)
class ConfiguracaoIngress:
    """Tudo que o ingress precisa — do servidor, nunca do envelope."""

    tenant_id: uuid.UUID
    instancia_ref: str
    allowlist_operadora: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class EntradaClassificada:
    provider_input_id: str
    remetente_normalizado: str
    classe: ClasseContexto
    texto: str | None


@dataclass(frozen=True)
class EntradaConversa:
    """Linha da inbox: fato persistido antes do ACK."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    instancia_ref: str
    envelope_instance_id: str
    provider_input_id: str
    remetente_normalizado: str
    classe: ClasseContexto
    texto: str | None
    estado: str
    recebido_em: datetime


@dataclass(frozen=True)
class SessaoConversa:
    """Contexto por remetente e classe — sem promoção automática."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    instancia_ref: str
    classe: ClasseContexto
    remetente_normalizado: str


def classificar_entrada(
    *,
    config: ConfiguracaoIngress,
    provider_input_id: str,
    sender: str,
    texto: str | None,
) -> EntradaClassificada:
    """Resolve a classe sem tocar em carteira, sessão ou histórico."""
    remetente = normalizar_remetente(sender)
    if eh_identidade_lid(sender) or remetente not in config.allowlist_operadora:
        classe = ClasseContexto.PRE_CADASTRO
    else:
        classe = ClasseContexto.OPERADORA
    return EntradaClassificada(
        provider_input_id=provider_input_id,
        remetente_normalizado=remetente,
        classe=classe,
        texto=texto,
    )


class InboxConversaRepository(ABC):
    """Porta do store durável da inbox."""

    @abstractmethod
    def salvar(self, entrada: EntradaConversa) -> bool:
        """Insere; devolve False quando a chave já existia (replay)."""
        ...

    @abstractmethod
    def buscar_por_chave(
        self,
        tenant_id: uuid.UUID,
        instancia_ref: str,
        provider_input_id: str,
    ) -> EntradaConversa | None: ...

    @abstractmethod
    def contar(self, tenant_id: uuid.UUID) -> int: ...


class SessaoConversaRepository(ABC):
    """Porta das sessões conversacionais, isoladas por classe."""

    @abstractmethod
    def garantir(
        self,
        tenant_id: uuid.UUID,
        instancia_ref: str,
        classe: ClasseContexto,
        remetente_normalizado: str,
    ) -> SessaoConversa:
        """Devolve a sessão existente ou cria; nunca promove classe."""
        ...

    @abstractmethod
    def buscar(
        self,
        tenant_id: uuid.UUID,
        instancia_ref: str,
        classe: ClasseContexto,
        remetente_normalizado: str,
    ) -> SessaoConversa | None: ...
