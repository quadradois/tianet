"""Qualificação de custo backend por ferramenta (IMP-356-F slice 5).

Prova única, fora do pytest (lenta de propósito): semeia 1.000 operações
e 10.000 pagamentos via ORM direto (só o caminho de LEITURA importa —
o Motor calcula ao ler) num banco descartável, e dispara 100 consultas
sintéticas por ferramenta do catálogo contra a API real, com 2 clientes
concorrentes. Critério: p95 ≤ 2 s e nenhuma > 5 s por ferramenta; quem
estourar é desabilitado via `ferramentas_habilitadas`, nunca "otimizado"
no escuro.

Uso: .venv\\Scripts\\python.exe scripts/benchmark_356f.py [--saida json]
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

# Banco descartável ANTES de qualquer import que resolva engine.
from db_guard import preparar_banco_descartavel  # noqa: E402
from emprestimo.infrastructure.db.session import database_url  # noqa: E402

os.environ["DATABASE_URL"] = preparar_banco_descartavel(database_url())

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from emprestimo.application.autorizacao import Principal  # noqa: E402
from emprestimo.domain.credit.carteira import Carteira  # noqa: E402
from emprestimo.infrastructure.db.orm import (  # noqa: E402
    Base,
    CarteiraORM,
    ContratoCreditoORM,
    DevedorORM,
    EmprestimoORM,
    PagamentoORM,
    PropostaComercialORM,
    TenantORM,
    UsuarioORM,
)
from emprestimo.presentation.api import dependencies  # noqa: E402
from emprestimo.presentation.api.main import create_app  # noqa: E402

N_DEVEDORES = 200
EMPRESTIMOS_POR_DEVEDOR = 5
PAGAMENTOS_POR_EMPRESTIMO = 10
CONSULTAS_POR_FERRAMENTA = 100
P95_LIMITE_S = 2.0
MAX_LIMITE_S = 5.0
HOJE = datetime(2026, 9, 16, tzinfo=UTC)

PARAMS = {
    "valor_contratado": "10000.00",
    "moeda": "BRL",
    "taxa_juros_mensal": "0.0200",
    "quantidade_parcelas": 10,
    "primeiro_vencimento": "2026-09-10",
    "regra_calculo": "juros_simples_periodo_real",
}


def _cpf_valido(seq: int) -> str:
    base = [int(d) for d in f"{seq % 1000000000:09d}"]
    for peso in (range(10, 1, -1), range(11, 1, -1)):
        soma = sum(d * p for d, p in zip(base, peso, strict=True))
        resto = soma % 11
        base.append(0 if resto < 2 else 11 - resto)
    return "".join(str(d) for d in base)


def semear(session: object) -> dict[str, object]:
    tenant_id, carteira_id, usuario_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    # Flush por nível de dependência (um flush por agregado, como os
    # repositórios fazem): evita contar com a ordem do UoW em massa.
    # Sufixo único: o banco descartável é reutilizado entre execuções.
    sufixo = uuid.uuid4().hex[:8]
    session.add(
        TenantORM(
            id=tenant_id,
            identificador_institucional=f"BENCH-{sufixo}",
            nome="Benchmark",
            estado="ativo",
        )
    )
    session.flush()
    session.add(
        UsuarioORM(
            id=usuario_id,
            tenant_id=tenant_id,
            nome="Bench",
            email="bench@exemplo.com",
            estado="ativo",
        )
    )
    session.add(CarteiraORM(id=carteira_id, tenant_id=tenant_id, nome="Bench"))
    session.flush()
    devedores = []
    for i in range(N_DEVEDORES):
        devedor_id = uuid.uuid4()
        devedores.append(devedor_id)
        session.add(
            DevedorORM(
                id=devedor_id,
                carteira_id=carteira_id,
                documento=_cpf_valido(100000000 + i),
                nome=f"Devedor Bench {i}",
                estado="ativo",
            )
        )
    session.flush()
    propostas, contratos, emprestimos = [], [], []
    for d, devedor_id in enumerate(devedores):
        for e in range(EMPRESTIMOS_POR_DEVEDOR):
            proposta_id, contrato_id, emprestimo_id = (
                uuid.uuid4(),
                uuid.uuid4(),
                uuid.uuid4(),
            )
            propostas.append(
                PropostaComercialORM(
                    id=proposta_id,
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    criada_por_usuario_id=usuario_id,
                    estado="aprovada",
                    parametros={"valor": 10000},
                )
            )
            contratos.append(
                ContratoCreditoORM(
                    id=contrato_id,
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    proposta_comercial_id=proposta_id,
                    criado_por_usuario_id=usuario_id,
                    estado="liberado_para_motor",
                    parametros={"valor": 10000},
                )
            )
            dia = 1 + ((d * EMPRESTIMOS_POR_DEVEDOR + e) % 28)
            emprestimos.append(
                EmprestimoORM(
                    id=emprestimo_id,
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    contrato_id=contrato_id,
                    estado="ativo",
                    principal_original=Decimal("10000.00"),
                    moeda="BRL",
                    parametros_financeiros=dict(PARAMS),
                    proximo_vencimento_em=datetime(2026, 8, dia, tzinfo=UTC),
                )
            )
    session.add_all(propostas)
    session.flush()
    session.add_all(contratos)
    session.flush()
    session.add_all(emprestimos)
    session.flush()
    pagamentos = []
    for n, emprestimo in enumerate(emprestimos):
        for p in range(PAGAMENTOS_POR_EMPRESTIMO):
            dia = 1 + ((n * PAGAMENTOS_POR_EMPRESTIMO + p) % 28)
            pagamentos.append(
                PagamentoORM(
                    id=uuid.uuid4(),
                    emprestimo_id=emprestimo.id,
                    valor_recebido=Decimal("100.00"),
                    recebido_em=datetime(2026, 8, dia, tzinfo=UTC),
                    valor_juros=Decimal("10.00"),
                    valor_amortizacao=Decimal("90.00"),
                    valor_encargos=Decimal("0.00"),
                    valor_devolvido=Decimal("0.00"),
                    valor_estornado=Decimal("0.00"),
                    chave_idempotencia=f"bench-{n}-{p}",
                    distribuicao={},
                    usuario_id=usuario_id,
                    estado="confirmado",
                )
            )
    session.add_all(pagamentos)
    session.commit()
    return {
        "tenant_id": tenant_id,
        "carteira_id": carteira_id,
        "usuario_id": usuario_id,
        "devedores": devedores,
        "emprestimos": [e.id for e in emprestimos],
    }


def medir(client: TestClient, metodo: str, caminho: str, params: dict[str, str]) -> float:
    inicio = time.perf_counter()
    resposta = client.request(metodo, caminho, params=params)
    duracao = time.perf_counter() - inicio
    assert resposta.status_code == 200, (caminho, resposta.status_code, resposta.text[:200])
    return duracao


def _montar_app(
    ids: dict[str, object],
) -> tuple[object, object, Carteira]:
    from datetime import UTC, timedelta

    principal = Principal(
        usuario_id=ids["usuario_id"],
        tenant_id=ids["tenant_id"],
        perfil_acesso="Operadora",
        access_token_expira_em=datetime.now(UTC) + timedelta(minutes=15),
    )
    carteira = Carteira(id=ids["carteira_id"], tenant_id=ids["tenant_id"], nome="Bench")
    app = create_app()
    autorizacao = Mock()
    autorizacao.exigir_permissao.return_value = None
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: principal
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao
    app.dependency_overrides[dependencies.get_carteira_do_principal] = lambda: carteira
    return app, principal, carteira


def main() -> int:
    parser = argparse.ArgumentParser(description="Qualificação de custo backend 356-F")
    parser.add_argument("--saida", type=str, default="relatorio-benchmark-356f.json")
    args = parser.parse_args()

    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine)
    with fabrica() as session:
        ids = semear(session)

    def _app() -> TestClient:
        app, _, _ = _montar_app(ids)
        return TestClient(app)

    cid = str(ids["carteira_id"])
    devedor_alvo = str(ids["devedores"][0])
    alvos: dict[str, tuple[str, str, dict[str, str]]] = {
        "localizar_devedor": ("GET", f"/credit/carteiras/{cid}/devedores", {"nome": "Bench"}),
        "consultar_saldo_devedor": (
            "GET",
            f"/credit/devedores/{devedor_alvo}/saldo",
            {"data_referencia": "2026-09-16"},
        ),
        "consultar_resumo_carteira": (
            "GET",
            f"/credit/carteiras/{cid}/relatorios/resumo",
            {"data_referencia": "2026-09-16"},
        ),
        "consultar_acertos": (
            "GET",
            f"/credit/carteiras/{cid}/relatorios/vencimentos",
            {"data_referencia": "2026-09-16"},
        ),
        "consultar_pagamentos_periodo": (
            "GET",
            f"/credit/carteiras/{cid}/relatorios/pagamentos",
            {"inicio": "2026-08-01", "fim": "2026-08-31"},
        ),
        "consultar_fluxo_realizado": (
            "GET",
            f"/credit/carteiras/{cid}/relatorios/fluxo",
            {"inicio": "2026-08-01", "fim": "2026-08-31"},
        ),
    }

    relatorio: dict[str, object] = {"ferramentas": {}, "ok": True}
    for nome, (metodo, caminho, params) in alvos.items():

        def _lote(
            n: int,
            metodo: str = metodo,
            caminho: str = caminho,
            params: dict[str, str] = params,
        ) -> list[float]:
            with _app() as cliente:
                return [medir(cliente, metodo, caminho, params) for _ in range(n)]

        with ThreadPoolExecutor(max_workers=2) as piscina:
            metades = [CONSULTAS_POR_FERRAMENTA // 2] * 2
            latencias = sorted(lat for lote in piscina.map(_lote, metades) for lat in lote)
        p50 = statistics.median(latencias)
        p95 = statistics.quantiles(latencias, n=100)[94]
        pico = latencias[-1]
        aprovado = p95 <= P95_LIMITE_S and pico <= MAX_LIMITE_S
        relatorio["ferramentas"][nome] = {  # type: ignore[index]
            "n": len(latencias),
            "p50_s": round(p50, 3),
            "p95_s": round(p95, 3),
            "max_s": round(pico, 3),
            "aprovada": aprovado,
        }
        if not aprovado:
            relatorio["ok"] = False
        print(
            f"{nome}: p50={p50:.3f}s p95={p95:.3f}s "
            f"max={pico:.3f}s {'OK' if aprovado else 'REPROVADA'}"
        )

    Path(args.saida).write_text(json.dumps(relatorio, indent=2), encoding="utf-8")
    engine.dispose()
    return 0 if relatorio["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
