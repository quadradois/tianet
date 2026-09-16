"""Intenção durável de egress (IMP-356-E slice 2)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from emprestimo.agent.egress import (
    ConflitoEgressError,
    EgressConversa,
    EgressRepository,
    EstadoEgress,
    chaves_conflitam,
    transicao_permitida,
)
from emprestimo.infrastructure.db.orm import EgressConversaORM


def _to_egress(row: EgressConversaORM) -> EgressConversa:
    return EgressConversa(
        id=row.id,
        inbox_id=row.inbox_id,
        sessao_id=row.sessao_id,
        indice=row.indice,
        chave=row.chave,
        payload_canonico=row.payload_canonico,
        payload_hash=row.payload_hash,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        instancia_ref=row.instancia_ref,
        classe=row.classe,
        principal_id=row.principal_id,
        destinatario=row.destinatario,
        ferramenta=row.ferramenta,
        call_id=row.call_id,
        estado=EstadoEgress(row.estado),
        tentativas=row.tentativas,
        provider_id=row.provider_id,
        codigo=row.codigo,
        conciliacao_chave=row.conciliacao_chave,
        criado_em=row.criado_em,
    )


class SqlAlchemyEgressRepository(EgressRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def preparar(self, egresso: EgressConversa) -> EgressConversa:
        existente = self.buscar_por_chave(egresso.chave)
        if existente is not None:
            if chaves_conflitam(
                egresso.chave, egresso.payload_canonico, existente.payload_canonico
            ):
                raise ConflitoEgressError("mesma chave com conteúdo divergente")
            return existente
        mesma_destino = self._session.scalars(
            select(EgressConversaORM)
            .where(EgressConversaORM.inbox_id == egresso.inbox_id)
            .where(EgressConversaORM.indice == egresso.indice)
        ).one_or_none()
        if mesma_destino is not None:
            if chaves_conflitam(
                mesma_destino.chave, egresso.payload_canonico, mesma_destino.payload_canonico
            ):
                raise ConflitoEgressError("mesmo destino com conteúdo divergente")
            return _to_egress(mesma_destino)
        row = EgressConversaORM(
            id=egresso.id,
            inbox_id=egresso.inbox_id,
            sessao_id=egresso.sessao_id,
            indice=egresso.indice,
            chave=egresso.chave,
            payload_canonico=egresso.payload_canonico,
            payload_hash=egresso.payload_hash,
            tenant_id=egresso.tenant_id,
            carteira_id=egresso.carteira_id,
            instancia_ref=egresso.instancia_ref,
            classe=egresso.classe,
            principal_id=egresso.principal_id,
            destinatario=egresso.destinatario,
            ferramenta=egresso.ferramenta,
            call_id=egresso.call_id,
            estado=egresso.estado.value,
            tentativas=egresso.tentativas,
            provider_id=egresso.provider_id,
            codigo=egresso.codigo,
            conciliacao_chave=egresso.conciliacao_chave,
        )
        try:
            with self._session.begin_nested():
                self._session.add(row)
                self._session.flush()
        except IntegrityError as exc:
            # Corrida: outro executor persistiu primeiro; lê o vencedor.
            vencedor = self.buscar_por_chave(egresso.chave)
            assert vencedor is not None
            if chaves_conflitam(egresso.chave, egresso.payload_canonico, vencedor.payload_canonico):
                raise ConflitoEgressError("mesma chave com conteúdo divergente") from exc
            return vencedor
        return _to_egress(row)

    def buscar_por_chave(self, chave: str) -> EgressConversa | None:
        row = self._session.scalars(
            select(EgressConversaORM).where(EgressConversaORM.chave == chave)
        ).one_or_none()
        return _to_egress(row) if row is not None else None

    def listar_incertos_por_sessao(self, sessao_id: UUID) -> list[EgressConversa]:
        rows = self._session.scalars(
            select(EgressConversaORM)
            .where(EgressConversaORM.sessao_id == sessao_id)
            .where(
                EgressConversaORM.estado.in_(
                    [EstadoEgress.EM_ENVIO.value, EstadoEgress.DESCONHECIDO.value]
                )
            )
            .order_by(EgressConversaORM.criado_em)
        ).all()
        return [_to_egress(row) for row in rows]

    def marcar_estado(
        self,
        egresso_id: UUID,
        para: EstadoEgress,
        provider_id: str | None = None,
        codigo: str | None = None,
    ) -> EgressConversa:
        row = self._session.get(EgressConversaORM, egresso_id)
        assert row is not None
        atual = EstadoEgress(row.estado)
        if not transicao_permitida(atual, para):
            raise ConflitoEgressError(f"transição {atual.value}→{para.value} proibida")
        row.estado = para.value
        row.provider_id = provider_id
        row.codigo = codigo
        if para == EstadoEgress.EM_ENVIO:
            row.tentativas = row.tentativas + 1
        row.atualizado_em = datetime.now().astimezone()
        self._session.flush()
        return _to_egress(row)
