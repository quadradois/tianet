"""Entity Credencial - segredo de acesso do Usuario (IMP-082)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from emprestimo.domain.common.errors import ViolacaoInvarianteError

ALGORITMO_CREDENCIAL = "pbkdf2_sha256"
ITERACOES_CREDENCIAL = 210_000
SALT_BYTES = 16


COMPRIMENTO_MINIMO_CREDENCIAL = 10
"""Piso de comprimento da credencial (IMP-342). Politica minima, nao elaborada."""

_CREDENCIAIS_PROIBIDAS = frozenset(
    {
        "0123456789",
        "1234567890",
        "administrador",
        "emprestimo",
        "password123",
        "qwertyuiop",
        "senha123456",
        "tianet2026",
    }
)
"""Trivialidades que passariam pelo comprimento minimo (IMP-342)."""


def _repeticao_unica(segredo: str) -> bool:
    return len(set(segredo)) == 1


def _sequencia_continua(segredo: str) -> bool:
    codigos = [ord(caractere) for caractere in segredo.lower()]
    passos = {b - a for a, b in zip(codigos, codigos[1:], strict=False)}
    return passos in ({1}, {-1})


def _trivial(segredo: str) -> bool:
    return (
        segredo.lower() in _CREDENCIAIS_PROIBIDAS
        or _repeticao_unica(segredo)
        or _sequencia_continua(segredo)
    )


def _normalizar_segredo(segredo: str) -> str:
    """Aplica a politica minima de credencial no unico funil por onde todo segredo novo passa.

    `definir` e `redefinir` chamam esta funcao; validar aqui cobre API, CLI de
    bootstrap e qualquer chamador futuro sem repetir regra na Presentation.
    A mensagem de erro nunca ecoa o segredo recebido.
    """
    segredo_normalizado = segredo.strip()
    if not segredo_normalizado:
        raise ViolacaoInvarianteError(
            "FEATURE-010",
            "credencial nao pode ser vazia",
        )
    if len(segredo_normalizado) < COMPRIMENTO_MINIMO_CREDENCIAL:
        raise ViolacaoInvarianteError(
            "FEATURE-010",
            f"credencial deve ter ao menos {COMPRIMENTO_MINIMO_CREDENCIAL} caracteres",
        )
    if _trivial(segredo_normalizado):
        raise ViolacaoInvarianteError(
            "FEATURE-010",
            "credencial trivial: evite repeticao, sequencia continua ou senha comum",
        )
    return segredo_normalizado


def _gerar_hash(segredo: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    derivado = hashlib.pbkdf2_hmac(
        "sha256",
        segredo.encode("utf-8"),
        salt.encode("utf-8"),
        ITERACOES_CREDENCIAL,
    ).hex()
    return f"{ALGORITMO_CREDENCIAL}${ITERACOES_CREDENCIAL}${salt}${derivado}"


def _verificar_hash(segredo: str, hash_credencial: str) -> bool:
    try:
        algoritmo, iteracoes_raw, salt, esperado = hash_credencial.split("$", 3)
        iteracoes = int(iteracoes_raw)
    except ValueError:
        return False
    if algoritmo != ALGORITMO_CREDENCIAL:
        return False
    derivado = hashlib.pbkdf2_hmac(
        "sha256",
        segredo.encode("utf-8"),
        salt.encode("utf-8"),
        iteracoes,
    ).hex()
    return hmac.compare_digest(derivado, esperado)


@dataclass
class Credencial:
    """Credencial persistivel sem texto legivel (FEATURE-010)."""

    usuario_id: uuid.UUID
    hash_credencial: str
    algoritmo: str = ALGORITMO_CREDENCIAL
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None

    @classmethod
    def definir(cls, *, usuario_id: uuid.UUID, segredo: str) -> Credencial:
        segredo_normalizado = _normalizar_segredo(segredo)
        return cls(usuario_id=usuario_id, hash_credencial=_gerar_hash(segredo_normalizado))

    def verificar(self, segredo: str) -> bool:
        segredo_normalizado = segredo.strip()
        if not segredo_normalizado:
            return False
        return _verificar_hash(segredo_normalizado, self.hash_credencial)

    def trocar(self, *, segredo_atual: str, novo_segredo: str) -> None:
        if not self.verificar(segredo_atual):
            raise ViolacaoInvarianteError(
                "FEATURE-010",
                "credencial atual invalida",
            )
        self.redefinir(novo_segredo)

    def redefinir(self, novo_segredo: str) -> None:
        segredo_normalizado = _normalizar_segredo(novo_segredo)
        self.hash_credencial = _gerar_hash(segredo_normalizado)
        self.algoritmo = ALGORITMO_CREDENCIAL
        self.atualizado_em = datetime.now(UTC)
