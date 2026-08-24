"""Motor Financeiro (IMP-152, EPIC-005)."""

from __future__ import annotations

import calendar
import copy
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.emprestimo import Emprestimo, EmprestimoState
from emprestimo.domain.credit.eventos_financeiros import (
    EmprestimoQuitado,
    EmprestimoRenegociado,
    PagamentoRegistrado,
)
from emprestimo.domain.credit.financeiro import PeriodoFinanceiro, ValorQuitacao
from emprestimo.domain.credit.memoria_calculo import MemoriaCalculo, PassoCalculo
from emprestimo.domain.credit.pagamento import Pagamento

__all__ = [
    "MemoriaCalculo",
    "MotorFinanceiro",
    "QuitacaoCalculada",
    "RenegociacaoFinanceira",
    "ResultadoPagamento",
    "SaldoFinanceiro",
]

CENTAVO = Decimal("0.01")


@dataclass(frozen=True)
class ResultadoPagamento:
    pagamento: Pagamento
    memoria: MemoriaCalculo
    evento: PagamentoRegistrado


@dataclass(frozen=True)
class SaldoFinanceiro:
    principal: Decimal
    juros: Decimal
    encargos: Decimal
    memoria: MemoriaCalculo

    @property
    def total(self) -> Decimal:
        return self.principal + self.juros + self.encargos


@dataclass(frozen=True)
class QuitacaoCalculada:
    valor_quitacao: ValorQuitacao
    memoria: MemoriaCalculo

    @property
    def valor_total(self) -> Decimal:
        return self.valor_quitacao.valor_total


@dataclass(frozen=True)
class RenegociacaoFinanceira:
    emprestimo_original_id: uuid.UUID
    novos_parametros: Mapping[str, object]
    memoria: MemoriaCalculo
    evento: EmprestimoRenegociado

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "novos_parametros",
            copy.deepcopy(dict(self.novos_parametros)),
        )


class MotorFinanceiro:
    """Unica superficie de calculo definitivo do dominio financeiro."""

    def __init__(self) -> None:
        self._pagamentos_por_emprestimo: dict[uuid.UUID, list[Pagamento]] = {}
        self._pagamentos_por_chave: dict[tuple[uuid.UUID, str], ResultadoPagamento] = {}

    def carregar_historico(
        self,
        *,
        emprestimo_id: uuid.UUID,
        pagamentos: Sequence[Pagamento] = (),
    ) -> None:
        """Carrega fatos persistidos para processar novas operacoes financeiras."""

        _validar_uuid("emprestimo_id", emprestimo_id)
        self._pagamentos_por_emprestimo[emprestimo_id] = list(pagamentos)

    def registrar_pagamento(
        self,
        *,
        emprestimo: Emprestimo,
        valor: Decimal,
        recebido_em: datetime,
        chave_idempotencia: str,
        usuario_id: uuid.UUID,
    ) -> ResultadoPagamento:
        self._validar_emprestimo_ativo(emprestimo)
        _validar_decimal("valor", valor)
        if valor <= Decimal("0.00"):
            raise ViolacaoInvarianteError("EPIC-005", "valor do pagamento deve ser positivo")
        if not chave_idempotencia:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "chave_idempotencia nao pode ser vazia",
            )
        _validar_uuid("usuario_id", usuario_id)
        chave = (emprestimo.id, chave_idempotencia)
        if chave in self._pagamentos_por_chave:
            return self._pagamentos_por_chave[chave]

        saldo = self.consultar_saldo(
            emprestimo=emprestimo,
            data_referencia=recebido_em.date(),
        )
        valor_juros = min(valor, saldo.juros)
        remanescente = valor - valor_juros
        valor_encargos = min(remanescente, saldo.encargos)
        remanescente -= valor_encargos
        valor_amortizacao = min(remanescente, saldo.principal)
        valor_devolvido = remanescente - valor_amortizacao
        pagamento = Pagamento(
            emprestimo_id=emprestimo.id,
            valor_recebido=valor,
            recebido_em=recebido_em,
            valor_juros=_quantizar(valor_juros),
            valor_amortizacao=_quantizar(valor_amortizacao),
            valor_encargos=_quantizar(valor_encargos),
            valor_devolvido=_quantizar(valor_devolvido),
            chave_idempotencia=chave_idempotencia,
            usuario_id=usuario_id,
        )
        self._pagamentos_por_emprestimo.setdefault(emprestimo.id, []).append(pagamento)
        emprestimo.ultimo_pagamento_em = recebido_em
        emprestimo.ultimo_processamento_em = recebido_em
        emprestimo.atualizado_em = datetime.now(UTC)
        memoria = self._memoria_pagamento(
            emprestimo=emprestimo,
            pagamento=pagamento,
            saldo=saldo,
            valor=valor,
            valor_juros=valor_juros,
            remanescente=remanescente,
        )
        evento = PagamentoRegistrado(
            emprestimo_id=emprestimo.id,
            tenant_id=emprestimo.tenant_id,
            carteira_id=emprestimo.carteira_id,
            devedor_id=emprestimo.devedor_id,
            usuario_id=usuario_id,
            tipo="pagamento_registrado",
            ocorrido_em=recebido_em,
            memoria_calculo_id=memoria.id,
            pagamento_id=pagamento.id,
            valor=pagamento.valor_recebido,
            detalhes={
                "valor_juros": str(pagamento.valor_juros),
                "valor_amortizacao": str(pagamento.valor_amortizacao),
                "valor_encargos": str(pagamento.valor_encargos),
                "valor_devolvido": str(pagamento.valor_devolvido),
            },
        )
        emprestimo.registrar_evento(evento)
        resultado = ResultadoPagamento(
            pagamento=pagamento,
            memoria=memoria,
            evento=evento,
        )
        self._pagamentos_por_chave[chave] = resultado
        return resultado

    def consultar_saldo(
        self,
        *,
        emprestimo: Emprestimo,
        data_referencia: date,
    ) -> SaldoFinanceiro:
        if not isinstance(emprestimo, Emprestimo):
            raise ViolacaoInvarianteError("EPIC-005", "emprestimo deve ser Emprestimo")
        if not isinstance(data_referencia, date):
            raise ViolacaoInvarianteError("EPIC-005", "data_referencia deve ser date")
        amortizado = sum(
            (pagamento.valor_amortizacao for pagamento in self._pagamentos(emprestimo.id)),
            Decimal("0.00"),
        )
        juros_pago = sum(
            (pagamento.valor_juros for pagamento in self._pagamentos(emprestimo.id)),
            Decimal("0.00"),
        )
        principal = max(emprestimo.principal_original - amortizado, Decimal("0.00"))
        juros = max(
            self._juros_acumulado(emprestimo, data_referencia) - juros_pago,
            Decimal("0.00"),
        )
        encargos = Decimal("0.00")
        return SaldoFinanceiro(
            principal=_quantizar(principal),
            juros=_quantizar(juros),
            encargos=encargos,
            memoria=MemoriaCalculo(
                tipo="saldo",
                entradas={
                    "emprestimo_id": str(emprestimo.id),
                    "data_referencia": data_referencia.isoformat(),
                },
                regra=_regra_memoria(emprestimo.parametros_financeiros),
                periodos=(
                    {
                        "data_inicio": emprestimo.criado_em.date().isoformat(),
                        "data_fim": data_referencia.isoformat(),
                    },
                ),
                passos=(
                    PassoCalculo(
                        nome="abater_amortizacoes",
                        entradas={
                            "principal_original": str(emprestimo.principal_original),
                            "amortizado": str(amortizado),
                        },
                        saidas={"principal": str(_quantizar(principal))},
                        arredondamento="ROUND_HALF_UP:0.01",
                    ),
                    PassoCalculo(
                        nome="apurar_juros",
                        entradas={
                            "principal": str(_quantizar(principal)),
                            "juros_pago": str(juros_pago),
                        },
                        saidas={"juros": str(_quantizar(juros))},
                        arredondamento="ROUND_HALF_UP:0.01",
                    ),
                ),
                arredondamentos=("ROUND_HALF_UP:0.01",),
                resultados={
                    "principal": str(_quantizar(principal)),
                    "juros": str(_quantizar(juros)),
                    "encargos": str(encargos),
                },
            ),
        )

    def calcular_valor_quitacao(
        self,
        *,
        emprestimo: Emprestimo,
        data_referencia: date,
    ) -> QuitacaoCalculada:
        saldo = self.consultar_saldo(
            emprestimo=emprestimo,
            data_referencia=data_referencia,
        )
        valor_quitacao = ValorQuitacao(
            valor_total=saldo.total,
            moeda=emprestimo.moeda,
            data_referencia=data_referencia,
            componentes={
                "principal": saldo.principal,
                "juros": saldo.juros,
                "encargos": saldo.encargos,
            },
        )
        return QuitacaoCalculada(
            valor_quitacao=valor_quitacao,
            memoria=MemoriaCalculo(
                tipo="quitacao",
                entradas=saldo.memoria.entradas,
                regra=saldo.memoria.regra,
                periodos=saldo.memoria.periodos,
                passos=(
                    *saldo.memoria.passos,
                    PassoCalculo(
                        nome="somar_componentes_quitacao",
                        entradas={
                            "principal": str(saldo.principal),
                            "juros": str(saldo.juros),
                            "encargos": str(saldo.encargos),
                        },
                        saidas={"valor_total": str(valor_quitacao.valor_total)},
                        arredondamento="ROUND_HALF_UP:0.01",
                    ),
                ),
                arredondamentos=saldo.memoria.arredondamentos,
                resultados={"valor_total": str(valor_quitacao.valor_total)},
            ),
        )

    def quitar(
        self,
        *,
        emprestimo: Emprestimo,
        valor: Decimal,
        recebido_em: datetime,
        chave_idempotencia: str,
        usuario_id: uuid.UUID,
    ) -> ResultadoPagamento:
        estado_anterior = emprestimo.estado
        resultado = self.registrar_pagamento(
            emprestimo=emprestimo,
            valor=valor,
            recebido_em=recebido_em,
            chave_idempotencia=chave_idempotencia,
            usuario_id=usuario_id,
        )
        if emprestimo.estado is EmprestimoState.ATIVO:
            emprestimo.marcar_quitado(quitado_em=recebido_em)
            evento = EmprestimoQuitado(
                emprestimo_id=emprestimo.id,
                tenant_id=emprestimo.tenant_id,
                carteira_id=emprestimo.carteira_id,
                devedor_id=emprestimo.devedor_id,
                usuario_id=usuario_id,
                tipo="emprestimo_quitado",
                ocorrido_em=recebido_em,
                memoria_calculo_id=resultado.memoria.id,
                pagamento_id=resultado.pagamento.id,
                estado_anterior=estado_anterior,
                estado_posterior=emprestimo.estado,
                valor=valor,
            )
            emprestimo.registrar_evento(evento)
        return resultado

    def renegociar(
        self,
        *,
        emprestimo: Emprestimo,
        novos_parametros: Mapping[str, object],
        usuario_id: uuid.UUID,
        renegociado_em: datetime,
    ) -> RenegociacaoFinanceira:
        self._validar_emprestimo_ativo(emprestimo)
        if not isinstance(novos_parametros, Mapping) or not novos_parametros:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                "novos_parametros devem ser mapeaveis e nao vazios",
            )
        memoria = MemoriaCalculo(
            tipo="renegociacao",
            entradas={
                "emprestimo_id": str(emprestimo.id),
                "usuario_id": str(usuario_id),
                "renegociado_em": renegociado_em.isoformat(),
            },
            regra={
                "tipo": "renegociacao_parametros",
                "versao": "1.0.0",
            },
            passos=(
                PassoCalculo(
                    nome="registrar_novos_parametros",
                    entradas={"parametros_anteriores": emprestimo.parametros_financeiros},
                    saidas={"novos_parametros": copy.deepcopy(dict(novos_parametros))},
                ),
            ),
            resultados={"novos_parametros": copy.deepcopy(dict(novos_parametros))},
        )
        evento = EmprestimoRenegociado(
            emprestimo_id=emprestimo.id,
            tenant_id=emprestimo.tenant_id,
            carteira_id=emprestimo.carteira_id,
            devedor_id=emprestimo.devedor_id,
            usuario_id=usuario_id,
            tipo="emprestimo_renegociado",
            ocorrido_em=renegociado_em,
            memoria_calculo_id=memoria.id,
            estado_anterior=emprestimo.estado,
            estado_posterior=emprestimo.estado,
            detalhes={"novos_parametros": copy.deepcopy(dict(novos_parametros))},
        )
        emprestimo.registrar_evento(evento)
        return RenegociacaoFinanceira(
            emprestimo_original_id=emprestimo.id,
            novos_parametros=novos_parametros,
            memoria=memoria,
            evento=evento,
        )

    def _validar_emprestimo_ativo(self, emprestimo: Emprestimo) -> None:
        if not isinstance(emprestimo, Emprestimo):
            raise ViolacaoInvarianteError("EPIC-005", "emprestimo deve ser Emprestimo")
        if emprestimo.estado is not EmprestimoState.ATIVO:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                f"emprestimo em {emprestimo.estado.value} nao pode ser processado",
            )

    def _pagamentos(self, emprestimo_id: uuid.UUID) -> tuple[Pagamento, ...]:
        return tuple(self._pagamentos_por_emprestimo.get(emprestimo_id, ()))

    def _juros_acumulado(
        self,
        emprestimo: Emprestimo,
        data_referencia: date,
    ) -> Decimal:
        """Juros acumulados desde a origem, trecho a trecho (DR-004).

        A acumulacao anterior media sempre da criacao ate a data de referencia
        aplicando o saldo **atual** sobre **todo** o periodo decorrido. Cada
        amortizacao devolvia retroativamente juros ja corretamente cobrados: um
        emprestimo de 10.000 que amortizou 4.500 passava a ser cobrado como se
        sempre tivesse sido de 5.500.

        O periodo e quebrado em dois marcos, e so nestes dois:

        - **cada pagamento**, porque muda o saldo sobre o qual a taxa incide;
        - **cada virada de mes**, porque muda a base de normalizacao da regra
          (`DOMAIN-030`: o periodo e medido pelos dias do mes a que pertence).

        Sem o segundo marco, dois meses cheios de um emprestimo sem pagamento
        nenhum custavam 983,87 em vez de 1.000,00, por normalizar setembro pela
        regua de agosto.
        """
        inicio = emprestimo.criado_em.date()
        if data_referencia <= inicio:
            return Decimal("0.00")

        amortizado_em: dict[date, Decimal] = {}
        for pagamento in self._pagamentos(emprestimo.id):
            recebido = pagamento.recebido_em.date()
            if inicio < recebido <= data_referencia:
                amortizado_em[recebido] = (
                    amortizado_em.get(recebido, Decimal("0.00")) + pagamento.valor_amortizacao
                )

        marcos = sorted(
            set(amortizado_em) | set(_viradas_de_mes(inicio, data_referencia)) | {data_referencia}
        )
        taxa = _taxa_mensal(emprestimo.parametros_financeiros)
        saldo = emprestimo.principal_original
        acumulado = Decimal("0.00")
        atual = inicio
        for marco in marcos:
            if marco <= atual:
                continue
            if saldo > Decimal("0.00"):
                acumulado += _calcular_juros(
                    principal=saldo,
                    taxa_mensal=taxa,
                    periodo=PeriodoFinanceiro(data_inicio=atual, data_fim=marco),
                )
            # A amortizacao do dia reduz o saldo depois de cobrado o trecho que
            # termina nele: quem pagou hoje deve os juros ate hoje.
            saldo = max(saldo - amortizado_em.get(marco, Decimal("0.00")), Decimal("0.00"))
            atual = marco
        return _quantizar(acumulado)

    def _memoria_pagamento(
        self,
        *,
        emprestimo: Emprestimo,
        pagamento: Pagamento,
        saldo: SaldoFinanceiro,
        valor: Decimal,
        valor_juros: Decimal,
        remanescente: Decimal,
    ) -> MemoriaCalculo:
        return MemoriaCalculo(
            tipo="pagamento",
            entradas={
                "emprestimo_id": str(emprestimo.id),
                "pagamento_id": str(pagamento.id),
                "valor": str(valor),
                "recebido_em": pagamento.recebido_em.isoformat(),
            },
            regra=_regra_memoria(emprestimo.parametros_financeiros),
            passos=(
                PassoCalculo(
                    nome="distribuir_juros",
                    entradas={
                        "valor_disponivel": str(valor),
                        "juros_abertos": str(saldo.juros),
                    },
                    saidas={"valor_juros": str(pagamento.valor_juros)},
                    arredondamento="ROUND_HALF_UP:0.01",
                ),
                PassoCalculo(
                    nome="distribuir_encargos",
                    entradas={
                        "valor_disponivel": str(valor - valor_juros),
                        "encargos_abertos": str(saldo.encargos),
                    },
                    saidas={"valor_encargos": str(pagamento.valor_encargos)},
                    arredondamento="ROUND_HALF_UP:0.01",
                ),
                PassoCalculo(
                    nome="amortizar_principal",
                    entradas={
                        "valor_disponivel": str(remanescente),
                        "principal_aberto": str(saldo.principal),
                    },
                    saidas={"valor_amortizacao": str(pagamento.valor_amortizacao)},
                    arredondamento="ROUND_HALF_UP:0.01",
                ),
                PassoCalculo(
                    nome="detectar_sobra",
                    entradas={
                        "valor_disponivel": str(remanescente),
                        "valor_amortizacao": str(pagamento.valor_amortizacao),
                    },
                    saidas={"valor_devolvido": str(pagamento.valor_devolvido)},
                    arredondamento="ROUND_HALF_UP:0.01",
                ),
            ),
            arredondamentos=("ROUND_HALF_UP:0.01",),
            resultados={
                "juros": str(pagamento.valor_juros),
                "amortizacao": str(pagamento.valor_amortizacao),
                "encargos": str(pagamento.valor_encargos),
                "devolvido": str(pagamento.valor_devolvido),
            },
        )


def _viradas_de_mes(inicio: date, fim: date) -> tuple[date, ...]:
    """Primeiro dia de cada mes estritamente entre `inicio` e `fim`."""
    viradas: list[date] = []
    ano, mes = (inicio.year, inicio.month + 1) if inicio.month < 12 else (inicio.year + 1, 1)
    virada = date(ano, mes, 1)
    while virada < fim:
        if virada > inicio:
            viradas.append(virada)
        ano, mes = (virada.year, virada.month + 1) if virada.month < 12 else (virada.year + 1, 1)
        virada = date(ano, mes, 1)
    return tuple(viradas)


def _calcular_juros(
    *,
    principal: Decimal,
    taxa_mensal: Decimal,
    periodo: PeriodoFinanceiro,
) -> Decimal:
    # Normaliza pelo mes a que o periodo pertence, nao pelo mes em que a parcela
    # vence (DR-003). A taxa e contratada "por mes": um periodo que cobre um mes
    # calendario deve custar exatamente essa taxa. Dividir pelos dias do mes de
    # vencimento media um mes com a regua de outro — 01/01 a 01/02 tem 31 dias de
    # janeiro e custava 1,107 mes por ser normalizado por fevereiro.
    dias_do_calendario = Decimal(
        calendar.monthrange(periodo.data_inicio.year, periodo.data_inicio.month)[1]
    )
    return _quantizar(principal * taxa_mensal * Decimal(periodo.dias) / dias_do_calendario)


def _adicionar_meses(valor: date, meses: int) -> date:
    mes_base = valor.month - 1 + meses
    ano = valor.year + mes_base // 12
    mes = mes_base % 12 + 1
    dia = min(valor.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def _data_parametro(parametros: Mapping[str, object], chave: str) -> date:
    valor = parametros.get(chave)
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return date.fromisoformat(valor)
        except ValueError as exc:
            raise ViolacaoInvarianteError(
                "EPIC-005",
                f"{chave} deve ser uma data ISO valida",
            ) from exc
    raise ViolacaoInvarianteError("EPIC-005", f"{chave} deve ser date ou string ISO")


def _inteiro_parametro(parametros: Mapping[str, object], chave: str) -> int:
    valor = parametros.get(chave)
    if not isinstance(valor, int):
        raise ViolacaoInvarianteError("EPIC-005", f"{chave} deve ser inteiro")
    return valor


def _taxa_mensal(parametros: Mapping[str, object]) -> Decimal:
    valor = parametros.get("taxa_juros_mensal", Decimal("0.00"))
    try:
        taxa = Decimal(str(valor))
    except (InvalidOperation, ValueError) as exc:
        raise ViolacaoInvarianteError(
            "EPIC-005",
            "taxa_juros_mensal deve ser Decimal valido",
        ) from exc
    if taxa < Decimal("0.00"):
        raise ViolacaoInvarianteError("EPIC-005", "taxa_juros_mensal nao pode ser negativa")
    return taxa


def _regra_memoria(parametros: Mapping[str, object]) -> dict[str, object]:
    return {
        "tipo": str(parametros.get("regra_calculo", "juros_simples_periodo_real")),
        "taxa_juros_mensal": str(_taxa_mensal(parametros)),
        "versao": "1.0.0",
    }


def _validar_decimal(campo: str, valor: object) -> None:
    if not isinstance(valor, Decimal):
        raise ViolacaoInvarianteError(
            "EPIC-005",
            f"{campo} deve ser Decimal, recebido {valor!r}",
        )


def _validar_uuid(campo: str, valor: object) -> None:
    if not isinstance(valor, uuid.UUID):
        raise ViolacaoInvarianteError(
            "EPIC-005",
            f"{campo} deve ser uuid.UUID, recebido {valor!r}",
        )


def _quantizar(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)
