from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from emprestimo.application.openai_conexao import (
    OpenAIConnectionService,
    OpenAIConnectionSnapshot,
    OpenAIDeviceChallenge,
    OpenAIDiagnostic,
    OpenAILogoutResult,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork


class _Idempotency:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str], dict[str, Any]] = {}

    def registrar(self, key: str, scope: str, request_hash: str) -> None:
        self.records[(key, scope)] = {
            "solicitacao_hash": request_hash,
            "estado": "in_progress",
            "resultado": None,
        }

    def find_by_chave(self, key: str, scope: str) -> dict[str, Any] | None:
        return self.records.get((key, scope))

    def concluir(self, key: str, scope: str, result: str) -> None:
        self.records[(key, scope)]["estado"] = "finished"
        self.records[(key, scope)]["resultado"] = result


class _Uow:
    def __init__(self, idempotency: _Idempotency) -> None:
        self.idempotencia = idempotency

    def __enter__(self) -> _Uow:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def commit(self) -> None:
        return None


class _Audit(AuditoriaRegistro):
    def __init__(self) -> None:
        self.events: list[tuple[str, str | None]] = []

    def registrar(
        self,
        entidade: str,
        entidade_id: uuid.UUID | None,
        acao: str,
        status: str,
        detalhes: str | None = None,
    ) -> None:
        del entidade, entidade_id, status
        self.events.append((acao, detalhes))


class _Provider:
    def __init__(self) -> None:
        self.logouts = 0

    async def connection(self) -> OpenAIConnectionSnapshot:
        return OpenAIConnectionSnapshot(True, True, False, None, "DESCONECTADO")

    async def diagnostic(self) -> OpenAIDiagnostic:
        raise AssertionError("nao chamado")

    async def begin_login(self) -> OpenAIDeviceChallenge:
        return OpenAIDeviceChallenge(
            "https://auth.openai.com/codex/device",
            "CODIGO-SECRETO",
            datetime(2026, 9, 9, tzinfo=UTC),
        )

    async def logout(self) -> OpenAILogoutResult:
        self.logouts += 1
        return OpenAILogoutResult("DESCONECTADO", True, False)


def _service(
    provider: _Provider, idempotency: _Idempotency, audit: _Audit
) -> OpenAIConnectionService:
    return OpenAIConnectionService(
        provider,
        lambda: cast(UnitOfWork, _Uow(idempotency)),
        audit,
    )


def test_logout_replay_nao_repete_efeito_externo() -> None:
    async def scenario() -> None:
        provider = _Provider()
        service = _service(provider, _Idempotency(), _Audit())
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        first = await service.logout(tenant_id, user_id, idempotency_key="logout-replay")
        second = await service.logout(tenant_id, user_id, idempotency_key="logout-replay")
        assert second == first
        assert provider.logouts == 1

    asyncio.run(scenario())


def test_auditoria_do_login_nao_grava_codigo_ou_url() -> None:
    async def scenario() -> None:
        audit = _Audit()
        await _service(_Provider(), _Idempotency(), audit).begin_login(uuid.uuid4(), uuid.uuid4())
        serialized = json.dumps(audit.events)
        assert "CODIGO-SECRETO" not in serialized
        assert "auth.openai.com" not in serialized

    asyncio.run(scenario())
