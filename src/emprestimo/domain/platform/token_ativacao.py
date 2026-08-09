"""Token descartavel para definicao segura da credencial inicial."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass
class TokenAtivacao:
    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    token_hash: str
    expira_em: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    utilizado_em: datetime | None = None

    @classmethod
    def emitir(
        cls,
        *,
        usuario_id: uuid.UUID,
        tenant_id: uuid.UUID,
        segredo: str,
        agora: datetime | None = None,
    ) -> TokenAtivacao:
        instante = _utc(agora)
        return cls(
            usuario_id=usuario_id,
            tenant_id=tenant_id,
            token_hash=_hash(segredo),
            expira_em=instante + timedelta(hours=24),
            criado_em=instante,
        )

    def valido(self, segredo: str, agora: datetime | None = None) -> bool:
        return (
            self.utilizado_em is None
            and _utc(agora) < self.expira_em
            and hmac.compare_digest(self.token_hash, _hash(segredo))
        )

    def utilizar(self, agora: datetime | None = None) -> None:
        self.utilizado_em = _utc(agora)


def _hash(segredo: str) -> str:
    return hashlib.sha256(segredo.encode("utf-8")).hexdigest()


def _utc(valor: datetime | None) -> datetime:
    instante = valor or datetime.now(UTC)
    return instante.replace(tzinfo=UTC) if instante.tzinfo is None else instante.astimezone(UTC)
