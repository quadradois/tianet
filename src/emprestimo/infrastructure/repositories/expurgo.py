"""Expurgo SQL das tabelas conversacionais (IMP-356-F slice 4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from emprestimo.agent.expurgo import ExpurgoRepository
from emprestimo.infrastructure.db.orm import (
    CredencialCopilotORM,
    InboxConversaORM,
    MensagemConversaORM,
    ReferenciaSessaoORM,
    SessaoConversaORM,
    ToolCallExecORM,
)


def _apagar_lote(session: Session, modelo: Any, condicao: Any, lote: int) -> int:
    ids = list(session.scalars(select(modelo.id).where(condicao).order_by(modelo.id).limit(lote)))
    if not ids:
        return 0
    session.execute(delete(modelo).where(modelo.id.in_(ids)))
    session.flush()
    return len(ids)


class SqlAlchemyExpurgoRepository(ExpurgoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def remover_mensagens_antigas(self, corte: datetime, lote: int) -> int:
        return _apagar_lote(
            self._session, MensagemConversaORM, MensagemConversaORM.criado_em < corte, lote
        )

    def remover_tool_calls_antigos(self, corte: datetime, lote: int) -> int:
        return _apagar_lote(self._session, ToolCallExecORM, ToolCallExecORM.criado_em < corte, lote)

    def remover_referencias_expiradas(self, agora: datetime, lote: int) -> int:
        return _apagar_lote(
            self._session, ReferenciaSessaoORM, ReferenciaSessaoORM.expira_em < agora, lote
        )

    def remover_credenciais_antigas(self, corte: datetime, lote: int) -> int:
        return _apagar_lote(
            self._session,
            CredencialCopilotORM,
            CredencialCopilotORM.atualizado_em < corte,
            lote,
        )

    def remover_sessoes_antigas(self, corte: datetime, lote: int) -> int:
        recentes = select(MensagemConversaORM.sessao_id).where(
            MensagemConversaORM.criado_em >= corte
        )
        return _apagar_lote(
            self._session,
            SessaoConversaORM,
            (SessaoConversaORM.criado_em < corte) & (SessaoConversaORM.id.not_in(recentes)),
            lote,
        )

    def remover_inbox_antiga(self, corte: datetime, lote: int) -> int:
        return _apagar_lote(
            self._session, InboxConversaORM, InboxConversaORM.recebido_em < corte, lote
        )
