"""Contratos de protecao dos endpoints existentes (IMP-091)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCredencialRepository,
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "segredo-api-protected-endpoints"
SEGREDO = "Senha forte 123"

TENANT_PAYLOAD = {
    "identificador_institucional": "IDENT-PROTECTED",
    "nome": "Financeira Protegida",
    "nome_administrador": "Maria",
    "email_administrador": "maria.protegida@exemplo.com",
}
DEVEDOR_PAYLOAD = {
    "documento": "52998224725",
    "nome": "Joao da Silva",
    "contatos": [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}],
}
RESPOSTA_401 = {
    "codigo": "autenticacao_recusada",
    "mensagem": "Autenticacao recusada",
}
ERRO_RESPONSE_REF = {"$ref": "#/components/schemas/ErroResponse"}
ROTAS_COM_404_DOCUMENTADO = {
    ("post", "/credit/carteiras/{carteira_id}/devedores"),
    ("get", "/credit/carteiras/{carteira_id}/devedores"),
    ("get", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}"),
    ("patch", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}"),
    ("get", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/historico"),
    ("post", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar"),
    ("post", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/reativar"),
    (
        "post",
        "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais",
    ),
    ("get", "/credit/simulacoes-comerciais/{simulacao_id}"),
    (
        "post",
        "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
    ),
    (
        "get",
        "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais",
    ),
    ("get", "/credit/propostas-comerciais/{proposta_id}"),
    ("patch", "/credit/propostas-comerciais/{proposta_id}"),
    ("post", "/credit/propostas-comerciais/{proposta_id}/enviar-para-analise"),
    ("post", "/credit/propostas-comerciais/{proposta_id}/aprovar"),
    ("post", "/credit/propostas-comerciais/{proposta_id}/recusar"),
    ("post", "/credit/propostas-comerciais/{proposta_id}/cancelar"),
    ("post", "/credit/propostas-comerciais/{proposta_id}/expirar"),
    ("get", "/credit/propostas-comerciais/{proposta_id}/contrato-logico"),
    ("post", "/credit/carteiras/{carteira_id}/contratos"),
    ("get", "/credit/carteiras/{carteira_id}/contratos"),
    ("get", "/credit/contratos/{contrato_id}"),
    ("get", "/credit/contratos/{contrato_id}/historico"),
    ("post", "/credit/contratos/{contrato_id}/assinar"),
    ("post", "/credit/contratos/{contrato_id}/liberar-para-motor"),
    ("post", "/credit/contratos/{contrato_id}/cancelar"),
    ("post", "/credit/contratos/{contrato_id}/encerrar"),
    ("post", "/credit/contratos/{contrato_id}/emprestimos"),
    ("get", "/credit/emprestimos/{emprestimo_id}"),
    ("get", "/credit/carteiras/{carteira_id}/emprestimos"),
    ("post", "/credit/emprestimos/{emprestimo_id}/parcelas"),
    ("get", "/credit/emprestimos/{emprestimo_id}/parcelas"),
    ("post", "/credit/emprestimos/{emprestimo_id}/pagamentos"),
    ("get", "/credit/emprestimos/{emprestimo_id}/saldo"),
    ("get", "/credit/emprestimos/{emprestimo_id}/memoria-calculo"),
    ("get", "/credit/emprestimos/{emprestimo_id}/quitacao"),
    ("post", "/credit/emprestimos/{emprestimo_id}/quitacao"),
    ("post", "/credit/emprestimos/{emprestimo_id}/renegociacoes"),
    ("get", "/credit/cobrancas/casos"),
    ("post", "/credit/cobrancas/casos/{cobranca_caso_id}/acoes"),
    ("post", "/credit/cobrancas/casos/{cobranca_caso_id}/promessas"),
    ("post", "/credit/cobrancas/promessas/{promessa_id}/apropriacoes"),
    ("get", "/credit/agenda"),
    ("post", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos"),
    ("post", "/credit/agenda/compromissos/{agenda_item_id}/lembretes"),
    ("post", "/credit/agenda/compromissos/{agenda_item_id}/reagendar"),
    ("post", "/credit/agenda/compromissos/{agenda_item_id}/concluir"),
    ("post", "/credit/agenda/compromissos/{agenda_item_id}/cancelar"),
    ("post", "/credit/agenda/lembretes/{lembrete_id}/reagendar"),
    ("post", "/credit/agenda/lembretes/{lembrete_id}/enviar"),
    ("post", "/credit/agenda/lembretes/{lembrete_id}/concluir"),
    ("post", "/credit/agenda/lembretes/{lembrete_id}/cancelar"),
    ("post", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes"),
    ("get", "/credit/comunicacoes"),
    ("get", "/credit/carteiras/{carteira_id}/relatorios/resumo"),
    ("get", "/credit/carteiras/{carteira_id}/relatorios/vencimentos"),
    ("get", "/credit/carteiras/{carteira_id}/relatorios/pagamentos"),
    ("get", "/credit/carteiras/{carteira_id}/relatorios/fluxo"),
    ("post", "/credit/configuracoes-financeiras/modalidades"),
    ("get", "/credit/configuracoes-financeiras/modalidades"),
    ("post", "/credit/configuracoes-financeiras/calendarios"),
    ("get", "/credit/configuracoes-financeiras/calendarios"),
    ("post", "/credit/configuracoes-financeiras"),
    ("get", "/credit/configuracoes-financeiras"),
    ("get", "/credit/configuracoes-financeiras/vigente"),
    ("post", "/credit/configuracoes-financeiras/snapshots"),
    ("get", "/credit/configuracoes-financeiras/{configuracao_id}"),
    ("post", "/credit/configuracoes-financeiras/{configuracao_id}/aprovar"),
    ("post", "/credit/configuracoes-financeiras/{configuracao_id}/programar"),
    ("post", "/credit/configuracoes-financeiras/{configuracao_id}/ativar"),
    ("post", "/credit/configuracoes-financeiras/{configuracao_id}/inativar"),
    ("patch", "/iam/credencial"),
    ("post", "/iam/usuarios/{usuario_id}/credencial/redefinir"),
    ("get", "/iam/perfis/{perfil_id}"),
    ("patch", "/iam/perfis/{perfil_id}"),
    ("post", "/iam/perfis/{perfil_id}/inativar"),
    ("put", "/iam/perfis/{perfil_id}/permissoes/{codigo}"),
    ("delete", "/iam/perfis/{perfil_id}/permissoes/{codigo}"),
    ("put", "/iam/usuarios/{usuario_id}/perfil/{perfil_id}"),
    ("delete", "/iam/usuarios/{usuario_id}/perfil"),
    ("get", "/iam/usuarios/{usuario_id}/permissoes"),
    ("get", "/platform/tenants"),
    ("get", "/platform/tenants/{tenant_id}"),
    ("patch", "/platform/tenants/{tenant_id}"),
    ("post", "/platform/tenants/{tenant_id}/inativar"),
    ("post", "/platform/tenants/{tenant_id}/reativar"),
}


@dataclass(frozen=True)
class EndpointProtegido:
    metodo: str
    path: str
    kwargs: dict[str, Any]


@dataclass(frozen=True)
class UsuarioAutenticado:
    usuario: Usuario
    token: str


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, JWT_SECRET)


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    del session
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def usuario_autenticado(session: Session) -> UsuarioAutenticado:
    tenant = Tenant(
        identificador_institucional="IDENT-USUARIO-PROTEGIDO",
        nome="Tenant Usuario Protegido",
        estado=TenantState.ATIVO,
    )
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = Usuario(
        tenant_id=tenant.id,
        nome="Usuario Protegido",
        email="usuario.protegido@exemplo.com",
        estado=UsuarioState.ATIVO,
        perfil_acesso="Operador",
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    perfil = PerfilAcesso(tenant_id=tenant.id, nome="Operador")
    for codigo in (
        "tenant.criar",
        "tenant.ler",
        "tenant.atualizar",
        "tenant.inativar",
        "tenant.reativar",
        "devedor.criar",
        "devedor.ler",
        "devedor.atualizar",
        "devedor.inativar",
        "devedor.reativar",
    ):
        perfil.adicionar_permissao(Permissao(codigo=codigo, descricao=codigo))
    perfil_repo = SqlAlchemyPerfilAcessoRepository(session)
    perfil_repo.save(perfil)
    perfil_repo.atribuir_usuario(usuario.id, perfil.id)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=usuario.id, segredo=SEGREDO)
    )
    session.commit()
    token = HmacAccessTokenService(JWT_SECRET).emitir(usuario).token
    return UsuarioAutenticado(usuario=usuario, token=token)


@pytest.fixture
def endpoints_protegidos() -> list[EndpointProtegido]:
    tenant_id = uuid.uuid4()
    carteira_id = uuid.uuid4()
    devedor_id = uuid.uuid4()
    proposta_id = uuid.uuid4()
    contrato_id = uuid.uuid4()
    emprestimo_id = uuid.uuid4()
    cobranca_caso_id = uuid.uuid4()
    promessa_id = uuid.uuid4()
    pagamento_id = uuid.uuid4()
    agenda_item_id = uuid.uuid4()
    lembrete_id = uuid.uuid4()
    configuracao_id = uuid.uuid4()
    return [
        EndpointProtegido(
            "post",
            "/platform/tenants",
            {"json": TENANT_PAYLOAD, "headers": {"Idempotency-Key": "imp-091-tenant"}},
        ),
        EndpointProtegido("get", "/platform/tenants", {}),
        EndpointProtegido("get", f"/platform/tenants/{tenant_id}", {}),
        EndpointProtegido("patch", f"/platform/tenants/{tenant_id}", {"json": {"nome": "Novo"}}),
        EndpointProtegido("post", f"/platform/tenants/{tenant_id}/inativar", {}),
        EndpointProtegido("post", f"/platform/tenants/{tenant_id}/reativar", {}),
        EndpointProtegido(
            "post",
            f"/credit/carteiras/{carteira_id}/devedores",
            {"json": DEVEDOR_PAYLOAD, "headers": {"Idempotency-Key": "imp-091-devedor"}},
        ),
        EndpointProtegido("get", f"/credit/carteiras/{carteira_id}/devedores", {}),
        EndpointProtegido("get", f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}", {}),
        EndpointProtegido(
            "get",
            f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/historico",
            {},
        ),
        EndpointProtegido(
            "patch",
            f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}",
            {"json": {"nome": "Novo"}, "headers": {"Idempotency-Key": "imp-091-patch"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar",
            {"headers": {"Idempotency-Key": "imp-091-inativar"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/reativar",
            {"headers": {"Idempotency-Key": "imp-091-reativar"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/carteiras/{carteira_id}/contratos",
            {"json": {"proposta_comercial_id": str(proposta_id)}},
        ),
        EndpointProtegido("get", f"/credit/carteiras/{carteira_id}/contratos", {}),
        EndpointProtegido("get", f"/credit/contratos/{contrato_id}", {}),
        EndpointProtegido("get", f"/credit/contratos/{contrato_id}/historico", {}),
        EndpointProtegido("post", f"/credit/contratos/{contrato_id}/assinar", {}),
        EndpointProtegido("post", f"/credit/contratos/{contrato_id}/liberar-para-motor", {}),
        EndpointProtegido(
            "post",
            f"/credit/contratos/{contrato_id}/cancelar",
            {"json": {"motivo": "teste"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/contratos/{contrato_id}/encerrar",
            {"json": {"motivo": "teste"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/contratos/{contrato_id}/emprestimos",
            {"headers": {"Idempotency-Key": "imp-168-emprestimo"}},
        ),
        EndpointProtegido("get", f"/credit/emprestimos/{emprestimo_id}", {}),
        EndpointProtegido("get", f"/credit/carteiras/{carteira_id}/emprestimos", {}),
        EndpointProtegido(
            "post",
            f"/credit/emprestimos/{emprestimo_id}/parcelas",
            {"json": {"data_referencia": "2026-08-10"}},
        ),
        EndpointProtegido("get", f"/credit/emprestimos/{emprestimo_id}/parcelas", {}),
        EndpointProtegido(
            "post",
            f"/credit/emprestimos/{emprestimo_id}/pagamentos",
            {
                "json": {"valor": "100.00", "recebido_em": "2026-09-10T12:00:00Z"},
                "headers": {"Idempotency-Key": "imp-168-pagamento"},
            },
        ),
        EndpointProtegido(
            "get",
            f"/credit/emprestimos/{emprestimo_id}/saldo?data_referencia=2026-10-10",
            {},
        ),
        EndpointProtegido("get", f"/credit/emprestimos/{emprestimo_id}/memoria-calculo", {}),
        EndpointProtegido(
            "get",
            f"/credit/emprestimos/{emprestimo_id}/quitacao?data_referencia=2026-10-10",
            {},
        ),
        EndpointProtegido(
            "post",
            f"/credit/emprestimos/{emprestimo_id}/quitacao",
            {
                "json": {"recebido_em": "2026-10-10T12:00:00Z"},
                "headers": {"Idempotency-Key": "imp-168-quitacao"},
            },
        ),
        EndpointProtegido(
            "post",
            f"/credit/emprestimos/{emprestimo_id}/renegociacoes",
            {
                "json": {
                    "novos_parametros": {"taxa_juros_mensal": "0.0150"},
                    "renegociado_em": "2026-10-10T12:00:00Z",
                },
                "headers": {"Idempotency-Key": "imp-168-renegociacao"},
            },
        ),
        EndpointProtegido("get", "/credit/cobrancas/casos", {}),
        EndpointProtegido(
            "post",
            f"/credit/cobrancas/casos/{cobranca_caso_id}/acoes",
            {
                "json": {"tipo": "telefone", "resultado": "contato realizado"},
                "headers": {"Idempotency-Key": "imp-183-acao"},
            },
        ),
        EndpointProtegido(
            "post",
            f"/credit/cobrancas/casos/{cobranca_caso_id}/promessas",
            {
                "json": {"valor_declarado": "100.00", "data_promessa": "2026-08-20"},
                "headers": {"Idempotency-Key": "imp-183-promessa"},
            },
        ),
        EndpointProtegido(
            "post",
            f"/credit/cobrancas/promessas/{promessa_id}/apropriacoes",
            {
                "json": {"pagamento_id": str(pagamento_id)},
                "headers": {"Idempotency-Key": "imp-183-apropriacao"},
            },
        ),
        EndpointProtegido("get", "/credit/agenda", {}),
        EndpointProtegido(
            "post",
            f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos",
            {
                "json": {"titulo": "Contato", "previsto_para": "2026-09-10T12:00:00Z"},
                "headers": {"Idempotency-Key": "imp-183-compromisso"},
            },
        ),
        EndpointProtegido(
            "post",
            f"/credit/agenda/compromissos/{agenda_item_id}/lembretes",
            {
                "json": {"horario": "2026-09-10T11:00:00Z", "mensagem": "Ligar"},
                "headers": {"Idempotency-Key": "imp-183-lembrete"},
            },
        ),
        EndpointProtegido(
            "post",
            f"/credit/agenda/compromissos/{agenda_item_id}/reagendar",
            {
                "json": {"novo_horario": "2026-09-11T12:00:00Z"},
                "headers": {"Idempotency-Key": "imp-183-compromisso-reagendar"},
            },
        ),
        EndpointProtegido(
            "post",
            f"/credit/agenda/compromissos/{agenda_item_id}/concluir",
            {"headers": {"Idempotency-Key": "imp-183-compromisso-concluir"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/agenda/compromissos/{agenda_item_id}/cancelar",
            {"headers": {"Idempotency-Key": "imp-183-compromisso-cancelar"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/agenda/lembretes/{lembrete_id}/reagendar",
            {
                "json": {"novo_horario": "2026-09-11T11:00:00Z"},
                "headers": {"Idempotency-Key": "imp-183-lembrete-reagendar"},
            },
        ),
        EndpointProtegido(
            "post",
            f"/credit/agenda/lembretes/{lembrete_id}/enviar",
            {"headers": {"Idempotency-Key": "imp-183-lembrete-enviar"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/agenda/lembretes/{lembrete_id}/concluir",
            {"headers": {"Idempotency-Key": "imp-183-lembrete-concluir"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/agenda/lembretes/{lembrete_id}/cancelar",
            {"headers": {"Idempotency-Key": "imp-183-lembrete-cancelar"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes",
            {
                "json": {
                    "canal": "telefone",
                    "ocorrido_em": "2026-09-10T12:00:00Z",
                    "resumo": "Contato",
                    "resultado": "sem resposta",
                },
                "headers": {"Idempotency-Key": "imp-183-comunicacao"},
            },
        ),
        EndpointProtegido("get", "/credit/comunicacoes", {}),
        EndpointProtegido(
            "get",
            f"/credit/carteiras/{carteira_id}/relatorios/resumo?data_referencia=2026-09-10",
            {},
        ),
        EndpointProtegido(
            "get",
            f"/credit/carteiras/{carteira_id}/relatorios/vencimentos?data_referencia=2026-09-10",
            {},
        ),
        EndpointProtegido(
            "get",
            f"/credit/carteiras/{carteira_id}/relatorios/pagamentos?inicio=2026-09-01&fim=2026-09-30",
            {},
        ),
        EndpointProtegido(
            "get",
            f"/credit/carteiras/{carteira_id}/relatorios/fluxo?inicio=2026-09-01&fim=2026-09-30",
            {},
        ),
        EndpointProtegido(
            "post",
            "/credit/configuracoes-financeiras/modalidades",
            {
                "json": {
                    "codigo": "prazo_fixo",
                    "nome": "Prazo fixo",
                    "carteira_id": str(carteira_id),
                }
            },
        ),
        EndpointProtegido(
            "get",
            "/credit/configuracoes-financeiras/modalidades",
            {},
        ),
        EndpointProtegido(
            "post",
            "/credit/configuracoes-financeiras/calendarios",
            {
                "json": {
                    "codigo": "br_padrao",
                    "nome": "Brasil padrao",
                    "feriados": [],
                    "carteira_id": str(carteira_id),
                }
            },
        ),
        EndpointProtegido(
            "get",
            "/credit/configuracoes-financeiras/calendarios",
            {},
        ),
        EndpointProtegido(
            "post",
            "/credit/configuracoes-financeiras",
            {
                "json": {
                    "modalidade": "prazo_fixo",
                    "calendario_id": str(uuid.uuid4()),
                    "carteira_id": str(carteira_id),
                    "vigencia_inicio": "2026-09-01",
                    "taxas": [
                        {
                            "nome": "taxa_juros_mensal",
                            "valor": "0.0200",
                            "periodicidade": "mensal",
                        }
                    ],
                    "parametros": [{"nome": "moeda", "valor": "BRL"}],
                    "politica_arredondamento": {"modo": "half_up", "escala": 2},
                }
            },
        ),
        EndpointProtegido(
            "get",
            "/credit/configuracoes-financeiras?modalidade=prazo_fixo&data_referencia=2026-09-10",
            {},
        ),
        EndpointProtegido(
            "get",
            f"/credit/configuracoes-financeiras/{configuracao_id}",
            {},
        ),
        EndpointProtegido(
            "post",
            f"/credit/configuracoes-financeiras/{configuracao_id}/aprovar",
            {"json": {"motivo": "teste"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/configuracoes-financeiras/{configuracao_id}/programar",
            {"json": {"data_ativacao": "2026-09-01", "motivo": "teste"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/configuracoes-financeiras/{configuracao_id}/ativar",
            {"json": {"motivo": "teste"}},
        ),
        EndpointProtegido(
            "post",
            f"/credit/configuracoes-financeiras/{configuracao_id}/inativar",
            {"json": {"motivo": "teste"}},
        ),
        EndpointProtegido(
            "get",
            "/credit/configuracoes-financeiras/vigente?modalidade=prazo_fixo&data_referencia=2026-09-10",
            {},
        ),
        EndpointProtegido(
            "post",
            "/credit/configuracoes-financeiras/snapshots",
            {"json": {"configuracao_id": str(configuracao_id), "motivo": "teste"}},
        ),
    ]


def _chamar(
    client: TestClient,
    endpoint: EndpointProtegido,
    **extra_kwargs: Any,
) -> Response:
    kwargs = {**endpoint.kwargs, **extra_kwargs}
    return cast(Response, getattr(client, endpoint.metodo)(endpoint.path, **kwargs))


def test_todos_endpoints_platform_e_credit_recusam_sem_token(
    client: TestClient,
    endpoints_protegidos: list[EndpointProtegido],
) -> None:
    assert len(endpoints_protegidos) == 65

    for endpoint in endpoints_protegidos:
        resp = _chamar(client, endpoint)

        assert resp.status_code == 401, endpoint.path
        assert resp.json() == RESPOSTA_401


@pytest.mark.parametrize(
    "authorization",
    [
        "Token abc",
        "Bearer",
        "Bearer token-malformado",
    ],
)
def test_endpoint_protegido_recusa_authorization_invalido(
    client: TestClient,
    authorization: str,
) -> None:
    resp = client.get("/platform/tenants", headers={"Authorization": authorization})

    assert resp.status_code == 401
    assert resp.json() == RESPOSTA_401


def test_endpoint_protegido_recusa_token_expirado(
    client: TestClient,
    usuario_autenticado: UsuarioAutenticado,
) -> None:
    token_expirado = HmacAccessTokenService(JWT_SECRET).emitir(
        usuario_autenticado.usuario,
        agora=datetime.now(UTC) - timedelta(hours=1),
    )

    resp = client.get(
        "/platform/tenants",
        headers={"Authorization": f"Bearer {token_expirado.token}"},
    )

    assert resp.status_code == 401
    assert resp.json() == RESPOSTA_401


def test_endpoint_protegido_aceita_token_valido(
    client: TestClient,
    usuario_autenticado: UsuarioAutenticado,
) -> None:
    resp = client.get(
        "/platform/tenants",
        headers={"Authorization": f"Bearer {usuario_autenticado.token}"},
    )

    assert resp.status_code == 200


def test_health_permanece_publico_sem_token(client: TestClient) -> None:
    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {
        "status": "healthy",
        "service": "api",
        "checks": {"database": "healthy"},
    }
    assert resp.headers["X-Correlation-ID"]


def test_auth_login_permanece_publico_sem_authorization(
    client: TestClient,
    usuario_autenticado: UsuarioAutenticado,
) -> None:
    resp = client.post(
        "/auth/login",
        json={
            "identificador_institucional": "IDENT-USUARIO-PROTEGIDO",
            "email": usuario_autenticado.usuario.email,
            "segredo": SEGREDO,
        },
    )

    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


def test_openapi_declara_bearer_somente_nas_rotas_protegidas() -> None:
    schema = create_app().openapi()

    assert schema["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "description": "Access token IAM no esquema Bearer.",
        "scheme": "bearer",
    }
    metodos_http = {"get", "post", "put", "patch", "delete"}
    for path, path_item in schema["paths"].items():
        publico = path == "/health" or path.startswith("/auth/")
        for metodo, operacao in path_item.items():
            if metodo not in metodos_http:
                continue
            if publico:
                assert "security" not in operacao, (metodo, path)
            else:
                assert operacao["security"] == [{"BearerAuth": []}], (metodo, path)


def test_openapi_declara_contratos_de_erro_iam_autorizacao() -> None:
    schema = create_app().openapi()

    assert schema["components"]["schemas"]["ErroResponse"]["required"] == ["codigo", "mensagem"]
    metodos_http = {"get", "post", "put", "patch", "delete"}
    rotas_com_404_encontradas: set[tuple[str, str]] = set()
    for path, path_item in schema["paths"].items():
        publico = path == "/health"
        for metodo, operacao in path_item.items():
            if metodo not in metodos_http:
                continue
            responses = operacao["responses"]
            if path.startswith("/auth/"):
                _assert_erro_response(responses, "401", metodo, path)
                assert "403" not in responses, (metodo, path)
                continue
            if publico:
                assert {"401", "403", "404"}.isdisjoint(responses), (metodo, path)
                continue

            _assert_erro_response(responses, "401", metodo, path)
            _assert_erro_response(responses, "403", metodo, path)
            if (metodo, path) in ROTAS_COM_404_DOCUMENTADO:
                _assert_erro_response(responses, "404", metodo, path)
                rotas_com_404_encontradas.add((metodo, path))
            else:
                assert "404" not in responses, (metodo, path)

    assert rotas_com_404_encontradas == ROTAS_COM_404_DOCUMENTADO


def _assert_erro_response(
    responses: dict[str, Any],
    status_code: str,
    metodo: str,
    path: str,
) -> None:
    content = responses[status_code]["content"]["application/json"]
    assert content["schema"] == ERRO_RESPONSE_REF, (metodo, path, status_code)
