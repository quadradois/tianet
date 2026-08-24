"""Varredura financeira diaria que alimenta a fila de cobranca.

Este modulo fica deliberadamente fora de application.operacao_diaria:
a varredura pode consultar o Motor Financeiro e entrega um snapshot pronto
para a fila atual e para as notificacoes do IMP-347.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from emprestimo.application.auditoria_escrita import auditar_escrita
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.application.scheduler import ClaimScheduler, ResultadoExecucao
from emprestimo.domain.credit.emprestimo import Emprestimo, EmprestimoState
from emprestimo.domain.credit.motor_financeiro import MotorFinanceiro, SaldoFinanceiro
from emprestimo.domain.credit.operacao_diaria import CobrancaCaso, EstadoCobranca
from emprestimo.domain.credit.pagamento import Pagamento
from emprestimo.domain.credit.ports import (
    CobrancaCasoFiltros,
    EmprestimoFiltros,
    Paginacao,
)
from emprestimo.domain.credit.scheduler import JobAgendado

TIPO_JOB_VARREDURA_COBRANCA = "varrer_cobranca_diaria"
ORIGEM_JOB_VARREDURA_COBRANCA = "varredura_cobranca_diaria"
ORIGEM_CASO_VARREDURA_COBRANCA = "varredura_diaria"
_NAMESPACE_VARREDURA = uuid.UUID("07442840-9522-5e16-85d1-5793c328df58")


@dataclass(frozen=True)
class EmprestimoVarreduraCobranca:
    """Snapshot financeiro de um emprestimo no passe diario."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    devedor_nome: str
    emprestimo_id: uuid.UUID
    data_referencia: date
    acerto_vigente_em: date | None
    proximo_acerto_em: date | None
    data_acerto_calculada: date | None
    vence_hoje: bool
    vence_amanha: bool
    saldo_devedor: Decimal
    percentual_juros: Decimal
    valor_juros_periodo: Decimal
    juros_pendente_acerto: Decimal
    em_atraso: bool


@dataclass(frozen=True)
class DevedorVarreduraCobranca:
    """Visao agrupada por devedor, pronta para consumidores posteriores."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    devedor_nome: str
    emprestimos: tuple[EmprestimoVarreduraCobranca, ...]

    @property
    def vence_hoje(self) -> bool:
        return any(item.vence_hoje for item in self.emprestimos)

    @property
    def vence_amanha(self) -> bool:
        return any(item.vence_amanha for item in self.emprestimos)

    @property
    def saldo_devedor(self) -> Decimal:
        return sum((item.saldo_devedor for item in self.emprestimos), Decimal("0.00"))

    @property
    def percentuais_juros(self) -> tuple[Decimal, ...]:
        return tuple(sorted({item.percentual_juros for item in self.emprestimos}))

    @property
    def valor_juros_periodo(self) -> Decimal:
        return sum(
            (item.valor_juros_periodo for item in self.emprestimos),
            Decimal("0.00"),
        )


@dataclass(frozen=True)
class ResultadoVarreduraCobranca:
    """Resultado reutilizavel pelo handler e pelas notificacoes do IMP-347."""

    data_referencia: date
    devedores: tuple[DevedorVarreduraCobranca, ...]
    casos_criados: int
    casos_atualizados: int
    casos_encerrados: int

    @property
    def vencem_hoje(self) -> tuple[DevedorVarreduraCobranca, ...]:
        return tuple(item for item in self.devedores if item.vence_hoje)

    @property
    def vencem_amanha(self) -> tuple[DevedorVarreduraCobranca, ...]:
        return tuple(item for item in self.devedores if item.vence_amanha)


class VarreduraCobrancaService:
    """Consulta o Motor e sincroniza o ciclo de vida dos casos da carteira."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
        *,
        motor_factory: Callable[[], MotorFinanceiro] = MotorFinanceiro,
        agora: Callable[[], datetime] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria
        self._motor_factory = motor_factory
        self._agora = agora or (lambda: datetime.now(UTC))

    def processar_job(self, claim: ClaimScheduler) -> ResultadoExecucao:
        """Handler registrado no scheduler duravel."""

        valor_data = claim.job.payload.get("data_referencia")
        if not isinstance(valor_data, str):
            raise ValueError("job de varredura sem data_referencia")
        self.executar(
            tenant_id=claim.job.tenant_id,
            carteira_id=claim.job.carteira_id,
            data_referencia=date.fromisoformat(valor_data),
            execucao_id=claim.tentativa.execution_id,
        )
        return ResultadoExecucao.SUCESSO

    def executar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        data_referencia: date,
        execucao_id: uuid.UUID | None = None,
    ) -> ResultadoVarreduraCobranca:
        identificador = execucao_id or uuid.uuid4()
        detalhes_base = {
            "tenant_id": str(tenant_id),
            "carteira_id": str(carteira_id),
            "data_referencia": data_referencia.isoformat(),
        }
        self._auditoria.registrar(
            "cobranca_varredura",
            identificador,
            "varrer.inicio",
            "iniciado",
            detalhes=json.dumps(detalhes_base, sort_keys=True),
        )
        try:
            resultado = self._executar_transacao(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                data_referencia=data_referencia,
            )
        except Exception as exc:
            self._auditoria.registrar(
                "cobranca_varredura",
                identificador,
                "varrer.falha",
                "falhou",
                detalhes=json.dumps(
                    {**detalhes_base, "erro_tipo": type(exc).__name__},
                    sort_keys=True,
                ),
            )
            raise
        self._auditoria.registrar(
            "cobranca_varredura",
            identificador,
            "varrer.sucesso",
            "ok",
            detalhes=json.dumps(
                {
                    **detalhes_base,
                    "casos_criados": resultado.casos_criados,
                    "casos_atualizados": resultado.casos_atualizados,
                    "casos_encerrados": resultado.casos_encerrados,
                    "devedores": len(resultado.devedores),
                },
                sort_keys=True,
            ),
        )
        return resultado

    def _executar_transacao(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        data_referencia: date,
    ) -> ResultadoVarreduraCobranca:
        agora = self._agora()
        with self._uow_factory() as uow:
            carteira = uow.carteira.find_by_id(carteira_id)
            if carteira is None or carteira.tenant_id != tenant_id:
                raise ValueError("carteira da varredura nao pertence ao tenant")
            emprestimos = _listar_emprestimos_ativos(
                uow,
                tenant_id=tenant_id,
                carteira_id=carteira_id,
            )
            itens = tuple(
                self._calcular_item(uow, emprestimo, data_referencia)
                for emprestimo in emprestimos
                if emprestimo.dia_de_acerto is not None
            )
            agrupados = _agrupar_por_devedor(itens)
            criados, atualizados, encerrados = _sincronizar_casos(
                uow,
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                itens=itens,
                agora=agora,
            )
            uow.commit()
        return ResultadoVarreduraCobranca(
            data_referencia=data_referencia,
            devedores=agrupados,
            casos_criados=criados,
            casos_atualizados=atualizados,
            casos_encerrados=encerrados,
        )

    def _calcular_item(
        self,
        uow: UnitOfWork,
        emprestimo: Emprestimo,
        data_referencia: date,
    ) -> EmprestimoVarreduraCobranca:
        pagamentos = tuple(
            pagamento
            for pagamento in uow.pagamento.find_by_emprestimo_id(emprestimo.id)
            if pagamento.recebido_em.date() <= data_referencia
        )
        saldo = _consultar_saldo(
            self._motor_factory,
            emprestimo,
            pagamentos,
            data_referencia,
        )
        acerto_vigente = emprestimo.acerto_vigente_em(data_referencia)
        proximo_acerto = emprestimo.proximo_acerto_em(data_referencia)
        juros_exigiveis = Decimal("0.00")
        if acerto_vigente is not None:
            juros_exigiveis = max(
                _juros_acumulados_brutos(
                    self._motor_factory,
                    emprestimo,
                    pagamentos,
                    acerto_vigente,
                )
                - sum((item.valor_juros for item in pagamentos), Decimal("0.00")),
                Decimal("0.00"),
            )
        em_atraso = (
            acerto_vigente is not None
            and data_referencia > acerto_vigente
            and juros_exigiveis > Decimal("0.00")
        )
        data_calculo = (
            acerto_vigente
            if acerto_vigente is not None and juros_exigiveis > Decimal("0.00")
            else proximo_acerto
        )
        valor_juros_periodo = (
            _juros_do_periodo(
                self._motor_factory,
                emprestimo,
                pagamentos,
                data_calculo,
            )
            if data_calculo is not None
            else Decimal("0.00")
        )
        devedor = uow.devedor.find_by_id(emprestimo.devedor_id)
        nome = devedor.nome if devedor is not None else str(emprestimo.devedor_id)
        taxa = Decimal(str(emprestimo.parametros_financeiros["taxa_juros_mensal"]))
        return EmprestimoVarreduraCobranca(
            tenant_id=emprestimo.tenant_id,
            carteira_id=emprestimo.carteira_id,
            devedor_id=emprestimo.devedor_id,
            devedor_nome=nome,
            emprestimo_id=emprestimo.id,
            data_referencia=data_referencia,
            acerto_vigente_em=acerto_vigente,
            proximo_acerto_em=proximo_acerto,
            data_acerto_calculada=data_calculo,
            vence_hoje=acerto_vigente == data_referencia,
            vence_amanha=proximo_acerto == data_referencia + timedelta(days=1),
            saldo_devedor=saldo.total,
            percentual_juros=taxa * Decimal("100"),
            valor_juros_periodo=valor_juros_periodo,
            juros_pendente_acerto=juros_exigiveis,
            em_atraso=em_atraso,
        )


class AgendadorVarreduraCobranca:
    """Semeia no scheduler duravel um job por carteira e dia."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("cobranca_varredura_agendamento", "agendar_dia")
    def agendar_dia(self, *, data_referencia: date, executar_em: datetime) -> int:
        criados = 0
        with self._uow_factory() as uow:
            for tenant in uow.tenant.find_all():
                for carteira in uow.carteira.find_by_tenant_id(tenant.id):
                    origem_id = uuid.uuid5(
                        _NAMESPACE_VARREDURA,
                        f"{carteira.id}:{data_referencia.isoformat()}",
                    )
                    job = JobAgendado(
                        id=uuid.uuid5(_NAMESPACE_VARREDURA, f"job:{origem_id}"),
                        tenant_id=tenant.id,
                        carteira_id=carteira.id,
                        tipo=TIPO_JOB_VARREDURA_COBRANCA,
                        executar_em=executar_em,
                        correlation_id=f"cobranca:{carteira.id}:{data_referencia.isoformat()}",
                        payload={"data_referencia": data_referencia.isoformat()},
                        origem_tipo=ORIGEM_JOB_VARREDURA_COBRANCA,
                        origem_id=origem_id,
                    )
                    criados += int(uow.job_agendado.save_if_absent(job))
            uow.commit()
        return criados


def _listar_emprestimos_ativos(
    uow: UnitOfWork,
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
) -> tuple[Emprestimo, ...]:
    pagina = 1
    itens: list[Emprestimo] = []
    while True:
        resultado = uow.emprestimo.listar_paginado(
            EmprestimoFiltros(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                estado=EmprestimoState.ATIVO,
            ),
            Paginacao(pagina=pagina, tamanho=100),
        )
        itens.extend(resultado.items)
        if len(itens) >= resultado.total:
            return tuple(itens)
        pagina += 1


def _consultar_saldo(
    motor_factory: Callable[[], MotorFinanceiro],
    emprestimo: Emprestimo,
    pagamentos: Sequence[Pagamento],
    data_referencia: date,
) -> SaldoFinanceiro:
    historico = tuple(item for item in pagamentos if item.recebido_em.date() <= data_referencia)
    motor = motor_factory()
    motor.carregar_historico(emprestimo_id=emprestimo.id, pagamentos=historico)
    return motor.consultar_saldo(
        emprestimo=emprestimo,
        data_referencia=data_referencia,
    )


def _juros_acumulados_brutos(
    motor_factory: Callable[[], MotorFinanceiro],
    emprestimo: Emprestimo,
    pagamentos: Sequence[Pagamento],
    data_referencia: date,
) -> Decimal:
    historico = tuple(item for item in pagamentos if item.recebido_em.date() <= data_referencia)
    saldo = _consultar_saldo(
        motor_factory,
        emprestimo,
        historico,
        data_referencia,
    )
    juros_pagos = sum((item.valor_juros for item in historico), Decimal("0.00"))
    return saldo.juros + juros_pagos


def _juros_do_periodo(
    motor_factory: Callable[[], MotorFinanceiro],
    emprestimo: Emprestimo,
    pagamentos: Sequence[Pagamento],
    data_acerto: date,
) -> Decimal:
    acerto_anterior = emprestimo.acerto_vigente_em(data_acerto - timedelta(days=1))
    juros_anteriores = (
        _juros_acumulados_brutos(
            motor_factory,
            emprestimo,
            pagamentos,
            acerto_anterior,
        )
        if acerto_anterior is not None
        else Decimal("0.00")
    )
    return max(
        _juros_acumulados_brutos(
            motor_factory,
            emprestimo,
            pagamentos,
            data_acerto,
        )
        - juros_anteriores,
        Decimal("0.00"),
    )


def _agrupar_por_devedor(
    itens: Sequence[EmprestimoVarreduraCobranca],
) -> tuple[DevedorVarreduraCobranca, ...]:
    grupos: dict[uuid.UUID, list[EmprestimoVarreduraCobranca]] = {}
    for item in itens:
        grupos.setdefault(item.devedor_id, []).append(item)
    return tuple(
        DevedorVarreduraCobranca(
            tenant_id=grupo[0].tenant_id,
            carteira_id=grupo[0].carteira_id,
            devedor_id=devedor_id,
            devedor_nome=grupo[0].devedor_nome,
            emprestimos=tuple(grupo),
        )
        for devedor_id, grupo in sorted(grupos.items(), key=lambda par: str(par[0]))
    )


def _sincronizar_casos(
    uow: UnitOfWork,
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    itens: Sequence[EmprestimoVarreduraCobranca],
    agora: datetime,
) -> tuple[int, int, int]:
    existentes = uow.cobranca_caso.listar(
        CobrancaCasoFiltros(tenant_id=tenant_id, carteira_id=carteira_id)
    )
    casos_por_devedor = {caso.devedor_id: caso for caso in existentes}
    pendentes: dict[uuid.UUID, list[EmprestimoVarreduraCobranca]] = {}
    for item in itens:
        if item.em_atraso:
            pendentes.setdefault(item.devedor_id, []).append(item)

    criados = atualizados = encerrados = 0
    for devedor_id, atrasados in pendentes.items():
        total = sum((item.saldo_devedor for item in atrasados), Decimal("0.00"))
        ids = {item.emprestimo_id for item in atrasados}
        caso = casos_por_devedor.get(devedor_id)
        if caso is None:
            caso = CobrancaCaso(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                devedor_id=devedor_id,
                emprestimo_id=atrasados[0].emprestimo_id if len(ids) == 1 else None,
                titulo=f"Acerto pendente - {atrasados[0].devedor_nome}",
                origem=ORIGEM_CASO_VARREDURA_COBRANCA,
                total_pendente=total,
                criado_em=agora,
            )
            uow.cobranca_caso.save(caso)
            criados += 1
            continue
        emprestimo_id = (
            caso.emprestimo_id
            if caso.emprestimo_id in ids
            else atrasados[0].emprestimo_id if len(ids) == 1 else None
        )
        if (
            caso.total_pendente != total
            or caso.emprestimo_id != emprestimo_id
            or caso.estado is EstadoCobranca.ENCERRADO
        ):
            caso.sincronizar_pendencia(
                total_pendente=total,
                emprestimo_id=emprestimo_id,
                agora=agora,
            )
            uow.cobranca_caso.save(caso)
            atualizados += 1

    for caso in existentes:
        gerenciado = caso.origem == ORIGEM_CASO_VARREDURA_COBRANCA
        if (
            gerenciado
            and caso.devedor_id not in pendentes
            and caso.estado is not EstadoCobranca.ENCERRADO
        ):
            caso.encerrar_por_acerto(agora=agora)
            uow.cobranca_caso.save(caso)
            encerrados += 1
    return criados, atualizados, encerrados
