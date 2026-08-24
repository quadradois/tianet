"""Testes unitarios dos servicos do Motor Financeiro (IMP-158)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import pytest

from emprestimo.application.errors import (
    ContratoCreditoNaoEncontradoError,
    EmprestimoNaoEncontradoError,
    IdempotenciaConflitoError,
    TransicaoEstadoInvalidaError,
)
from emprestimo.application.motor_financeiro import (
    ESCOPO_IDEMPOTENCIA,
    ESCOPO_IDEMPOTENCIA_RENEGOCIACAO,
    ConsultaSaldoService,
    CriacaoEmprestimoService,
    PagamentoService,
    QuitacaoRenegociacaoService,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.credit.contrato_liberado import ContratoLiberadoLogico
from emprestimo.domain.credit.emprestimo import Emprestimo, EmprestimoState
from emprestimo.domain.credit.eventos_financeiros import EventoFinanceiro
from emprestimo.domain.credit.memoria_calculo import MemoriaCalculo
from emprestimo.domain.credit.pagamento import Pagamento

TENANT_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
CARTEIRA_ID = uuid.UUID("20000000-0000-0000-0000-000000000002")
DEVEDOR_ID = uuid.UUID("20000000-0000-0000-0000-000000000003")
CONTRATO_ID = uuid.UUID("20000000-0000-0000-0000-000000000004")
PROPOSTA_ID = uuid.UUID("20000000-0000-0000-0000-000000000005")
USUARIO_ID = uuid.UUID("20000000-0000-0000-0000-000000000006")


def test_criacao_emprestimo_cria_aggregate_com_auditoria_e_commit() -> None:
    uow = _FakeUoW(contrato=_ContratoLiberado())
    auditoria = _AuditoriaFake()
    service = CriacaoEmprestimoService(
        _uow_factory(uow),
        cast(AuditoriaRegistro, auditoria),
    )

    resultado = service.criar_de_contrato(
        contrato_id=CONTRATO_ID,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        idempotency_key="emp-001",
    )

    assert resultado.estado is EmprestimoState.ATIVO
    assert resultado.principal_original == Decimal("10000.00")
    assert uow.emprestimo.salvo is not None
    assert uow.idempotencia.registros[("emp-001", ESCOPO_IDEMPOTENCIA)]["estado"] == "finished"
    assert uow.commits == 1
    assert uow.rollbacks == 0
    assert {
        "criar.inicio",
        "criar.aggregate_criado",
        "criar.evento_criado",
        "criar.sucesso",
    } <= {evento["acao"] for evento in auditoria.eventos}


def test_criacao_emprestimo_replay_idempotente_retorna_mesmo_resultado() -> None:
    uow = _FakeUoW(contrato=_ContratoLiberado())
    auditoria = _AuditoriaFake()
    service = CriacaoEmprestimoService(
        _uow_factory(uow),
        cast(AuditoriaRegistro, auditoria),
    )

    primeiro = service.criar_de_contrato(
        contrato_id=CONTRATO_ID,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        idempotency_key="emp-replay",
    )
    segundo = service.criar_de_contrato(
        contrato_id=CONTRATO_ID,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        idempotency_key="emp-replay",
    )

    assert segundo == primeiro
    assert uow.emprestimo.saves == 1
    assert uow.commits == 2


def test_criacao_emprestimo_chave_divergente_gera_conflito() -> None:
    uow = _FakeUoW(contrato=_ContratoLiberado())
    service = CriacaoEmprestimoService(
        _uow_factory(uow),
        cast(AuditoriaRegistro, _AuditoriaFake()),
    )
    service.criar_de_contrato(
        contrato_id=CONTRATO_ID,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        idempotency_key="emp-div",
    )

    with pytest.raises(IdempotenciaConflitoError):
        service.criar_de_contrato(
            contrato_id=CONTRATO_ID,
            tenant_id=TENANT_ID,
            usuario_id=uuid.uuid4(),
            idempotency_key="emp-div",
        )


def test_criacao_emprestimo_contrato_cross_tenant_responde_nao_encontrado() -> None:
    uow = _FakeUoW(contrato=_ContratoLiberado(tenant_id=uuid.uuid4()))
    service = CriacaoEmprestimoService(
        _uow_factory(uow),
        cast(AuditoriaRegistro, _AuditoriaFake()),
    )

    with pytest.raises(ContratoCreditoNaoEncontradoError):
        service.criar_de_contrato(
            contrato_id=CONTRATO_ID,
            tenant_id=TENANT_ID,
            usuario_id=USUARIO_ID,
            idempotency_key="emp-404",
        )

    assert uow.emprestimo.salvo is None
    assert uow.commits == 0
    assert uow.rollbacks == 1


def test_criacao_emprestimo_duplicado_sem_replay_gera_conflito() -> None:
    existente = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=existente)
    service = CriacaoEmprestimoService(
        _uow_factory(uow),
        cast(AuditoriaRegistro, _AuditoriaFake()),
    )

    with pytest.raises(TransicaoEstadoInvalidaError, match="ja possui emprestimo"):
        service.criar_de_contrato(
            contrato_id=CONTRATO_ID,
            tenant_id=TENANT_ID,
            usuario_id=USUARIO_ID,
            idempotency_key="emp-dup",
        )

    assert uow.emprestimo.salvo is None


def test_pagamento_service_registra_pagamento_com_memoria_evento_e_commit() -> None:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)
    uow.commits = 0

    resultado = PagamentoService(_uow_factory(uow), _auditoria()).registrar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        valor=Decimal("1000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key="pag-001",
    )

    assert resultado.valor_recebido == Decimal("1000.00")
    assert resultado.memoria is not None
    assert resultado.memoria.tipo == "pagamento"
    assert uow.pagamento.salvos[0].chave_idempotencia == "pag-001"
    assert uow.memoria_calculo.salvas[-1][2] == resultado.pagamento_id
    assert uow.evento_financeiro.salvos[0].tipo == "pagamento_registrado"
    assert uow.emprestimo.salvo is emprestimo
    assert uow.commits == 1


def test_pagamento_service_replay_por_chave_nao_duplica() -> None:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)
    service = PagamentoService(_uow_factory(uow), _auditoria())
    primeiro = service.registrar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        valor=Decimal("100.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key="pag-replay",
    )
    uow.pagamento.saves = 0

    segundo = service.registrar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        valor=Decimal("100.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key="pag-replay",
    )

    assert segundo.pagamento_id == primeiro.pagamento_id
    assert segundo.valor_recebido == primeiro.valor_recebido
    assert uow.pagamento.saves == 0


def test_pagamento_service_rejeita_replay_com_payload_divergente() -> None:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)
    service = PagamentoService(_uow_factory(uow), _auditoria())
    service.registrar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        valor=Decimal("100.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key="pag-divergente",
    )

    with pytest.raises(IdempotenciaConflitoError, match="payload divergente"):
        service.registrar(
            emprestimo_id=emprestimo.id,
            tenant_id=TENANT_ID,
            usuario_id=USUARIO_ID,
            valor=Decimal("999.00"),
            recebido_em=datetime(2026, 9, 11, 12, 0, tzinfo=UTC),
            idempotency_key="pag-divergente",
        )


def test_pagamento_service_rejeita_valor_invalido_sem_commit() -> None:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)
    uow.commits = 0

    with pytest.raises(TransicaoEstadoInvalidaError, match="positivo"):
        PagamentoService(_uow_factory(uow), _auditoria()).registrar(
            emprestimo_id=emprestimo.id,
            tenant_id=TENANT_ID,
            usuario_id=USUARIO_ID,
            valor=Decimal("0.00"),
            recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            idempotency_key="pag-zero",
        )

    assert uow.pagamento.salvos == []
    assert uow.commits == 0
    assert uow.rollbacks == 1


def test_pagamento_service_rejeita_emprestimo_quitado() -> None:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)
    emprestimo.marcar_quitado(quitado_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC))
    uow.commits = 0

    with pytest.raises(TransicaoEstadoInvalidaError, match="nao pode ser processado"):
        PagamentoService(_uow_factory(uow), _auditoria()).registrar(
            emprestimo_id=emprestimo.id,
            tenant_id=TENANT_ID,
            usuario_id=USUARIO_ID,
            valor=Decimal("100.00"),
            recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            idempotency_key="pag-quitado",
        )

    assert uow.pagamento.salvos == []
    assert uow.commits == 0


def test_consulta_saldo_retorna_componentes_e_memoria_sem_commit() -> None:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)
    PagamentoService(_uow_factory(uow), _auditoria()).registrar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        valor=Decimal("1000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key="pag-antes-saldo",
    )
    uow.commits = 0
    memorias_antes = len(uow.memoria_calculo.salvas)

    saldo = ConsultaSaldoService(_uow_factory(uow)).consultar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        data_referencia=date(2026, 10, 10),
    )

    assert saldo.principal >= Decimal("0.00")
    assert saldo.juros >= Decimal("0.00")
    assert saldo.encargos == Decimal("0.00")
    assert saldo.total == saldo.principal + saldo.juros + saldo.encargos
    assert saldo.memoria.tipo == "saldo"
    assert saldo.memoria.resultados["principal"] == str(saldo.principal)
    assert len(uow.memoria_calculo.salvas) == memorias_antes
    assert uow.commits == 0


def test_consulta_saldo_emprestimo_cross_tenant_responde_404() -> None:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)

    with pytest.raises(EmprestimoNaoEncontradoError):
        ConsultaSaldoService(_uow_factory(uow)).consultar(
            emprestimo_id=emprestimo.id,
            tenant_id=uuid.uuid4(),
            data_referencia=date(2026, 10, 10),
        )


def test_quitacao_calcula_valor_sem_commit() -> None:
    emprestimo, uow = _emprestimo_com_pagamento()
    uow.commits = 0
    memorias_antes = len(uow.memoria_calculo.salvas)

    resultado = QuitacaoRenegociacaoService(
        _uow_factory(uow), _auditoria()
    ).calcular_valor_quitacao(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        data_referencia=date(2026, 10, 10),
    )

    assert resultado.valor_quitacao.valor_total >= Decimal("0.00")
    assert resultado.memoria.tipo == "quitacao"
    assert len(uow.memoria_calculo.salvas) == memorias_antes
    assert uow.commits == 0


def test_quitacao_quita_emprestimo_preserva_memorias_e_eventos() -> None:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)
    uow.commits = 0

    resultado = QuitacaoRenegociacaoService(_uow_factory(uow), _auditoria()).quitar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        recebido_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        idempotency_key="quit-001",
    )

    assert resultado.estado is EmprestimoState.QUITADO
    assert resultado.memoria_quitacao.tipo == "quitacao"
    assert resultado.pagamento.memoria is not None
    assert resultado.pagamento.memoria.tipo == "pagamento"
    assert [memoria.tipo for memoria, _emprestimo_id, _pagamento_id in uow.memoria_calculo.salvas][
        -2:
    ] == ["quitacao", "pagamento"]
    assert {evento.tipo for evento in uow.evento_financeiro.salvos} >= {
        "pagamento_registrado",
        "emprestimo_quitado",
    }
    assert uow.emprestimo.salvo is emprestimo
    assert uow.commits == 1


def test_quitacao_replay_por_chave_nao_duplica_pagamento() -> None:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)
    service = QuitacaoRenegociacaoService(_uow_factory(uow), _auditoria())
    primeiro = service.quitar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        recebido_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        idempotency_key="quit-replay",
    )
    uow.pagamento.saves = 0

    segundo = service.quitar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        recebido_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        idempotency_key="quit-replay",
    )

    assert segundo.pagamento.pagamento_id == primeiro.pagamento.pagamento_id
    assert uow.pagamento.saves == 0


def test_quitacao_service_rejeita_replay_com_payload_divergente() -> None:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)
    service = QuitacaoRenegociacaoService(_uow_factory(uow), _auditoria())
    service.quitar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        recebido_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        idempotency_key="quit-divergente",
    )

    with pytest.raises(IdempotenciaConflitoError, match="payload divergente"):
        service.quitar(
            emprestimo_id=emprestimo.id,
            tenant_id=TENANT_ID,
            usuario_id=USUARIO_ID,
            recebido_em=datetime(2026, 10, 11, 12, 0, tzinfo=UTC),
            idempotency_key="quit-divergente",
        )


def test_renegociacao_preserva_memoria_evento_e_estado() -> None:
    emprestimo, uow = _emprestimo_com_pagamento()
    uow.commits = 0

    resultado = QuitacaoRenegociacaoService(_uow_factory(uow), _auditoria()).renegociar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        novos_parametros={"taxa_juros_mensal": "0.0150"},
        renegociado_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        idempotency_key="ren-001",
    )

    assert resultado.novos_parametros["taxa_juros_mensal"] == "0.0150"
    assert resultado.memoria.tipo == "renegociacao"
    assert uow.evento_financeiro.salvos[-1].tipo == "emprestimo_renegociado"
    assert emprestimo.estado is EmprestimoState.ATIVO
    assert uow.commits == 1


def test_renegociacao_service_replay_idempotente_e_conflito_divergente() -> None:
    emprestimo, uow = _emprestimo_com_pagamento()
    uow.commits = 0
    service = QuitacaoRenegociacaoService(_uow_factory(uow), _auditoria())
    primeiro = service.renegociar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        novos_parametros={"taxa_juros_mensal": "0.0150"},
        renegociado_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        idempotency_key="ren-replay",
    )
    total_eventos = len(uow.evento_financeiro.salvos)

    replay = service.renegociar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        novos_parametros={"taxa_juros_mensal": "0.0150"},
        renegociado_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        idempotency_key="ren-replay",
    )

    assert replay.memoria.id == primeiro.memoria.id
    assert len(uow.evento_financeiro.salvos) == total_eventos
    assert (
        uow.idempotencia.registros[("ren-replay", ESCOPO_IDEMPOTENCIA_RENEGOCIACAO)]["estado"]
        == "finished"
    )
    with pytest.raises(IdempotenciaConflitoError, match="payload divergente"):
        service.renegociar(
            emprestimo_id=emprestimo.id,
            tenant_id=TENANT_ID,
            usuario_id=USUARIO_ID,
            novos_parametros={"taxa_juros_mensal": "0.0200"},
            renegociado_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
            idempotency_key="ren-replay",
        )


def test_renegociacao_rejeita_parametros_vazios_sem_commit() -> None:
    emprestimo, uow = _emprestimo_com_pagamento()
    uow.commits = 0

    with pytest.raises(TransicaoEstadoInvalidaError, match="nao vazios"):
        QuitacaoRenegociacaoService(_uow_factory(uow), _auditoria()).renegociar(
            emprestimo_id=emprestimo.id,
            tenant_id=TENANT_ID,
            usuario_id=USUARIO_ID,
            novos_parametros={},
            renegociado_em=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
            idempotency_key="ren-vazio",
        )

    assert uow.commits == 0
    assert uow.rollbacks == 1


def _emprestimo_com_pagamento() -> tuple[Emprestimo, _FakeUoW]:
    emprestimo = Emprestimo.criar_de_contrato_liberado(_contrato_liberado_logico())
    uow = _FakeUoW(contrato=_ContratoLiberado(), emprestimo_existente=emprestimo)
    PagamentoService(_uow_factory(uow), _auditoria()).registrar(
        emprestimo_id=emprestimo.id,
        tenant_id=TENANT_ID,
        usuario_id=USUARIO_ID,
        valor=Decimal("100.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        idempotency_key="pag-helper",
    )
    return emprestimo, uow


def _auditoria() -> AuditoriaRegistro:
    return cast(AuditoriaRegistro, _AuditoriaFake())


def _uow_factory(uow: _FakeUoW) -> Callable[[], UnitOfWork]:
    return lambda: cast(UnitOfWork, uow)


def _contrato_liberado_logico(
    *,
    tenant_id: uuid.UUID = TENANT_ID,
) -> ContratoLiberadoLogico:
    return ContratoLiberadoLogico(
        contrato_id=CONTRATO_ID,
        proposta_comercial_id=PROPOSTA_ID,
        tenant_id=tenant_id,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        parametros_contratados={
            "valor_contratado": "10000.00",
            "prazo_meses": 10,
            "quantidade_parcelas": 2,
            "primeiro_vencimento": "2026-09-10",
            "taxa_juros_mensal": "0.0200",
        },
        liberado_por_usuario_id=USUARIO_ID,
        liberado_em=datetime.now(UTC),
    )


@dataclass
class _ContratoLiberado:
    tenant_id: uuid.UUID = TENANT_ID

    def gerar_saida_logica(self) -> ContratoLiberadoLogico:
        return _contrato_liberado_logico(tenant_id=self.tenant_id)


@dataclass
class _RepoId:
    value: object

    def find_by_id(self, _id: uuid.UUID) -> object:
        return self.value


@dataclass
class _EmprestimoRepo:
    existente: Emprestimo | None = None
    salvo: Emprestimo | None = None
    saves: int = 0

    def find_by_id(self, emprestimo_id: uuid.UUID) -> Emprestimo | None:
        if self.existente is not None and self.existente.id == emprestimo_id:
            return self.existente
        if self.salvo is not None and self.salvo.id == emprestimo_id:
            return self.salvo
        return None

    def find_by_contrato_id(self, _contrato_id: uuid.UUID) -> Emprestimo | None:
        return self.existente or self.salvo

    def save(self, emprestimo: Emprestimo) -> None:
        self.salvo = emprestimo
        self.saves += 1


@dataclass
class _MemoriaCalculoRepo:
    salvas: list[tuple[MemoriaCalculo, uuid.UUID, uuid.UUID | None]] = field(default_factory=list)

    def save(
        self,
        memoria: MemoriaCalculo,
        emprestimo_id: uuid.UUID,
        pagamento_id: uuid.UUID | None = None,
    ) -> None:
        self.salvas.append((memoria, emprestimo_id, pagamento_id))

    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[MemoriaCalculo]:
        return [
            memoria
            for memoria, memoria_emprestimo_id, _pagamento_id in self.salvas
            if memoria_emprestimo_id == emprestimo_id
        ]


@dataclass
class _PagamentoRepo:
    salvos: list[Pagamento] = field(default_factory=list)
    saves: int = 0

    def save(self, pagamento: Pagamento) -> None:
        self.salvos.append(pagamento)
        self.saves += 1

    def find_by_idempotency_key(
        self,
        emprestimo_id: uuid.UUID,
        chave_idempotencia: str,
    ) -> Pagamento | None:
        for pagamento in self.salvos:
            if (
                pagamento.emprestimo_id == emprestimo_id
                and pagamento.chave_idempotencia == chave_idempotencia
            ):
                return pagamento
        return None

    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[Pagamento]:
        return [pagamento for pagamento in self.salvos if pagamento.emprestimo_id == emprestimo_id]


@dataclass
class _EventoFinanceiroRepo:
    salvos: list[EventoFinanceiro] = field(default_factory=list)

    def save(self, evento: EventoFinanceiro) -> None:
        self.salvos.append(evento)

    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[EventoFinanceiro]:
        return [evento for evento in self.salvos if evento.emprestimo_id == emprestimo_id]


@dataclass
class _IdempotenciaFake:
    registros: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)

    def registrar(self, chave: str, escopo: str, solicitacao_hash: str) -> None:
        self.registros[(chave, escopo)] = {
            "estado": "processing",
            "solicitacao_hash": solicitacao_hash,
            "resultado": None,
        }

    def find_by_chave(self, chave: str, escopo: str) -> dict[str, Any] | None:
        return self.registros.get((chave, escopo))

    def concluir(self, chave: str, escopo: str, resultado: str) -> None:
        self.registros[(chave, escopo)]["estado"] = "finished"
        self.registros[(chave, escopo)]["resultado"] = resultado


@dataclass
class _FakeUoW:
    contrato: object
    emprestimo_existente: Emprestimo | None = None
    commits: int = 0
    rollbacks: int = 0
    closed: bool = False
    contrato_credito: _RepoId = field(init=False)
    usuario: _RepoId = field(init=False)
    emprestimo: _EmprestimoRepo = field(init=False)
    pagamento: _PagamentoRepo = field(default_factory=_PagamentoRepo)
    memoria_calculo: _MemoriaCalculoRepo = field(default_factory=_MemoriaCalculoRepo)
    evento_financeiro: _EventoFinanceiroRepo = field(default_factory=_EventoFinanceiroRepo)
    idempotencia: _IdempotenciaFake = field(default_factory=_IdempotenciaFake)

    def __post_init__(self) -> None:
        self.contrato_credito = _RepoId(self.contrato)
        self.usuario = _RepoId(_EntidadeTenant(id=USUARIO_ID, tenant_id=TENANT_ID))
        self.emprestimo = _EmprestimoRepo(self.emprestimo_existente)

    def __enter__(self) -> _FakeUoW:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            self.rollback()
        self.close()

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


@dataclass(frozen=True)
class _EntidadeTenant:
    id: uuid.UUID
    tenant_id: uuid.UUID


@dataclass
class _AuditoriaFake:
    eventos: list[dict[str, object]] = field(default_factory=list)

    def registrar(
        self,
        entidade: str,
        entidade_id: uuid.UUID | None,
        acao: str,
        status: str,
        detalhes: str | None = None,
    ) -> None:
        self.eventos.append(
            {
                "entidade": entidade,
                "entidade_id": entidade_id,
                "acao": acao,
                "status": status,
                "detalhes": detalhes,
            }
        )
