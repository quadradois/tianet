"""Ports do Credit Context — contratos de persistência (DECISION-001 / ADR-001)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.emprestimo import EmprestimoState
from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState

if TYPE_CHECKING:
    from collections.abc import Sequence

    from emprestimo.domain.credit.configuracoes_financeiras import (
        CalendarioFinanceiro,
        ConfiguracaoFinanceira,
        ConfiguracaoFinanceiraState,
        ModalidadeFinanceira,
        SnapshotConfiguracaoContratualV1,
    )
    from emprestimo.domain.credit.contato import Contato
    from emprestimo.domain.credit.contrato_credito import ContratoCredito
    from emprestimo.domain.credit.devedor import Devedor
    from emprestimo.domain.credit.emprestimo import Emprestimo
    from emprestimo.domain.credit.eventos_financeiros import EventoFinanceiro
    from emprestimo.domain.credit.memoria_calculo import MemoriaCalculo
    from emprestimo.domain.credit.operacao_diaria import (
        AcaoCobranca,
        AgendaItem,
        CobrancaCaso,
        EstadoCompromisso,
        EstadoOperacional,
        Lembrete,
        RegistroComunicacao,
        RelatorioOperacionalCache,
    )
    from emprestimo.domain.credit.operacao_diaria import (
        EstadoCobranca as CobrancaCasoState,
    )
    from emprestimo.domain.credit.pagamento import Pagamento
    from emprestimo.domain.credit.parcela import Parcela
    from emprestimo.domain.credit.promessa import (
        ApropriacaoPagamento,
        PromessaPagamento,
        PromessaPagamentoState,
    )
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


@dataclass(frozen=True)
class CobrancaCasoFiltros:
    """Filtros para busca de casos de cobrança (EPIC-007/P2)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    devedor_id: uuid.UUID | None = None
    estado: CobrancaCasoState | None = None


@dataclass(frozen=True)
class AcaoCobrancaFiltros:
    """Filtros para busca de ações de cobrança manual (EPIC-007/P2)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    devedor_id: uuid.UUID | None = None
    emprestimo_id: uuid.UUID | None = None
    cobranca_caso_id: uuid.UUID | None = None
    usuario_id: uuid.UUID | None = None
    estado: EstadoOperacional | None = None


@dataclass(frozen=True)
class PromessaPagamentoFiltros:
    """Filtros para busca de promessas de pagamento (EPIC-007/P2)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    devedor_id: uuid.UUID | None = None
    emprestimo_id: uuid.UUID | None = None
    estado: PromessaPagamentoState | None = None


@dataclass(frozen=True)
class ApropriacaoPagamentoFiltros:
    """Filtros para busca de apropriações de promessa (EPIC-007/P2)."""

    promessa_id: uuid.UUID | None = None
    pagamento_id: uuid.UUID | None = None


@dataclass(frozen=True)
class AgendaItemFiltros:
    """Filtros para busca de agenda operacional (EPIC-007/P2)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    devedor_id: uuid.UUID | None = None
    emprestimo_id: uuid.UUID | None = None
    estado: EstadoCompromisso | None = None
    janela_inicio: datetime | None = None
    janela_fim: datetime | None = None


@dataclass(frozen=True)
class RegistroComunicacaoFiltros:
    """Filtros para registros de comunicação manual (EPIC-007/P2)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    devedor_id: uuid.UUID | None = None
    emprestimo_id: uuid.UUID | None = None
    cobranca_acao_id: uuid.UUID | None = None
    agenda_item_id: uuid.UUID | None = None


@dataclass(frozen=True)
class RelatorioOperacionalCacheFiltros:
    """Filtros para relatório operacional em cache (EPIC-007/P2)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    familia_relatorio: str | None = None
    janela_inicio: date | None = None
    janela_fim: date | None = None


class CobrancaCasoRepository(ABC):
    """Contrato de persistência do Aggregate CobrancaCaso."""

    @abstractmethod
    def save(self, caso: CobrancaCaso) -> None: ...

    @abstractmethod
    def find_by_id(self, caso_id: uuid.UUID) -> CobrancaCaso | None: ...

    @abstractmethod
    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[CobrancaCaso]: ...

    @abstractmethod
    def listar(self, filtros: CobrancaCasoFiltros) -> list[CobrancaCaso]: ...


class AcaoCobrancaRepository(ABC):
    """Contrato de persistência de ações de cobrança manual."""

    @abstractmethod
    def save(self, acao: AcaoCobranca) -> None: ...

    @abstractmethod
    def find_by_id(self, acao_id: uuid.UUID) -> AcaoCobranca | None: ...

    @abstractmethod
    def listar(self, filtros: AcaoCobrancaFiltros) -> list[AcaoCobranca]: ...


class PromessaPagamentoRepository(ABC):
    """Contrato de persistência de promessas de pagamento."""

    @abstractmethod
    def save(self, promessa: PromessaPagamento) -> None: ...

    @abstractmethod
    def find_by_id(self, promessa_id: uuid.UUID) -> PromessaPagamento | None: ...

    @abstractmethod
    def listar(self, filtros: PromessaPagamentoFiltros) -> list[PromessaPagamento]: ...


class ApropriacaoPagamentoRepository(ABC):
    """Contrato de persistência de apropriações de promessa."""

    @abstractmethod
    def save(self, apropriacao: ApropriacaoPagamento) -> None: ...

    @abstractmethod
    def find_by_id(self, apropriacao_id: uuid.UUID) -> ApropriacaoPagamento | None: ...

    @abstractmethod
    def listar(self, filtros: ApropriacaoPagamentoFiltros) -> list[ApropriacaoPagamento]: ...


class AgendaItemRepository(ABC):
    """Contrato de persistência do item de agenda operacional."""

    @abstractmethod
    def save(self, agenda_item: AgendaItem) -> None: ...

    @abstractmethod
    def find_by_id(self, agenda_item_id: uuid.UUID) -> AgendaItem | None: ...

    @abstractmethod
    def listar(self, filtros: AgendaItemFiltros) -> list[AgendaItem]: ...


class LembreteRepository(ABC):
    """Contrato de persistência de lembretes."""

    @abstractmethod
    def save(self, lembrete: Lembrete) -> None: ...

    @abstractmethod
    def find_by_id(self, lembrete_id: uuid.UUID) -> Lembrete | None: ...

    @abstractmethod
    def find_by_agenda_item_id(self, agenda_item_id: uuid.UUID) -> list[Lembrete]: ...


class RegistroComunicacaoRepository(ABC):
    """Contrato de persistência de registros de comunicação manual."""

    @abstractmethod
    def save(self, registro: RegistroComunicacao) -> None: ...

    @abstractmethod
    def find_by_id(self, registro_id: uuid.UUID) -> RegistroComunicacao | None: ...

    @abstractmethod
    def listar(self, filtros: RegistroComunicacaoFiltros) -> list[RegistroComunicacao]: ...


class RelatorioOperacionalCacheRepository(ABC):
    """Contrato de persistência de caches operacionais de leitura."""

    @abstractmethod
    def save(self, relatorio: RelatorioOperacionalCache) -> None: ...

    @abstractmethod
    def find_by_id(self, relatorio_id: uuid.UUID) -> RelatorioOperacionalCache | None: ...

    @abstractmethod
    def listar(
        self,
        filtros: RelatorioOperacionalCacheFiltros,
    ) -> list[RelatorioOperacionalCache]: ...


@dataclass(frozen=True)
class ConfiguracaoFinanceiraFiltros:
    """Filtros de consulta das configuracoes financeiras (EPIC-009)."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID | None = None
    modalidade: str | None = None
    estado: ConfiguracaoFinanceiraState | None = None
    data_referencia: date | None = None


class ModalidadeFinanceiraRepository(ABC):
    """Persistencia de ModalidadeFinanceira (EPIC-009)."""

    @abstractmethod
    def save(self, modalidade: ModalidadeFinanceira) -> None: ...

    @abstractmethod
    def find_by_id(self, modalidade_id: uuid.UUID) -> ModalidadeFinanceira | None: ...

    @abstractmethod
    def listar(self, tenant_id: uuid.UUID) -> list[ModalidadeFinanceira]: ...


class CalendarioFinanceiroRepository(ABC):
    """Persistencia de CalendarioFinanceiro (EPIC-009)."""

    @abstractmethod
    def save(self, calendario: CalendarioFinanceiro) -> None: ...

    @abstractmethod
    def find_by_id(self, calendario_id: uuid.UUID) -> CalendarioFinanceiro | None: ...

    @abstractmethod
    def listar(self, tenant_id: uuid.UUID) -> list[CalendarioFinanceiro]: ...


class ConfiguracaoFinanceiraRepository(ABC):
    """Persistencia de ConfiguracaoFinanceira e snapshots (EPIC-009)."""

    @abstractmethod
    def save(self, configuracao: ConfiguracaoFinanceira) -> None: ...

    @abstractmethod
    def save_snapshot(self, snapshot: SnapshotConfiguracaoContratualV1) -> None: ...

    @abstractmethod
    def find_by_id(self, configuracao_id: uuid.UUID) -> ConfiguracaoFinanceira | None: ...

    @abstractmethod
    def listar(self, filtros: ConfiguracaoFinanceiraFiltros) -> list[ConfiguracaoFinanceira]: ...


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
