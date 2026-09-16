"""Egress slice 1 — identidade e idempotência puras (IMP-356-E).

Vetores de chave (estabilidade + divergência), cross-tenant negativo,
normalização (grupo/LID/curto recusados) e payload canônico estável.
Sem rede, sem banco, sem segredo real.
"""

from __future__ import annotations

import uuid

import pytest

from emprestimo.agent.egress import (
    VERSAO_CHAVE_EGRESS,
    ConflitoEgressError,
    DestinoInvalidoError,
    EstadoEgress,
    IntencaoEgress,
    ResolvedorTokenEgress,
    TokenEgressError,
    chaves_conflitam,
    derivar_chave,
    normalizar_destino,
    payload_canonico,
    transicao_permitida,
)

TENANT = uuid.uuid4()
CARTEIRA = uuid.uuid4()
PRINCIPAL = uuid.uuid4()


def _intencao(**trocar: object) -> IntencaoEgress:
    base: dict[str, object] = {
        "tenant_id": TENANT,
        "carteira_id": CARTEIRA,
        "instancia_ref": "tianet_teste",
        "classe": "operadora",
        "principal_id": PRINCIPAL,
        "destinatario": "5511999999999",
        "provider_input_id": "pid-1",
        "indice": 0,
        "ferramenta": "consultar_acertos",
        "call_id": "call_1",
        "texto": "texto",
    }
    base.update(trocar)
    return IntencaoEgress(**base)  # type: ignore[arg-type]


def test_chave_estavel_e_sensivel_a_conteudo_e_vinculo() -> None:
    assert VERSAO_CHAVE_EGRESS == "egress/v1"
    assert derivar_chave(_intencao()) == derivar_chave(_intencao())
    assert derivar_chave(_intencao()) != derivar_chave(_intencao(texto="outro"))
    assert derivar_chave(_intencao()) != derivar_chave(_intencao(indice=1))
    assert derivar_chave(_intencao()) != derivar_chave(_intencao(destinatario="5511888888888"))
    assert derivar_chave(_intencao()) != derivar_chave(_intencao(tenant_id=uuid.uuid4()))
    chave = derivar_chave(_intencao())
    assert chave.startswith("egress/v1/") and "5511999999999" not in chave


def test_conflito_e_divergencia_terminal() -> None:
    payload = payload_canonico({"a": 1})
    assert chaves_conflitam("k", payload, payload) is False
    assert chaves_conflitam("k", payload, payload_canonico({"a": 2})) is True
    assert issubclass(ConflitoEgressError, Exception)


def test_payload_canonico_estavel_a_ordem() -> None:
    assert payload_canonico({"b": 1, "a": 2}) == payload_canonico({"a": 2, "b": 1})


@pytest.mark.parametrize(
    "destinatario",
    ["5511999999999", "+55 (11) 99999-9999", "55119888888888"],
)
def test_destinos_discaveis_passam(destinatario: str) -> None:
    assert normalizar_destino(destinatario).isdigit()


@pytest.mark.parametrize(
    "destinatario",
    ["123", "1234567890123456", "", "grupo@g.us", "abc@lid", "sem-numero"],
)
def test_destinos_nao_discaveis_recusam(destinatario: str) -> None:
    with pytest.raises(DestinoInvalidoError):
        normalizar_destino(destinatario)


def test_resolvedor_single_tenant() -> None:
    resolvedor = ResolvedorTokenEgress(
        TENANT,
        "tianet_teste",
        carregar=lambda t, i: b"cifrado" if (t, i) == (TENANT, "tianet_teste") else None,
        decifrar=lambda b: "token-secreto",
    )
    assert resolvedor.resolver(TENANT, "tianet_teste") == "token-secreto"
    with pytest.raises(TokenEgressError):
        resolvedor.resolver(uuid.uuid4(), "tianet_teste")
    with pytest.raises(TokenEgressError):
        resolvedor.resolver(TENANT, "outra-instancia")
    vazio = ResolvedorTokenEgress(TENANT, "x", carregar=lambda t, i: None, decifrar=lambda b: "")
    with pytest.raises(TokenEgressError):
        vazio.resolver(TENANT, "x")


def test_transicoes_terminais_nao_saem_do_lugar() -> None:
    assert transicao_permitida(EstadoEgress.PREPARADO, EstadoEgress.EM_ENVIO)
    assert transicao_permitida(EstadoEgress.EM_ENVIO, EstadoEgress.DESCONHECIDO)
    assert transicao_permitida(EstadoEgress.FALHA, EstadoEgress.EM_ENVIO)
    assert not transicao_permitida(EstadoEgress.ACEITO, EstadoEgress.EM_ENVIO)
    assert not transicao_permitida(EstadoEgress.DESCONHECIDO, EstadoEgress.EM_ENVIO)
    assert not transicao_permitida(EstadoEgress.PREPARADO, EstadoEgress.ACEITO)
