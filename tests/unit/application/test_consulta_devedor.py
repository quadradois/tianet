"""Testes unitários dos casos de uso de consulta de Devedor (IMP-052, IMP-053)."""

from __future__ import annotations

import uuid
from unittest.mock import Mock

import pytest

from emprestimo.application.consulta_devedor import (
    DevedorConsultaPorDocumentoService,
    DevedorConsultaService,
    DevedorListagemService,
)
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.ports import DevedorFiltros, DevedorResultadoPaginado, Paginacao

CARTEIRA_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DEVEDOR_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DOCUMENTO = "52998224725"


def _mock_devedor() -> Devedor:
    """Cria um Devedor mock para testes."""
    contatos = (
        Contato(
            devedor_id=DEVEDOR_ID,
            tipo=TipoContato.TELEFONE,
            valor="(11) 1234-5678",
            preferencial=True,
        ),
        Contato(
            devedor_id=DEVEDOR_ID,
            tipo=TipoContato.EMAIL,
            valor="joao@exemplo.com",
            preferencial=False,
        ),
    )
    devedor = Devedor.criar(
        carteira_id=CARTEIRA_ID,
        documento=Documento.from_str(DOCUMENTO),
        nome="João da Silva",
        contatos=contatos,
    )
    # Força o ID para controle nos testes
    devedor.id = DEVEDOR_ID
    return devedor


def _mock_uow_factory(devedor: Devedor | None = None) -> Mock:
    """Cria um mock do UnitOfWork com DevedorRepository."""
    uow = Mock(spec=UnitOfWork)
    uow.devedor = Mock()
    uow.devedor.find_by_id.return_value = devedor
    uow.devedor.find_by_documento_carteira.return_value = devedor
    uow.commit = Mock()
    uow.rollback = Mock()
    uow.close = Mock()
    uow.__enter__ = Mock(return_value=uow)
    uow.__exit__ = Mock(return_value=None)
    return uow


class TestDevedorConsultaService:
    """Testes do DevedorConsultaService (IMP-052)."""

    def test_consultar_por_id_encontrado(self) -> None:
        """Deve retornar Devedor quando encontrado por ID."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)

        def uow_factory() -> Mock:
            return uow

        service = DevedorConsultaService(uow_factory)
        resultado = service.consultar_por_id(DEVEDOR_ID)

        assert resultado is not None
        assert resultado.id == DEVEDOR_ID
        assert resultado.carteira_id == CARTEIRA_ID
        assert resultado.documento.valor == DOCUMENTO
        assert resultado.nome == "João da Silva"
        assert resultado.estado == DevedorState.ATIVO
        assert len(resultado.contatos) == 2

        uow.devedor.find_by_id.assert_called_once_with(DEVEDOR_ID)

    def test_consultar_por_id_nao_encontrado(self) -> None:
        """Deve retornar None quando Devedor não encontrado por ID."""
        uow = _mock_uow_factory(None)

        def uow_factory() -> Mock:
            return uow

        service = DevedorConsultaService(uow_factory)
        resultado = service.consultar_por_id(DEVEDOR_ID)

        assert resultado is None
        uow.devedor.find_by_id.assert_called_once_with(DEVEDOR_ID)


class TestDevedorConsultaPorDocumentoService:
    """Testes do DevedorConsultaPorDocumentoService (IMP-052)."""

    def test_consultar_por_documento_encontrado(self) -> None:
        """Deve retornar Devedor quando encontrado por documento na Carteira."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)

        def uow_factory() -> Mock:
            return uow

        service = DevedorConsultaPorDocumentoService(uow_factory)
        resultado = service.consultar_por_documento(CARTEIRA_ID, DOCUMENTO)

        assert resultado is not None
        assert resultado.id == DEVEDOR_ID
        assert resultado.carteira_id == CARTEIRA_ID
        assert resultado.documento.valor == DOCUMENTO
        assert resultado.nome == "João da Silva"
        assert resultado.estado == DevedorState.ATIVO
        assert len(resultado.contatos) == 2

        uow.devedor.find_by_documento_carteira.assert_called_once()
        call_args = uow.devedor.find_by_documento_carteira.call_args
        assert call_args[0][0].valor == DOCUMENTO  # Documento VO
        assert call_args[0][1] == CARTEIRA_ID

    def test_consultar_por_documento_nao_encontrado(self) -> None:
        """Deve retornar None quando Devedor não encontrado por documento."""
        uow = _mock_uow_factory(None)

        def uow_factory() -> Mock:
            return uow

        service = DevedorConsultaPorDocumentoService(uow_factory)
        resultado = service.consultar_por_documento(CARTEIRA_ID, DOCUMENTO)

        assert resultado is None
        uow.devedor.find_by_documento_carteira.assert_called_once()

    def test_consultar_por_documento_normaliza_entrada(self) -> None:
        """Deve normalizar documento de entrada (CPF com formatação)."""
        devedor = _mock_devedor()
        uow = _mock_uow_factory(devedor)

        def uow_factory() -> Mock:
            return uow

        service = DevedorConsultaPorDocumentoService(uow_factory)
        # Documento com formatação: 529.982.247-25
        resultado = service.consultar_por_documento(CARTEIRA_ID, "529.982.247-25")

        assert resultado is not None
        # Verifica que o Documento VO foi normalizado
        call_args = uow.devedor.find_by_documento_carteira.call_args
        assert call_args[0][0].valor == DOCUMENTO


class TestDevedorListagemService:
    """Testes do DevedorListagemService (IMP-053)."""

    def test_listar_sem_filtros(self) -> None:
        """Deve listar Devedores com paginação padrão sem filtros."""
        devedor = _mock_devedor()
        resultado_paginado = DevedorResultadoPaginado(
            items=(devedor,),
            total=1,
            pagina=1,
            tamanho=20,
        )
        uow = _mock_uow_factory()
        uow.devedor.listar_paginado.return_value = resultado_paginado

        def uow_factory() -> Mock:
            return uow

        service = DevedorListagemService(uow_factory)
        resultado = service.listar(CARTEIRA_ID)

        assert isinstance(resultado, DevedorResultadoPaginado)
        assert resultado.total == 1
        assert resultado.pagina == 1
        assert resultado.tamanho == 20
        assert resultado.paginas == 1
        assert len(resultado.items) == 1
        assert resultado.items[0].id == DEVEDOR_ID

        uow.devedor.listar_paginado.assert_called_once()
        call_args = uow.devedor.listar_paginado.call_args
        assert call_args[0][0] == CARTEIRA_ID
        assert isinstance(call_args[0][1], DevedorFiltros)
        assert call_args[0][1] == DevedorFiltros()
        assert call_args[0][2].pagina == 1
        assert call_args[0][2].tamanho == 20

    def test_listar_com_paginacao_customizada(self) -> None:
        """Deve listar com paginação customizada (página e tamanho)."""
        resultado_paginado = DevedorResultadoPaginado(
            items=(),
            total=0,
            pagina=2,
            tamanho=50,
        )
        uow = _mock_uow_factory()
        uow.devedor.listar_paginado.return_value = resultado_paginado

        def uow_factory() -> Mock:
            return uow

        service = DevedorListagemService(uow_factory)
        resultado = service.listar(CARTEIRA_ID, pagina=2, tamanho=50)

        assert resultado.pagina == 2
        assert resultado.tamanho == 50

        call_args = uow.devedor.listar_paginado.call_args
        assert call_args[0][2].pagina == 2
        assert call_args[0][2].tamanho == 50

    def test_listar_com_filtros(self) -> None:
        """Deve listar aplicando filtros (nome, estado, documento)."""
        resultado_paginado = DevedorResultadoPaginado(
            items=(),
            total=0,
            pagina=1,
            tamanho=20,
        )
        uow = _mock_uow_factory()
        uow.devedor.listar_paginado.return_value = resultado_paginado

        def uow_factory() -> Mock:
            return uow

        service = DevedorListagemService(uow_factory)
        filtros = DevedorFiltros(nome="João", estado=DevedorState.ATIVO, documento="529")
        service.listar(CARTEIRA_ID, filtros=filtros)

        call_args = uow.devedor.listar_paginado.call_args
        assert call_args[0][1] == filtros
        assert call_args[0][1].nome == "João"
        assert call_args[0][1].estado == DevedorState.ATIVO
        assert call_args[0][1].documento == "529"


class TestPaginacao:
    """Validação dos parâmetros de paginação (IMP-063).

    ``Paginacao`` protege os próprios limites no ``__post_init__``; sem isso um
    ``pagina=0`` produziria offset negativo na query.
    """

    def test_rejeita_pagina_menor_que_um(self) -> None:
        with pytest.raises(ValueError, match="pagina deve ser >= 1"):
            Paginacao(pagina=0, tamanho=20)

    def test_rejeita_tamanho_zero(self) -> None:
        with pytest.raises(ValueError, match="tamanho deve ser entre 1 e 100"):
            Paginacao(pagina=1, tamanho=0)

    def test_rejeita_tamanho_acima_do_maximo(self) -> None:
        with pytest.raises(ValueError, match="tamanho deve ser entre 1 e 100"):
            Paginacao(pagina=1, tamanho=101)

    def test_offset_e_limit_derivam_da_pagina(self) -> None:
        assert Paginacao(pagina=3, tamanho=20).offset == 40
        assert Paginacao(pagina=3, tamanho=20).limit == 20
