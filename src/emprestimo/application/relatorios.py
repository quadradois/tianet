"""Servicos de relatorios operacionais (EPIC-007/IMP-180)."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from emprestimo.application.errors import CarteiraNaoEncontradaError
from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.credit.emprestimo import Emprestimo, EmprestimoState
from emprestimo.domain.credit.pagamento import Pagamento, PagamentoState
from emprestimo.domain.credit.parcela import Parcela
from emprestimo.domain.credit.ports import EmprestimoFiltros, Paginacao


@dataclass(frozen=True)
class ResumoCarteiraResultado:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    data_referencia: date
    total_operacoes: int
    operacoes_ativas: int
    operacoes_quitadas: int
    acertos_pendentes: int
    principal_a_receber: Decimal
    total_realizado: Decimal


@dataclass(frozen=True)
class VencimentoOperacionalResultado:
    """Um acerto mensal, no lugar de uma parcela (DR-004).

    `situacao` diz o que esta camada consegue afirmar: "pendente" quando o
    acerto ja venceu e ninguem apareceu, "em dia" caso contrario. Nao diz
    "inadimplente" — julgar se os juros do periodo foram quitados exige o saldo,
    e saldo e do Motor, que esta camada nao importa.
    """

    emprestimo_id: uuid.UUID
    devedor_id: uuid.UUID
    dia_de_acerto: int
    acerto_em: date
    dias_sem_pagamento: int
    principal_original: Decimal
    situacao: str


@dataclass(frozen=True)
class VencimentosInadimplenciaResultado:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    data_referencia: date
    itens: tuple[VencimentoOperacionalResultado, ...]

    @property
    def total(self) -> int:
        return len(self.itens)


@dataclass(frozen=True)
class PagamentoOperacionalResultado:
    pagamento_id: uuid.UUID
    emprestimo_id: uuid.UUID
    recebido_em: date
    valor_recebido: Decimal
    estado: PagamentoState


@dataclass(frozen=True)
class PagamentosEncerramentosResultado:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    inicio: date
    fim: date
    pagamentos: tuple[PagamentoOperacionalResultado, ...]
    operacoes_quitadas: tuple[uuid.UUID, ...]
    total_realizado: Decimal


@dataclass(frozen=True)
class FluxoDiaResultado:
    data: date
    previsto: Decimal
    realizado: Decimal
    parcela_ids: tuple[uuid.UUID, ...]
    pagamento_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class FluxoPrevistoRealizadoResultado:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    inicio: date
    fim: date
    itens: tuple[FluxoDiaResultado, ...]


class RelatoriosOperacionaisService:
    """Consolida leituras operacionais a partir dos fatos oficiais persistidos."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def resumo_carteira(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        data_referencia: date,
    ) -> ResumoCarteiraResultado:
        with self._uow_factory() as uow:
            _validar_carteira(uow, tenant_id=tenant_id, carteira_id=carteira_id)
            emprestimos = _emprestimos_da_carteira(
                uow,
                tenant_id=tenant_id,
                carteira_id=carteira_id,
            )
            pagamentos = _pagamentos_dos_emprestimos(uow, emprestimos)
            return ResumoCarteiraResultado(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                data_referencia=data_referencia,
                total_operacoes=len(emprestimos),
                operacoes_ativas=sum(
                    1 for item in emprestimos if item.estado is EmprestimoState.ATIVO
                ),
                operacoes_quitadas=sum(
                    1 for item in emprestimos if item.estado is EmprestimoState.QUITADO
                ),
                # Quem nao apareceu no acerto que ja venceu. Nao se chama
                # "inadimplentes": saber se os juros do periodo foram quitados
                # exige o saldo, e saldo e do Motor, que esta camada nao importa.
                acertos_pendentes=sum(
                    1
                    for item in emprestimos
                    if item.estado is EmprestimoState.ATIVO
                    and item.acerto_sem_pagamento_em(data_referencia) is not None
                ),
                # Quanto do dinheiro emprestado ainda esta na rua: o que saiu,
                # menos o que ja voltou como amortizacao. Nao inclui juros
                # acumulados — isso e saldo, e saldo e do Motor.
                principal_a_receber=_somar_decimal(item.principal_original for item in emprestimos)
                - _somar_decimal(
                    pagamento.valor_amortizacao
                    for pagamento in pagamentos
                    if pagamento.estado is not PagamentoState.ESTORNADO
                ),
                total_realizado=_somar_decimal(
                    pagamento.valor_recebido
                    for pagamento in pagamentos
                    if pagamento.estado is not PagamentoState.ESTORNADO
                ),
            )

    def vencimentos_inadimplencia(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        data_referencia: date,
    ) -> VencimentosInadimplenciaResultado:
        with self._uow_factory() as uow:
            _validar_carteira(uow, tenant_id=tenant_id, carteira_id=carteira_id)
            emprestimos = _emprestimos_da_carteira(
                uow,
                tenant_id=tenant_id,
                carteira_id=carteira_id,
            )
            itens = tuple(
                sorted(
                    (
                        _vencimento_resultado(item, data_referencia)
                        for item in emprestimos
                        if item.estado is EmprestimoState.ATIVO and item.dia_de_acerto is not None
                    ),
                    key=lambda resultado: (resultado.acerto_em, resultado.emprestimo_id),
                )
            )
            return VencimentosInadimplenciaResultado(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                data_referencia=data_referencia,
                itens=itens,
            )

    def pagamentos_encerramentos(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        inicio: date,
        fim: date,
    ) -> PagamentosEncerramentosResultado:
        with self._uow_factory() as uow:
            _validar_periodo(inicio, fim)
            _validar_carteira(uow, tenant_id=tenant_id, carteira_id=carteira_id)
            emprestimos = _emprestimos_da_carteira(
                uow,
                tenant_id=tenant_id,
                carteira_id=carteira_id,
            )
            pagamentos = [
                pagamento
                for pagamento in _pagamentos_dos_emprestimos(uow, emprestimos)
                if inicio <= pagamento.recebido_em.date() <= fim
            ]
            return PagamentosEncerramentosResultado(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                inicio=inicio,
                fim=fim,
                pagamentos=tuple(_pagamento_resultado(item) for item in pagamentos),
                operacoes_quitadas=tuple(
                    item.id
                    for item in emprestimos
                    if item.estado is EmprestimoState.QUITADO
                    and item.quitado_em is not None
                    and inicio <= item.quitado_em.date() <= fim
                ),
                total_realizado=_somar_decimal(
                    pagamento.valor_recebido
                    for pagamento in pagamentos
                    if pagamento.estado is not PagamentoState.ESTORNADO
                ),
            )

    def fluxo_previsto_realizado(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        inicio: date,
        fim: date,
    ) -> FluxoPrevistoRealizadoResultado:
        with self._uow_factory() as uow:
            _validar_periodo(inicio, fim)
            _validar_carteira(uow, tenant_id=tenant_id, carteira_id=carteira_id)
            emprestimos = _emprestimos_da_carteira(
                uow,
                tenant_id=tenant_id,
                carteira_id=carteira_id,
            )
            parcelas = [
                parcela
                for parcela in _parcelas_dos_emprestimos(uow, emprestimos)
                if inicio <= parcela.vencimento <= fim
            ]
            pagamentos = [
                pagamento
                for pagamento in _pagamentos_dos_emprestimos(uow, emprestimos)
                if inicio <= pagamento.recebido_em.date() <= fim
            ]
            datas = sorted(
                {parcela.vencimento for parcela in parcelas}
                | {pagamento.recebido_em.date() for pagamento in pagamentos}
            )
            return FluxoPrevistoRealizadoResultado(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                inicio=inicio,
                fim=fim,
                itens=tuple(
                    FluxoDiaResultado(
                        data=dia,
                        previsto=_somar_decimal(
                            parcela.valor_previsto
                            for parcela in parcelas
                            if parcela.vencimento == dia
                        ),
                        realizado=_somar_decimal(
                            pagamento.valor_recebido
                            for pagamento in pagamentos
                            if pagamento.recebido_em.date() == dia
                            and pagamento.estado is not PagamentoState.ESTORNADO
                        ),
                        parcela_ids=tuple(
                            parcela.id for parcela in parcelas if parcela.vencimento == dia
                        ),
                        pagamento_ids=tuple(
                            pagamento.id
                            for pagamento in pagamentos
                            if pagamento.recebido_em.date() == dia
                        ),
                    )
                    for dia in datas
                ),
            )


def _validar_carteira(
    uow: UnitOfWork,
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
) -> None:
    carteira = uow.carteira.find_by_id(carteira_id)
    if carteira is None or carteira.tenant_id != tenant_id:
        raise CarteiraNaoEncontradaError(carteira_id)


def _emprestimos_da_carteira(
    uow: UnitOfWork,
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
) -> tuple[Emprestimo, ...]:
    filtros = EmprestimoFiltros(tenant_id=tenant_id, carteira_id=carteira_id)
    pagina = 1
    tamanho = 100
    emprestimos: list[Emprestimo] = []
    while True:
        resultado = uow.emprestimo.listar_paginado(
            filtros,
            Paginacao(pagina=pagina, tamanho=tamanho),
        )
        emprestimos.extend(resultado.items)
        if len(emprestimos) >= resultado.total or not resultado.items:
            return tuple(emprestimos)
        pagina += 1


def _parcelas_dos_emprestimos(
    uow: UnitOfWork,
    emprestimos: tuple[Emprestimo, ...],
) -> tuple[Parcela, ...]:
    return tuple(
        parcela
        for emprestimo in emprestimos
        for parcela in uow.parcela.find_by_emprestimo_id(emprestimo.id)
    )


def _pagamentos_dos_emprestimos(
    uow: UnitOfWork,
    emprestimos: tuple[Emprestimo, ...],
) -> tuple[Pagamento, ...]:
    return tuple(
        pagamento
        for emprestimo in emprestimos
        for pagamento in uow.pagamento.find_by_emprestimo_id(emprestimo.id)
    )


def _vencimento_resultado(
    emprestimo: Emprestimo, data_referencia: date
) -> VencimentoOperacionalResultado:
    pendente = emprestimo.acerto_sem_pagamento_em(data_referencia)
    proximo = emprestimo.proximo_acerto_em(data_referencia)
    dia = emprestimo.dia_de_acerto
    assert dia is not None  # filtrado por quem chama
    return VencimentoOperacionalResultado(
        emprestimo_id=emprestimo.id,
        devedor_id=emprestimo.devedor_id,
        dia_de_acerto=dia,
        # Pendente mostra o acerto que ja venceu; em dia, o proximo que vem.
        acerto_em=pendente or proximo or data_referencia,
        dias_sem_pagamento=emprestimo.dias_sem_pagamento_em(data_referencia),
        principal_original=emprestimo.principal_original,
        situacao="pendente" if pendente is not None else "em dia",
    )


def _pagamento_resultado(pagamento: Pagamento) -> PagamentoOperacionalResultado:
    return PagamentoOperacionalResultado(
        pagamento_id=pagamento.id,
        emprestimo_id=pagamento.emprestimo_id,
        recebido_em=pagamento.recebido_em.date(),
        valor_recebido=pagamento.valor_recebido,
        estado=pagamento.estado,
    )


def _somar_decimal(valores: Iterable[Decimal]) -> Decimal:
    total = Decimal("0.00")
    for valor in valores:
        total += valor
    return total


def _validar_periodo(inicio: date, fim: date) -> None:
    if inicio > fim:
        raise ValueError("inicio deve ser menor ou igual ao fim")
