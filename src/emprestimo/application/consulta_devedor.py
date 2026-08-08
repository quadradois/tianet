"""Casos de uso de consulta de Devedor (IMP-052, IMP-053).

Reutilizam exclusivamente métodos do DevedorRepository.
Retornam o Aggregate `Devedor` ou `None` / `DevedorResultadoPaginado` —
sem transformação para DTO.
A responsabilidade pelo tratamento de "não encontrado" permanece na camada Presentation.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.ports import (
    DevedorFiltros,
    DevedorRepository,
    DevedorResultadoPaginado,
    Paginacao,
)


class DevedorConsultaService:
    """Caso de uso para consultar Devedor por ID (IMP-052)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def consultar_por_id(self, devedor_id: uuid.UUID) -> Devedor | None:
        """Busca um Devedor pelo seu ID.

        Args:
            devedor_id: UUID do Devedor.

        Returns:
            Aggregate `Devedor` se encontrado, `None` caso contrário.
        """
        with self._uow_factory() as uow:
            return uow.devedor.find_by_id(devedor_id)


class DevedorConsultaPorDocumentoService:
    """Caso de uso para consultar Devedor por documento na Carteira (IMP-052)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def consultar_por_documento(self, carteira_id: uuid.UUID, documento: str) -> Devedor | None:
        """Busca um Devedor pelo documento normalizado na Carteira.

        Args:
            carteira_id: UUID da Carteira.
            documento: Documento do Devedor (CPF) — será normalizado.

        Returns:
            Aggregate `Devedor` se encontrado, `None` caso contrário.
        """
        from emprestimo.domain.credit.documento import Documento

        doc_vo = Documento.from_str(documento)
        with self._uow_factory() as uow:
            return uow.devedor.find_by_documento_carteira(doc_vo, carteira_id)


class DevedorListagemService:
    """Caso de uso para listagem paginada de Devedores (IMP-053)."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def listar(
        self,
        carteira_id: uuid.UUID,
        pagina: int = 1,
        tamanho: int = 20,
        filtros: DevedorFiltros | None = None,
    ) -> DevedorResultadoPaginado:
        """Lista Devedores de uma Carteira com paginação e filtros.

        Args:
            carteira_id: UUID da Carteira.
            pagina: Número da página (base 1, default 1).
            tamanho: Tamanho da página (default 20, max 100).
            filtros: Filtros opcionais (nome, estado, documento).

        Returns:
            DevedorResultadoPaginado com items, total, pagina, tamanho, paginas.
        """
        paginacao = Paginacao(pagina=pagina, tamanho=tamanho)
        with self._uow_factory() as uow:
            return uow.devedor.listar_paginado(carteira_id, filtros, paginacao)
