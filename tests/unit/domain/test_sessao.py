"""Testes unitarios da Entity Sessao (IMP-083, FEATURE-009)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.sessao import Sessao

USUARIO_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
AGORA = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def test_iniciar_sessao_armazena_hash_do_refresh_token() -> None:
    sessao = Sessao.iniciar(
        usuario_id=USUARIO_ID,
        tenant_id=TENANT_ID,
        refresh_token="refresh-token-legivel",
        agora=AGORA,
    )

    assert sessao.usuario_id == USUARIO_ID
    assert sessao.tenant_id == TENANT_ID
    assert "refresh-token-legivel" not in sessao.refresh_token_hash
    # `agora` explicito como no restante do arquivo: sem ele a verificacao usa o
    # relogio real e o teste passa a falhar sete dias depois de AGORA.
    assert sessao.verificar_refresh_token("refresh-token-legivel", AGORA) is True
    assert sessao.verificar_refresh_token("outro-token", AGORA) is False


def test_refresh_token_expira_em_sete_dias() -> None:
    sessao = Sessao.iniciar(
        usuario_id=USUARIO_ID,
        tenant_id=TENANT_ID,
        refresh_token="refresh-token-legivel",
        agora=AGORA,
    )

    assert sessao.expira_em == AGORA + timedelta(days=7)
    assert sessao.expirada(AGORA + timedelta(days=7, seconds=-1)) is False
    assert sessao.expirada(AGORA + timedelta(days=7)) is True


def test_sessao_revogada_deixa_de_ficar_ativa() -> None:
    sessao = Sessao.iniciar(
        usuario_id=USUARIO_ID,
        tenant_id=TENANT_ID,
        refresh_token="refresh-token-legivel",
        agora=AGORA,
    )

    sessao.revogar(AGORA + timedelta(hours=1))

    assert sessao.revogado_em == AGORA + timedelta(hours=1)
    assert sessao.ativa(AGORA + timedelta(hours=1)) is False
    assert (
        sessao.verificar_refresh_token("refresh-token-legivel", AGORA + timedelta(hours=1)) is False
    )


def test_refresh_token_expirado_nao_valida() -> None:
    sessao = Sessao.iniciar(
        usuario_id=USUARIO_ID,
        tenant_id=TENANT_ID,
        refresh_token="refresh-token-legivel",
        agora=AGORA,
    )

    assert (
        sessao.verificar_refresh_token(
            "refresh-token-legivel",
            AGORA + timedelta(days=7),
        )
        is False
    )


def test_rejeita_refresh_token_vazio() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Sessao.iniciar(
            usuario_id=USUARIO_ID,
            tenant_id=TENANT_ID,
            refresh_token=" ",
            agora=AGORA,
        )

    assert exc.value.codigo == "FEATURE-009"
