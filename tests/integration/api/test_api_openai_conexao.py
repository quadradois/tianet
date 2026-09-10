"""Contrato HTTP e RBAC da conexão OpenAI/Codex."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.application.openai_conexao import (
    OpenAIConnectionSnapshot,
    OpenAIDeviceChallenge,
    OpenAIDiagnostic,
    OpenAILogoutResult,
    OpenAIRateLimit,
    OpenAIRateWindow,
    OpenAIUsageSummary,
)
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.repositories import (
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "segredo-api-openai-conexao"
LER = "openai.conexao.ler"
GERIR = "openai.conexao.gerir"
CONEXAO = "/platform/openai/conexao"
DIAGNOSTICO = "/platform/openai/diagnostico"
LOGIN = "/platform/openai/conexao/login"


class _ServiceStub:
    def __init__(self) -> None:
        self.login_identity: tuple[uuid.UUID, uuid.UUID] | None = None
        self.logout_identity: tuple[uuid.UUID, uuid.UUID, str] | None = None

    async def connection(self) -> OpenAIConnectionSnapshot:
        return OpenAIConnectionSnapshot(
            True,
            True,
            False,
            None,
            "DESCONECTADO",
            OpenAIUsageSummary(
                observed_at=datetime(2026, 9, 9, tzinfo=UTC),
                rate_limits_status="ok",
                rate_limits=(
                    OpenAIRateLimit("codex", "free", OpenAIRateWindow(50, 300, 123), None),
                ),
            ),
        )

    async def diagnostic(self) -> OpenAIDiagnostic:
        return OpenAIDiagnostic(
            state="DESCONECTADO",
            observed_at=datetime(2026, 9, 9, tzinfo=UTC),
            account_status="ok",
            account_connected=False,
            plan_type=None,
            models_status="ok",
            models=(),
            rate_limits_status="ok",
            rate_limits=(),
        )

    async def begin_login(
        self, tenant_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> OpenAIDeviceChallenge:
        self.login_identity = (tenant_id, usuario_id)
        return OpenAIDeviceChallenge(
            "https://auth.openai.com/codex/device",
            "ABCD-EFGH",
            datetime(2026, 9, 9, 0, 10, tzinfo=UTC),
        )

    async def logout(
        self,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        *,
        idempotency_key: str,
    ) -> OpenAILogoutResult:
        self.logout_identity = (tenant_id, usuario_id, idempotency_key)
        return OpenAILogoutResult("DESCONECTADO", True, False)


@dataclass(frozen=True)
class _Authenticated:
    user: Usuario
    tenant: Tenant
    token: str


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, JWT_SECRET)


@pytest.fixture
def service() -> _ServiceStub:
    return _ServiceStub()


@pytest.fixture
def client(service: _ServiceStub) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[dependencies.get_openai_connection_service] = lambda: service
    with TestClient(app) as result:
        yield result


def _headers(token: str, **extra: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", **extra}


def _authenticate(session: Session, *permissions: str) -> _Authenticated:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    user = UsuarioFactory.build(
        tenant_id=tenant.id,
        estado=UsuarioState.ATIVO,
        perfil_acesso="OperadorOpenAI",
    )
    SqlAlchemyUsuarioRepository(session).save(user)
    profile = PerfilAcesso(tenant_id=tenant.id, nome="OperadorOpenAI")
    for code in permissions:
        profile.adicionar_permissao(Permissao(codigo=code, descricao=code))
    repository = SqlAlchemyPerfilAcessoRepository(session)
    repository.save(profile)
    repository.atribuir_usuario(user.id, profile.id)
    session.commit()
    return _Authenticated(
        user=user,
        tenant=tenant,
        token=HmacAccessTokenService(JWT_SECRET).emitir(user).token,
    )


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", CONEXAO), ("GET", DIAGNOSTICO), ("POST", LOGIN), ("DELETE", CONEXAO)],
)
def test_routes_require_authentication(
    client: TestClient, session: Session, method: str, path: str
) -> None:
    del session
    response = client.request(method, path)
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", CONEXAO), ("GET", DIAGNOSTICO), ("POST", LOGIN), ("DELETE", CONEXAO)],
)
def test_routes_require_permission(
    client: TestClient, session: Session, method: str, path: str
) -> None:
    authenticated = _authenticate(session)
    response = client.request(
        method,
        path,
        headers=_headers(authenticated.token, **{"Idempotency-Key": "logout-1"}),
    )
    assert response.status_code == 403


def test_read_permission_only_reads(client: TestClient, session: Session) -> None:
    authenticated = _authenticate(session, LER)
    headers = _headers(authenticated.token)
    connection = client.get(CONEXAO, headers=headers)
    assert connection.status_code == 200
    assert connection.json()["usageSummary"]["rateLimits"][0]["primary"]["usedPercent"] == 50
    assert client.get(DIAGNOSTICO, headers=headers).status_code == 200
    assert client.post(LOGIN, headers=headers).status_code == 403


def test_manage_permission_starts_login_without_idempotency_key(
    client: TestClient, session: Session, service: _ServiceStub
) -> None:
    authenticated = _authenticate(session, GERIR)
    response = client.post(LOGIN, headers=_headers(authenticated.token))
    assert response.status_code == 200
    assert set(response.json()) == {"verificationUrl", "userCode", "expiresAt"}
    assert service.login_identity == (authenticated.tenant.id, authenticated.user.id)


def test_logout_requires_key_and_forwards_tenant_identity(
    client: TestClient, session: Session, service: _ServiceStub
) -> None:
    authenticated = _authenticate(session, GERIR)
    assert client.delete(CONEXAO, headers=_headers(authenticated.token)).status_code == 400
    response = client.delete(
        CONEXAO,
        headers=_headers(authenticated.token, **{"Idempotency-Key": "logout-1"}),
    )
    assert response.status_code == 200
    assert response.json()["remoteRevocationVerified"] is False
    assert service.logout_identity == (
        authenticated.tenant.id,
        authenticated.user.id,
        "logout-1",
    )
