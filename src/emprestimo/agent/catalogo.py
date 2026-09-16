"""Catálogo nominal de ferramentas — `consulta_operadora_v1` (IMP-356-D).

Registro fechado: seis leituras de negócio, três permissões mínimas, URLs
internas fixas. Nada aqui é montado a partir de entrada do modelo — nome,
rota, permissão e campos de saída são literais revisados. Qualquer chamada
fora desta lista é recusada antes de qualquer HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RestricaoArgumento:
    tipo: str  # "texto" | "data" | "vazio"
    obrigatorio: bool = True
    minimo: int = 0
    maximo: int = 0


@dataclass(frozen=True)
class Ferramenta:
    nome: str
    metodo_http: str
    rota: str
    permissao: str
    descricao: str = ""
    argumentos: dict[str, RestricaoArgumento] = field(default_factory=dict)
    apresentador: str = ""


CATALOGO_VERSAO = "consulta_operadora_v1"

CATALOGO: dict[str, Ferramenta] = {
    "localizar_devedor": Ferramenta(
        nome="localizar_devedor",
        metodo_http="GET",
        rota="/credit/carteiras/{carteira_id}/devedores",
        permissao="devedor.ler",
        descricao=(
            "Localiza cadastros de devedores pelo nome. "
            "Nunca use documento, ID ou endereço como argumento."
        ),
        argumentos={"nome": RestricaoArgumento("texto", True, 1, 200)},
        apresentador="localizar_devedor",
    ),
    "consultar_saldo_devedor": Ferramenta(
        nome="consultar_saldo_devedor",
        metodo_http="GET",
        rota="/credit/devedores/{devedor_id}/saldo",
        permissao="motor.saldo.ler",
        descricao=(
            "Consulta a posição de dívida de um devedor já localizado. "
            "Use apenas a referência opaca devolvida pela localização, "
            "nunca um ID."
        ),
        argumentos={"devedor_ref": RestricaoArgumento("texto", True, 1, 64)},
        apresentador="consultar_saldo_devedor",
    ),
    "consultar_resumo_carteira": Ferramenta(
        nome="consultar_resumo_carteira",
        metodo_http="GET",
        rota="/credit/carteiras/{carteira_id}/relatorios/resumo",
        permissao="relatorios.operacionais.ler",
        descricao=(
            "Resumo operacional da carteira na data de hoje: panorama com "
            "contadores, sem listar vencimentos."
        ),
        apresentador="consultar_resumo_carteira",
    ),
    "consultar_acertos": Ferramenta(
        nome="consultar_acertos",
        metodo_http="GET",
        rota="/credit/carteiras/{carteira_id}/relatorios/vencimentos",
        permissao="relatorios.operacionais.ler",
        descricao=(
            "Acertos pendentes na data de hoje: lista quem deve e quando. "
            "Use para perguntas sobre atraso, vencimento ou situação de cobrança."
        ),
        apresentador="consultar_acertos",
    ),
    "consultar_pagamentos_periodo": Ferramenta(
        nome="consultar_pagamentos_periodo",
        metodo_http="GET",
        rota="/credit/carteiras/{carteira_id}/relatorios/pagamentos",
        permissao="relatorios.operacionais.ler",
        descricao=(
            "Pagamentos recebidos num período de até 31 dias, "
            "nunca acima de hoje. Lista item a item, com encerramentos. "
            "Use para detalhe, lista ou item a item; nunca para totais "
            "por dia. Datas no formato AAAA-MM-DD."
        ),
        argumentos={
            "inicio": RestricaoArgumento("data"),
            "fim": RestricaoArgumento("data"),
        },
        apresentador="consultar_pagamentos_periodo",
    ),
    "consultar_fluxo_realizado": Ferramenta(
        nome="consultar_fluxo_realizado",
        metodo_http="GET",
        rota="/credit/carteiras/{carteira_id}/relatorios/fluxo",
        permissao="relatorios.operacionais.ler",
        descricao=(
            "Recebimentos por dia num período de até 31 dias, "
            "nunca acima de hoje. Total agregado por dia, sem detalhe. "
            "Use para quanto entrou, totais ou por dia; nunca para "
            "lista item a item. Datas no formato AAAA-MM-DD."
        ),
        argumentos={
            "inicio": RestricaoArgumento("data"),
            "fim": RestricaoArgumento("data"),
        },
        apresentador="consultar_fluxo_realizado",
    ),
}

JANELA_MAXIMA_RELATORIO_DIAS = 31
