"""Testes de integração do SqlAlchemyDevedorRepository (IMP-049) — PostgreSQL.

Cobrem o que os testes unitários com dublês não alcançam: as queries reais
(round-trip, busca por documento, verificação de unicidade e listagem paginada
com filtros) e as constraints do banco.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.factories import CarteiraFactory, TenantFactory

from emprestimo.domain.common.errors import DevedorJaExisteError
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.ports import DevedorFiltros, Paginacao
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyContatoRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyTenantRepository,
)

# CPFs válidos distintos (dígitos verificadores corretos)
CPF_A = "52998224725"
CPF_B = "11144477735"


def _carteira_persistida(session: Session) -> uuid.UUID:
    """Cria Tenant + Carteira reais — o Devedor exige a FK da Carteira."""
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(session).save(carteira)
    session.commit()
    return carteira.id


def _devedor(carteira_id: uuid.UUID, documento: str, nome: str = "João da Silva") -> Devedor:
    contatos = (
        Contato(
            devedor_id=uuid.uuid4(),  # substituído pelo Aggregate
            tipo=TipoContato.TELEFONE,
            valor="(11) 1234-5678",
            preferencial=True,
        ),
    )
    return Devedor.criar(
        carteira_id=carteira_id,
        documento=Documento.from_str(documento),
        nome=nome,
        contatos=contatos,
    )


def test_round_trip_preserva_documento_e_estado(session: Session) -> None:
    carteira_id = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    devedor = _devedor(carteira_id, CPF_A)

    repo.save(devedor)
    session.commit()
    carregado = repo.find_by_id(devedor.id)

    assert carregado is not None
    assert carregado.carteira_id == carteira_id
    assert carregado.documento.valor == CPF_A
    assert carregado.nome == "João da Silva"
    assert carregado.estado is DevedorState.ATIVO


def test_round_trip_preserva_soft_delete_de_contato(session: Session) -> None:
    carteira_id = _carteira_persistida(session)
    devedor_repo = SqlAlchemyDevedorRepository(session)
    contato_repo = SqlAlchemyContatoRepository(session)
    devedor = _devedor(carteira_id, CPF_A)
    contato_id = devedor.contatos[0].id

    devedor_repo.save(devedor)
    for contato in devedor.contatos:
        contato_repo.save(contato)
    session.commit()

    devedor.remover_contato(contato_id)
    for contato in devedor.contatos_historico:
        contato_repo.save(contato)
    session.commit()

    carregado = devedor_repo.find_by_id(devedor.id)
    contatos_persistidos = contato_repo.find_by_devedor(devedor.id)

    assert carregado is not None
    assert carregado.contatos == ()
    assert len(carregado.contatos_historico) == 1
    assert contatos_persistidos[0].removido_em is not None


def test_find_by_id_inexistente_retorna_none(session: Session) -> None:
    repo = SqlAlchemyDevedorRepository(session)

    assert repo.find_by_id(uuid.uuid4()) is None


def test_find_by_documento_carteira(session: Session) -> None:
    carteira_id = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    devedor = _devedor(carteira_id, CPF_A)
    repo.save(devedor)
    session.commit()

    encontrado = repo.find_by_documento_carteira(Documento.from_str(CPF_A), carteira_id)

    assert encontrado is not None
    assert encontrado.id == devedor.id


def test_find_by_documento_de_outra_carteira_nao_vaza(session: Session) -> None:
    """INV-002: o documento é único por Carteira — a busca é isolada por Carteira."""
    carteira_a = _carteira_persistida(session)
    carteira_b = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    repo.save(_devedor(carteira_a, CPF_A))
    session.commit()

    assert repo.find_by_documento_carteira(Documento.from_str(CPF_A), carteira_b) is None


def test_exists_by_documento_carteira(session: Session) -> None:
    """IMP-046: é a query que sustenta a recusa de documento duplicado."""
    carteira_id = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    doc = Documento.from_str(CPF_A)

    assert repo.exists_by_documento_carteira(doc, carteira_id) is False

    repo.save(_devedor(carteira_id, CPF_A))
    session.commit()

    assert repo.exists_by_documento_carteira(doc, carteira_id) is True


def test_exists_isolado_por_carteira(session: Session) -> None:
    """O mesmo documento pode existir em Carteiras distintas."""
    carteira_a = _carteira_persistida(session)
    carteira_b = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    repo.save(_devedor(carteira_a, CPF_A))
    session.commit()

    doc = Documento.from_str(CPF_A)
    assert repo.exists_by_documento_carteira(doc, carteira_a) is True
    assert repo.exists_by_documento_carteira(doc, carteira_b) is False


def test_documento_duplicado_na_carteira_traduz_para_erro_de_dominio(
    session: Session,
) -> None:
    """A constraint UNIQUE é a última linha de defesa e vira erro de domínio.

    O ``save()`` faz ``flush()``, então a violação estoura ali — e o repositório
    a traduz para ``DevedorJaExisteError``, que a API responde como 409.
    """
    carteira_id = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    repo.save(_devedor(carteira_id, CPF_A))
    session.commit()

    with pytest.raises(DevedorJaExisteError):
        repo.save(_devedor(carteira_id, CPF_A, nome="Outro Nome"))
    session.rollback()


def test_devedor_sem_carteira_viola_fk(session: Session) -> None:
    """INV-001: todo Devedor pertence exatamente a uma Carteira.

    A FK não é traduzida para erro de domínio (só a UNIQUE é), então vaza como
    ``IntegrityError`` no flush do ``save()``.
    """
    repo = SqlAlchemyDevedorRepository(session)

    with pytest.raises(IntegrityError):
        repo.save(_devedor(uuid.uuid4(), CPF_A))
    session.rollback()


def test_listar_paginado_sem_filtros(session: Session) -> None:
    carteira_id = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    repo.save(_devedor(carteira_id, CPF_A, nome="Ana Souza"))
    repo.save(_devedor(carteira_id, CPF_B, nome="Bruno Lima"))
    session.commit()

    resultado = repo.listar_paginado(carteira_id, DevedorFiltros(), Paginacao(1, 20))

    assert resultado.total == 2
    assert len(resultado.items) == 2
    assert resultado.paginas == 1


def test_listar_paginado_isolado_por_carteira(session: Session) -> None:
    carteira_a = _carteira_persistida(session)
    carteira_b = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    repo.save(_devedor(carteira_a, CPF_A))
    session.commit()

    resultado = repo.listar_paginado(carteira_b, DevedorFiltros(), Paginacao(1, 20))

    assert resultado.total == 0
    assert resultado.items == [] or list(resultado.items) == []


def test_listar_paginado_filtro_nome(session: Session) -> None:
    carteira_id = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    repo.save(_devedor(carteira_id, CPF_A, nome="Ana Souza"))
    repo.save(_devedor(carteira_id, CPF_B, nome="Bruno Lima"))
    session.commit()

    resultado = repo.listar_paginado(carteira_id, DevedorFiltros(nome="Ana"), Paginacao(1, 20))

    assert resultado.total == 1
    assert list(resultado.items)[0].nome == "Ana Souza"


def test_listar_paginado_filtro_estado(session: Session) -> None:
    carteira_id = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    ativo = _devedor(carteira_id, CPF_A, nome="Ana Souza")
    inativo = _devedor(carteira_id, CPF_B, nome="Bruno Lima")
    inativo.inativar()
    repo.save(ativo)
    repo.save(inativo)
    session.commit()

    resultado = repo.listar_paginado(
        carteira_id, DevedorFiltros(estado="inativo"), Paginacao(1, 20)
    )

    assert resultado.total == 1
    assert list(resultado.items)[0].estado is DevedorState.INATIVO


def test_listar_paginado_segunda_pagina(session: Session) -> None:
    carteira_id = _carteira_persistida(session)
    repo = SqlAlchemyDevedorRepository(session)
    repo.save(_devedor(carteira_id, CPF_A, nome="Ana Souza"))
    repo.save(_devedor(carteira_id, CPF_B, nome="Bruno Lima"))
    session.commit()

    resultado = repo.listar_paginado(carteira_id, DevedorFiltros(), Paginacao(2, 1))

    assert resultado.total == 2
    assert resultado.pagina == 2
    assert len(list(resultado.items)) == 1
    assert resultado.paginas == 2
