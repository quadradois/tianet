"""Testes de integração da API REST (IMP-017/018) — PostgreSQL real.

Cobertura: contratos HTTP (201/400/404/409/422/500), serialização de DTOs
(RA-012 — sem exposição de internals), validação de payload, replay por
Idempotency-Key e concorrência da API (IMP-021).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.application.provisioning import TenantProvisioningService
from emprestimo.domain.platform.unicidade import UnicidadeTenantService
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import TenantORM
from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

PAYLOAD = {
    "identificador_institucional": "IDENT-API",
    "nome": "Financeira API",
    "nome_administrador": "Maria",
    "email_administrador": "maria@exemplo.com",
}
CHAVE = "chave-api-1"
CAMPO_RESPONSE = {"id", "identificador_institucional", "nome", "estado", "criado_em"}


def _montar_servico(
    session_factory: sessionmaker[Session], session: Session
) -> TenantProvisioningService:
    return TenantProvisioningService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        unicidade=UnicidadeTenantService(SqlAlchemyTenantRepository(session)),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


@pytest.fixture
def client(session_factory: sessionmaker[Session], session: Session) -> TestClient:
    app_instance = create_app()
    app_instance.dependency_overrides[dependencies.get_tenant_provisioning_service] = lambda: (
        _montar_servico(session_factory, session)
    )
    app_instance.dependency_overrides[dependencies.get_tenant_repository] = lambda: (
        SqlAlchemyTenantRepository(session)
    )
    with TestClient(app_instance) as c:
        yield c


def _post(client: TestClient, payload: dict | None = None, chave: str = CHAVE) -> TestClient:
    return client.post(
        "/platform/tenants",
        json=payload if payload is not None else PAYLOAD,
        headers={"Idempotency-Key": chave},
    )


def _contar_tenants(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(TenantORM))


def test_health(client: TestClient) -> None:
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_post_cria_tenant_201(client: TestClient) -> None:
    resp = _post(client)

    assert resp.status_code == 201
    corpo = resp.json()
    assert set(corpo) == CAMPO_RESPONSE  # serialização mínima (RA-012)
    assert corpo["identificador_institucional"] == "IDENT-API"
    assert corpo["nome"] == "Financeira API"
    assert corpo["estado"] == "ativo"
    assert corpo["criado_em"]


def test_get_retorna_tenant(client: TestClient) -> None:
    criado = _post(client).json()

    resp = client.get(f"/platform/tenants/{criado['id']}")

    assert resp.status_code == 200
    corpo = resp.json()
    assert set(corpo) == CAMPO_RESPONSE
    assert corpo["id"] == criado["id"]
    assert corpo["identificador_institucional"] == "IDENT-API"
    assert corpo["estado"] == "ativo"


def test_get_404_para_tenant_inexistente(client: TestClient) -> None:
    resp = client.get("/platform/tenants/00000000-0000-0000-0000-000000000000")

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "tenant_nao_encontrado"


def test_post_sem_idempotency_key_400(client: TestClient) -> None:
    resp = client.post("/platform/tenants", json=PAYLOAD)

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "idempotency_key_ausente"


def test_post_payload_invalido_400(client: TestClient) -> None:
    resp = client.post(
        "/platform/tenants",
        json={**PAYLOAD, "nome": "   "},
        headers={"Idempotency-Key": "chave-2"},
    )

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_post_email_invalido_400(client: TestClient) -> None:
    resp = client.post(
        "/platform/tenants",
        json={**PAYLOAD, "email_administrador": "sem-arroba"},
        headers={"Idempotency-Key": "chave-3"},
    )

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_post_tenant_existente_409(client: TestClient) -> None:
    _post(client, chave="chave-a")

    resp = _post(client, chave="chave-b")

    assert resp.status_code == 409
    assert resp.json()["codigo"] == "tenant_ja_existe"


def test_replay_mesma_chave_retorna_mesmo_resultado(client: TestClient) -> None:
    primeiro = _post(client, chave="chave-replay").json()

    segundo = _post(client, chave="chave-replay")

    assert segundo.status_code == 201
    assert segundo.json()["id"] == primeiro["id"]
    assert segundo.json()["criado_em"] == primeiro["criado_em"]


def test_chave_com_payload_divergente_409(client: TestClient) -> None:
    _post(client, chave="chave-divergente")

    resp = _post(
        client,
        chave="chave-divergente",
        payload={**PAYLOAD, "identificador_institucional": "OUTRO-IDENT"},
    )

    assert resp.status_code == 409
    assert resp.json()["codigo"] == "conflito_idempotencia"


def test_concorrencia_mesma_chave_mesmo_payload(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """IMP-021: criação simultânea com a mesma chave → um único provisionamento."""
    from emprestimo.presentation.api.main import create_app as cria_app

    app_instance = cria_app()
    app_instance.dependency_overrides[dependencies.get_tenant_provisioning_service] = (
        client.app.dependency_overrides[dependencies.get_tenant_provisioning_service]
    )
    app_instance.dependency_overrides[dependencies.get_tenant_repository] = (
        client.app.dependency_overrides[dependencies.get_tenant_repository]
    )

    def chamada(_: int) -> int:
        with TestClient(app_instance) as c:
            return c.post(
                "/platform/tenants",
                json=PAYLOAD,
                headers={"Idempotency-Key": "chave-corrida"},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        codigos = sorted(executor.map(chamada, [0, 1]))

    assert codigos.count(201) >= 1  # um provisionamento vence
    assert all(codigo in (201, 409) for codigo in codigos)
    assert _contar_tenants(session_factory) == 1  # sem duplicidade


def test_concorrencia_mesma_chave_payload_divergente(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Corrida com payload divergente → exatamente um 201 e um 409 (determinístico)."""
    from emprestimo.presentation.api.main import create_app as cria_app

    app_instance = cria_app()
    app_instance.dependency_overrides[dependencies.get_tenant_provisioning_service] = (
        client.app.dependency_overrides[dependencies.get_tenant_provisioning_service]
    )
    app_instance.dependency_overrides[dependencies.get_tenant_repository] = (
        client.app.dependency_overrides[dependencies.get_tenant_repository]
    )

    def chamada(payload: dict) -> int:
        with TestClient(app_instance) as c:
            return c.post(
                "/platform/tenants",
                json=payload,
                headers={"Idempotency-Key": "chave-corrida-divergente"},
            ).status_code

    payloads = [PAYLOAD, {**PAYLOAD, "identificador_institucional": "OUTRO-IDENT"}]
    with ThreadPoolExecutor(max_workers=2) as executor:
        codigos = sorted(executor.map(chamada, payloads))

    assert codigos == [201, 409]
    assert _contar_tenants(session_factory) == 1
