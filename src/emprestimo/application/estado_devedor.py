"""DevedorEstadoService — orquestrador das transições de estado do Devedor (IMP-055).

Fluxo (inativar/reativar):
1. Buscar Devedor existente por ID;
2. Aplicar a transição no Aggregate (``inativar()``/``reativar()``,
   DOMAIN-020 INV-005 — levantando ``ViolacaoInvarianteError`` se inválida);
3. Registrar trilha de auditoria (ADR-002) com evento DevedorInativado/Reativado;
4. Persistir via Unit of Work em transação única (AD-001);
5. Idempotência (AD-002): Idempotency-Key registrada na mesma transação;
   replay com a mesma chave retorna exatamente o mesmo resultado.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.credit.devedor import DevedorState
from emprestimo.domain.credit.eventos_devedor import (
    DevedorInativado,
    DevedorReativado,
)

ESCOPO_IDEMPOTENCIA = "devedor-estado"
"""Escopo da Idempotency-Key: isola chaves por caso de uso (AD-002)."""


@dataclass(frozen=True)
class DevedorEstadoAlteradoResultado:
    """Resultado da transição de estado do Devedor (IMP-055).

    Dados suficientes para a confirmação na API: identidade, documento,
    nome, estado anterior/novo e timestamp de atualização.
    """

    devedor_id: uuid.UUID
    carteira_id: uuid.UUID
    documento: str
    nome: str
    estado_anterior: DevedorState
    estado_novo: DevedorState
    atualizado_em: datetime


def _solicitacao_hash(devedor_id: uuid.UUID, acao: str) -> str:
    """Fingerprint do pedido — detecta chave reenviada com resultado divergente."""
    bruto = f"{acao}|{devedor_id}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


class DevedorEstadoService:
    """Orquestra as transições inativar/reativar de um Devedor (US-025/US-026)."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def inativar(
        self, devedor_id: uuid.UUID, idempotency_key: str
    ) -> DevedorEstadoAlteradoResultado:
        """Transição Ativo → Inativo (FEATURE-008, US-025)."""
        return self._aplicar_transicao(devedor_id, idempotency_key, "inativar")

    def reativar(
        self, devedor_id: uuid.UUID, idempotency_key: str
    ) -> DevedorEstadoAlteradoResultado:
        """Transição Inativo → Ativo (FEATURE-008, US-026)."""
        return self._aplicar_transicao(devedor_id, idempotency_key, "reativar")

    def _aplicar_transicao(
        self, devedor_id: uuid.UUID, idempotency_key: str, acao: str
    ) -> DevedorEstadoAlteradoResultado:
        """Executa a transição de estado em transação única."""
        hash_solicitacao = _solicitacao_hash(devedor_id, acao)

        self._auditoria.registrar(
            "devedor",
            devedor_id,
            f"{acao}.inicio",
            "iniciado",
            detalhes=json.dumps({"idempotency_key": idempotency_key}),
        )
        try:
            with self._uow_factory() as uow:
                resultado = self._replay_ou_registrar_chave(
                    uow, idempotency_key, hash_solicitacao, acao
                )
                if resultado is not None:
                    uow.commit()
                    return resultado

                # 1. Buscar Devedor existente
                devedor = uow.devedor.find_by_id(devedor_id)
                if devedor is None:
                    from emprestimo.application.errors import DevedorNaoEncontradoError

                    raise DevedorNaoEncontradoError(devedor_id)

                # 2. Aplicar transição (INV-005 no Aggregate)
                estado_anterior = devedor.estado
                if acao == "inativar":
                    devedor.inativar()
                else:
                    devedor.reativar()

                # 3. Trilha de auditoria — aggregate alterado
                self._auditoria.registrar(
                    "devedor",
                    devedor.id,
                    f"{acao}.estado_alterado",
                    "ok",
                    detalhes=json.dumps(
                        {
                            "devedor_id": str(devedor.id),
                            "carteira_id": str(devedor.carteira_id),
                            "estado_anterior": estado_anterior.value,
                            "estado_novo": devedor.estado.value,
                            "idempotency_key": idempotency_key,
                        }
                    ),
                )

                # 4. Persistir via UoW (mesma transação)
                uow.devedor.save(devedor)

                # 5. Evento de domínio para auditoria (ADR-002)
                carteira = uow.carteira.find_by_id(devedor.carteira_id)
                tenant_id = carteira.tenant_id if carteira else uuid.UUID(int=0)
                evento: DevedorInativado | DevedorReativado
                if acao == "inativar":
                    evento = DevedorInativado.from_devedor(devedor, tenant_id)
                    evento_chave = "inativar.evento_inativado"
                else:
                    evento = DevedorReativado.from_devedor(devedor, tenant_id)
                    evento_chave = "reativar.evento_reativado"
                self._auditoria.registrar(
                    "devedor",
                    devedor.id,
                    evento_chave,
                    "ok",
                    detalhes=json.dumps(evento.to_audit_dict()),
                )

                resultado = DevedorEstadoAlteradoResultado(
                    devedor_id=devedor.id,
                    carteira_id=devedor.carteira_id,
                    documento=devedor.documento.valor,
                    nome=devedor.nome,
                    estado_anterior=estado_anterior,
                    estado_novo=devedor.estado,
                    atualizado_em=devedor.atualizado_em or datetime.now(),
                )
                uow.idempotencia.concluir(
                    idempotency_key, ESCOPO_IDEMPOTENCIA, _serializar_resultado(resultado)
                )
                uow.commit()

            self._auditoria.registrar(
                "devedor",
                resultado.devedor_id,
                f"{acao}.sucesso",
                "ok",
                detalhes=json.dumps(
                    {"estado_novo": resultado.estado_novo.value, "idempotency_key": idempotency_key}
                ),
            )
            return resultado
        except Exception as exc:
            self._auditoria.registrar(
                "devedor",
                devedor_id,
                f"{acao}.falha",
                "falhou",
                detalhes=f"{type(exc).__name__}: {exc}",
            )
            self._auditoria.registrar(
                "devedor", devedor_id, f"{acao}.rollback", "rollback_aplicado"
            )
            raise

    def _replay_ou_registrar_chave(
        self, uow: UnitOfWork, idempotency_key: str, hash_solicitacao: str, acao: str
    ) -> DevedorEstadoAlteradoResultado | None:
        """Replay seguro (AD-002): mesma chave → mesmo resultado; divergente → conflito."""
        existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA)
        if existente is None:
            uow.idempotencia.registrar(idempotency_key, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
            return None
        # Verifica estado ANTES do hash: se em andamento, bloqueia independentemente do hash
        if existente["estado"] != "finished":
            raise IdempotenciaConflitoError(idempotency_key, f"{acao} em andamento")
        if existente["solicitacao_hash"] != hash_solicitacao:
            raise IdempotenciaConflitoError(idempotency_key, "resultado divergente")
        self._auditoria.registrar(
            "devedor",
            None,
            f"{acao}.replay",
            "ok",
            detalhes=json.dumps({"idempotency_key": idempotency_key}),
        )
        return _desserializar_resultado(existente["resultado"])


def _serializar_resultado(resultado: DevedorEstadoAlteradoResultado) -> str:
    return json.dumps(
        {
            "devedor_id": str(resultado.devedor_id),
            "carteira_id": str(resultado.carteira_id),
            "documento": resultado.documento,
            "nome": resultado.nome,
            "estado_anterior": resultado.estado_anterior.value,
            "estado_novo": resultado.estado_novo.value,
            "atualizado_em": resultado.atualizado_em.isoformat(),
        }
    )


def _desserializar_resultado(conteudo: str | None) -> DevedorEstadoAlteradoResultado:
    if not conteudo:
        raise IdempotenciaConflitoError("?", "resultado ausente no registro")
    dados = json.loads(conteudo)
    return DevedorEstadoAlteradoResultado(
        devedor_id=uuid.UUID(dados["devedor_id"]),
        carteira_id=uuid.UUID(dados["carteira_id"]),
        documento=dados["documento"],
        nome=dados["nome"],
        estado_anterior=DevedorState(dados["estado_anterior"]),
        estado_novo=DevedorState(dados["estado_novo"]),
        atualizado_em=datetime.fromisoformat(dados["atualizado_em"]),
    )
