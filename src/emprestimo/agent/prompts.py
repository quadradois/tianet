"""Instruções versionadas do copiloto (IMP-356-D lote 2, slice 2).

Texto fixo e revisado, sem nada inventado além das invariantes aprovadas:
o modelo interpreta intenção e pede ferramenta da allowlist; número de
dinheiro nunca sai em prosa livre; escopo vem do servidor; falha degrada
para resposta fixa. Versão congelada — qualquer mudança exige revisão.
"""

from __future__ import annotations

from datetime import date

from emprestimo.agent.catalogo import CATALOGO_VERSAO

INSTRUCOES_VERSAO = "instrucoes_operadora_v1"

RESPOSTA_FIXA_PRE_CADASTRO = (
    "Olá! Sou a assistente da TiaNet. Para consultar valores, "
    "fale com a operadora da sua carteira."
)

_SISTEMA_OPERADORA = """Você é a assistente operacional da TiaNet. \
Catálogo: {catalogo}. Data de hoje: {hoje}. \
Regras invioláveis: use apenas ferramentas do catálogo; nunca invente nome \
de ferramenta, argumento, valor, data ou total; nunca some, arredonde ou \
projete valores; apresente números somente como recebidos do sistema; \
não escolha carteira, devedor, permissão ou endereço; se algo falhar ou \
faltar, responda apenas que a informação está indisponível no momento."""


def montar_sistema_operadora(hoje: date) -> str:
    """System prompt da Operadora: invariantes + versão + hoje do servidor."""
    return _SISTEMA_OPERADORA.format(catalogo=CATALOGO_VERSAO, hoje=hoje.isoformat())


def montar_sistema(classe: str, hoje: date) -> str:
    """System por classe: Operadora interpreta; resto recebe texto fixo."""
    if classe == "operadora":
        return montar_sistema_operadora(hoje)
    return RESPOSTA_FIXA_PRE_CADASTRO


__all__ = [
    "INSTRUCOES_VERSAO",
    "RESPOSTA_FIXA_PRE_CADASTRO",
    "montar_sistema",
    "montar_sistema_operadora",
]
