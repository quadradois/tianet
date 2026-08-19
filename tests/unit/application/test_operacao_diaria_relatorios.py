"""Testes unitarios dos relatorios operacionais (IMP-180)."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

import pytest

from emprestimo.application.errors import CarteiraNaoEncontradaError
from emprestimo.application.ports import UnitOfWork
from emprestimo.application.relatorios import RelatoriosOperacionaisService
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.emprestimo import Emprestimo, EmprestimoState
from emprestimo.domain.credit.pagamento import Pagamento, PagamentoState
from emprestimo.domain.credit.parcela import Parcela, ParcelaState
from emprestimo.domain.credit.ports import EmprestimoResultadoPaginado

TENANT_ID = uuid.UUID("77000000-0000-0000-0000-000000000001")
CARTEIRA_ID = uuid.UUID("77000000-0000-0000-0000-000000000002")
DEVEDOR_ID = uuid.UUID("77000000-0000-0000-0000-000000000003")
CONTRATO_ID = uuid.UUID("77000000-0000-0000-0000-000000000004")
EMPRESTIMO_ID = uuid.UUID("77000000-0000-0000-0000-000000000005")
EMPRESTIMO_QUITADO_ID = uuid.UUID("77000000-0000-0000-0000-000000000006")


def test_resumo_carteira_agrega_fatos_oficiais_sem_commit() -> None:
    ativo = _emprestimo(id=EMPRESTIMO_ID)
    quitado = _emprestimo(
        id=EMPRESTIMO_QUITADO_ID,
        estado=EmprestimoState.QUITADO,
        quitado_em=datetime(2026, 8, 5, 10, 0, tzinfo=UTC),
    )
    uow = _FakeUoW(
        emprestimos=[ativo, quitado],
        parcelas=[
            _parcela(ativo.id, numero=1, vencimento=date(2026, 8, 1), valor="100.00"),
            _parcela(
                ativo.id,
                numero=2,
                vencimento=date(2026, 9, 1),
                valor="120.00",
            ),
            _parcela(
                quitado.id,
                numero=1,
                vencimento=date(2026, 7, 1),
                valor="80.00",
                estado=ParcelaState.LIQUIDADA,
                valor_liquidado="80.00",
            ),
        ],
        pagamentos=[
            _pagamento(ativo.id, valor="50.00", recebido_em=datetime(2026, 8, 2, tzinfo=UTC)),
            _pagamento(
                quitado.id,
                valor="80.00",
                recebido_em=datetime(2026, 8, 5, tzinfo=UTC),
            ),
            _pagamento(
                ativo.id,
                valor="20.00",
                recebido_em=datetime(2026, 8, 7, tzinfo=UTC),
                estado=PagamentoState.ESTORNADO,
            ),
        ],
    )

    resultado = RelatoriosOperacionaisService(_uow_factory(uow)).resumo_carteira(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        data_referencia=date(2026, 8, 10),
    )

    assert resultado.total_operacoes == 2
    assert resultado.operacoes_ativas == 1
    assert resultado.operacoes_quitadas == 1
    # Nenhum dos dois tem dia de acerto combinado, entao nenhum entra na fila.
    assert resultado.acertos_pendentes == 0
    # Dois emprestimos de 1.000, menos 130,00 de amortizacao efetiva: o estorno
    # de 20,00 nao reduz o que esta na rua.
    assert resultado.principal_a_receber == Decimal("1870.00")
    assert resultado.total_realizado == Decimal("130.00")
    assert uow.commits == 0


def test_resumo_conta_quem_nao_apareceu_no_acerto_que_ja_venceu() -> None:
    """A fila que substitui "parcelas vencidas" (DR-004, PLAN-030 fase C).

    Nao se chama inadimplencia: saber se os juros do periodo foram quitados
    exige o saldo, e saldo e do Motor, que esta camada nao importa.
    """
    sem_acerto = _emprestimo(id=uuid.UUID("77000000-0000-0000-0000-000000000101"))
    venceu_e_ninguem_apareceu = _emprestimo(
        id=uuid.UUID("77000000-0000-0000-0000-000000000102"),
        dia_de_acerto=5,
        criado_em=datetime(2026, 7, 20, tzinfo=UTC),
    )
    venceu_e_pagou = _emprestimo(
        id=uuid.UUID("77000000-0000-0000-0000-000000000103"),
        dia_de_acerto=5,
        ultimo_pagamento_em=datetime(2026, 8, 6, tzinfo=UTC),
        criado_em=datetime(2026, 7, 20, tzinfo=UTC),
    )
    ainda_nao_venceu = _emprestimo(
        id=uuid.UUID("77000000-0000-0000-0000-000000000104"),
        dia_de_acerto=28,
        # Emprestado em 01/08: o primeiro acerto so cai em 28/08.
        criado_em=datetime(2026, 8, 1, tzinfo=UTC),
    )
    quitado = _emprestimo(
        id=uuid.UUID("77000000-0000-0000-0000-000000000105"),
        dia_de_acerto=5,
        estado=EmprestimoState.QUITADO,
        criado_em=datetime(2026, 7, 20, tzinfo=UTC),
    )
    uow = _FakeUoW(
        emprestimos=[
            sem_acerto,
            venceu_e_ninguem_apareceu,
            venceu_e_pagou,
            ainda_nao_venceu,
            quitado,
        ]
    )

    resultado = RelatoriosOperacionaisService(_uow_factory(uow)).resumo_carteira(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        data_referencia=date(2026, 8, 10),
    )

    # So o segundo: o primeiro nao tem dia combinado, o terceiro pagou, o quarto
    # ainda nao venceu e o quinto ja esta quitado.
    assert resultado.acertos_pendentes == 1


def test_resumo_carteira_percorre_todas_as_paginas_de_emprestimos() -> None:
    emprestimos = [
        _emprestimo(id=uuid.UUID(f"77000000-0000-0000-0001-{indice:012d}")) for indice in range(105)
    ]
    uow = _FakeUoW(emprestimos=emprestimos)

    resultado = RelatoriosOperacionaisService(_uow_factory(uow)).resumo_carteira(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        data_referencia=date(2026, 8, 10),
    )

    assert resultado.total_operacoes == 105
    assert uow.emprestimo.paginas_consultadas == [1, 2]


def test_vencimentos_lista_acertos_e_separa_pendente_de_em_dia() -> None:
    """Substitui a classificacao por parcela (DR-004).

    A situacao diz "pendente" ou "em dia", nunca "inadimplente": julgar se os
    juros do periodo foram quitados exige o saldo, e saldo e do Motor, que esta
    camada nao importa.
    """
    venceu_e_ninguem_apareceu = _emprestimo(
        id=EMPRESTIMO_ID,
        dia_de_acerto=5,
        criado_em=datetime(2026, 7, 20, tzinfo=UTC),
    )
    venceu_e_pagou = _emprestimo(
        id=uuid.UUID("77000000-0000-0000-0000-0000000000a2"),
        dia_de_acerto=5,
        ultimo_pagamento_em=datetime(2026, 8, 6, tzinfo=UTC),
        criado_em=datetime(2026, 7, 20, tzinfo=UTC),
    )
    sem_dia_combinado = _emprestimo(id=uuid.UUID("77000000-0000-0000-0000-0000000000a3"))
    uow = _FakeUoW(emprestimos=[venceu_e_ninguem_apareceu, venceu_e_pagou, sem_dia_combinado])

    resultado = RelatoriosOperacionaisService(_uow_factory(uow)).vencimentos_inadimplencia(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        data_referencia=date(2026, 8, 10),
    )

    # O sem dia combinado nao entra: nao ha acerto a cobrar dele.
    assert [item.situacao for item in resultado.itens] == ["pendente", "em dia"]
    assert resultado.itens[0].acerto_em == date(2026, 8, 5)
    assert resultado.itens[0].dias_sem_pagamento == 5
    assert resultado.itens[0].dia_de_acerto == 5
    assert resultado.itens[1].dias_sem_pagamento == 0
    assert resultado.total == 2


def test_pagamentos_encerramentos_filtra_periodo_e_ignora_estorno_no_total() -> None:
    quitado = _emprestimo(
        id=EMPRESTIMO_QUITADO_ID,
        estado=EmprestimoState.QUITADO,
        quitado_em=datetime(2026, 8, 5, 10, 0, tzinfo=UTC),
    )
    uow = _FakeUoW(
        emprestimos=[quitado],
        pagamentos=[
            _pagamento(quitado.id, valor="80.00", recebido_em=datetime(2026, 8, 5, tzinfo=UTC)),
            _pagamento(
                quitado.id,
                valor="30.00",
                recebido_em=datetime(2026, 8, 6, tzinfo=UTC),
                estado=PagamentoState.ESTORNADO,
            ),
            _pagamento(
                quitado.id,
                valor="70.00",
                recebido_em=datetime(2026, 9, 1, tzinfo=UTC),
            ),
        ],
    )

    resultado = RelatoriosOperacionaisService(_uow_factory(uow)).pagamentos_encerramentos(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        inicio=date(2026, 8, 1),
        fim=date(2026, 8, 31),
    )

    assert [item.valor_recebido for item in resultado.pagamentos] == [
        Decimal("80.00"),
        Decimal("30.00"),
    ]
    assert resultado.operacoes_quitadas == (quitado.id,)
    assert resultado.total_realizado == Decimal("80.00")


def test_fluxo_previsto_realizado_agrupa_por_dia() -> None:
    emprestimo = _emprestimo(id=EMPRESTIMO_ID)
    uow = _FakeUoW(
        emprestimos=[emprestimo],
        parcelas=[
            _parcela(emprestimo.id, numero=1, vencimento=date(2026, 8, 10), valor="100.00"),
            _parcela(emprestimo.id, numero=2, vencimento=date(2026, 8, 11), valor="120.00"),
        ],
        pagamentos=[
            _pagamento(emprestimo.id, valor="40.00", recebido_em=datetime(2026, 8, 10, tzinfo=UTC)),
            _pagamento(emprestimo.id, valor="60.00", recebido_em=datetime(2026, 8, 12, tzinfo=UTC)),
        ],
    )

    resultado = RelatoriosOperacionaisService(_uow_factory(uow)).fluxo_previsto_realizado(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        inicio=date(2026, 8, 10),
        fim=date(2026, 8, 12),
    )

    assert [(item.data, item.previsto, item.realizado) for item in resultado.itens] == [
        (date(2026, 8, 10), Decimal("100.00"), Decimal("40.00")),
        (date(2026, 8, 11), Decimal("120.00"), Decimal("0.00")),
        (date(2026, 8, 12), Decimal("0.00"), Decimal("60.00")),
    ]


def test_relatorios_rejeitam_carteira_de_outro_tenant() -> None:
    uow = _FakeUoW(carteira=Carteira(tenant_id=uuid.uuid4(), nome="Outra"))

    with pytest.raises(CarteiraNaoEncontradaError):
        RelatoriosOperacionaisService(_uow_factory(uow)).resumo_carteira(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            data_referencia=date(2026, 8, 10),
        )


def _uow_factory(uow: _FakeUoW) -> Callable[[], UnitOfWork]:
    return lambda: cast(UnitOfWork, uow)


def _emprestimo(
    *,
    id: uuid.UUID,
    estado: EmprestimoState = EmprestimoState.ATIVO,
    quitado_em: datetime | None = None,
    dia_de_acerto: int | None = None,
    ultimo_pagamento_em: datetime | None = None,
    criado_em: datetime | None = None,
) -> Emprestimo:
    emprestimo = Emprestimo(
        id=id,
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        contrato_id=CONTRATO_ID,
        principal_original=Decimal("1000.00"),
        moeda="BRL",
        _parametros_financeiros=(
            {"fonte": "motor"}
            if dia_de_acerto is None
            else {"fonte": "motor", "dia_de_acerto": dia_de_acerto}
        ),
        estado=estado,
        quitado_em=quitado_em,
        ultimo_pagamento_em=ultimo_pagamento_em,
    )
    if criado_em is not None:
        emprestimo.criado_em = criado_em
    return emprestimo


def _parcela(
    emprestimo_id: uuid.UUID,
    *,
    numero: int,
    vencimento: date,
    valor: str,
    estado: ParcelaState = ParcelaState.PREVISTA,
    valor_liquidado: str = "0.00",
) -> Parcela:
    return Parcela(
        emprestimo_id=emprestimo_id,
        numero=numero,
        vencimento=vencimento,
        valor_previsto=Decimal(valor),
        valor_liquidado=Decimal(valor_liquidado),
        estado=estado,
    )


def _pagamento(
    emprestimo_id: uuid.UUID,
    *,
    valor: str,
    recebido_em: datetime,
    estado: PagamentoState = PagamentoState.PROCESSADO,
) -> Pagamento:
    return Pagamento(
        emprestimo_id=emprestimo_id,
        valor_recebido=Decimal(valor),
        recebido_em=recebido_em,
        valor_juros=Decimal("0.00"),
        valor_amortizacao=Decimal(valor),
        estado=estado,
    )


@dataclass
class _CarteiraFakeRepository:
    carteira: Carteira | None

    def find_by_id(self, carteira_id: uuid.UUID) -> Carteira | None:
        if self.carteira is None or self.carteira.id != carteira_id:
            return None
        return self.carteira


@dataclass
class _EmprestimoFakeRepository:
    emprestimos: Sequence[Emprestimo]
    paginas_consultadas: list[int] = field(default_factory=list)

    def listar_paginado(self, _filtros: object, paginacao: object) -> EmprestimoResultadoPaginado:
        assert hasattr(paginacao, "pagina")
        assert hasattr(paginacao, "tamanho")
        pagina = cast(int, paginacao.pagina)
        tamanho = cast(int, paginacao.tamanho)
        self.paginas_consultadas.append(pagina)
        inicio = (pagina - 1) * tamanho
        fim = inicio + tamanho
        return EmprestimoResultadoPaginado(
            items=tuple(self.emprestimos[inicio:fim]),
            total=len(self.emprestimos),
            pagina=pagina,
            tamanho=tamanho,
        )


@dataclass
class _ParcelaFakeRepository:
    parcelas: Sequence[Parcela]

    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[Parcela]:
        return [item for item in self.parcelas if item.emprestimo_id == emprestimo_id]


@dataclass
class _PagamentoFakeRepository:
    pagamentos: Sequence[Pagamento]

    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[Pagamento]:
        return [item for item in self.pagamentos if item.emprestimo_id == emprestimo_id]


class _FakeUoW:
    def __init__(
        self,
        *,
        carteira: Carteira | None = None,
        emprestimos: Sequence[Emprestimo] = (),
        parcelas: Sequence[Parcela] = (),
        pagamentos: Sequence[Pagamento] = (),
    ) -> None:
        self.carteira = _CarteiraFakeRepository(
            carteira or Carteira(id=CARTEIRA_ID, tenant_id=TENANT_ID, nome="Carteira")
        )
        self.emprestimo = _EmprestimoFakeRepository(emprestimos)
        self.parcela = _ParcelaFakeRepository(parcelas)
        self.pagamento = _PagamentoFakeRepository(pagamentos)
        self.commits = 0

    def __enter__(self) -> _FakeUoW:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        return None
