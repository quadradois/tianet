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


# --- Testes dos novos endpoints da IMP-026 / IMP-027 (FEATURE-002) ---


def test_get_por_identificador_200(client: TestClient) -> None:
    """IMP-026, US-010: GET /platform/tenants?identificador_institucional=..."""
    criado = _post(client, chave="chave-ident").json()

    resp = client.get(
        "/platform/tenants",
        params={"identificador_institucional": criado["identificador_institucional"]},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert set(corpo) == CAMPO_RESPONSE
    assert corpo["id"] == criado["id"]
    assert corpo["identificador_institucional"] == criado["identificador_institucional"]


def test_get_por_identificador_com_espacos_normaliza(client: TestClient) -> None:
    """Presentation deve normalizar (strip) o identificador antes de consultar."""
    _post(client, chave="chave-ident-espacos")

    # Chama com espaços - a Presentation deve fazer strip
    resp = client.get(
        "/platform/tenants",
        params={"identificador_institucional": "  IDENT-API  "},
    )

    assert resp.status_code == 200
    assert resp.json()["identificador_institucional"] == "IDENT-API"


def test_get_por_identificador_404(client: TestClient) -> None:
    """Deve retornar 404 quando identificador não existe."""
    resp = client.get(
        "/platform/tenants",
        params={"identificador_institucional": "IDENT-INEXISTENTE"},
    )

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "tenant_nao_encontrado"


def test_get_sem_parametros_lista_tenants(client: TestClient) -> None:
    """Sem identificador_institucional, o GET /platform/tenants vira listagem (200)."""
    resp = client.get("/platform/tenants")

    assert resp.status_code == 200
    corpo = resp.json()
    assert "items" in corpo
    assert "total" in corpo


def test_get_por_identificador_vazio_400(client: TestClient) -> None:
    """Identificador vazio (min_length=1) falha a validação → 400 payload_invalido."""
    resp = client.get("/platform/tenants", params={"identificador_institucional": ""})

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_listar_tenants_200(client: TestClient) -> None:
    """IMP-027, US-011: GET /platform/tenants - listagem paginada."""
    _post(
        client, chave="chave-list-1", payload={**PAYLOAD, "identificador_institucional": "IDENT-L1"}
    )
    _post(
        client,
        chave="chave-list-2",
        payload={**PAYLOAD, "identificador_institucional": "IDENT-L2", "nome": "Outra"},
    )
    _post(
        client,
        chave="chave-list-3",
        payload={**PAYLOAD, "identificador_institucional": "IDENT-L3", "nome": "Terceira"},
    )

    resp = client.get("/platform/tenants", params={"page": 1, "size": 10})

    assert resp.status_code == 200
    corpo = resp.json()
    assert "items" in corpo
    assert "total" in corpo
    assert "page" in corpo
    assert "size" in corpo
    assert "pages" in corpo
    assert corpo["total"] >= 3
    assert len(corpo["items"]) >= 3
    assert corpo["page"] == 1
    assert corpo["size"] == 10
    # Verificar envelope e serialização
    for item in corpo["items"]:
        assert set(item) == CAMPO_RESPONSE


def test_listar_tenants_paginacao(client: TestClient) -> None:
    """Deve respeitar paginação (page, size)."""
    for i in range(5):
        _post(
            client,
            chave=f"chave-pag-{i}",
            payload={
                **PAYLOAD,
                "identificador_institucional": f"IDENT-PAG-{i}",
                "nome": f"Tenant {i}",
            },
        )

    page1 = client.get("/platform/tenants", params={"page": 1, "size": 2}).json()
    page2 = client.get("/platform/tenants", params={"page": 2, "size": 2}).json()
    page3 = client.get("/platform/tenants", params={"page": 3, "size": 2}).json()

    assert page1["total"] >= 5
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 2
    assert len(page3["items"]) >= 1
    assert page1["page"] == 1
    assert page2["page"] == 2
    assert page3["page"] == 3
    assert page1["pages"] >= 3


def test_listar_tenants_ordenacao(client: TestClient) -> None:
    """Deve ordenar conforme sort (campo:direcao)."""
    _post(
        client,
        chave="chave-ord-1",
        payload={**PAYLOAD, "identificador_institucional": "IDENT-Z", "nome": "Zebra"},
    )
    _post(
        client,
        chave="chave-ord-2",
        payload={**PAYLOAD, "identificador_institucional": "IDENT-A", "nome": "Alpha"},
    )

    # Ordenação por identificador_institucional asc
    resp = client.get(
        "/platform/tenants", params={"sort": "identificador_institucional:asc", "size": 10}
    ).json()

    # Encontrar nossos tenants na lista
    nossos = [
        item
        for item in resp["items"]
        if item["identificador_institucional"] in ("IDENT-A", "IDENT-Z")
    ]
    assert len(nossos) == 2
    # Deve vir A antes de Z
    assert nossos[0]["identificador_institucional"] == "IDENT-A"
    assert nossos[1]["identificador_institucional"] == "IDENT-Z"


def test_listar_tenants_filtro_estado(client: TestClient) -> None:
    """Deve filtrar por estado operacional."""
    # Criar tenants (todos ficam ativo após provisionamento)
    _post(
        client,
        chave="chave-est-1",
        payload={**PAYLOAD, "identificador_institucional": "IDENT-EST-1"},
    )
    _post(
        client,
        chave="chave-est-2",
        payload={**PAYLOAD, "identificador_institucional": "IDENT-EST-2"},
    )

    # Filtrar por ativo
    resp = client.get("/platform/tenants", params={"estado": "ativo", "size": 10}).json()

    nossos = [
        item
        for item in resp["items"]
        if item["identificador_institucional"].startswith("IDENT-EST-")
    ]
    assert len(nossos) == 2
    for item in nossos:
        assert item["estado"] == "ativo"

    # Filtrar por inativo (não deve encontrar os recém-criados)
    resp = client.get("/platform/tenants", params={"estado": "inativo", "size": 10}).json()
    nossos = [
        item
        for item in resp["items"]
        if item["identificador_institucional"].startswith("IDENT-EST-")
    ]
    assert len(nossos) == 0


def test_listar_tenants_sort_invalido_400(client: TestClient) -> None:
    """Deve retornar 400 (payload_invalido) para parâmetro sort inválido."""
    resp = client.get("/platform/tenants", params={"sort": "campo_inexistente:asc"})

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_listar_tenants_size_maximo_100(client: TestClient) -> None:
    """Deve limitar size a 100 (validação no schema)."""
    resp = client.get("/platform/tenants", params={"size": 150})

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


# --- Testes do endpoint PATCH /platform/tenants/{id} (IMP-032, FEATURE-003) ---


def test_patch_atualiza_nome_200(client: TestClient) -> None:
    """IMP-032, US-012: PATCH atualiza o nome e responde TenantResponse."""
    criado = _post(client, chave="chave-patch-ok").json()

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "Financeira Atualizada"},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert set(corpo) == CAMPO_RESPONSE  # DTO compatível com FEATURE-002
    assert corpo["id"] == criado["id"]
    assert corpo["nome"] == "Financeira Atualizada"


def test_patch_tenant_inexistente_404(client: TestClient) -> None:
    """Deve responder 404 quando o Tenant não existe."""
    resp = client.patch(
        "/platform/tenants/00000000-0000-0000-0000-000000000000",
        json={"nome": "Qualquer Nome"},
    )

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "tenant_nao_encontrado"


def test_patch_payload_invalido_sem_nome_400(client: TestClient) -> None:
    """Payload sem o campo nome → 400 payload_invalido."""
    resp = client.patch(
        "/platform/tenants/00000000-0000-0000-0000-000000000000",
        json={},
    )

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_patch_payload_tipo_invalido_400(client: TestClient) -> None:
    """Nome com tipo inválido (não-string) → 400 payload_invalido."""
    resp = client.patch(
        "/platform/tenants/00000000-0000-0000-0000-000000000000",
        json={"nome": 123},
    )

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_patch_nome_vazio_422(client: TestClient) -> None:
    """Nome vazio → violação de invariante no Aggregate → 422 regra_violada."""
    criado = _post(client, chave="chave-patch-vazio").json()

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "   "},
    )

    assert resp.status_code == 422
    assert resp.json()["codigo"] == "regra_violada"


def test_patch_nome_acima_do_limite_422(client: TestClient) -> None:
    """Nome com mais de 200 caracteres → 422 regra_violada."""
    criado = _post(client, chave="chave-patch-longo").json()

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "A" * 201},
    )

    assert resp.status_code == 422
    assert resp.json()["codigo"] == "regra_violada"


def test_patch_preserva_identificador_institucional(client: TestClient) -> None:
    """A atualização não altera o identificador institucional."""
    criado = _post(client, chave="chave-patch-ident").json()

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "Novo Nome"},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["identificador_institucional"] == criado["identificador_institucional"]
    assert corpo["id"] == criado["id"]


def test_patch_preserva_estado_e_criacao(client: TestClient) -> None:
    """A atualização preserva estado e criado_em."""
    criado = _post(client, chave="chave-patch-estado").json()

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "Financeira Atualizada"},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["estado"] == criado["estado"]
    assert corpo["criado_em"] == criado["criado_em"]


def test_patch_normaliza_nome_com_espacos(client: TestClient) -> None:
    """A Presentation normaliza (strip) o nome na borda."""
    criado = _post(client, chave="chave-patch-strip").json()

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "  Financeira Normalizada  "},
    )

    assert resp.status_code == 200
    assert resp.json()["nome"] == "Financeira Normalizada"


def test_patch_persistencia_real(client: TestClient) -> None:
    """Após PATCH, a consulta GET reflete o nome atualizado (persistência)."""
    criado = _post(client, chave="chave-patch-persist").json()

    client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "Nome Persistido"},
    )

    resp = client.get(f"/platform/tenants/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Nome Persistido"
