"""Factories (Factory Boy) para entidades da Fase 1 — fixtures dos testes."""

from __future__ import annotations

import uuid

import factory

from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.tenant import Tenant
from emprestimo.domain.platform.usuario import Usuario


class TenantFactory(factory.Factory):
    class Meta:
        model = Tenant

    identificador_institucional = factory.Sequence(lambda n: f"IDENT-{n:06d}")
    nome = factory.Sequence(lambda n: f"Organização {n}")


class UsuarioFactory(factory.Factory):
    class Meta:
        model = Usuario

    tenant_id = factory.LazyFunction(uuid.uuid4)
    nome = factory.Sequence(lambda n: f"Usuário {n}")
    email = factory.Sequence(lambda n: f"usuario{n}@exemplo.com")


class ConfiguracaoFactory(factory.Factory):
    class Meta:
        model = Configuracao

    tenant_id = factory.LazyFunction(uuid.uuid4)
    chave = factory.Sequence(lambda n: f"chave_{n}")
    valor = factory.Sequence(lambda n: f"valor_{n}")


class CarteiraFactory(factory.Factory):
    class Meta:
        model = Carteira

    tenant_id = factory.LazyFunction(uuid.uuid4)
    nome = factory.Sequence(lambda n: f"Carteira {n}")
