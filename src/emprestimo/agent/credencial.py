"""Credencial do copiloto (IMP-356-F slice 2).

O agente faz login como um usuário comum e mantém o refresh cifrado no
store próprio; o access vive só em memória e é renovado proativamente
antes de expirar. Em 401, no máximo UM refresh e UMA repetição da
operação — o segundo 401 encerra sem loop. Token nunca aparece em
`repr`, erro, log ou métrica.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar
from uuid import UUID

MARGEM_RENOVACAO_SEGUNDOS = 120
ENV_CHAVE_CIFRA = "COPILOT_TOKEN_ENCRYPTION_KEY"

T = TypeVar("T")


class CredencialError(Exception):
    """Falha fechada de credencial — encerra, nunca tenta outro caminho."""


class RenovacaoEsgotadaError(CredencialError):
    """401 persistiu após 1 refresh, ou o refresh foi recusado."""


@dataclass(frozen=True)
class CredenciaisLogin:
    identificador_institucional: str
    email: str
    segredo: str = field(repr=False)


class ArmazenRefresh(ABC):
    """Store do refresh cifrado, separado por tenant e instância."""

    @abstractmethod
    def guardar(
        self, tenant_id: UUID, instancia_ref: str, refresh_cifrado: bytes, chave_id: str
    ) -> None: ...

    @abstractmethod
    def carregar(self, tenant_id: UUID, instancia_ref: str) -> tuple[bytes, str] | None: ...


def _agora_utc() -> datetime:
    return datetime.now(UTC)


class ProvedorTokenCopilot:
    """Access em memória com renovação proativa + 401 único.

    `autenticacao` é o `AutenticacaoService` (login/refresh reais);
    `cifrar`/`decifrar` vêm da cifra da casa (Fernet via ambiente);
    `agora` é injetável para testes.
    """

    def __init__(
        self,
        autenticacao: Any,
        stored: ArmazenRefresh,
        cifrar: Callable[[str], bytes],
        decifrar: Callable[[bytes], str],
        tenant_id: UUID,
        instancia_ref: str,
        agora: Callable[[], datetime] = _agora_utc,
    ) -> None:
        self._autenticacao = autenticacao
        self._stored = stored
        self._cifrar = cifrar
        self._decifrar = decifrar
        self._tenant_id = tenant_id
        self._instancia_ref = instancia_ref
        self._agora = agora
        self._access_token: str | None = None
        self._expira_em: datetime | None = None

    def __repr__(self) -> str:
        return (
            f"ProvedorTokenCopilot(tenant_id={self._tenant_id} "
            f"instancia_ref={self._instancia_ref} autenticado={self._access_token is not None})"
        )

    def _guardar_refresh(self, refresh: str) -> None:
        self._stored.guardar(self._tenant_id, self._instancia_ref, self._cifrar(refresh), "v1")

    def _refresh_guardado(self) -> str | None:
        achado = self._stored.carregar(self._tenant_id, self._instancia_ref)
        if achado is None:
            return None
        cifrado, _ = achado
        return self._decifrar(cifrado)

    def _aplicar_renovacao(self, resultado: Any) -> None:
        self._access_token = resultado.access_token
        self._expira_em = resultado.access_token_expira_em

    def entrar(self, credenciais: CredenciaisLogin) -> None:
        """Autentica: tenta o refresh guardado antes da senha."""
        guardado = self._refresh_guardado()
        if guardado is not None:
            try:
                self._aplicar_renovacao(self._autenticacao.refresh(refresh_token=guardado))
                return
            except Exception:
                # Refresh guardado e obsoleto: cai para o login com senha.
                pass
        resultado = self._autenticacao.login(
            identificador_institucional=credenciais.identificador_institucional,
            email=credenciais.email,
            segredo=credenciais.segredo,
        )
        self._aplicar_renovacao(resultado)
        self._guardar_refresh(resultado.refresh_token)

    def _precisa_renovar(self) -> bool:
        if self._access_token is None or self._expira_em is None:
            return True
        margem = timedelta(seconds=MARGEM_RENOVACAO_SEGUNDOS)
        return self._expira_em - self._agora() <= margem

    def _renovar(self) -> None:
        guardado = self._refresh_guardado()
        if guardado is None:
            raise RenovacaoEsgotadaError("sem refresh guardado")
        try:
            self._aplicar_renovacao(self._autenticacao.refresh(refresh_token=guardado))
        except Exception as exc:
            raise RenovacaoEsgotadaError("refresh recusado") from exc

    def renovar(self) -> None:
        """Força uma renovação (reautorização antes de reconsulta)."""
        self._renovar()

    def token(self) -> str:
        """Access válido, renovando proativamente antes de expirar."""
        if self._precisa_renovar():
            self._renovar()
        assert self._access_token is not None
        return self._access_token

    def executar(self, operacao: Callable[[str], T]) -> T:
        """Roda a operação; em 401, 1 refresh + 1 repetição, e encerra."""
        from emprestimo.agent.api_client import ApiAutorizacaoError

        try:
            return operacao(self.token())
        except ApiAutorizacaoError:
            self._renovar()
        try:
            return operacao(self.token())
        except ApiAutorizacaoError as exc:
            raise RenovacaoEsgotadaError("autorização negada após renovação") from exc
