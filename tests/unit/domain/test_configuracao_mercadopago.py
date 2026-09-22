"""ConfiguracaoMercadoPago (IMP-388): a integracao e opcional e nasce desligada.

O provedor cobra por recebimento e a Credora ja tem o caminho sem taxa (ela
avisa o agente, que registra). Ligar e escolha economica dela — e o desligado
precisa ser um estado de primeira classe, nao um efeito colateral de
credencial ausente.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.configuracao_mercadopago import ConfiguracaoMercadoPago

AGORA = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
TOKEN = b"gAAAAA-token-cifrado"
SECRET = b"gAAAAA-secret-cifrado"


def _nova() -> ConfiguracaoMercadoPago:
    return ConfiguracaoMercadoPago.nova(tenant_id=uuid.uuid4(), agora=AGORA)


def test_tenant_novo_nasce_desligado_e_sem_credencial() -> None:
    config = _nova()

    assert config.habilitado is False
    assert config.access_token_cifrado is None
    assert config.webhook_secret_cifrado is None
    assert config.testado_em is None


def test_definir_credenciais_invalida_o_teste_anterior() -> None:
    """Trocar credencial sem retestar nao pode manter o aval antigo."""
    config = _nova()
    usuario = uuid.uuid4()
    config.definir_credenciais(
        access_token_cifrado=TOKEN,
        webhook_secret_cifrado=SECRET,
        usuario_id=usuario,
        agora=AGORA,
    )
    config.registrar_teste_bem_sucedido(agora=AGORA)
    assert config.testado_em == AGORA

    config.definir_credenciais(
        access_token_cifrado=b"outro",
        webhook_secret_cifrado=SECRET,
        usuario_id=usuario,
        agora=AGORA,
    )

    assert config.testado_em is None


def test_habilitar_exige_as_duas_credenciais() -> None:
    config = _nova()
    config.definir_credenciais(
        access_token_cifrado=TOKEN,
        webhook_secret_cifrado=None,
        usuario_id=uuid.uuid4(),
        agora=AGORA,
    )
    config.registrar_teste_bem_sucedido(agora=AGORA)

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        config.habilitar(usuario_id=uuid.uuid4(), agora=AGORA)

    assert excinfo.value.codigo == "INV-001"
    assert config.habilitado is False


def test_habilitar_exige_teste_bem_sucedido() -> None:
    """Credencial gravada nao prova credencial valida."""
    config = _nova()
    config.definir_credenciais(
        access_token_cifrado=TOKEN,
        webhook_secret_cifrado=SECRET,
        usuario_id=uuid.uuid4(),
        agora=AGORA,
    )

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        config.habilitar(usuario_id=uuid.uuid4(), agora=AGORA)

    assert excinfo.value.codigo == "INV-002"


def test_habilitar_com_credenciais_e_teste_liga() -> None:
    config = _nova()
    usuario = uuid.uuid4()
    config.definir_credenciais(
        access_token_cifrado=TOKEN,
        webhook_secret_cifrado=SECRET,
        usuario_id=usuario,
        agora=AGORA,
    )
    config.registrar_teste_bem_sucedido(agora=AGORA)

    config.habilitar(usuario_id=usuario, agora=AGORA)

    assert config.habilitado is True
    assert config.atualizado_por == usuario


def test_desabilitar_preserva_credenciais_para_religar_depois() -> None:
    """Desligar nao e esquecer: a Credora pode voltar a ligar sem redigitar."""
    config = _nova()
    usuario = uuid.uuid4()
    config.definir_credenciais(
        access_token_cifrado=TOKEN,
        webhook_secret_cifrado=SECRET,
        usuario_id=usuario,
        agora=AGORA,
    )
    config.registrar_teste_bem_sucedido(agora=AGORA)
    config.habilitar(usuario_id=usuario, agora=AGORA)

    config.desabilitar(usuario_id=usuario, agora=AGORA)

    assert config.habilitado is False
    assert config.access_token_cifrado == TOKEN
    assert config.testado_em == AGORA


def test_repr_nunca_mostra_segredo() -> None:
    config = _nova()
    config.definir_credenciais(
        access_token_cifrado=b"segredo-do-provedor",
        webhook_secret_cifrado=b"segredo-do-webhook",
        usuario_id=uuid.uuid4(),
        agora=AGORA,
    )

    texto = repr(config)

    assert "segredo-do-provedor" not in texto
    assert "segredo-do-webhook" not in texto
