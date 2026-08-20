"""Seed governado do IMP-301 para jornadas compostas em stack real."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from emprestimo.application.iam_catalogo import CATALOGO_PERMISSOES
from emprestimo.application.notifications import FakeNotificationChannel, NotificationService
from emprestimo.application.scheduler import SchedulerService
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.operacao_diaria import CobrancaCaso
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.tenant import Tenant
from emprestimo.domain.platform.usuario import Usuario
from emprestimo.infrastructure.db import orm  # noqa: F401
from emprestimo.infrastructure.db.base import Base
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyCobrancaCasoRepository,
    SqlAlchemyCredencialRepository,
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.presentation.api.main import create_app


@dataclass(frozen=True)
class PrincipalSeed:
    carteira_id: str
    email: str
    institution: str
    password: str
    tenant_id: str
    usuario_id: str


def reset_schema(database_url: str) -> sessionmaker[Session]:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(sa.text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(sa.text("CREATE SCHEMA public"))
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_principal(
    session: Session,
    *,
    institution: str,
    nome: str,
    password: str,
    permissions: tuple[Any, ...],
) -> PrincipalSeed:
    tenant = Tenant(identificador_institucional=institution, nome=f"Instituicao {institution}")
    tenant.ativar()
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = Carteira(tenant_id=tenant.id, nome=f"Carteira {institution}")
    SqlAlchemyCarteiraRepository(session).save(carteira)
    usuario = Usuario(
        tenant_id=tenant.id,
        nome=nome,
        email="operador@example.test",
        perfil_acesso="Operador Integrado",
    )
    usuario.ativar()
    SqlAlchemyUsuarioRepository(session).save(usuario)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=usuario.id, segredo=password)
    )
    perfil = PerfilAcesso(tenant_id=tenant.id, nome="Operador Integrado")
    for permissao in permissions:
        perfil.adicionar_permissao(permissao)
    perfil_repo = SqlAlchemyPerfilAcessoRepository(session)
    perfil_repo.save(perfil)
    perfil_repo.atribuir_usuario(usuario.id, perfil.id)
    session.commit()
    return PrincipalSeed(
        carteira_id=str(carteira.id),
        email=usuario.email,
        institution=institution,
        password=password,
        tenant_id=str(tenant.id),
        usuario_id=str(usuario.id),
    )


def create_tenant_user(
    session: Session,
    *,
    carteira_id: str,
    email: str,
    institution: str,
    nome: str,
    password: str,
    permissions: tuple[Any, ...],
    tenant_id: str,
) -> PrincipalSeed:
    tenant_uuid = uuid.UUID(tenant_id)
    usuario = Usuario(
        tenant_id=tenant_uuid,
        nome=nome,
        email=email,
        perfil_acesso="Operador Integrado",
    )
    usuario.ativar()
    SqlAlchemyUsuarioRepository(session).save(usuario)
    SqlAlchemyCredencialRepository(session).save(
        Credencial.definir(usuario_id=usuario.id, segredo=password)
    )
    perfil = PerfilAcesso(tenant_id=tenant_uuid, nome=f"Perfil {nome}")
    for permissao in permissions:
        perfil.adicionar_permissao(permissao)
    perfil_repo = SqlAlchemyPerfilAcessoRepository(session)
    perfil_repo.save(perfil)
    perfil_repo.atribuir_usuario(usuario.id, perfil.id)
    session.commit()
    return PrincipalSeed(
        carteira_id=carteira_id,
        email=usuario.email,
        institution=institution,
        password=password,
        tenant_id=tenant_id,
        usuario_id=str(usuario.id),
    )


def post_ok(
    client: TestClient,
    path: str,
    *,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
    expected: int = 200,
) -> dict[str, Any]:
    response = client.post(path, json=json_body, headers=headers)
    assert response.status_code == expected, (path, response.status_code, response.text)
    return dict(response.json())


def get_ok(
    client: TestClient, path: str, *, headers: dict[str, str], params: dict[str, Any] | None = None
) -> dict[str, Any]:
    response = client.get(path, params=params, headers=headers)
    assert response.status_code == 200, (path, response.status_code, response.text)
    return (
        dict(response.json()) if isinstance(response.json(), dict) else {"items": response.json()}
    )


def login(client: TestClient, principal: PrincipalSeed) -> str:
    response = client.post(
        "/auth/login",
        json={
            "identificador_institucional": principal.institution,
            "email": principal.email,
            "segredo": principal.password,
        },
        headers={"X-Correlation-ID": f"corr-seed-login-{principal.institution.lower()}"},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


def bearer(ticket: str, correlation: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {ticket}", "X-Correlation-ID": correlation}


def create_devedor(
    client: TestClient, principal: PrincipalSeed, headers: dict[str, str]
) -> dict[str, Any]:
    return post_ok(
        client,
        f"/credit/carteiras/{principal.carteira_id}/devedores",
        expected=201,
        headers={**headers, "Idempotency-Key": f"imp301-devedor-{uuid.uuid4()}"},
        json_body={
            "documento": "52998224725",
            "nome": "Cliente Integrado IMP-301",
            "contatos": [
                {
                    "tipo": "email",
                    "valor": f"cliente-{uuid.uuid4().hex[:8]}@example.test",
                    "preferencial": True,
                    "notificacao_estado": "permitido",
                    "notificacao_evidencia": "consentimento integrado",
                    "notificacao_origem": "imp-301",
                }
            ],
        },
    )


def financial_parameters() -> dict[str, Any]:
    """Parametros do emprestimo livre (DR-004).

    `quantidade_parcelas` e `primeiro_vencimento` sairam com o plano de
    parcelas. O que resta e o dia combinado do acerto: `dia_de_acerto` chega ao
    Emprestimo pelos parametros do Contrato, e e dele que o Motor deriva o
    proximo acerto a cada consulta.
    """
    return {
        "valor_contratado": "10000.00",
        "dia_de_acerto": 10,
        "taxa_juros_mensal": "0.0200",
        "moeda": "BRL",
    }


def create_approved_proposal(
    client: TestClient, principal: PrincipalSeed, headers: dict[str, str], devedor_id: str
) -> dict[str, Any]:
    simulation = post_ok(
        client,
        f"/credit/carteiras/{principal.carteira_id}/devedores/{devedor_id}/simulacoes-comerciais",
        expected=201,
        headers=headers,
        json_body={"parametros": financial_parameters()},
    )
    proposal = post_ok(
        client,
        f"/credit/carteiras/{principal.carteira_id}/devedores/{devedor_id}/propostas-comerciais",
        expected=201,
        headers=headers,
        json_body={"simulacao_id": simulation["id"], "parametros": financial_parameters()},
    )
    post_ok(
        client,
        f"/credit/propostas-comerciais/{proposal['id']}/enviar-para-analise",
        headers=headers,
    )
    approved = post_ok(
        client, f"/credit/propostas-comerciais/{proposal['id']}/aprovar", headers=headers
    )
    return {"proposal": approved, "simulation": simulation}


def create_contract_and_loan(
    client: TestClient, principal: PrincipalSeed, headers: dict[str, str], proposal_id: str
) -> dict[str, Any]:
    contract = post_ok(
        client,
        f"/credit/carteiras/{principal.carteira_id}/contratos",
        expected=201,
        headers=headers,
        json_body={"proposta_comercial_id": proposal_id},
    )
    post_ok(client, f"/credit/contratos/{contract['id']}/assinar", headers=headers)
    released = post_ok(
        client, f"/credit/contratos/{contract['id']}/liberar-para-motor", headers=headers
    )
    loan = post_ok(
        client,
        f"/credit/contratos/{contract['id']}/emprestimos",
        expected=201,
        headers={**headers, "Idempotency-Key": "imp301-emprestimo"},
    )
    # Nao ha plano a gerar (DR-004). O pagamento vale por si: o Motor separa
    # juros de amortizacao sobre o saldo do dia, sem parcela a liquidar.
    recebido_em = f"{datetime.now(UTC).date().isoformat()}T12:00:00Z"
    payment_headers = {**headers, "Idempotency-Key": "imp301-pagamento-repetido"}
    payment = post_ok(
        client,
        f"/credit/emprestimos/{loan['id']}/pagamentos",
        headers=payment_headers,
        json_body={"valor": "500.00", "recebido_em": recebido_em},
    )
    replay = post_ok(
        client,
        f"/credit/emprestimos/{loan['id']}/pagamentos",
        headers=payment_headers,
        json_body={"valor": "500.00", "recebido_em": recebido_em},
    )
    assert replay["id"] == payment["id"]
    return {
        "contract": released,
        "loan": loan,
        "payment": payment,
        "paymentReplayVerified": True,
    }


def seed_cobranca_agenda(
    client: TestClient,
    session_factory: sessionmaker[Session],
    principal: PrincipalSeed,
    headers: dict[str, str],
    devedor_id: str,
    loan_id: str,
    payment_id: str,
) -> dict[str, Any]:
    with session_factory() as session:
        case = CobrancaCaso(
            tenant_id=uuid.UUID(principal.tenant_id),
            carteira_id=uuid.UUID(principal.carteira_id),
            devedor_id=uuid.UUID(devedor_id),
            emprestimo_id=uuid.UUID(loan_id),
            titulo="Caso integrado de cobranca",
            origem="imp301",
            total_pendente=Decimal("100.00"),
        )
        SqlAlchemyCobrancaCasoRepository(session).save(case)
        session.commit()
        case_id = str(case.id)
    post_ok(
        client,
        f"/credit/cobrancas/casos/{case_id}/acoes",
        headers={**headers, "Idempotency-Key": "imp301-acao"},
        json_body={"tipo": "telefone", "resultado": "cliente contatado"},
    )
    promise = post_ok(
        client,
        f"/credit/cobrancas/casos/{case_id}/promessas",
        headers={**headers, "Idempotency-Key": "imp301-promessa"},
        json_body={"valor_declarado": "100.00", "data_promessa": "2026-09-20"},
    )
    post_ok(
        client,
        f"/credit/cobrancas/promessas/{promise['promessa_id']}/apropriacoes",
        headers={**headers, "Idempotency-Key": "imp301-apropriacao"},
        json_body={"pagamento_id": payment_id},
    )
    template = post_ok(
        client,
        "/credit/notificacoes/templates",
        expected=201,
        headers=headers,
        json_body={
            "codigo": "jornada-integrada",
            "versao": 1,
            "assunto": "Lembrete {data_hora}",
            "corpo": "Atendimento via {canal_atendimento} em {data_hora}",
            "parametros_permitidos": ["data_hora", "canal_atendimento"],
        },
    )
    post_ok(
        client,
        f"/credit/notificacoes/templates/{template['id']}/aprovar",
        headers=headers,
        json_body={"motivo": "seed"},
    )
    post_ok(client, f"/credit/notificacoes/templates/{template['id']}/ativar", headers=headers)
    commitment = post_ok(
        client,
        f"/credit/carteiras/{principal.carteira_id}/devedores/{devedor_id}/agenda/compromissos",
        headers={**headers, "Idempotency-Key": "imp301-compromisso"},
        json_body={
            "titulo": "Retorno integrado",
            "previsto_para": "2026-09-10T12:00:00Z",
            "emprestimo_id": loan_id,
        },
    )
    reminder = post_ok(
        client,
        f"/credit/agenda/compromissos/{commitment['agenda_item_id']}/lembretes",
        headers={**headers, "Idempotency-Key": "imp301-lembrete"},
        json_body={"horario": "2026-09-10T11:00:00Z", "mensagem": "Ligar para cliente"},
    )
    post_ok(
        client,
        f"/credit/carteiras/{principal.carteira_id}/devedores/{devedor_id}/comunicacoes",
        headers={**headers, "Idempotency-Key": "imp301-comunicacao"},
        json_body={
            "canal": "telefone",
            "ocorrido_em": "2026-09-10T12:30:00Z",
            "resumo": "Acompanhamento integrado",
            "resultado": "registrado",
            "emprestimo_id": loan_id,
        },
    )
    scheduler = SchedulerService(lambda: SqlAlchemyUnitOfWork(session_factory))
    claims = scheduler.reivindicar(
        slots_livres=1, batch_size=1, agora=datetime(2026, 9, 10, 11, 1, tzinfo=UTC)
    )
    if claims:
        NotificationService(
            lambda: SqlAlchemyUnitOfWork(session_factory), FakeNotificationChannel()
        ).processar_lembrete(claims[0])
    return {
        "case": case_id,
        "commitment": commitment["agenda_item_id"],
        "reminder": reminder["lembrete_id"],
        "template": template["id"],
    }


def seed_configuracoes(
    client: TestClient, principal: PrincipalSeed, headers: dict[str, str]
) -> dict[str, Any]:
    modality = post_ok(
        client,
        "/credit/configuracoes-financeiras/modalidades",
        expected=201,
        headers=headers,
        json_body={
            "codigo": "consignado",
            "nome": "Consignado",
            "carteira_id": principal.carteira_id,
        },
    )
    calendar = post_ok(
        client,
        "/credit/configuracoes-financeiras/calendarios",
        expected=201,
        headers=headers,
        json_body={
            "codigo": "br",
            "nome": "Brasil",
            "feriados": [],
            "carteira_id": principal.carteira_id,
        },
    )
    config = post_ok(
        client,
        "/credit/configuracoes-financeiras",
        expected=201,
        headers=headers,
        json_body={
            "modalidade": "consignado",
            "calendario_id": calendar["id"],
            "carteira_id": principal.carteira_id,
            "vigencia_inicio": "2026-08-14",
            "taxas": [{"nome": "taxa_operacional", "valor": "0.00", "periodicidade": "mensal"}],
            "parametros": [{"nome": "canal", "valor": "integrado"}],
            "politica_arredondamento": {"modo": "half_even", "escala": 2},
        },
    )
    approved = post_ok(
        client,
        f"/credit/configuracoes-financeiras/{config['id']}/aprovar",
        headers=headers,
        json_body={"motivo": "seed"},
    )
    return {"calendar": calendar["id"], "config": approved["id"], "modality": modality["id"]}


def seed(path: Path, database_url: str) -> None:
    os.environ["DATABASE_URL"] = database_url
    os.environ.setdefault("JWT_SECRET_KEY", "imp301-integrated-stack-only")
    os.environ["APP_ENV"] = "test"
    session_factory = reset_schema(database_url)
    with session_factory() as session:
        full = create_principal(
            session,
            institution="JORNADAS",
            nome="Operador Integrado",
            password="segredo-jornadas",
            permissions=tuple(CATALOGO_PERMISSOES),
        )
        denied = create_tenant_user(
            session,
            carteira_id=full.carteira_id,
            email="sem-permissao@example.test",
            institution=full.institution,
            nome="Operador Sem Permissao",
            password="segredo-jornadas",
            permissions=(),
            tenant_id=full.tenant_id,
        )
    with TestClient(create_app()) as client:
        ticket = login(client, full)
        headers = bearer(ticket, "corr-imp301-seed")
        devedor = create_devedor(client, full, headers)
        commercial = create_approved_proposal(client, full, headers, devedor["id"])
        motor = create_contract_and_loan(client, full, headers, commercial["proposal"]["id"])
        daily = seed_cobranca_agenda(
            client,
            session_factory,
            full,
            headers,
            devedor["id"],
            motor["loan"]["id"],
            motor["payment"]["id"],
        )
        config = seed_configuracoes(client, full, headers)
        # Garante credenciais e perfil sem permissao existem e validam RBAC pelo frontend.
        assert login(client, denied)
        payload = {
            "credentials": asdict(full),
            "deniedCredentials": asdict(denied),
            "ids": {
                "case": daily["case"],
                "commitment": daily["commitment"],
                "config": config["config"],
                "contract": motor["contract"]["contrato_id"],
                "devedor": devedor["id"],
                "loan": motor["loan"]["id"],
                "payment": motor["payment"]["id"],
                "proposal": commercial["proposal"]["id"],
                "reminder": daily["reminder"],
                "simulation": commercial["simulation"]["id"],
                "template": daily["template"],
            },
            "paymentReplayVerified": motor["paymentReplayVerified"],
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    seed(Path(args.output), args.database_url)


if __name__ == "__main__":
    main()
