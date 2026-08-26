"""Testes de integração da API REST (IMP-017/018) — PostgreSQL real.

Cobertura: contratos HTTP (201/400/404/409/422/500), serialização de DTOs
(RA-012 — sem exposição de internals), validação de payload, replay por
Idempotency-Key e concorrência da API (IMP-021).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from emprestimo.application.autorizacao import Principal, RecursoDeOutroTenantError
from emprestimo.domain.platform.tenant import Tenant
from emprestimo.infrastructure.db.orm import TenantORM
from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

PAYLOAD = {
    "identificador_institucional": "IDENT-API",
    "nome": "Financeira API",
    "nome_administrador": "Maria",
    "email_administrador": "maria@exemplo.com",
}
CHAVE = "chave-api-1"
CAMPO_RESPONSE = {
    "id",
    "identificador_institucional",
    "nome",
    "estado",
    "criado_em",
}
CAMPO_PROVISIONAMENTO_RESPONSE = {
    *CAMPO_RESPONSE,
    "usuario_administrador_id",
    "token_ativacao",
}
PRINCIPAL_TESTE = Principal(
    usuario_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
    tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
    perfil_acesso="Teste",
    access_token_expira_em=datetime.now(UTC) + timedelta(minutes=15),
    administrador_plataforma=True,
)


@pytest.fixture
def client(session_factory: sessionmaker[Session], session: Session) -> Iterator[TestClient]:
    app_instance = create_app()
    app_instance.dependency_overrides[dependencies.get_tenant_repository] = lambda: (
        SqlAlchemyTenantRepository(session)
    )
    app_instance.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL_TESTE
    autorizacao = Mock()
    autorizacao.exigir_permissao.return_value = None
    autorizacao.exigir_tenant_do_recurso.side_effect = RecursoDeOutroTenantError()
    app_instance.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    with TestClient(app_instance) as c:
        yield c


def _criar_tenant(
    client: TestClient,
    session: Session,
    payload: dict[str, object] | None = None,
    chave: str | None = None,
) -> dict[str, str]:
    """Cria o Tenant direto no banco — o POST /platform/tenants nao existe mais.

    Antes estes testes usavam o endpoint de provisionamento como setup. Ele saiu
    no IMP-351 junto com o fluxo de ativacao: o Tenant unico nasce pela CLI
    `bootstrap_plataforma`, nao pela API. O que os testes abaixo exercitam —
    consulta, listagem, atualizacao e estado — nao mudou; so a forma de chegar
    ao estado inicial.
    """
    del chave  # nao ha mais idempotencia a exercitar na criacao
    dados = payload if payload is not None else PAYLOAD
    tenant = Tenant(
        identificador_institucional=str(dados["identificador_institucional"]),
        nome=str(dados["nome"]),
    )
    # O provisionamento terminava com o Tenant ATIVO; criar direto para em PROVISAO.
    tenant.ativar()
    SqlAlchemyTenantRepository(session).save(tenant)
    session.commit()
    app_instance = cast(FastAPI, client.app)
    app_instance.dependency_overrides[dependencies.get_principal_atual] = lambda: replace(
        PRINCIPAL_TESTE,
        tenant_id=tenant.id,
    )
    return {
        "id": str(tenant.id),
        "identificador_institucional": tenant.identificador_institucional,
        "nome": tenant.nome,
        "estado": tenant.estado.value,
        # A API serializa UTC com sufixo Z; o helper precisa falar a mesma lingua.
        "criado_em": tenant.criado_em.isoformat().replace("+00:00", "Z"),
    }


def _contar_tenants(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(TenantORM)) or 0


def test_health(client: TestClient) -> None:
    resp = client.get("/health")

    assert resp.status_code == 200
    # IMP-343: a suite nao sobe worker, entao o heartbeat esta ausente e o
    # /health degrada — sem tirar a API de rotacao (200, nao 503).
    assert resp.json() == {
        "status": "degraded",
        "service": "api",
        "checks": {"database": "healthy", "worker": "unhealthy"},
    }
    assert resp.headers["X-Correlation-ID"]


def test_get_retorna_tenant(client: TestClient, session: Session) -> None:
    criado = _criar_tenant(client, session)

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


def test_get_por_identificador_200(client: TestClient, session: Session) -> None:
    """IMP-026, US-010: GET /platform/tenants?identificador_institucional=..."""
    criado = _criar_tenant(client, session, chave="chave-ident")

    resp = client.get(
        "/platform/tenants",
        params={"identificador_institucional": criado["identificador_institucional"]},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert set(corpo) == CAMPO_RESPONSE
    assert corpo["id"] == criado["id"]
    assert corpo["identificador_institucional"] == criado["identificador_institucional"]


def test_get_por_identificador_com_espacos_normaliza(client: TestClient, session: Session) -> None:
    """Presentation deve normalizar (strip) o identificador antes de consultar."""
    _criar_tenant(client, session, chave="chave-ident-espacos")

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


def test_listar_tenants_200(client: TestClient, session: Session) -> None:
    """IMP-027, US-011: GET /platform/tenants - listagem paginada."""
    criado = _criar_tenant(
        client,
        session,
        chave="chave-list-1",
        payload={**PAYLOAD, "identificador_institucional": "IDENT-L1"},
    )

    resp = client.get("/platform/tenants", params={"page": 1, "size": 10})

    assert resp.status_code == 200
    corpo = resp.json()
    assert "items" in corpo
    assert "total" in corpo
    assert "page" in corpo
    assert "size" in corpo
    assert "pages" in corpo
    assert corpo["total"] == 1
    assert [item["id"] for item in corpo["items"]] == [criado["id"]]
    assert corpo["page"] == 1
    assert corpo["size"] == 10
    # Verificar envelope e serialização
    for item in corpo["items"]:
        assert set(item) == CAMPO_RESPONSE


def test_listar_tenants_paginacao(client: TestClient, session: Session) -> None:
    """Deve respeitar paginação (page, size)."""
    _criar_tenant(client, session, chave="chave-pag")

    page1 = client.get("/platform/tenants", params={"page": 1, "size": 2}).json()
    page2 = client.get("/platform/tenants", params={"page": 2, "size": 2}).json()

    assert page1["total"] == 1
    assert len(page1["items"]) == 1
    assert page2["total"] == 1
    assert page2["items"] == []
    assert page1["page"] == 1
    assert page2["page"] == 2
    assert page1["pages"] == 1


def test_listar_tenants_ordenacao(client: TestClient, session: Session) -> None:
    """Deve ordenar conforme sort (campo:direcao)."""
    criado = _criar_tenant(
        client,
        session,
        chave="chave-ord",
        payload={**PAYLOAD, "identificador_institucional": "IDENT-A", "nome": "Alpha"},
    )

    # Ordenação por identificador_institucional asc
    resp = client.get(
        "/platform/tenants", params={"sort": "identificador_institucional:asc", "size": 10}
    ).json()

    assert [item["id"] for item in resp["items"]] == [criado["id"]]


def test_listar_tenants_filtro_estado(client: TestClient, session: Session) -> None:
    """Deve filtrar por estado operacional."""
    # Criar tenants (todos ficam ativo após provisionamento)
    criado = _criar_tenant(
        client,
        session,
        chave="chave-est-1",
        payload={**PAYLOAD, "identificador_institucional": "IDENT-EST-1"},
    )

    # Filtrar por ativo
    resp = client.get("/platform/tenants", params={"estado": "ativo", "size": 10}).json()

    assert [item["id"] for item in resp["items"]] == [criado["id"]]

    # Filtrar por inativo (não deve encontrar os recém-criados)
    resp = client.get("/platform/tenants", params={"estado": "inativo", "size": 10}).json()
    assert resp["items"] == []
    assert resp["total"] == 0


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


def test_rotas_de_tenant_isolam_principal_com_dois_tenants(
    client: TestClient,
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    primeiro = _criar_tenant(
        client,
        session,
        chave="chave-isolamento-1",
        payload={
            **PAYLOAD,
            "identificador_institucional": "IDENT-ISOLADO-1",
            "nome": "Tenant Oculto",
        },
    )
    segundo = _criar_tenant(
        client,
        session,
        chave="chave-isolamento-2",
        payload={
            **PAYLOAD,
            "identificador_institucional": "IDENT-ISOLADO-2",
            "nome": "Tenant do Principal",
        },
    )

    principal_local = replace(
        PRINCIPAL_TESTE,
        tenant_id=uuid.UUID(segundo["id"]),
        administrador_plataforma=False,
    )
    cast(FastAPI, client.app).dependency_overrides[
        dependencies.get_principal_atual
    ] = lambda: principal_local

    assert client.get(f"/platform/tenants/{primeiro['id']}").status_code == 404
    assert (
        client.get(
            "/platform/tenants",
            params={"identificador_institucional": primeiro["identificador_institucional"]},
        ).status_code
        == 404
    )

    listagem = client.get("/platform/tenants", params={"size": 100})
    assert listagem.status_code == 200
    assert listagem.json()["total"] == 1
    assert [item["id"] for item in listagem.json()["items"]] == [segundo["id"]]

    assert (
        client.patch(
            f"/platform/tenants/{primeiro['id']}",
            json={"nome": "Nome Indevido"},
            headers={"Idempotency-Key": "tenant-scope-patch"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/platform/tenants/{primeiro['id']}/inativar",
            headers={"Idempotency-Key": "tenant-scope-inativar"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/platform/tenants/{primeiro['id']}/reativar",
            headers={"Idempotency-Key": "tenant-scope-reativar"},
        ).status_code
        == 404
    )

    with session_factory() as session:
        tenant_oculto = session.get(TenantORM, uuid.UUID(primeiro["id"]))
        assert tenant_oculto is not None
        assert tenant_oculto.nome == "Tenant Oculto"
        assert tenant_oculto.estado == "ativo"


# --- Testes do endpoint PATCH /platform/tenants/{id} (IMP-032, FEATURE-003) ---


def test_patch_atualiza_nome_200(client: TestClient, session: Session) -> None:
    """IMP-032, US-012: PATCH atualiza o nome e responde TenantResponse."""
    criado = _criar_tenant(client, session, chave="chave-patch-ok")

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "Financeira Atualizada"},
        headers={"Idempotency-Key": "patch-atualiza-nome"},
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
        headers={"Idempotency-Key": "patch-tenant-inexistente"},
    )

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "tenant_nao_encontrado"


def test_patch_payload_invalido_sem_nome_400(client: TestClient) -> None:
    """Payload sem o campo nome → 400 payload_invalido."""
    resp = client.patch(
        "/platform/tenants/00000000-0000-0000-0000-000000000000",
        json={},
        headers={"Idempotency-Key": "patch-payload-sem-nome"},
    )

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_patch_payload_tipo_invalido_400(client: TestClient) -> None:
    """Nome com tipo inválido (não-string) → 400 payload_invalido."""
    resp = client.patch(
        "/platform/tenants/00000000-0000-0000-0000-000000000000",
        json={"nome": 123},
        headers={"Idempotency-Key": "patch-payload-tipo-invalido"},
    )

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_patch_nome_vazio_422(client: TestClient, session: Session) -> None:
    """Nome vazio → violação de invariante no Aggregate → 422 regra_violada."""
    criado = _criar_tenant(client, session, chave="chave-patch-vazio")

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "   "},
        headers={"Idempotency-Key": "patch-nome-vazio"},
    )

    assert resp.status_code == 422
    assert resp.json()["codigo"] == "regra_violada"


def test_patch_nome_acima_do_limite_422(client: TestClient, session: Session) -> None:
    """Nome com mais de 200 caracteres → 422 regra_violada."""
    criado = _criar_tenant(client, session, chave="chave-patch-longo")

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "A" * 201},
        headers={"Idempotency-Key": "patch-nome-longo"},
    )

    assert resp.status_code == 422
    assert resp.json()["codigo"] == "regra_violada"


def test_patch_preserva_identificador_institucional(client: TestClient, session: Session) -> None:
    """A atualização não altera o identificador institucional."""
    criado = _criar_tenant(client, session, chave="chave-patch-ident")

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "Novo Nome"},
        headers={"Idempotency-Key": "patch-preserva-identificador"},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["identificador_institucional"] == criado["identificador_institucional"]
    assert corpo["id"] == criado["id"]


def test_patch_preserva_estado_e_criacao(client: TestClient, session: Session) -> None:
    """A atualização preserva estado e criado_em."""
    criado = _criar_tenant(client, session, chave="chave-patch-estado")

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "Financeira Atualizada"},
        headers={"Idempotency-Key": "patch-preserva-estado"},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["estado"] == criado["estado"]
    assert corpo["criado_em"] == criado["criado_em"]


def test_patch_normaliza_nome_com_espacos(client: TestClient, session: Session) -> None:
    """A Presentation normaliza (strip) o nome na borda."""
    criado = _criar_tenant(client, session, chave="chave-patch-strip")

    resp = client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "  Financeira Normalizada  "},
        headers={"Idempotency-Key": "patch-normaliza-nome"},
    )

    assert resp.status_code == 200
    assert resp.json()["nome"] == "Financeira Normalizada"


def test_patch_persistencia_real(client: TestClient, session: Session) -> None:
    """Após PATCH, a consulta GET reflete o nome atualizado (persistência)."""
    criado = _criar_tenant(client, session, chave="chave-patch-persist")

    client.patch(
        f"/platform/tenants/{criado['id']}",
        json={"nome": "Nome Persistido"},
        headers={"Idempotency-Key": "patch-persistencia"},
    )

    resp = client.get(f"/platform/tenants/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Nome Persistido"


# --- Testes dos endpoints POST inativar/reativar (IMP-036, FEATURE-004) ---


def test_post_inativar_200(client: TestClient, session: Session) -> None:
    """IMP-036, US-013: POST /tenants/{id}/inativar responde TenantResponse."""
    criado = _criar_tenant(client, session, chave="chave-inat-ok")
    resp = client.post(
        f"/platform/tenants/{criado['id']}/inativar",
        headers={"Idempotency-Key": "inativar-200"},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert set(corpo) == CAMPO_RESPONSE
    assert corpo["id"] == criado["id"]
    assert corpo["estado"] == "inativo"
    assert corpo["identificador_institucional"] == criado["identificador_institucional"]
    assert corpo["nome"] == criado["nome"]


def test_post_inativar_tenant_inexistente_404(client: TestClient) -> None:
    """Deve responder 404 quando o Tenant não existe."""
    resp = client.post(
        "/platform/tenants/00000000-0000-0000-0000-000000000000/inativar",
        headers={"Idempotency-Key": "inativar-inexistente"},
    )

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "tenant_nao_encontrado"


def test_post_inativar_ja_inativo_409(client: TestClient, session: Session) -> None:
    """Estado divergente (já Inativo) → 409 conflito_estado."""
    criado = _criar_tenant(client, session, chave="chave-inat-409")
    client.post(
        f"/platform/tenants/{criado['id']}/inativar",
        headers={"Idempotency-Key": "inativar-conflito-primeira"},
    )

    resp = client.post(
        f"/platform/tenants/{criado['id']}/inativar",
        headers={"Idempotency-Key": "inativar-conflito-segunda"},
    )

    assert resp.status_code == 409
    assert resp.json()["codigo"] == "conflito_estado"


def test_post_reativar_200(client: TestClient, session: Session) -> None:
    """IMP-036, US-014: POST /tenants/{id}/reativar responde TenantResponse."""
    criado = _criar_tenant(client, session, chave="chave-reat-ok")
    client.post(
        f"/platform/tenants/{criado['id']}/inativar",
        headers={"Idempotency-Key": "reativar-200-inativar"},
    )

    resp = client.post(
        f"/platform/tenants/{criado['id']}/reativar",
        headers={"Idempotency-Key": "reativar-200"},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert set(corpo) == CAMPO_RESPONSE
    assert corpo["id"] == criado["id"]
    assert corpo["estado"] == "ativo"
    assert corpo["identificador_institucional"] == criado["identificador_institucional"]


def test_post_reativar_tenant_inexistente_404(client: TestClient) -> None:
    """Deve responder 404 quando o Tenant não existe."""
    resp = client.post(
        "/platform/tenants/00000000-0000-0000-0000-000000000000/reativar",
        headers={"Idempotency-Key": "reativar-inexistente"},
    )

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "tenant_nao_encontrado"


def test_post_reativar_ja_ativo_409(client: TestClient, session: Session) -> None:
    """Estado divergente (já Ativo) → 409 conflito_estado."""
    criado = _criar_tenant(client, session, chave="chave-reat-409")

    resp = client.post(
        f"/platform/tenants/{criado['id']}/reativar",
        headers={"Idempotency-Key": "reativar-ja-ativo"},
    )

    assert resp.status_code == 409
    assert resp.json()["codigo"] == "conflito_estado"


def test_post_inativar_persistencia_real(client: TestClient, session: Session) -> None:
    """Após inativar, a consulta GET reflete o estado Inativo (persistência)."""
    criado = _criar_tenant(client, session, chave="chave-inat-persist")

    client.post(
        f"/platform/tenants/{criado['id']}/inativar",
        headers={"Idempotency-Key": "inativar-persistencia"},
    )

    resp = client.get(f"/platform/tenants/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["estado"] == "inativo"


def test_post_inativar_preserva_dados_cadastrais(client: TestClient, session: Session) -> None:
    """Inativação altera apenas o estado; cadastro permanece intacto."""
    criado = _criar_tenant(client, session, chave="chave-inat-preserva")

    resp = client.post(
        f"/platform/tenants/{criado['id']}/inativar",
        headers={"Idempotency-Key": "inativar-preserva-dados"},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["id"] == criado["id"]
    assert corpo["identificador_institucional"] == criado["identificador_institucional"]
    assert corpo["nome"] == criado["nome"]
    assert corpo["criado_em"] == criado["criado_em"]


def test_post_reativar_nao_recria_dados(client: TestClient, session: Session) -> None:
    """Reativação preserva identidade; nada é recriado."""
    criado = _criar_tenant(client, session, chave="chave-reat-preserva")
    client.post(
        f"/platform/tenants/{criado['id']}/inativar",
        headers={"Idempotency-Key": "reativar-preserva-inativar"},
    )

    resp = client.post(
        f"/platform/tenants/{criado['id']}/reativar",
        headers={"Idempotency-Key": "reativar-preserva"},
    )

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["id"] == criado["id"]
    assert corpo["identificador_institucional"] == criado["identificador_institucional"]
    assert corpo["nome"] == criado["nome"]
    assert corpo["criado_em"] == criado["criado_em"]


def test_listagem_filtra_estado_inativo_apos_inativacao(
    client: TestClient, session: Session
) -> None:
    """IMP-039: após inativar, o filtro por estado inativo encontra o Tenant."""
    criado = _criar_tenant(client, session, chave="chave-inat-filtro")
    client.post(
        f"/platform/tenants/{criado['id']}/inativar",
        headers={"Idempotency-Key": "inativar-filtro"},
    )

    resp = client.get("/platform/tenants", params={"estado": "inativo", "size": 10}).json()

    nossos = [item for item in resp["items"] if item["id"] == criado["id"]]
    assert len(nossos) == 1
    assert nossos[0]["estado"] == "inativo"
