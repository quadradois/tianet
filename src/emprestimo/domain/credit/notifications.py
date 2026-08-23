"""Dominio de notificacoes transacionais do EPIC-010."""

from __future__ import annotations

import hashlib
import json
import string
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from emprestimo.domain.common.errors import ViolacaoInvarianteError


class EstadoPreferenciaNotificacao(StrEnum):
    PERMITIDO = "permitido"
    OPT_OUT = "opt_out"
    REVOGADO = "revogado"


class EstadoTemplateNotificacao(StrEnum):
    RASCUNHO = "rascunho"
    APROVADO = "aprovado"
    ATIVO = "ativo"
    INATIVO = "inativo"


class EstadoSolicitacaoNotificacao(StrEnum):
    PREPARADA = "preparada"
    ACEITA = "aceita"
    FALHA_TEMPORARIA = "falha_temporaria"
    FALHA_PERMANENTE = "falha_permanente"
    RESULTADO_DESCONHECIDO = "resultado_desconhecido"
    CONCILIADA = "conciliada"


class ResultadoCanal(StrEnum):
    ACEITA = "aceita"
    FALHA_TEMPORARIA = "falha_temporaria"
    FALHA_PERMANENTE = "falha_permanente"
    DESCONHECIDO = "desconhecido"


@dataclass
class PreferenciaNotificacao:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    contato_id: uuid.UUID
    estado: EstadoPreferenciaNotificacao
    evidencia: str
    origem: str
    ator_id: uuid.UUID
    registrada_em: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    revogada_em: datetime | None = None

    def __post_init__(self) -> None:
        if not self.evidencia.strip() or not self.origem.strip():
            raise ViolacaoInvarianteError("EPIC-010", "evidencia e origem sao obrigatorias")
        if self.registrada_em.tzinfo is None:
            raise ViolacaoInvarianteError("EPIC-010", "instante deve possuir timezone")

    @property
    def permite_envio(self) -> bool:
        return self.estado is EstadoPreferenciaNotificacao.PERMITIDO and self.revogada_em is None

    def revogar(self, *, agora: datetime) -> None:
        if agora.tzinfo is None:
            raise ViolacaoInvarianteError("EPIC-010", "instante deve possuir timezone")
        self.estado = EstadoPreferenciaNotificacao.REVOGADO
        self.revogada_em = agora


@dataclass
class TemplateNotificacao:
    tenant_id: uuid.UUID
    codigo: str
    versao: int
    assunto: str
    corpo: str
    parametros_permitidos: tuple[str, ...]
    criado_por_usuario_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    estado: EstadoTemplateNotificacao = EstadoTemplateNotificacao.RASCUNHO
    aprovado_por_usuario_id: uuid.UUID | None = None
    aprovado_em: datetime | None = None
    ativado_em: datetime | None = None
    motivo_aprovacao: str | None = None

    def __post_init__(self) -> None:
        if not self.codigo.strip() or self.versao < 1:
            raise ViolacaoInvarianteError("EPIC-010", "codigo e versao de template invalidos")
        if not self.assunto.strip() or not self.corpo.strip():
            raise ViolacaoInvarianteError("EPIC-010", "template vazio")
        if set(self.parametros_permitidos) != {"data_hora", "canal_atendimento"}:
            raise ViolacaoInvarianteError("EPIC-010", "allowlist de template invalida")
        permitidos = set(self.parametros_permitidos)
        for texto in (self.assunto, self.corpo):
            try:
                campos = [campo for _, campo, _, _ in string.Formatter().parse(texto) if campo]
            except ValueError as exc:
                raise ViolacaoInvarianteError("EPIC-010", "sintaxe de template invalida") from exc
            if any(campo not in permitidos or "." in campo or "[" in campo for campo in campos):
                raise ViolacaoInvarianteError(
                    "EPIC-010", "template usa parametro fora da allowlist"
                )

    @property
    def hash_conteudo(self) -> str:
        bruto = json.dumps(
            {
                "assunto": self.assunto,
                "corpo": self.corpo,
                "parametros": sorted(self.parametros_permitidos),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(bruto.encode()).hexdigest()

    def aprovar(self, *, usuario_id: uuid.UUID, motivo: str, agora: datetime) -> None:
        if self.estado is not EstadoTemplateNotificacao.RASCUNHO:
            raise ViolacaoInvarianteError("EPIC-010", "somente rascunho pode ser aprovado")
        if not motivo.strip():
            raise ViolacaoInvarianteError("EPIC-010", "motivo de aprovacao obrigatorio")
        self.estado = EstadoTemplateNotificacao.APROVADO
        self.aprovado_por_usuario_id = usuario_id
        self.aprovado_em = agora
        self.motivo_aprovacao = motivo

    def ativar(self, *, agora: datetime) -> None:
        if self.estado is not EstadoTemplateNotificacao.APROVADO:
            raise ViolacaoInvarianteError("EPIC-010", "template precisa estar aprovado")
        self.estado = EstadoTemplateNotificacao.ATIVO
        self.ativado_em = agora


@dataclass(frozen=True)
class ResultadoEnvio:
    resultado: ResultadoCanal
    provider_message_id: str | None = None
    codigo: str | None = None
    chave_idempotente: str | None = None
    ocorrido_em: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class SolicitacaoNotificacao:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    lembrete_id: uuid.UUID | None
    job_id: uuid.UUID
    tentativa_job_id: uuid.UUID
    contato_id: uuid.UUID
    template_id: uuid.UUID | None
    chave_idempotente: str
    payload_canonico: dict[str, Any]
    payload_hash: str
    versao_solicitacao: int = 1
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    preparada_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    estado: EstadoSolicitacaoNotificacao = EstadoSolicitacaoNotificacao.PREPARADA
    provider_message_id: str | None = None
    resultado_em: datetime | None = None
    codigo_resultado: str | None = None
    conciliacao_chave: str | None = None

    def __post_init__(self) -> None:
        if self.preparada_em.tzinfo is None or self.preparada_em.utcoffset() is None:
            raise ViolacaoInvarianteError("EPIC-010", "preparada_em deve possuir timezone")

    @classmethod
    def preparar(
        cls,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        lembrete_id: uuid.UUID,
        job_id: uuid.UUID,
        tentativa_job_id: uuid.UUID,
        contato_id: uuid.UUID,
        template_id: uuid.UUID,
        chave_idempotente: str,
        payload: dict[str, Any],
    ) -> SolicitacaoNotificacao:
        if not chave_idempotente.strip() or "@" in chave_idempotente:
            raise ViolacaoInvarianteError("EPIC-010", "chave idempotente invalida")
        canonico = json.loads(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        bruto = json.dumps(canonico, sort_keys=True, separators=(",", ":"))
        return cls(
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            lembrete_id=lembrete_id,
            job_id=job_id,
            tentativa_job_id=tentativa_job_id,
            contato_id=contato_id,
            template_id=template_id,
            chave_idempotente=chave_idempotente,
            payload_canonico=canonico,
            payload_hash=hashlib.sha256(bruto.encode()).hexdigest(),
        )

    @classmethod
    def preparar_comprovante(
        cls,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        job_id: uuid.UUID,
        tentativa_job_id: uuid.UUID,
        contato_id: uuid.UUID,
        chave_idempotente: str,
        payload: dict[str, Any],
    ) -> SolicitacaoNotificacao:
        """Prepara notificacao transacional cujo texto ja nasceu do Motor."""

        if not chave_idempotente.strip() or "@" in chave_idempotente:
            raise ViolacaoInvarianteError("EPIC-010", "chave idempotente invalida")
        canonico = json.loads(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        bruto = json.dumps(canonico, sort_keys=True, separators=(",", ":"))
        return cls(
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            lembrete_id=None,
            job_id=job_id,
            tentativa_job_id=tentativa_job_id,
            contato_id=contato_id,
            template_id=None,
            chave_idempotente=chave_idempotente,
            payload_canonico=canonico,
            payload_hash=hashlib.sha256(bruto.encode()).hexdigest(),
        )

    def registrar_resultado(self, resultado: ResultadoEnvio) -> None:
        if self.estado is not EstadoSolicitacaoNotificacao.PREPARADA:
            raise ViolacaoInvarianteError("EPIC-010", "solicitacao ja possui resultado")
        mapa = {
            ResultadoCanal.ACEITA: EstadoSolicitacaoNotificacao.ACEITA,
            ResultadoCanal.FALHA_TEMPORARIA: EstadoSolicitacaoNotificacao.FALHA_TEMPORARIA,
            ResultadoCanal.FALHA_PERMANENTE: EstadoSolicitacaoNotificacao.FALHA_PERMANENTE,
            ResultadoCanal.DESCONHECIDO: EstadoSolicitacaoNotificacao.RESULTADO_DESCONHECIDO,
        }
        self.estado = mapa[resultado.resultado]
        self.provider_message_id = resultado.provider_message_id
        self.codigo_resultado = resultado.codigo
        self.resultado_em = resultado.ocorrido_em

    def preparar_retry(self, *, tentativa_job_id: uuid.UUID, agora: datetime) -> None:
        if self.estado is not EstadoSolicitacaoNotificacao.FALHA_TEMPORARIA:
            raise ViolacaoInvarianteError("EPIC-010", "somente falha temporaria permite retry")
        if agora.tzinfo is None or agora.utcoffset() is None:
            raise ViolacaoInvarianteError("EPIC-010", "instante deve possuir timezone")
        if agora - self.preparada_em >= timedelta(hours=24):
            raise ViolacaoInvarianteError("EPIC-010", "janela idempotente expirada")
        self.tentativa_job_id = tentativa_job_id
        self.estado = EstadoSolicitacaoNotificacao.PREPARADA
        self.provider_message_id = None
        self.resultado_em = None
        self.codigo_resultado = None

    def conciliar(self, resultado: ResultadoEnvio, *, idempotency_key: str) -> bool:
        if self.estado is EstadoSolicitacaoNotificacao.CONCILIADA:
            if (
                self.conciliacao_chave == idempotency_key
                and self.provider_message_id == resultado.provider_message_id
                and resultado.chave_idempotente == self.chave_idempotente
            ):
                return False
            raise ViolacaoInvarianteError("EPIC-010", "evidencia de conciliacao divergente")
        if self.estado is not EstadoSolicitacaoNotificacao.RESULTADO_DESCONHECIDO:
            raise ViolacaoInvarianteError(
                "EPIC-010", "somente resultado desconhecido e conciliavel"
            )
        if resultado.resultado is ResultadoCanal.DESCONHECIDO:
            raise ViolacaoInvarianteError("EPIC-010", "conciliacao exige evidencia conclusiva")
        if resultado.chave_idempotente != self.chave_idempotente:
            raise ViolacaoInvarianteError("EPIC-010", "evidencia nao pertence a solicitacao")
        self.estado = EstadoSolicitacaoNotificacao.CONCILIADA
        self.provider_message_id = resultado.provider_message_id
        self.codigo_resultado = resultado.codigo
        self.resultado_em = resultado.ocorrido_em
        self.conciliacao_chave = idempotency_key
        return True
