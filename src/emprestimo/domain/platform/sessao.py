"""Entity Sessao - refresh token persistido e revogavel (IMP-083)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from emprestimo.domain.common.errors import ViolacaoInvarianteError

ALGORITMO_REFRESH = "sha256_salted"
REFRESH_TOKEN_DIAS = 7
SALT_BYTES = 16


def _normalizar_token(refresh_token: str) -> str:
    token = refresh_token.strip()
    if not token:
        raise ViolacaoInvarianteError(
            "FEATURE-009",
            "refresh token nao pode ser vazio",
        )
    return token


def _gerar_hash(refresh_token: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    digest = hashlib.sha256(f"{salt}:{refresh_token}".encode()).hexdigest()
    return f"{ALGORITMO_REFRESH}${salt}${digest}"


def _verificar_hash(refresh_token: str, refresh_token_hash: str) -> bool:
    try:
        algoritmo, salt, esperado = refresh_token_hash.split("$", 2)
    except ValueError:
        return False
    if algoritmo != ALGORITMO_REFRESH:
        return False
    digest = hashlib.sha256(f"{salt}:{refresh_token}".encode()).hexdigest()
    return hmac.compare_digest(digest, esperado)


@dataclass
class Sessao:
    """Sessao de autenticacao baseada em refresh token."""

    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    refresh_token_hash: str
    expira_em: datetime
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    revogado_em: datetime | None = None

    @classmethod
    def iniciar(
        cls,
        *,
        usuario_id: uuid.UUID,
        tenant_id: uuid.UUID,
        refresh_token: str,
        agora: datetime | None = None,
    ) -> Sessao:
        token = _normalizar_token(refresh_token)
        referencia = agora or datetime.now(UTC)
        return cls(
            usuario_id=usuario_id,
            tenant_id=tenant_id,
            refresh_token_hash=_gerar_hash(token),
            expira_em=referencia + timedelta(days=REFRESH_TOKEN_DIAS),
            criado_em=referencia,
        )

    def expirada(self, agora: datetime | None = None) -> bool:
        referencia = agora or datetime.now(UTC)
        return referencia >= self.expira_em

    def ativa(self, agora: datetime | None = None) -> bool:
        return self.revogado_em is None and not self.expirada(agora)

    def verificar_refresh_token(self, refresh_token: str, agora: datetime | None = None) -> bool:
        if not self.ativa(agora):
            return False
        token = refresh_token.strip()
        if not token:
            return False
        return _verificar_hash(token, self.refresh_token_hash)

    def corresponde_refresh_token(self, refresh_token: str) -> bool:
        token = refresh_token.strip()
        if not token:
            return False
        return _verificar_hash(token, self.refresh_token_hash)

    def revogar(self, agora: datetime | None = None) -> None:
        if self.revogado_em is None:
            self.revogado_em = agora or datetime.now(UTC)
