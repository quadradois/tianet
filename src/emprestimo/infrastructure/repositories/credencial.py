"""Store do refresh cifrado do copiloto (IMP-356-F slice 2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from emprestimo.agent.credencial import ArmazenRefresh
from emprestimo.infrastructure.db.orm import CredencialCopilotORM


class SqlAlchemyArmazenRefresh(ArmazenRefresh):
    """Upsert por (tenant, instância); leitura nunca cria linha."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(
        self, tenant_id: UUID, instancia_ref: str, refresh_cifrado: bytes, chave_id: str
    ) -> None:
        row = self._session.scalars(
            select(CredencialCopilotORM)
            .where(CredencialCopilotORM.tenant_id == tenant_id)
            .where(CredencialCopilotORM.instancia_ref == instancia_ref)
        ).one_or_none()
        agora = datetime.now().astimezone()
        if row is None:
            try:
                with self._session.begin_nested():
                    self._session.add(
                        CredencialCopilotORM(
                            id=uuid.uuid4(),
                            tenant_id=tenant_id,
                            instancia_ref=instancia_ref,
                            refresh_cifrado=refresh_cifrado,
                            chave_id=chave_id,
                        )
                    )
                    self._session.flush()
            except IntegrityError:
                row = self._session.scalars(
                    select(CredencialCopilotORM)
                    .where(CredencialCopilotORM.tenant_id == tenant_id)
                    .where(CredencialCopilotORM.instancia_ref == instancia_ref)
                ).one()
                row.refresh_cifrado = refresh_cifrado
                row.chave_id = chave_id
                row.atualizado_em = agora
                self._session.flush()
        else:
            row.refresh_cifrado = refresh_cifrado
            row.chave_id = chave_id
            row.atualizado_em = agora
            self._session.flush()

    def carregar(self, tenant_id: UUID, instancia_ref: str) -> tuple[bytes, str] | None:
        row = self._session.scalars(
            select(CredencialCopilotORM)
            .where(CredencialCopilotORM.tenant_id == tenant_id)
            .where(CredencialCopilotORM.instancia_ref == instancia_ref)
        ).one_or_none()
        if row is None:
            return None
        return (bytes(row.refresh_cifrado), row.chave_id)
