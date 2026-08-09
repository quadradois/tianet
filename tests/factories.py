"""Factories tipadas para entidades usadas nos testes."""

from __future__ import annotations

import uuid
from itertools import count
from typing import Any

from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.tenant import Tenant
from emprestimo.domain.platform.usuario import Usuario


class TenantFactory:
    _seq = count()

    @classmethod
    def build(cls, **overrides: Any) -> Tenant:
        n = next(cls._seq)
        valores = {
            "identificador_institucional": f"IDENT-{n:06d}",
            "nome": f"Organizacao {n}",
            **overrides,
        }
        return Tenant(**valores)


class UsuarioFactory:
    _seq = count()

    @classmethod
    def build(cls, **overrides: Any) -> Usuario:
        n = next(cls._seq)
        valores = {
            "tenant_id": uuid.uuid4(),
            "nome": f"Usuario {n}",
            "email": f"usuario{n}@exemplo.com",
            **overrides,
        }
        return Usuario(**valores)


class ConfiguracaoFactory:
    _seq = count()

    @classmethod
    def build(cls, **overrides: Any) -> Configuracao:
        n = next(cls._seq)
        valores = {
            "tenant_id": uuid.uuid4(),
            "chave": f"chave_{n}",
            "valor": f"valor_{n}",
            **overrides,
        }
        return Configuracao(**valores)


class CarteiraFactory:
    _seq = count()

    @classmethod
    def build(cls, **overrides: Any) -> Carteira:
        n = next(cls._seq)
        valores = {
            "tenant_id": uuid.uuid4(),
            "nome": f"Carteira {n}",
            **overrides,
        }
        return Carteira(**valores)
