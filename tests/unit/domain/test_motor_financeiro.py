"""Testes unitarios do Motor Financeiro (IMP-146, EPIC-005)."""

from __future__ import annotations

import importlib
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contrato_liberado import ContratoLiberadoLogico

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CARTEIRA_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEVEDOR_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
CONTRATO_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
PROPOSTA_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
USUARIO_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")


def _classe(modulo: str, nome: str) -> Any:
    return getattr(importlib.import_module(modulo), nome)


def _contrato_liberado(
    *,
    valor: str = "10000.00",
    taxa_mensal: str = "0.0200",
    parcelas: int = 10,
) -> ContratoLiberadoLogico:
    return ContratoLiberadoLogico(
        contrato_id=CONTRATO_ID,
        proposta_comercial_id=PROPOSTA_ID,
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        parametros_contratados={
            "valor_contratado": valor,
            "moeda": "BRL",
            "taxa_juros_mensal": taxa_mensal,
            "quantidade_parcelas": parcelas,
            "primeiro_vencimento": "2026-09-10",
            "regra_calculo": "juros_simples_periodo_real",
        },
        liberado_por_usuario_id=USUARIO_ID,
        liberado_em=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
    )


def test_cria_emprestimo_somente_a_partir_de_contrato_liberado() -> None:
    emprestimo_cls = _classe("emprestimo.domain.credit.emprestimo", "Emprestimo")

    emprestimo = emprestimo_cls.criar_de_contrato_liberado(_contrato_liberado())

    assert emprestimo.id is not None
    assert emprestimo.tenant_id == TENANT_ID
    assert emprestimo.carteira_id == CARTEIRA_ID
    assert emprestimo.devedor_id == DEVEDOR_ID
    assert emprestimo.contrato_id == CONTRATO_ID
    assert emprestimo.principal_original == Decimal("10000.00")
    assert emprestimo.moeda == "BRL"
    assert emprestimo.estado.value == "ativo"
    assert emprestimo.eventos[0].tipo == "emprestimo_criado"


def test_rejeita_criacao_de_emprestimo_sem_contrato_liberado() -> None:
    emprestimo_cls = _classe("emprestimo.domain.credit.emprestimo", "Emprestimo")

    with pytest.raises(ViolacaoInvarianteError) as exc:
        emprestimo_cls.criar_de_contrato_liberado(None)

    assert exc.value.codigo == "EPIC-005"


def test_snapshot_do_contrato_liberado_nao_vaza_mutacao_para_emprestimo() -> None:
    emprestimo_cls = _classe("emprestimo.domain.credit.emprestimo", "Emprestimo")
    contrato = _contrato_liberado()

    emprestimo = emprestimo_cls.criar_de_contrato_liberado(contrato)

    with pytest.raises(TypeError):
        contrato.parametros_contratados["valor_contratado"] = "5000.00"  # type: ignore[index]
    assert emprestimo.parametros_financeiros["valor_contratado"] == "10000.00"


def test_pagamento_registra_distribuicao_processada_pelo_motor() -> None:
    pagamento_cls = _classe("emprestimo.domain.credit.pagamento", "Pagamento")

    pagamento = pagamento_cls(
        emprestimo_id=CONTRATO_ID,
        valor_recebido=Decimal("1000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        valor_juros=Decimal("100.00"),
        valor_amortizacao=Decimal("900.00"),
        chave_idempotencia="pag-001",
        usuario_id=USUARIO_ID,
    )

    assert pagamento.id is not None
    assert pagamento.estado.value == "processado"
    assert pagamento.valor_distribuido == Decimal("1000.00")


def test_pagamento_rejeita_valor_zero_ou_distribuicao_maior_que_recebido() -> None:
    pagamento_cls = _classe("emprestimo.domain.credit.pagamento", "Pagamento")

    with pytest.raises(ViolacaoInvarianteError) as exc:
        pagamento_cls(
            emprestimo_id=CONTRATO_ID,
            valor_recebido=Decimal("0.00"),
            recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            valor_juros=Decimal("0.00"),
            valor_amortizacao=Decimal("0.00"),
        )
    assert exc.value.codigo == "EPIC-005"

    with pytest.raises(ViolacaoInvarianteError):
        pagamento_cls(
            emprestimo_id=CONTRATO_ID,
            valor_recebido=Decimal("100.00"),
            recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            valor_juros=Decimal("50.00"),
            valor_amortizacao=Decimal("60.00"),
        )


def test_periodo_financeiro_usa_datas_reais() -> None:
    periodo_cls = _classe("emprestimo.domain.credit.financeiro", "PeriodoFinanceiro")

    periodo = periodo_cls(
        data_inicio=date(2026, 1, 31),
        data_fim=date(2026, 2, 28),
    )

    assert periodo.dias == 28


def test_periodo_financeiro_rejeita_intervalo_invalido() -> None:
    periodo_cls = _classe("emprestimo.domain.credit.financeiro", "PeriodoFinanceiro")

    with pytest.raises(ViolacaoInvarianteError) as exc:
        periodo_cls(
            data_inicio=date(2026, 2, 28),
            data_fim=date(2026, 2, 28),
        )

    assert exc.value.codigo == "EPIC-005"


def test_taxa_juros_usa_decimal_e_periodicidade_explicita() -> None:
    taxa_cls = _classe("emprestimo.domain.credit.financeiro", "TaxaJuros")

    taxa = taxa_cls.de_percentual(
        percentual=Decimal("2.50"),
        periodicidade="mensal",
    )

    assert taxa.valor == Decimal("0.025")
    assert taxa.periodicidade == "mensal"


def test_taxa_juros_rejeita_float_ou_periodicidade_vazia() -> None:
    taxa_cls = _classe("emprestimo.domain.credit.financeiro", "TaxaJuros")

    with pytest.raises(ViolacaoInvarianteError):
        taxa_cls(valor=0.02, periodicidade="mensal")
    with pytest.raises(ViolacaoInvarianteError):
        taxa_cls(valor=Decimal("0.02"), periodicidade="")


def test_regra_calculo_preserva_tipo_parametros_e_versao() -> None:
    modulo = importlib.import_module("emprestimo.domain.credit.financeiro")

    regra = modulo.RegraCalculo(
        tipo=modulo.TipoRegraCalculo.JUROS_SIMPLES_PERIODO_REAL,
        parametros={"base": "dias_reais"},
        versao="1.0.0",
    )

    assert regra.tipo.value == "juros_simples_periodo_real"
    assert regra.parametros["base"] == "dias_reais"
    assert regra.versao == "1.0.0"


def test_valor_quitacao_exige_decimal_componentes_e_data_referencia() -> None:
    valor_quitacao_cls = _classe("emprestimo.domain.credit.financeiro", "ValorQuitacao")

    valor = valor_quitacao_cls(
        valor_total=Decimal("1050.00"),
        moeda="BRL",
        data_referencia=date(2026, 9, 10),
        componentes={
            "principal": Decimal("1000.00"),
            "juros": Decimal("50.00"),
        },
    )

    assert valor.valor_total == Decimal("1050.00")
    assert valor.componentes["principal"] == Decimal("1000.00")


def test_valor_quitacao_rejeita_componentes_inconsistentes() -> None:
    valor_quitacao_cls = _classe("emprestimo.domain.credit.financeiro", "ValorQuitacao")

    with pytest.raises(ViolacaoInvarianteError) as exc:
        valor_quitacao_cls(
            valor_total=Decimal("1050.00"),
            moeda="BRL",
            data_referencia=date(2026, 9, 10),
            componentes={
                "principal": Decimal("1000.00"),
                "juros": Decimal("40.00"),
            },
        )

    assert exc.value.codigo == "EPIC-005"


def test_memoria_calculo_formaliza_regra_passos_e_resultados() -> None:
    memoria_cls = _classe("emprestimo.domain.credit.memoria_calculo", "MemoriaCalculo")
    passo_cls = _classe("emprestimo.domain.credit.memoria_calculo", "PassoCalculo")
    entradas = {"principal": "1000.00"}

    memoria = memoria_cls(
        tipo="saldo",
        entradas=entradas,
        regra={"tipo": "juros_simples_periodo_real", "versao": "1.0.0"},
        periodos=({"data_inicio": "2026-08-10", "data_fim": "2026-09-10"},),
        passos=(
            passo_cls(
                nome="apurar_juros",
                entradas={"taxa": "0.0200"},
                saidas={"juros": "20.00"},
                arredondamento="ROUND_HALF_UP:0.01",
            ),
        ),
        arredondamentos=("ROUND_HALF_UP:0.01",),
        resultados={"total": "1020.00"},
    )

    entradas["principal"] = "1.00"

    assert memoria.tipo == "saldo"
    assert memoria.entradas["principal"] == "1000.00"
    assert memoria.regra["tipo"] == "juros_simples_periodo_real"
    assert memoria.periodos[0]["data_fim"] == "2026-09-10"
    assert memoria.passos[0].nome == "apurar_juros"
    assert memoria.arredondamentos == ("ROUND_HALF_UP:0.01",)
    assert memoria.resultados["total"] == "1020.00"


def test_memoria_calculo_rejeita_passos_invalidos() -> None:
    memoria_cls = _classe("emprestimo.domain.credit.memoria_calculo", "MemoriaCalculo")

    with pytest.raises(ViolacaoInvarianteError) as exc:
        memoria_cls(
            tipo="saldo",
            entradas={},
            regra={"tipo": "juros_simples_periodo_real"},
            passos=({"nome": "passo_em_dict"},),
        )

    assert exc.value.codigo == "EPIC-005"


def test_registra_pagamento_positivo_e_distribui_juros_antes_da_amortizacao() -> None:
    emprestimo_cls = _classe("emprestimo.domain.credit.emprestimo", "Emprestimo")
    motor_cls = _classe("emprestimo.domain.credit.motor_financeiro", "MotorFinanceiro")
    emprestimo = emprestimo_cls.criar_de_contrato_liberado(_contrato_liberado(parcelas=2))
    motor = motor_cls()

    resultado = motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=Decimal("1200.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        chave_idempotencia="pag-001",
        usuario_id=USUARIO_ID,
    )

    assert resultado.pagamento.valor_recebido == Decimal("1200.00")
    assert resultado.pagamento.valor_juros >= Decimal("0.00")
    assert resultado.pagamento.valor_amortizacao > Decimal("0.00")
    assert resultado.pagamento.valor_juros + resultado.pagamento.valor_amortizacao <= Decimal(
        "1200.00"
    )
    assert resultado.memoria.tipo == "pagamento"
    assert [passo.nome for passo in resultado.memoria.passos] == [
        "distribuir_juros",
        "distribuir_encargos",
        "amortizar_principal",
    ]
    assert resultado.evento.tipo == "pagamento_registrado"
    assert resultado.evento.memoria_calculo_id == resultado.memoria.id
    assert resultado.evento.pagamento_id == resultado.pagamento.id
    assert emprestimo.eventos[-1].tipo == "pagamento_registrado"


def test_rejeita_pagamento_zero_ou_negativo() -> None:
    emprestimo_cls = _classe("emprestimo.domain.credit.emprestimo", "Emprestimo")
    motor_cls = _classe("emprestimo.domain.credit.motor_financeiro", "MotorFinanceiro")
    emprestimo = emprestimo_cls.criar_de_contrato_liberado(_contrato_liberado())

    with pytest.raises(ViolacaoInvarianteError) as exc:
        motor_cls().registrar_pagamento(
            emprestimo=emprestimo,
            valor=Decimal("0.00"),
            recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
            chave_idempotencia="pag-zero",
            usuario_id=USUARIO_ID,
        )

    assert exc.value.codigo == "EPIC-005"


def test_pagamento_idempotente_nao_altera_saldo_duas_vezes() -> None:
    emprestimo_cls = _classe("emprestimo.domain.credit.emprestimo", "Emprestimo")
    motor_cls = _classe("emprestimo.domain.credit.motor_financeiro", "MotorFinanceiro")
    emprestimo = emprestimo_cls.criar_de_contrato_liberado(_contrato_liberado())
    motor = motor_cls()

    primeiro = motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=Decimal("1000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        chave_idempotencia="pag-duplicado",
        usuario_id=USUARIO_ID,
    )
    segundo = motor.registrar_pagamento(
        emprestimo=emprestimo,
        valor=Decimal("1000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        chave_idempotencia="pag-duplicado",
        usuario_id=USUARIO_ID,
    )

    assert segundo.pagamento.id == primeiro.pagamento.id
    saldo = motor.consultar_saldo(
        emprestimo=emprestimo,
        data_referencia=date(2026, 9, 10),
    )
    assert saldo.total == emprestimo.principal_original - primeiro.pagamento.valor_amortizacao


def test_consulta_saldo_retorna_componentes_e_memoria_de_calculo() -> None:
    emprestimo_cls = _classe("emprestimo.domain.credit.emprestimo", "Emprestimo")
    motor_cls = _classe("emprestimo.domain.credit.motor_financeiro", "MotorFinanceiro")
    emprestimo = emprestimo_cls.criar_de_contrato_liberado(_contrato_liberado())

    saldo = motor_cls().consultar_saldo(
        emprestimo=emprestimo,
        data_referencia=date(2026, 9, 10),
    )

    assert saldo.principal >= Decimal("0.00")
    assert saldo.juros >= Decimal("0.00")
    assert saldo.encargos >= Decimal("0.00")
    assert saldo.total == saldo.principal + saldo.juros + saldo.encargos
    assert saldo.memoria.tipo == "saldo"
    assert saldo.memoria.regra["taxa_juros_mensal"] == "0.0200"
    assert saldo.memoria.passos[0].nome == "abater_amortizacoes"


def test_calcula_valor_para_quitacao_sem_alterar_estado() -> None:
    emprestimo_cls = _classe("emprestimo.domain.credit.emprestimo", "Emprestimo")
    motor_cls = _classe("emprestimo.domain.credit.motor_financeiro", "MotorFinanceiro")
    emprestimo = emprestimo_cls.criar_de_contrato_liberado(_contrato_liberado())

    quitacao = motor_cls().calcular_valor_quitacao(
        emprestimo=emprestimo,
        data_referencia=date(2026, 9, 10),
    )

    assert quitacao.valor_total > Decimal("0.00")
    assert quitacao.memoria.tipo == "quitacao"
    assert quitacao.memoria.passos[-1].nome == "somar_componentes_quitacao"
    assert emprestimo.estado.value == "ativo"


def test_quita_emprestimo_e_bloqueia_novo_pagamento() -> None:
    emprestimo_cls = _classe("emprestimo.domain.credit.emprestimo", "Emprestimo")
    motor_cls = _classe("emprestimo.domain.credit.motor_financeiro", "MotorFinanceiro")
    emprestimo = emprestimo_cls.criar_de_contrato_liberado(_contrato_liberado())
    motor = motor_cls()

    motor.quitar(
        emprestimo=emprestimo,
        valor=Decimal("12000.00"),
        recebido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        chave_idempotencia="quitacao-001",
        usuario_id=USUARIO_ID,
    )

    assert emprestimo.estado.value == "quitado"
    assert emprestimo.eventos[-1].tipo == "emprestimo_quitado"
    assert emprestimo.eventos[-1].estado_anterior.value == "ativo"
    assert emprestimo.eventos[-1].estado_posterior.value == "quitado"
    with pytest.raises(ViolacaoInvarianteError) as exc:
        motor.registrar_pagamento(
            emprestimo=emprestimo,
            valor=Decimal("10.00"),
            recebido_em=datetime(2026, 9, 11, 12, 0, tzinfo=UTC),
            chave_idempotencia="pag-pos-quitacao",
            usuario_id=USUARIO_ID,
        )

    assert exc.value.codigo == "EPIC-005"


def test_renegociacao_preserva_trilha_da_operacao_original() -> None:
    emprestimo_cls = _classe("emprestimo.domain.credit.emprestimo", "Emprestimo")
    motor_cls = _classe("emprestimo.domain.credit.motor_financeiro", "MotorFinanceiro")
    emprestimo = emprestimo_cls.criar_de_contrato_liberado(_contrato_liberado())

    renegociacao = motor_cls().renegociar(
        emprestimo=emprestimo,
        novos_parametros={
            "valor_contratado": "8500.00",
            "taxa_juros_mensal": "0.0180",
            "quantidade_parcelas": 8,
        },
        usuario_id=USUARIO_ID,
        renegociado_em=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
    )

    assert renegociacao.emprestimo_original_id == emprestimo.id
    assert renegociacao.novos_parametros["valor_contratado"] == "8500.00"
    assert renegociacao.memoria.tipo == "renegociacao"
    assert renegociacao.evento.memoria_calculo_id == renegociacao.memoria.id
    assert emprestimo.eventos[-1].tipo == "emprestimo_renegociado"


def test_eventos_financeiros_serializam_para_auditoria() -> None:
    evento_cls = _classe(
        "emprestimo.domain.credit.eventos_financeiros",
        "EmprestimoQuitado",
    )
    estado_cls = _classe("emprestimo.domain.credit.emprestimo", "EmprestimoState")
    evento = evento_cls(
        emprestimo_id=CONTRATO_ID,
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        usuario_id=USUARIO_ID,
        tipo="emprestimo_quitado",
        ocorrido_em=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        memoria_calculo_id=uuid.UUID("77777777-7777-7777-7777-777777777777"),
        pagamento_id=uuid.UUID("88888888-8888-8888-8888-888888888888"),
        estado_anterior=estado_cls.ATIVO,
        estado_posterior=estado_cls.QUITADO,
        valor=Decimal("12000.00"),
        detalhes={"origem": "quitacao"},
    )

    audit = evento.to_audit_dict()

    assert audit["evento"] == "EmprestimoQuitado"
    assert audit["tipo"] == "emprestimo_quitado"
    assert audit["estado_anterior"] == "ativo"
    assert audit["estado_posterior"] == "quitado"
    assert audit["valor"] == "12000.00"
    assert audit["detalhes"] == {"origem": "quitacao"}
