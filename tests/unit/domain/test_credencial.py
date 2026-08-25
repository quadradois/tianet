"""Testes unitarios da Entity Credencial (IMP-082, FEATURE-010)."""

from __future__ import annotations

import uuid

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.credencial import Credencial

USUARIO_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def test_definir_credencial_armazena_hash_sem_texto_legivel() -> None:
    credencial = Credencial.definir(usuario_id=USUARIO_ID, segredo="Senha Forte 123")

    assert credencial.usuario_id == USUARIO_ID
    assert "Senha Forte 123" not in credencial.hash_credencial
    assert credencial.verificar("Senha Forte 123") is True
    assert credencial.verificar("senha errada") is False


def test_rejeita_segredo_vazio() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Credencial.definir(usuario_id=USUARIO_ID, segredo="   ")

    assert exc.value.codigo == "FEATURE-010"


def test_trocar_credencial_exige_segredo_atual() -> None:
    credencial = Credencial.definir(usuario_id=USUARIO_ID, segredo="Senha Forte 123")

    with pytest.raises(ViolacaoInvarianteError) as exc:
        credencial.trocar(segredo_atual="senha errada", novo_segredo="Nova Senha 456")

    assert exc.value.codigo == "FEATURE-010"
    assert credencial.verificar("Senha Forte 123") is True


def test_trocar_credencial_substitui_hash_anterior() -> None:
    credencial = Credencial.definir(usuario_id=USUARIO_ID, segredo="Senha Forte 123")
    hash_anterior = credencial.hash_credencial

    credencial.trocar(segredo_atual="Senha Forte 123", novo_segredo="Nova Senha 456")

    assert credencial.hash_credencial != hash_anterior
    assert credencial.verificar("Senha Forte 123") is False
    assert credencial.verificar("Nova Senha 456") is True


def test_redefinir_credencial_nao_exige_segredo_anterior() -> None:
    credencial = Credencial.definir(usuario_id=USUARIO_ID, segredo="Senha Forte 123")

    credencial.redefinir("Nova Senha Administrativa 789")

    assert credencial.verificar("Senha Forte 123") is False
    assert credencial.verificar("Nova Senha Administrativa 789") is True


@pytest.mark.parametrize(
    "segredo",
    [
        "curta",
        "Senha 123",
        "aaaaaaaaaaaa",
        "1234567890",
        "abcdefghij",
        "password123",
        "  Senha 1  ",
    ],
)
def test_rejeita_credencial_fora_da_politica_minima(segredo: str) -> None:
    """IMP-342: comprimento minimo e trivialidades barrados no funil do dominio."""
    with pytest.raises(ViolacaoInvarianteError) as exc:
        Credencial.definir(usuario_id=USUARIO_ID, segredo=segredo)

    assert exc.value.codigo == "FEATURE-010"
    assert segredo.strip() not in exc.value.mensagem


def test_redefinir_tambem_aplica_a_politica_minima() -> None:
    """IMP-342: trocar/redefinir passam pelo mesmo funil que definir."""
    credencial = Credencial.definir(usuario_id=USUARIO_ID, segredo="Senha Forte 123")

    with pytest.raises(ViolacaoInvarianteError):
        credencial.redefinir("curta")

    assert credencial.verificar("Senha Forte 123") is True
