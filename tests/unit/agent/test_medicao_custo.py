"""Medição de consumo LLM (IMP-356-D lote 2, slice 3).

Prova observar-sem-bloquear da DR-005 §3: agregação de contagens, custo
estimado exato em Decimal, alerta uma vez por patamar — e o retrato nunca
carrega prompt, resposta, chave ou qualquer conteúdo.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from emprestimo.agent.custo import TABELA_PRECOS_VERSAO, estimar_custo_usd
from emprestimo.agent.llm_client import Uso
from emprestimo.agent.metricas import METRICAS_LLM, MetricasLlm


def test_tabela_precos_versionada_e_matematica_exata() -> None:
    assert TABELA_PRECOS_VERSAO == "precos_openai_2026_09"
    assert estimar_custo_usd("gpt-4o-mini", 1000, 500) == Decimal("0.00045")
    assert estimar_custo_usd("modelo-desconhecido", 1000, 500) is None
    with pytest.raises(ValueError):
        estimar_custo_usd("gpt-4o-mini", -1, 0)


def test_registro_agrega_contagens_custo_e_falhas() -> None:
    metricas = MetricasLlm()
    metricas.registrar_chamada(Uso(1000, 500, 1500), Decimal("0.00045"))
    metricas.registrar_chamada(Uso(2000, 0, 2000), None)
    metricas.registrar_chamada(None, None, falha="timeout")
    assert metricas.chamadas == 3
    assert metricas.chamadas_sem_medicao == 1
    assert metricas.tokens_entrada == 3000
    assert metricas.tokens_saida == 500
    assert metricas.custo_estimado_usd == Decimal("0.00045")
    assert metricas.falhas_por_motivo == {"timeout": 1}


def test_alerta_dispara_uma_vez_por_patamar() -> None:
    metricas = MetricasLlm()
    assert metricas.deve_alertar(Decimal("1.00")) is False
    metricas.registrar_chamada(Uso(10_000_000, 0, 10_000_000), Decimal("1.50"))
    assert metricas.deve_alertar(Decimal("1.00")) is True
    metricas.marcar_alerta(Decimal("1.00"))
    assert metricas.deve_alertar(Decimal("1.00")) is False
    assert metricas.deve_alertar(Decimal("2.00")) is False
    assert metricas.deve_alertar(Decimal("1.50")) is True
    metricas.marcar_alerta(Decimal("1.50"))
    assert metricas.deve_alertar(Decimal("1.50")) is False
    metricas.registrar_chamada(Uso(10_000_000, 0, 10_000_000), Decimal("1.50"))
    assert metricas.deve_alertar(Decimal("2.00")) is True


def test_retrato_so_contagens_sem_conteudo() -> None:
    metricas = MetricasLlm()
    metricas.registrar_chamada(Uso(10, 5, 15), Decimal("0.00001"))
    retrato = metricas.retrato()
    assert set(retrato) == {
        "chamadas",
        "chamadas_sem_medicao",
        "tokens_entrada",
        "tokens_saida",
        "custo_estimado_usd",
        "falhas_por_motivo",
        "ultimo_alerta_usd",
    }
    assert retrato["custo_estimado_usd"] == "0.00001"
    import json

    json.dumps(retrato)


def test_modulo_global_existe_e_inicia_zerado() -> None:
    assert METRICAS_LLM.retrato()["chamadas"] == 0
