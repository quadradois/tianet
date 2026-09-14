"""Dispatcher do catálogo (IMP-356-D): nome, argumentos, URL e permissão.

Tudo que o modelo sugere passa por aqui antes de qualquer HTTP:
- nome fora do catálogo, argumento extra ou URL livre: recusado sem rede;
- datas validadas contra o relógio do servidor (período inclusivo,
  `fim <= hoje`, janela máxima) — o modelo nunca define "hoje";
- `devedor_id` e `carteira_id` vêm do contexto/resolvedor do servidor,
  nunca dos argumentos;
- autorização final é da API (bearer copilot); 401/403 encerram sem loop.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from emprestimo.agent.api_client import ApiError, ProtocoloClienteApi
from emprestimo.agent.catalogo import (
    CATALOGO,
    JANELA_MAXIMA_RELATORIO_DIAS,
    Ferramenta,
)


class FerramentaDesconhecidaError(ApiError):
    """Nome fora do catálogo — nem chega à rede."""


class ArgumentoInvalidoError(ApiError):
    """Argumento extra, ausente ou fora do schema — recusado localmente."""


@dataclass(frozen=True)
class ContextoFerramentas:
    """Escopo resolvido pelo servidor para montar URLs fixas."""

    carteira_id: str
    resolvedor_devedor: Callable[[str], str | None]
    hoje: date


def _validar_texto(valor: object, minimo: int, maximo: int, campo: str) -> str:
    if not isinstance(valor, str):
        raise ArgumentoInvalidoError(f"{campo} deve ser texto")
    texto = valor.strip()
    if not (minimo <= len(texto) <= maximo):
        raise ArgumentoInvalidoError(f"{campo} fora do tamanho permitido")
    return texto


def _validar_data(valor: object, campo: str) -> date:
    if not isinstance(valor, str):
        raise ArgumentoInvalidoError(f"{campo} deve ser data ISO")
    try:
        ano, mes, dia = (int(parte) for parte in valor.split("-"))
        return date(ano, mes, dia)
    except (ValueError, AttributeError) as exc:
        raise ArgumentoInvalidoError(f"{campo} deve ser data ISO") from exc


def validar_argumentos(
    ferramenta: Ferramenta, argumentos: Mapping[str, Any], hoje: date
) -> dict[str, str]:
    """Schema fechado: extras recusados, datas validadas contra `hoje`."""
    if set(argumentos) != set(ferramenta.argumentos):
        raise ArgumentoInvalidoError("argumentos divergem do schema fechado")
    saidas: dict[str, str] = {}
    for nome, restricao in ferramenta.argumentos.items():
        valor = argumentos[nome]
        if restricao.tipo == "texto":
            saidas[nome] = _validar_texto(valor, restricao.minimo, restricao.maximo, nome)
        elif restricao.tipo == "data":
            data = _validar_data(valor, nome)
            if data > hoje:
                raise ArgumentoInvalidoError(f"{nome} nao pode ser futura")
            saidas[nome] = data.isoformat()
        else:
            raise ArgumentoInvalidoError(f"tipo desconhecido em {nome}")
    if ferramenta.nome in ("consultar_pagamentos_periodo", "consultar_fluxo_realizado"):
        inicio = _validar_data(argumentos["inicio"], "inicio")
        fim = _validar_data(argumentos["fim"], "fim")
        if inicio > fim:
            raise ArgumentoInvalidoError("inicio posterior ao fim")
        if (fim - inicio).days > JANELA_MAXIMA_RELATORIO_DIAS:
            raise ArgumentoInvalidoError("periodo acima da janela maxima")
    return saidas


async def executar_ferramenta(
    cliente: ProtocoloClienteApi,
    contexto: ContextoFerramentas,
    nome: str,
    argumentos: Mapping[str, Any],
) -> dict[str, Any]:
    """Executa uma chamada validada; nada além do catálogo alcança a rede."""
    ferramenta = CATALOGO.get(nome)
    if ferramenta is None:
        raise FerramentaDesconhecidaError(f"ferramenta fora do catalogo: {nome}")
    args = validar_argumentos(ferramenta, argumentos, contexto.hoje)
    caminho = ferramenta.rota
    params: dict[str, str | int] = {}
    if "{carteira_id}" in caminho:
        caminho = caminho.replace("{carteira_id}", contexto.carteira_id)
    if "{devedor_id}" in caminho:
        devedor_id = contexto.resolvedor_devedor(args["devedor_ref"])
        if devedor_id is None:
            raise ArgumentoInvalidoError("referencia de devedor invalida ou expirada")
        caminho = caminho.replace("{devedor_id}", devedor_id)
    if ferramenta.nome == "localizar_devedor":
        params = {"nome": args["nome"], "page": 1, "size": 20}
    elif ferramenta.nome in (
        "consultar_saldo_devedor",
        "consultar_resumo_carteira",
        "consultar_acertos",
    ):
        params = {"data_referencia": contexto.hoje.isoformat()}
    elif ferramenta.nome in ("consultar_pagamentos_periodo", "consultar_fluxo_realizado"):
        params = {"inicio": args["inicio"], "fim": args["fim"]}
    return await cliente.get(caminho, params)
