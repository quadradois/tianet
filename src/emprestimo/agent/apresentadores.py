"""Apresentadores determinísticos (IMP-356-D): DTO da API vira texto fixo.

Regras invioláveis, testadas uma a uma:
- só campos allowlist entram no texto; IDs nunca, referências opacas só em
  localizar; nada de URL, SQL, stack ou cabeçalho;
- nomes oficiais do Motor: principal, juros, encargos, total, principal a
  receber, total realizado. "Lucro", "projeção" e afins nunca aparecem;
- decimais: formatação para exibição preserva o valor exato; casas além de
  duas são mantidas como vieram, nunca arredondadas nem cortadas;
- zero (HTTP 200 com total 0) não é ausência (HTTP 404): textos distintos;
- ambiguidade nunca se resolve sozinha: vários candidatos exigem escolha.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

PALAVRAS_PROIBIDAS = ("lucro", "projec", "previs", "estim", "sofrer", "cobran")


def mascarar_nome(nome: str) -> str:
    """Primeiro nome por extenso + iniciais; LGPD por padrão."""
    partes = [p for p in nome.split() if p]
    if not partes:
        return "não identificado"
    return " ".join([partes[0], *(f"{p[0].upper()}." for p in partes[1:])])


def formatar_valor(valor: object) -> str:
    """Decimal exato para exibição pt-BR; nunca recalcula nem arredonda."""
    try:
        numero = valor if isinstance(valor, Decimal) else Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("valor monetario invalido") from exc
    if not numero.is_finite():
        raise ValueError("valor monetario invalido")
    expoente = numero.as_tuple().exponent
    if not isinstance(expoente, int):
        raise ValueError("valor monetario invalido")
    if expoente < -2:
        return format(numero, "f")
    texto = f"{numero:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def mascarar_documento(valor: object) -> str:
    """Só os 2 últimos dígitos; o resto nunca chega ao modelo (LGPD)."""
    digitos = "".join(c for c in str(valor) if c.isdigit())
    if len(digitos) < 2:
        return "***"
    return f"***{digitos[-2:]}"


def _rotulo(valor: object) -> str:
    return f"R$ {formatar_valor(valor)}"
    return f"R$ {formatar_valor(valor)}"


def _verificar_proibidas(texto: str) -> str:
    baixo = texto.lower()
    for palavra in PALAVRAS_PROIBIDAS:
        if palavra in baixo:
            raise ValueError("texto com termo proibido")
    return texto


def _itens(dto: Mapping[str, Any], chave: str) -> list[Mapping[str, Any]]:
    itens = dto.get(chave, [])
    if not isinstance(itens, list):
        raise ValueError("lista invalida na resposta")
    return [i for i in itens if isinstance(i, Mapping)]


def apresentar_localizar(dto: Mapping[str, Any], refs: Mapping[str, str] | None = None) -> str:
    # Contrato real da listagem: `items[]` com `id/nome/documento/estado`
    # (documento e contatos vêm crus do servidor — o mascaramento acontece
    # AQUI, ponto único entre API e modelo; nada cru vaza por construção,
    # pois só estas quatro chaves são lidas).
    itens = _itens(dto, "items")
    total = dto.get("total", len(itens))
    if not itens:
        return "Nenhum cadastro localizado com esse nome."
    refs = refs or {}
    linhas = []
    for item in itens:
        item_id = str(item.get("id", ""))
        ref = refs.get(item_id, "")
        nome = mascarar_nome(str(item.get("nome", "")))
        doc = mascarar_documento(item.get("documento", ""))
        estado = str(item.get("estado", ""))
        sufixo = f" [ref {ref}]" if ref else ""
        linhas.append(f"- {nome} — doc. {doc} — {estado}{sufixo}")
    if len(itens) == 1 and (not isinstance(total, int) or total <= 1):
        return _verificar_proibidas("Cadastro localizado:\n" + "\n".join(linhas))
    cabeca = f"{total} cadastros localizados. Escolha uma opção para continuar:"
    if isinstance(total, int) and total > len(itens):
        cabeca += " (há mais resultados — refine a busca se não vir o desejado)"
    return _verificar_proibidas(cabeca + "\n" + "\n".join(linhas))


def apresentar_saldo(dto: Mapping[str, Any]) -> str:
    itens = _itens(dto, "itens")
    linhas = [
        f"Posição em {dto.get('data_referencia', '')}:",
        f"principal {_rotulo(dto['principal'])}",
        f"juros {_rotulo(dto['juros'])}",
        f"encargos {_rotulo(dto['encargos'])}",
        f"total {_rotulo(dto['total'])}",
    ]
    if itens:
        linhas.append(f"{len(itens)} empréstimo(s) compõem o total.")
    else:
        linhas.append("Sem empréstimos ativos — total zerado.")
    return _verificar_proibidas("\n".join(linhas))


def apresentar_resumo(dto: Mapping[str, Any]) -> str:
    # `projecao_juros` existe no contrato mas nunca entra no texto: o modelo
    # jamais apresenta valor futuro como fato. Queda por construção.
    return _verificar_proibidas(
        "\n".join(
            [
                f"Resumo da carteira em {dto.get('data_referencia', '')}:",
                f"operações ativas: {dto.get('operacoes_ativas', 0)}",
                f"operações quitadas: {dto.get('operacoes_quitadas', 0)}",
                f"acertos pendentes: {dto.get('acertos_pendentes', 0)}",
                f"principal a receber: {_rotulo(dto['principal_a_receber'])}",
                f"total realizado: {_rotulo(dto['total_realizado'])}",
            ]
        )
    )


def apresentar_acertos(dto: Mapping[str, Any]) -> str:
    itens = _itens(dto, "itens")
    if not itens:
        return "Nenhum acerto pendente na data de referência."
    linhas = [f"{len(itens)} acerto(s) pendente(s):"]
    for item in itens:
        linhas.append(
            f"- acerto em {item.get('acerto_em', '')}: "
            f"{item.get('dias_sem_pagamento', 0)} dia(s) sem pagamento "
            f"— situação {item.get('situacao', '')}"
        )
    return _verificar_proibidas("\n".join(linhas))


def apresentar_pagamentos(dto: Mapping[str, Any]) -> str:
    pagamentos = _itens(dto, "pagamentos")
    quitadas = dto.get("operacoes_quitadas", [])
    linhas = [f"Pagamentos de {dto.get('inicio', '')} a {dto.get('fim', '')}:"]
    if not pagamentos:
        linhas.append("Nenhum pagamento no período.")
    for item in pagamentos:
        linhas.append(
            f"- {item.get('recebido_em', '')}: "
            f"{_rotulo(item.get('valor_recebido', 0))} "
            f"— {item.get('estado', '')}"
        )
    linhas.append(f"total realizado: {_rotulo(dto.get('total_realizado', 0))}")
    if isinstance(quitadas, list) and quitadas:
        linhas.append(f"operações quitadas no período: {len(quitadas)}")
    return _verificar_proibidas("\n".join(linhas))


def apresentar_fluxo(dto: Mapping[str, Any]) -> str:
    itens = _itens(dto, "itens")
    if not itens:
        return "Sem recebimentos no período."
    linhas = [f"Recebimentos de {dto.get('inicio', '')} a {dto.get('fim', '')}:"]
    for item in itens:
        linhas.append(
            f"- {item.get('data', '')}: {_rotulo(item.get('realizado', 0))} "
            f"({item.get('acertos', 0)} acerto(s))"
        )
    return _verificar_proibidas("\n".join(linhas))


AUSENCIAS_NEUTRAS = {
    "localizar_devedor": "Nenhum cadastro localizado.",
    "consultar_saldo_devedor": "Sem posição para essa referência.",
    "consultar_resumo_carteira": "Resumo indisponível no momento.",
    "consultar_acertos": "Acertos indisponíveis no momento.",
    "consultar_pagamentos_periodo": "Pagamentos indisponíveis no momento.",
    "consultar_fluxo_realizado": "Recebimentos indisponíveis no momento.",
}


def mensagem_ausencia(nome_ferramenta: str) -> str:
    """Texto neutro para 404: ausência, nunca zero, nunca detalhe interno."""
    return AUSENCIAS_NEUTRAS.get(nome_ferramenta, "Informação indisponível.")


def renderizar(
    nome_ferramenta: str,
    dto: Mapping[str, Any],
    refs: Mapping[str, str] | None = None,
) -> str:
    roteador = {
        "localizar_devedor": lambda d: apresentar_localizar(d, refs),
        "consultar_saldo_devedor": apresentar_saldo,
        "consultar_resumo_carteira": apresentar_resumo,
        "consultar_acertos": apresentar_acertos,
        "consultar_pagamentos_periodo": apresentar_pagamentos,
        "consultar_fluxo_realizado": apresentar_fluxo,
    }
    apresentar = roteador.get(nome_ferramenta)
    if apresentar is None:
        raise ValueError("ferramenta fora do catalogo")
    try:
        return apresentar(dto)
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("resposta fora do contrato") from exc
