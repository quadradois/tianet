"""Catálogo Operadora: contrato fechado, dispatcher e apresentadores (IMP-356-D).

Inclui a bateria anti-fraude T3: cada teste simula uma tentativa real de
abuso pelo modelo (ferramenta fantasma, argumento extra, ID cru no lugar
de referência, campo inventado, injeção em texto livre, URL livre) e prova
recusa ou neutralização — sem rede, sem mock permissivo.
"""

from __future__ import annotations

import asyncio
import dataclasses
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest

from emprestimo.agent.api_client import (
    ApiAusenciaError,
    ApiAutorizacaoError,
    ApiError,
    ClienteApi,
)
from emprestimo.agent.apresentadores import (
    formatar_valor,
    mascarar_documento,
    mascarar_nome,
    mensagem_ausencia,
    renderizar,
)
from emprestimo.agent.catalogo import CATALOGO, CATALOGO_VERSAO
from emprestimo.agent.dispatcher import (
    ArgumentoInvalidoError,
    ContextoFerramentas,
    FerramentaDesconhecidaError,
    executar_ferramenta,
)

HOJE = date(2026, 9, 14)
CARTEIRA = "11111111-1111-1111-1111-111111111111"
DEVEDOR_ID = "22222222-2222-2222-2222-222222222222"
REF = "ref-sessao-1"


class ClienteFalso:
    """Registra chamadas; nunca inventa resposta."""

    def __init__(self, resposta: dict[str, Any] | Exception) -> None:
        self.chamadas: list[tuple[str, dict[str, str | int]]] = []
        self._resposta = resposta

    async def get(
        self,
        caminho: str,
        params: Mapping[str, str | int] | None = None,
        timeout_segundos: float | None = None,
    ) -> dict[str, Any]:
        del timeout_segundos
        self.chamadas.append((caminho, dict(params or {})))
        if isinstance(self._resposta, Exception):
            raise self._resposta
        return self._resposta


def _contexto() -> ContextoFerramentas:
    return ContextoFerramentas(
        carteira_id=CARTEIRA,
        resolvedor_devedor=lambda ref: DEVEDOR_ID if ref == REF else None,
        hoje=HOJE,
    )


def _executar(
    nome: str, argumentos: dict[str, Any], resposta: Any = None
) -> tuple[Any, ClienteFalso]:
    cliente = ClienteFalso(resposta if resposta is not None else {})
    resultado = asyncio.run(executar_ferramenta(cliente, _contexto(), nome, argumentos))
    return resultado, cliente


# ---------------------------------------------------------------- catálogo

PERMISSOES_ESPERADAS = {
    "localizar_devedor": "devedor.ler",
    "consultar_saldo_devedor": "motor.saldo.ler",
    "consultar_resumo_carteira": "relatorios.operacionais.ler",
    "consultar_acertos": "relatorios.operacionais.ler",
    "consultar_pagamentos_periodo": "relatorios.operacionais.ler",
    "consultar_fluxo_realizado": "relatorios.operacionais.ler",
}


def test_catalogo_tem_seis_leituras_com_permissoes_minimas() -> None:
    assert CATALOGO_VERSAO == "consulta_operadora_v1"
    assert set(CATALOGO) == set(PERMISSOES_ESPERADAS)
    for nome, permissao in PERMISSOES_ESPERADAS.items():
        ferramenta = CATALOGO[nome]
        assert ferramenta.permissao == permissao
        assert ferramenta.metodo_http == "GET"
        with pytest.raises(dataclasses.FrozenInstanceError):
            ferramenta.nome = "outra"  # type: ignore[misc]


# ------------------------------------------------------------- validação


def test_ferramenta_fantasma_recusada_sem_rede() -> None:
    cliente = ClienteFalso({})
    with pytest.raises(FerramentaDesconhecidaError):
        asyncio.run(executar_ferramenta(cliente, _contexto(), "executar_sql", {}))
    with pytest.raises(FerramentaDesconhecidaError):
        asyncio.run(executar_ferramenta(cliente, _contexto(), "CONSULTAR_SALDO_DEVEDOR", {}))
    assert cliente.chamadas == []


@pytest.mark.parametrize(
    "nome,argumentos",
    [
        ("localizar_devedor", {"nome": "ana", "documento": "123"}),
        ("localizar_devedor", {}),
        ("localizar_devedor", {"nome": ""}),
        ("localizar_devedor", {"nome": "x" * 201}),
        ("localizar_devedor", {"nome": 123}),
        ("consultar_resumo_carteira", {"data_referencia": "2026-09-14"}),
        ("consultar_saldo_devedor", {"devedor_ref": REF, "data_referencia": "2026-09-14"}),
        ("consultar_pagamentos_periodo", {"inicio": "2026-09-01"}),
        ("consultar_pagamentos_periodo", {"inicio": "2026-09-10", "fim": "2026-09-01"}),
        ("consultar_pagamentos_periodo", {"inicio": "2026-09-15", "fim": "2026-09-15"}),
        ("consultar_pagamentos_periodo", {"inicio": "2026-08-01", "fim": "2026-09-14"}),
        ("consultar_fluxo_realizado", {"inicio": "10/09/2026", "fim": "2026-09-14"}),
    ],
)
def test_argumentos_fora_do_schema_recusados(nome: str, argumentos: dict[str, Any]) -> None:
    cliente = ClienteFalso({})
    with pytest.raises(ArgumentoInvalidoError):
        asyncio.run(executar_ferramenta(cliente, _contexto(), nome, argumentos))
    assert cliente.chamadas == []


def test_janela_limite_31_dias_passa_32_recusa() -> None:
    ok, _ = _executar(
        "consultar_pagamentos_periodo",
        {"inicio": "2026-08-14", "fim": "2026-09-14"},
    )
    assert ok == {}
    cliente = ClienteFalso({})
    with pytest.raises(ArgumentoInvalidoError):
        asyncio.run(
            executar_ferramenta(
                cliente,
                _contexto(),
                "consultar_pagamentos_periodo",
                {"inicio": "2026-08-13", "fim": "2026-09-14"},
            )
        )
    assert cliente.chamadas == []


def test_id_cru_no_lugar_da_referencia_nao_resolve() -> None:
    cliente = ClienteFalso({})
    with pytest.raises(ArgumentoInvalidoError):
        asyncio.run(
            executar_ferramenta(
                cliente,
                _contexto(),
                "consultar_saldo_devedor",
                {"devedor_ref": DEVEDOR_ID},
            )
        )
    assert cliente.chamadas == []


# ------------------------------------------------------------- URLs fixas


def test_localizar_usa_rota_fixa_e_paginacao_da_aplicacao() -> None:
    _, cliente = _executar("localizar_devedor", {"nome": "ana"}, {"items": []})
    assert cliente.chamadas == [
        (f"/credit/carteiras/{CARTEIRA}/devedores", {"nome": "ana", "page": 1, "size": 20})
    ]


def test_saldo_resolve_ref_e_carimba_data_do_servidor() -> None:
    _, cliente = _executar("consultar_saldo_devedor", {"devedor_ref": REF}, {})
    assert cliente.chamadas == [
        (f"/credit/devedores/{DEVEDOR_ID}/saldo", {"data_referencia": "2026-09-14"})
    ]


def test_resumo_e_acertos_usam_hoje_do_servidor() -> None:
    for nome in ("consultar_resumo_carteira", "consultar_acertos"):
        _, cliente = _executar(nome, {}, {})
        caminho, params = cliente.chamadas[0]
        assert CARTEIRA in caminho
        assert params == {"data_referencia": "2026-09-14"}


def test_relatorios_de_periodo_repassam_janela_validada() -> None:
    _, cliente = _executar(
        "consultar_fluxo_realizado", {"inicio": "2026-09-01", "fim": "2026-09-14"}, {}
    )
    assert cliente.chamadas[0][1] == {"inicio": "2026-09-01", "fim": "2026-09-14"}


def test_texto_livre_com_injecao_vira_parametro_opaco() -> None:
    _, cliente = _executar("localizar_devedor", {"nome": "../../admin'; DROP TABLE x; --"}, {})
    caminho, params = cliente.chamadas[0]
    assert ".." not in caminho
    assert params["nome"] == "../../admin'; DROP TABLE x; --"


# ---------------------------------------------------------------- cliente


def _cliente_http(status: int, corpo: Any = None) -> ClienteApi:
    def _handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer segredo"
        if corpo is None:
            return httpx.Response(status, json={"ok": True})
        return httpx.Response(status, json=corpo)

    return ClienteApi(
        "https://api.exemplo",
        lambda: "segredo",
        transporte=httpx.MockTransport(_handler),
    )


def test_cliente_mapeia_autorizacao_e_ausencia() -> None:
    async def _cenario() -> None:
        assert await _cliente_http(200).get("/x") == {"ok": True}
        with pytest.raises(ApiAutorizacaoError):
            await _cliente_http(401).get("/x")
        with pytest.raises(ApiAutorizacaoError):
            await _cliente_http(403).get("/x")
        with pytest.raises(ApiAusenciaError):
            await _cliente_http(404).get("/x")
        with pytest.raises(ApiError):
            await _cliente_http(500).get("/x")
        with pytest.raises(ApiError):
            await _cliente_http(200, ["lista"]).get("/x")
        with pytest.raises(ApiError):
            await _cliente_http(200).get("relativo")

    asyncio.run(_cenario())


# ---------------------------------------------------------- apresentadores


def test_mascaramento_nome_e_documento() -> None:
    assert mascarar_nome("João da Silva") == "João D. S."
    assert mascarar_nome("Ana") == "Ana"
    assert mascarar_documento("52998224725") == "***25"
    assert mascarar_documento("") == "***"


def test_formatar_valor_preserva_exatidao() -> None:
    assert formatar_valor(Decimal("1234.5")) == "1.234,50"
    assert formatar_valor(Decimal("0")) == "0,00"
    assert formatar_valor(Decimal("10.125")) == "10.125"


def test_localizar_um_resultado_direto_sem_escolha() -> None:
    dto = {
        "items": [
            {
                "id": DEVEDOR_ID,
                "nome": "João da Silva",
                "documento": "52998224725",
                "contatos": [{"tipo": "telefone", "valor": "(11) 99999-9999"}],
                "estado": "ativo",
            }
        ],
        "total": 1,
    }
    texto = renderizar("localizar_devedor", dto, {DEVEDOR_ID: REF})
    assert "João D. S." in texto and "Silva" not in texto
    assert "52998224725" not in texto and "***25" in texto
    assert "(11)" not in texto and "Escolha" not in texto
    assert REF in texto


def test_localizar_varios_exige_escolha_e_avisa_pagina() -> None:
    dto = {
        "items": [
            {"id": "a", "nome": "Ana Souza", "documento": "11111111111", "estado": "ativo"},
            {"id": "b", "nome": "Ana Santos", "documento": "22222222222", "estado": "ativo"},
        ],
        "total": 5,
    }
    texto = renderizar("localizar_devedor", dto, {"a": "r1", "b": "r2"})
    assert "Escolha" in texto and "refine a busca" in texto
    assert "r1" in texto and "r2" in texto


def test_localizar_vazio_e_ausencia_sao_textos_distintos() -> None:
    assert renderizar("localizar_devedor", {"items": [], "total": 0}) == (
        "Nenhum cadastro localizado com esse nome."
    )
    assert mensagem_ausencia("localizar_devedor") != "Nenhum cadastro localizado com esse nome."


def test_saldo_rotulos_oficiais_e_zero_nao_e_ausencia() -> None:
    dto = {
        "devedor_id": DEVEDOR_ID,
        "data_referencia": "2026-09-14",
        "principal": "1000.00",
        "juros": "50.50",
        "encargos": "0.00",
        "total": "1050.50",
        "emprestimos_considerados": 1,
        "itens": [
            {
                "emprestimo_id": "9Z9Z-ID-EMPRESTIMO",
                "principal": "1000.00",
                "juros": "50.50",
                "encargos": "0.00",
                "total": "1050.50",
            }
        ],
    }
    texto = renderizar("consultar_saldo_devedor", dto)
    assert "principal R$ 1.000,00" in texto
    assert "total R$ 1.050,50" in texto
    assert "9Z9Z" not in texto
    zerado = renderizar(
        "consultar_saldo_devedor",
        {
            "data_referencia": "2026-09-14",
            "principal": "0.00",
            "juros": "0.00",
            "encargos": "0.00",
            "total": "0.00",
            "itens": [],
        },
    )
    assert "Sem empréstimos ativos" in zerado
    assert zerado != mensagem_ausencia("consultar_saldo_devedor")


def test_resumo_descarta_projecao_e_nao_inventa_nomes() -> None:
    dto = {
        "data_referencia": "2026-09-14",
        "operacoes_ativas": 3,
        "operacoes_quitadas": 1,
        "acertos_pendentes": 2,
        "principal_a_receber": "5000.00",
        "projecao_juros": "999999.99",
        "total_realizado": "1200.00",
    }
    texto = renderizar("consultar_resumo_carteira", dto)
    assert "999999" not in texto
    assert "principal a receber: R$ 5.000,00" in texto
    assert "total realizado: R$ 1.200,00" in texto
    for proibida in ("lucro", "projec", "previs", "estim"):
        assert proibida not in texto.lower()


def test_acertos_sem_ids_e_sem_totais() -> None:
    dto = {
        "data_referencia": "2026-09-14",
        "total": 1,
        "itens": [
            {
                "emprestimo_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "devedor_id": DEVEDOR_ID,
                "dia_de_acerto": 10,
                "acerto_em": "2026-09-10",
                "dias_sem_pagamento": 4,
                "principal_original": "500.00",
                "situacao": "em_atraso",
            }
        ],
    }
    texto = renderizar("consultar_acertos", dto)
    assert "aaaaaaaa" not in texto and DEVEDOR_ID not in texto
    assert "2026-09-10" in texto and "4 dia(s)" in texto
    assert renderizar("consultar_acertos", {"itens": [], "total": 0}) == (
        "Nenhum acerto pendente na data de referência."
    )


def test_pagamentos_e_fluxo_sem_campos_inventados() -> None:
    texto = renderizar(
        "consultar_pagamentos_periodo",
        {
            "inicio": "2026-09-01",
            "fim": "2026-09-14",
            "pagamentos": [
                {
                    "pagamento_id": "p1",
                    "recebido_em": "2026-09-10",
                    "valor_recebido": "200.00",
                    "estado": "alocado",
                }
            ],
            "operacoes_quitadas": ["q1"],
            "total_realizado": "200.00",
            "lucro": "1.00",
        },
    )
    assert "p1" not in texto and "q1" not in texto and "lucro" not in texto.lower()
    assert "total realizado: R$ 200,00" in texto
    fluxo = renderizar(
        "consultar_fluxo_realizado",
        {
            "inicio": "2026-09-01",
            "fim": "2026-09-14",
            "itens": [
                {"data": "2026-09-10", "realizado": "200.00", "acertos": 1, "pagamento_ids": ["p1"]}
            ],
        },
    )
    assert "total" not in fluxo.lower() and "p1" not in fluxo
    assert "R$ 200,00" in fluxo


def test_renderizar_recusa_ferramenta_fantasma_e_dto_quebrado() -> None:
    with pytest.raises(ValueError):
        renderizar("prever_lucro", {})
    with pytest.raises(ValueError):
        renderizar("consultar_saldo_devedor", {"total": "x"})
