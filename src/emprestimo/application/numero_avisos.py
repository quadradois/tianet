"""Numero de WhatsApp que recebe os avisos do sistema (IMP-353).

E a configuracao `credor_whatsapp` do Tenant — destino do resumo diario e do
aviso de sobra. Um numero por Tenant; gravar de novo substitui. Chave de
idempotencia obrigatoria (AD-002): mesma chave + mesmo numero = replay,
mesma chave + numero diferente = conflito.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.notifications import CHAVE_WHATSAPP_CREDOR
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.configuracao import Configuracao

ESCOPO_IDEMPOTENCIA = "whatsapp-numero-avisos"
_NAO_DIGITO = re.compile(r"\D+")


class NumeroAvisosInvalidoError(ValueError):
    """Numero fora do formato discavel (10 a 15 digitos com DDI)."""


def normalizar_numero(bruto: str) -> str:
    digitos = _NAO_DIGITO.sub("", bruto)
    if not 10 <= len(digitos) <= 15:
        raise NumeroAvisosInvalidoError("numero deve ter de 10 a 15 digitos, com DDI")
    return digitos


@dataclass(frozen=True)
class NumeroAvisos:
    numero: str | None


class NumeroAvisosService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def consultar(self, tenant_id: uuid.UUID) -> NumeroAvisos:
        with self._uow_factory() as uow:
            return NumeroAvisos(_atual(uow, tenant_id))

    def definir(
        self,
        *,
        tenant_id: uuid.UUID,
        numero: str,
        idempotency_key: str,
        usuario_id: uuid.UUID | None = None,
    ) -> NumeroAvisos:
        normalizado = normalizar_numero(numero)
        hash_solicitacao = hashlib.sha256(f"{tenant_id}:{normalizado}".encode()).hexdigest()
        with self._uow_factory() as uow:
            existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA)
            if existente is not None:
                if existente["estado"] != "finished":
                    raise IdempotenciaConflitoError(idempotency_key, "definir em andamento")
                if existente["solicitacao_hash"] != hash_solicitacao:
                    raise IdempotenciaConflitoError(idempotency_key, "resultado divergente")
                uow.commit()
                return NumeroAvisos(normalizado)
            uow.idempotencia.registrar(idempotency_key, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
            atual = next(
                (
                    c
                    for c in uow.configuracao.find_by_tenant_id(tenant_id)
                    if c.chave == CHAVE_WHATSAPP_CREDOR
                ),
                None,
            )
            # `save` faz merge por id: reusar o id existente substitui a linha em
            # vez de bater na unicidade (tenant_id, chave).
            uow.configuracao.save(
                Configuracao(
                    tenant_id=tenant_id,
                    chave=CHAVE_WHATSAPP_CREDOR,
                    valor=normalizado,
                    id=atual.id if atual is not None else uuid.uuid4(),
                )
            )
            uow.idempotencia.concluir(
                idempotency_key, ESCOPO_IDEMPOTENCIA, json.dumps({"numero": normalizado})
            )
            uow.commit()
        self._auditoria.registrar(
            "whatsapp_numero_avisos",
            tenant_id,
            "definir.sucesso",
            "ok",
            detalhes=json.dumps(
                {"usuario_id": str(usuario_id) if usuario_id else None, "numero": normalizado},
                sort_keys=True,
            ),
        )
        return NumeroAvisos(normalizado)


def _atual(uow: UnitOfWork, tenant_id: uuid.UUID) -> str | None:
    return next(
        (
            c.valor.strip()
            for c in uow.configuracao.find_by_tenant_id(tenant_id)
            if c.chave == CHAVE_WHATSAPP_CREDOR and c.valor.strip()
        ),
        None,
    )
