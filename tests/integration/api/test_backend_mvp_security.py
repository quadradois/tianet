"""Recertificacao P2 de seguranca, isolamento, idempotencia e auditoria."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.factories import CarteiraFactory, TenantFactory
from tests.integration.api.test_backend_mvp_e2e import AmbienteMVP, ambiente_mvp

from emprestimo.application.iam_catalogo import CATALOGO_POR_CODIGO
from emprestimo.infrastructure.db.orm import AuditoriaLogORM, DevedorORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyTenantRepository,
)
from emprestimo.presentation.api.main import create_app

__all__ = ["ambiente_mvp"]

API_DIR = Path("src/emprestimo/presentation/api")
PERMISSAO_LITERAL_RE = re.compile(r'exigir_permissao\("([^"]+)"\)')
CONSTANTE_RE = re.compile(r'^(PERMISSAO_[A-Z0-9_]+)\s*=\s*"([^"]+)"', re.MULTILINE)
DEPENDENCIA_CONSTANTE_RE = re.compile(r"exigir_permissao\((PERMISSAO_[A-Z0-9_]+)\)")


def test_imp_262_catalogo_rbac_cobre_permissoes_usadas_pelas_rotas() -> None:
    permissoes_usadas: set[str] = set()

    for path in sorted({*API_DIR.glob("*_routes.py"), API_DIR / "routes.py"}):
        texto = path.read_text(encoding="utf-8")
        constantes = dict(CONSTANTE_RE.findall(texto))
        permissoes_usadas.update(PERMISSAO_LITERAL_RE.findall(texto))
        permissoes_usadas.update(
            constantes[nome] for nome in DEPENDENCIA_CONSTANTE_RE.findall(texto)
        )

    assert permissoes_usadas
    assert permissoes_usadas <= set(CATALOGO_POR_CODIGO)
    # IMP-351: "tenant.criar" saiu desta lista porque POST /platform/tenants nao
    # existe mais. Ela continua no catalogo, com outro proposito: e o marcador
    # do papel de Administrador da Plataforma, lido por bootstrap_plataforma,
    # autorizacao.py e estado.py. Aqui a lista e de permissoes usadas por ROTAS.
    assert {
        "devedor.criar",
        "comercial.proposta.decidir",
        "contratos.contrato.liberar",
        "motor.pagamento.registrar",
        "cobranca.acao.registrar",
        "configuracoes_financeiras.configuracao.aprovar",
        "automacao.job.consultar",
        "notificacao.conciliar",
        "perfil.gerir",
    } <= permissoes_usadas


def test_imp_262_openapi_protege_todas_as_rotas_nao_publicas() -> None:
    schema = create_app().openapi()
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


def test_imp_263_carteira_cross_tenant_responde_404_e_nao_persiste(
    ambiente_mvp: AmbienteMVP,
    session: Session,
) -> None:
    outro_tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(outro_tenant)
    outra_carteira = CarteiraFactory.build(tenant_id=outro_tenant.id)
    SqlAlchemyCarteiraRepository(session).save(outra_carteira)
    session.commit()
    antes = _contar(session, DevedorORM)

    listagem = ambiente_mvp.client.get(
        f"/credit/carteiras/{outra_carteira.id}/devedores",
        headers=ambiente_mvp.headers,
    )
    escrita = ambiente_mvp.client.post(
        f"/credit/carteiras/{outra_carteira.id}/devedores",
        json=_devedor_payload("52998224725"),
        headers={**ambiente_mvp.headers, "Idempotency-Key": "plan020-cross-tenant"},
    )

    assert listagem.status_code == 404
    assert escrita.status_code == 404
    assert _contar(session, DevedorORM) == antes


def test_imp_264_idempotencia_replay_e_payload_divergente_em_api_mutavel(
    ambiente_mvp: AmbienteMVP,
) -> None:
    path = f"/credit/carteiras/{ambiente_mvp.carteira_id}/devedores"
    headers = {**ambiente_mvp.headers, "Idempotency-Key": "plan020-idempotencia-devedor"}
    payload_original = _devedor_payload("52998224725")

    primeiro = ambiente_mvp.client.post(path, json=payload_original, headers=headers)
    replay = ambiente_mvp.client.post(path, json=payload_original, headers=headers)
    divergente = ambiente_mvp.client.post(
        path,
        json=_devedor_payload("15350946056"),
        headers=headers,
    )

    assert primeiro.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["id"] == primeiro.json()["id"]
    assert divergente.status_code == 409
    assert divergente.json()["codigo"] == "conflito_idempotencia"


def test_imp_265_auditoria_append_only_sem_segredo_e_sem_mutacao_por_leitura(
    ambiente_mvp: AmbienteMVP,
    session: Session,
) -> None:
    criar = ambiente_mvp.client.post(
        f"/credit/carteiras/{ambiente_mvp.carteira_id}/devedores",
        json=_devedor_payload("52998224725"),
        headers={**ambiente_mvp.headers, "Idempotency-Key": "plan020-auditoria"},
    )
    assert criar.status_code == 201

    linhas_apos_escrita = _auditoria_snapshot(session)
    assert len(linhas_apos_escrita) >= 3
    assert all("senha-mvp-segura" not in (linha["detalhes"] or "") for linha in linhas_apos_escrita)

    historico = ambiente_mvp.client.get(
        f"/credit/carteiras/{ambiente_mvp.carteira_id}/devedores/{criar.json()['id']}/historico",
        headers=ambiente_mvp.headers,
    )
    assert historico.status_code == 200

    linhas_apos_leitura = _auditoria_snapshot(session)
    assert linhas_apos_leitura == linhas_apos_escrita


def _devedor_payload(documento: str) -> dict[str, Any]:
    return {
        "documento": documento,
        "nome": "Cliente Seguranca MVP",
        "contatos": [
            {
                "tipo": "email",
                "valor": f"seguranca-{uuid.uuid4().hex[:8]}@example.com",
                "preferencial": True,
                "notificacao_estado": "permitido",
                "notificacao_evidencia": "consentimento de teste",
                "notificacao_origem": "plan-020-p2",
            }
        ],
    }


def _contar(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _auditoria_snapshot(session: Session) -> list[dict[str, str | None]]:
    rows = session.scalars(select(AuditoriaLogORM).order_by(AuditoriaLogORM.criado_em)).all()
    return [
        {
            "id": str(row.id),
            "entidade": row.entidade,
            "acao": row.acao,
            "status": row.status,
            "detalhes": row.detalhes,
        }
        for row in rows
    ]
