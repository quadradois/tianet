"""Chave de telefone (IMP-381): o mesmo celular escrito de jeitos diferentes.

O devedor foi cadastrado como "(11) 98888-7766"; o WhatsApp manda
"5511988887766@s.whatsapp.net" — ou, em contas antigas, sem o nono digito
("551188887766"). Sem uma chave comum, o agente trataria o proprio devedor
como desconhecido.
"""

from __future__ import annotations

import pytest

from emprestimo.agent.conversa import chave_telefone, normalizar_remetente

CANONICA = "11988887766"


@pytest.mark.parametrize(
    "forma",
    [
        "(11) 98888-7766",  # como o cadastro guarda
        "11988887766",
        "+55 11 98888-7766",
        "5511988887766",  # JID atual do WhatsApp
        "551188887766",  # JID antigo, sem o nono digito
        "1188887766",  # cadastro antigo, sem o nono digito
        "011 98888-7766",  # com prefixo de operadora
    ],
)
def test_formas_do_mesmo_celular_convergem(forma: str) -> None:
    assert chave_telefone(forma) == CANONICA


def test_jid_do_whatsapp_passa_pela_normalizacao_do_remetente() -> None:
    assert chave_telefone(normalizar_remetente("5511988887766@s.whatsapp.net")) == CANONICA


def test_fixo_nao_ganha_nono_digito() -> None:
    """Fixo comeca com 2-5; inserir o 9 criaria um numero que nao existe."""
    assert chave_telefone("(11) 3333-4444") == "1133334444"
    assert chave_telefone("551133334444") == "1133334444"


def test_celulares_diferentes_nao_colidem() -> None:
    assert chave_telefone("(11) 98888-7766") != chave_telefone("(21) 98888-7766")
    assert chave_telefone("(11) 98888-7766") != chave_telefone("(11) 98888-7767")


def test_numero_estrangeiro_so_casa_consigo_mesmo() -> None:
    assert chave_telefone("+1 415 555 0100") == "14155550100"
    assert chave_telefone("14155550100") != CANONICA


@pytest.mark.parametrize("vazio", ["", "   ", "sem-digitos"])
def test_sem_digitos_nao_vira_chave(vazio: str) -> None:
    assert chave_telefone(vazio) == ""


# --- Classificacao credora -> devedor -> pre-cadastro --------------------------

from emprestimo.agent.conversa import ClasseContexto, classificar_entrada  # noqa: E402

CREDORA = "5562999998888"
DEVEDOR_JID = "5511988887766@s.whatsapp.net"


def _classe(
    sender: str, *, credora: str | None = CREDORA, devedores: frozenset[str] = frozenset({CANONICA})
) -> ClasseContexto:
    return classificar_entrada(
        provider_input_id="id-1",
        sender=sender,
        texto="oi",
        numero_credora=credora,
        telefones_devedores=devedores,
    ).classe


def test_credora_pelo_numero_de_avisos() -> None:
    assert _classe("5562999998888@s.whatsapp.net") is ClasseContexto.OPERADORA


def test_credora_sem_nono_digito_ainda_e_credora() -> None:
    assert _classe("556299998888@s.whatsapp.net") is ClasseContexto.OPERADORA


def test_devedor_cadastrado_com_mascara() -> None:
    assert _classe(DEVEDOR_JID) is ClasseContexto.DEVEDOR


def test_desconhecido_vai_para_pre_cadastro() -> None:
    assert _classe("5531977776666@s.whatsapp.net") is ClasseContexto.PRE_CADASTRO


def test_credora_vence_devedor_com_o_mesmo_numero() -> None:
    assert (
        _classe(DEVEDOR_JID, credora="(11) 98888-7766", devedores=frozenset({CANONICA}))
        is ClasseContexto.OPERADORA
    )


def test_sem_credor_whatsapp_ninguem_vira_operadora() -> None:
    """Sem numero configurado, a identidade da Credora nao existe — fail-closed."""
    assert _classe("5562999998888@s.whatsapp.net", credora=None) is ClasseContexto.PRE_CADASTRO


def test_lid_nunca_resolve_identidade() -> None:
    assert _classe("11988887766@lid") is ClasseContexto.PRE_CADASTRO
