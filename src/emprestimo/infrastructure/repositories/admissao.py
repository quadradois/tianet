"""Repositório SQLAlchemy da admissão (IMP-356-C)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, cast

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from emprestimo.agent.admissao import TTL_RESERVA_SEGUNDOS, AdmissaoRepository
from emprestimo.infrastructure.db.orm import CotaEventoORM, SlotExecucaoORM


class SqlAlchemyAdmissaoRepository(AdmissaoRepository):
    """Contagens por janela e reserva de slots na mesma transação da inbox."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def contar_janela(self, escopo: str, chave: str, desde: datetime) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(CotaEventoORM)
                .where(CotaEventoORM.escopo == escopo)
                .where(CotaEventoORM.chave == chave)
                .where(CotaEventoORM.instante >= desde)
            )
            or 0
        )

    def registrar_evento(
        self,
        tenant_id: uuid.UUID,
        instancia_ref: str,
        escopo: str,
        chave: str,
        instante: datetime,
    ) -> None:
        self._session.add(
            CotaEventoORM(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                instancia_ref=instancia_ref,
                escopo=escopo,
                chave=chave,
                instante=instante,
            )
        )
        self._session.flush()

    def expurgar_antes(self, corte: datetime) -> int:
        resultado = cast(
            CursorResult[Any],
            self._session.execute(delete(CotaEventoORM).where(CotaEventoORM.instante < corte)),
        )
        return int(resultado.rowcount or 0)

    def reservar_slot(self, sessao_ref: str, *, operadora: bool, agora: datetime) -> bool:
        from datetime import timedelta

        expira = agora + timedelta(seconds=TTL_RESERVA_SEGUNDOS)
        vagas = or_(
            SlotExecucaoORM.dono_sessao.is_(None),
            SlotExecucaoORM.expira_em <= agora,
        )
        if not operadora:
            vagas = vagas & ~SlotExecucaoORM.reservado_operadora
        candidato = (
            select(SlotExecucaoORM.id)
            .where(vagas)
            .order_by(
                SlotExecucaoORM.reservado_operadora.desc() if operadora else SlotExecucaoORM.id,
                SlotExecucaoORM.id,
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        linha = self._session.execute(
            update(SlotExecucaoORM)
            .where(SlotExecucaoORM.id == candidato.scalar_subquery())
            .values(dono_sessao=sessao_ref, expira_em=expira)
            .returning(SlotExecucaoORM.id)
        ).first()
        self._session.flush()
        return linha is not None

    def liberar_slot(self, sessao_ref: str) -> None:
        self._session.execute(
            update(SlotExecucaoORM)
            .where(SlotExecucaoORM.dono_sessao == sessao_ref)
            .values(dono_sessao=None, expira_em=None)
        )
        self._session.flush()

    def liberar_expiradas(self, agora: datetime) -> int:
        resultado = cast(
            CursorResult[Any],
            self._session.execute(
                update(SlotExecucaoORM)
                .where(SlotExecucaoORM.dono_sessao.is_not(None))
                .where(SlotExecucaoORM.expira_em <= agora)
                .values(dono_sessao=None, expira_em=None)
            ),
        )
        return int(resultado.rowcount or 0)
