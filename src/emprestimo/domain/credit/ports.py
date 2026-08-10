"""Ports do Credit Context — contratos de persistência (DECISION-001 / ADR-001)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.emprestimo import EmprestimoState
from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState

if TYPE_CHECKING:
    from collections.abc import Sequence

    from emprestimo.domain.credit.contato import Contato
    from emprestimo.domain.credit.contrato_credito import ContratoCredito
    from emprestimo.domain.credit.devedor import Devedor
    from emprestimo.domain.credit.emprestimo import Emprestimo
    from emprestimo.domain.credit.eventos_financeiros import EventoFinanceiro
    from emprestimo.domain.credit.memoria_calculo import MemoriaCalculo
    from emprestimo.domain.credit.pagamento import Pagamento
    from emprestimo.domain.credit.parcela import Parcela
    from emprestimo.domain.credit.proposta_comercial import PropostaComercial
    from emprestimo.domain.credit.simulacao_comercial import SimulacaoComercial


class CarteiraRepository(ABC):
    """Persistência do Aggregate Carteira (IMP-007)."""

    @abstractmethod
    def save(self, carteira: Carteira) -> None: ...

    @abstractmethod
    def find_by_id(self, carteira_id: uuid.UUID) -> Carteira | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Carteira]: ...


class DevedorUniquenessChecker(ABC):
    """Contrato mínimo para verificação de unicidade do Devedor (IMP-046).

    Usado pelo UnicidadeDevedorService (DOMAIN-023) sem acoplar ao
    repositório completo (IMP-048).
    """

    @abstractmethod
    def exists_by_documento_carteira(
        self, documento: Documento, carteira_id: uuid.UUID
    ) -> bool: ...


@dataclass(frozen=True)
class DevedorFiltros:
    """Filtros para listagem paginada de Devedores (IMP-053)."""

    nome: str | None = None
    estado: str | None = None  # "ativo" | "inativo"
    documento: str | None = None


@dataclass(frozen=True)
class Paginacao:
    """Parâmetros de paginação (IMP-053)."""

    pagina: int = 1
    tamanho: int = 20

    def __post_init__(self) -> None:
        if self.pagina < 1:
            raise ValueError("pagina deve ser >= 1")
        if self.tamanho < 1 or self.tamanho > 100:
            raise ValueError("tamanho deve ser entre 1 e 100")

    @property
    def offset(self) -> int:
        return (self.pagina - 1) * self.tamanho

    @property
    def limit(self) -> int:
        return self.tamanho


@dataclass(frozen=True)
class DevedorResultadoPaginado:
    """Resultado de listagem paginada de Devedores (IMP-053)."""

    items: Sequence[Devedor]
    total: int
    pagina: int
    tamanho: int

    @property
    def paginas(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.tamanho - 1) // self.tamanho


@dataclass(frozen=True)
class PropostaComercialFiltros:
    """Filtros para consulta de propostas comerciais (EPIC-003/P3)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    devedor_id: uuid.UUID | None = None
    estado: PropostaComercialState | None = None


@dataclass(frozen=True)
class PropostaComercialResultadoPaginado:
    """Resultado paginado de propostas comerciais."""

    items: Sequence[PropostaComercial]
    total: int
    pagina: int
    tamanho: int

    @property
    def paginas(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.tamanho - 1) // self.tamanho


@dataclass(frozen=True)
class ContratoCreditoFiltros:
    """Filtros para consulta de contratos de credito (EPIC-004/P3)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    devedor_id: uuid.UUID | None = None
    estado: ContratoCreditoState | None = None


@dataclass(frozen=True)
class ContratoCreditoResultadoPaginado:
    """Resultado paginado de contratos de credito."""

    items: Sequence[ContratoCredito]
    total: int
    pagina: int
    tamanho: int

    @property
    def paginas(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.tamanho - 1) // self.tamanho


@dataclass(frozen=True)
class EmprestimoFiltros:
    """Filtros para consulta de emprestimos financeiros (EPIC-005/P3)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    devedor_id: uuid.UUID | None = None
    estado: EmprestimoState | None = None


@dataclass(frozen=True)
class EmprestimoResultadoPaginado:
    """Resultado paginado de emprestimos financeiros."""

    items: Sequence[Emprestimo]
    total: int
    pagina: int
    tamanho: int

    @property
    def paginas(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.tamanho - 1) // self.tamanho


class SimulacaoComercialRepository(ABC):
    """Contrato de persistencia de SimulacaoComercial."""

    @abstractmethod
    def save(self, simulacao: SimulacaoComercial) -> None: ...

    @abstractmethod
    def find_by_id(self, simulacao_id: uuid.UUID) -> SimulacaoComercial | None: ...

    @abstractmethod
    def find_by_devedor(self, devedor_id: uuid.UUID) -> list[SimulacaoComercial]: ...


class PropostaComercialRepository(ABC):
    """Contrato de persistencia do Aggregate PropostaComercial."""

    @abstractmethod
    def save(self, proposta: PropostaComercial) -> None: ...

    @abstractmethod
    def find_by_id(self, proposta_id: uuid.UUID) -> PropostaComercial | None: ...

    @abstractmethod
    def listar_paginado(
        self,
        filtros: PropostaComercialFiltros,
        paginacao: Paginacao,
    ) -> PropostaComercialResultadoPaginado: ...


class ContratoCreditoRepository(ABC):
    """Contrato de persistencia do Aggregate ContratoCredito."""

    @abstractmethod
    def save(self, contrato: ContratoCredito) -> None: ...

    @abstractmethod
    def find_by_id(self, contrato_id: uuid.UUID) -> ContratoCredito | None: ...

    @abstractmethod
    def find_by_proposta_id(self, proposta_id: uuid.UUID) -> ContratoCredito | None: ...

    @abstractmethod
    def listar_paginado(
        self,
        filtros: ContratoCreditoFiltros,
        paginacao: Paginacao,
    ) -> ContratoCreditoResultadoPaginado: ...


class EmprestimoRepository(ABC):
    """Contrato de persistencia do Aggregate Emprestimo."""

    @abstractmethod
    def save(self, emprestimo: Emprestimo) -> None: ...

    @abstractmethod
    def find_by_id(self, emprestimo_id: uuid.UUID) -> Emprestimo | None: ...

    @abstractmethod
    def find_by_contrato_id(self, contrato_id: uuid.UUID) -> Emprestimo | None: ...

    @abstractmethod
    def listar_paginado(
        self,
        filtros: EmprestimoFiltros,
        paginacao: Paginacao,
    ) -> EmprestimoResultadoPaginado: ...


class ParcelaRepository(ABC):
    """Contrato de persistencia das Parcelas do Emprestimo."""

    @abstractmethod
    def save_many(self, parcelas: Sequence[Parcela]) -> None: ...

    @abstractmethod
    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[Parcela]: ...


class PagamentoRepository(ABC):
    """Contrato de persistencia dos Pagamentos processados."""

    @abstractmethod
    def save(self, pagamento: Pagamento) -> None: ...

    @abstractmethod
    def find_by_id(self, pagamento_id: uuid.UUID) -> Pagamento | None: ...

    @abstractmethod
    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[Pagamento]: ...

    @abstractmethod
    def find_by_idempotency_key(
        self,
        emprestimo_id: uuid.UUID,
        chave_idempotencia: str,
    ) -> Pagamento | None: ...


class MemoriaCalculoRepository(ABC):
    """Contrato de persistencia das memorias de calculo."""

    @abstractmethod
    def save(
        self,
        memoria: MemoriaCalculo,
        emprestimo_id: uuid.UUID,
        pagamento_id: uuid.UUID | None = None,
    ) -> None: ...

    @abstractmethod
    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[MemoriaCalculo]: ...


class EventoFinanceiroRepository(ABC):
    """Contrato de persistencia dos eventos financeiros."""

    @abstractmethod
    def save(self, evento: EventoFinanceiro) -> None: ...

    @abstractmethod
    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[EventoFinanceiro]: ...


class DevedorRepository(ABC):
    """Contrato de persistência do Aggregate Devedor (IMP-048).

    Segue o padrão do EPIC-001: merge/flush no repositório, commit no UoW.
    Sem acoplamento a SQLAlchemy no Domain.
    """

    @abstractmethod
    def save(self, devedor: Devedor) -> None: ...

    @abstractmethod
    def find_by_id(self, devedor_id: uuid.UUID) -> Devedor | None: ...

    @abstractmethod
    def find_by_documento_carteira(
        self, documento: Documento, carteira_id: uuid.UUID
    ) -> Devedor | None: ...

    @abstractmethod
    def listar_paginado(
        self,
        carteira_id: uuid.UUID,
        filtros: DevedorFiltros,
        paginacao: Paginacao,
    ) -> DevedorResultadoPaginado: ...


class ContatoRepository(ABC):
    """Contrato de persistência da Entity Contato (IMP-048).

    Segue o mesmo padrão: merge/flush no repositório, commit no UoW.
    """

    @abstractmethod
    def save(self, contato: Contato) -> None: ...

    @abstractmethod
    def find_by_id(self, contato_id: uuid.UUID) -> Contato | None: ...

    @abstractmethod
    def find_by_devedor(self, devedor_id: uuid.UUID) -> list[Contato]: ...

    # remove() foi retirado do port. A remoção de Contato é soft-delete
    # (DOMAIN-021 §141): o Aggregate marca o Contato via Contato.remover() e a
    # persistência é feita por save(). O DELETE físico violava a regra de
    # preservação do histórico de auditoria (RN-006/INV-003).
