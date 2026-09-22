"""Chave Pix da Credora (IMP-390, PLAN-045 §3.12-b).

E o que o agente envia ao devedor no caminho **sem taxa**: "paga aqui e me
manda o comprovante". Sem chave configurada, o agente nao promete Pix — ele
informa os valores e encaminha a conversa para a Credora.

Configuracao do Tenant, nao segredo: chave Pix e dado publico por construcao
(quem paga precisa dela). Por isso vive em `configuracao`, ao lado do
`credor_whatsapp`, e nao na cifra.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.configuracao import Configuracao

__all__ = [
    "CHAVE_PIX_TIPO",
    "CHAVE_PIX_VALOR",
    "CHAVE_PIX_FAVORECIDO",
    "ChavePixCredora",
    "ChavePixInvalidaError",
    "ChavePixService",
    "TipoChavePix",
]

CHAVE_PIX_TIPO = "credor_pix_tipo"
CHAVE_PIX_VALOR = "credor_pix_valor"
CHAVE_PIX_FAVORECIDO = "credor_pix_favorecido"
ESCOPO_IDEMPOTENCIA = "platform-chave-pix"
RECURSO_AUDITORIA = "chave_pix_credora"

_SO_DIGITOS = re.compile(r"^\d+$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ALEATORIA = re.compile(r"^[0-9a-fA-F-]{32,36}$")


class TipoChavePix(StrEnum):
    CPF = "cpf"
    CNPJ = "cnpj"
    TELEFONE = "telefone"
    EMAIL = "email"
    ALEATORIA = "aleatoria"


class ChavePixInvalidaError(ValueError):
    """Formato incompativel com o tipo declarado."""

    def __init__(self, motivo: str) -> None:
        super().__init__(f"chave Pix invalida: {motivo}")
        self.motivo = motivo


@dataclass(frozen=True)
class ChavePixCredora:
    """Ausente quando o Tenant ainda nao configurou — e isso nao e erro."""

    tipo: TipoChavePix | None
    valor: str | None
    favorecido: str | None

    @property
    def configurada(self) -> bool:
        return self.tipo is not None and bool(self.valor)


def validar(tipo: TipoChavePix, valor: str) -> str:
    """Normaliza e recusa o que o banco recusaria — antes de o devedor tentar.

    Uma chave errada so apareceria quando alguem tentasse pagar, e a mensagem
    do banco nao chega ate a Credora. Validar aqui e barato e evita isso.
    """
    limpo = valor.strip()
    if not limpo:
        raise ChavePixInvalidaError("valor_vazio")
    if tipo in (TipoChavePix.CPF, TipoChavePix.CNPJ, TipoChavePix.TELEFONE):
        digitos = re.sub(r"\D+", "", limpo)
        esperado = {TipoChavePix.CPF: 11, TipoChavePix.CNPJ: 14}.get(tipo)
        if esperado is not None and len(digitos) != esperado:
            raise ChavePixInvalidaError(f"{tipo.value}_com_digitos_invalidos")
        if tipo is TipoChavePix.TELEFONE and not 10 <= len(digitos) <= 15:
            raise ChavePixInvalidaError("telefone_com_digitos_invalidos")
        if not _SO_DIGITOS.match(digitos):
            raise ChavePixInvalidaError("formato_invalido")
        return digitos
    if tipo is TipoChavePix.EMAIL:
        if not _EMAIL.match(limpo):
            raise ChavePixInvalidaError("email_invalido")
        return limpo.lower()
    if not _ALEATORIA.match(limpo):
        raise ChavePixInvalidaError("aleatoria_invalida")
    return limpo.lower()


class ChavePixService:
    """Le e grava a chave Pix que o agente oferece ao devedor."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def consultar(self, *, tenant_id: uuid.UUID) -> ChavePixCredora:
        with self._uow_factory() as uow:
            valores = {
                item.chave: item.valor
                for item in uow.configuracao.find_by_tenant_id(tenant_id)
                if item.chave in (CHAVE_PIX_TIPO, CHAVE_PIX_VALOR, CHAVE_PIX_FAVORECIDO)
            }
        tipo = valores.get(CHAVE_PIX_TIPO)
        return ChavePixCredora(
            tipo=TipoChavePix(tipo) if tipo else None,
            valor=valores.get(CHAVE_PIX_VALOR),
            favorecido=valores.get(CHAVE_PIX_FAVORECIDO),
        )

    def definir(
        self,
        *,
        tenant_id: uuid.UUID,
        tipo: str,
        valor: str,
        favorecido: str,
        usuario_id: uuid.UUID,
        idempotency_key: str,
    ) -> ChavePixCredora:
        try:
            tipo_valido = TipoChavePix(tipo)
        except ValueError as exc:
            raise ChavePixInvalidaError("tipo_desconhecido") from exc
        normalizado = validar(tipo_valido, valor)
        nome = favorecido.strip()
        if not nome:
            raise ChavePixInvalidaError("favorecido_vazio")
        hash_solicitacao = hashlib.sha256(
            f"{tenant_id}:{tipo_valido.value}:{normalizado}:{nome}".encode()
        ).hexdigest()

        with self._uow_factory() as uow:
            existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA)
            if existente is not None:
                if existente["estado"] != "finished":
                    raise IdempotenciaConflitoError(idempotency_key, "definir em andamento")
                if existente["solicitacao_hash"] != hash_solicitacao:
                    raise IdempotenciaConflitoError(idempotency_key, "solicitacao divergente")
                uow.commit()
                return ChavePixCredora(tipo_valido, normalizado, nome)
            uow.idempotencia.registrar(idempotency_key, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
            atuais = {
                item.chave: item
                for item in uow.configuracao.find_by_tenant_id(tenant_id)
                if item.chave in (CHAVE_PIX_TIPO, CHAVE_PIX_VALOR, CHAVE_PIX_FAVORECIDO)
            }
            for chave, conteudo in (
                (CHAVE_PIX_TIPO, tipo_valido.value),
                (CHAVE_PIX_VALOR, normalizado),
                (CHAVE_PIX_FAVORECIDO, nome),
            ):
                anterior = atuais.get(chave)
                # `save` faz merge por id: reusar o id existente substitui a
                # linha em vez de bater na unicidade (tenant_id, chave).
                uow.configuracao.save(
                    Configuracao(
                        tenant_id=tenant_id,
                        chave=chave,
                        valor=conteudo,
                        id=anterior.id if anterior is not None else uuid.uuid4(),
                    )
                )
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA,
                json.dumps({"tipo": tipo_valido.value}),
            )
            uow.commit()
        self._auditoria.registrar(
            RECURSO_AUDITORIA,
            tenant_id,
            "definir.sucesso",
            "ok",
            detalhes=json.dumps(
                {"usuario_id": str(usuario_id), "tipo": tipo_valido.value}, sort_keys=True
            ),
        )
        return ChavePixCredora(tipo_valido, normalizado, nome)
