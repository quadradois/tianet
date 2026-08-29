"""Servicos de aplicacao do Motor Financeiro (EPIC-005/P4)."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from emprestimo.application.auditoria_escrita import auditar_escrita
from emprestimo.application.errors import (
    ContratoCreditoNaoEncontradoError,
    DevedorNaoEncontradoError,
    EmprestimoNaoEncontradoError,
    IdempotenciaConflitoError,
    PagamentoNaoEncontradoError,
    TransicaoEstadoInvalidaError,
    UsuarioNaoEncontradoError,
)
from emprestimo.application.notifications import AvisoSobraPagamento
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.dia_de_acerto import proximo_acerto, validar_dia_de_acerto
from emprestimo.domain.credit.emprestimo import Emprestimo, EmprestimoState
from emprestimo.domain.credit.eventos_financeiros import EventoFinanceiro
from emprestimo.domain.credit.financeiro import TaxaJuros, ValorQuitacao
from emprestimo.domain.credit.memoria_calculo import MemoriaCalculo
from emprestimo.domain.credit.motor_financeiro import MotorFinanceiro
from emprestimo.domain.credit.pagamento import Pagamento, PagamentoState
from emprestimo.domain.credit.ports import EmprestimoFiltros, Paginacao

logger = logging.getLogger(__name__)

ESCOPO_IDEMPOTENCIA = "motor-criacao-emprestimo"
"""Escopo da Idempotency-Key para criacao de Emprestimo."""

ESCOPO_IDEMPOTENCIA_PAGAMENTO = "motor-pagamento"
"""Escopo da Idempotency-Key para registro de Pagamento."""

ESCOPO_IDEMPOTENCIA_ESTORNO = "motor-pagamento-estorno"
"""Escopo da Idempotency-Key para estorno parcial de Pagamento."""

ESCOPO_IDEMPOTENCIA_QUITACAO = "motor-quitacao"
"""Escopo da Idempotency-Key para quitacao de Emprestimo."""

ESCOPO_IDEMPOTENCIA_RENEGOCIACAO = "motor-renegociacao"
"""Escopo da Idempotency-Key para renegociacao financeira."""


@dataclass(frozen=True)
class EmprestimoCriadoResultado:
    """Resultado do caso de uso de criacao de Emprestimo."""

    emprestimo_id: uuid.UUID
    contrato_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    estado: EmprestimoState
    principal_original: Decimal
    moeda: str
    parametros_financeiros: dict[str, object]
    criado_em: datetime
    # Acerto mensal (DR-004). `None` nos emprestimos anteriores a decisao, que
    # nasceram com plano de parcelas e nao tem dia combinado.
    dia_de_acerto: int | None
    proximo_acerto_em: date | None
    acerto_pendente_desde: date | None


@dataclass(frozen=True)
class EmprestimoListagemResultado:
    """Resultado paginado de Emprestimos financeiros."""

    items: tuple[EmprestimoCriadoResultado, ...]
    total: int
    pagina: int
    tamanho: int
    paginas: int


@dataclass(frozen=True)
class PagamentoResultado:
    """Resultado do processamento oficial de um pagamento."""

    pagamento_id: uuid.UUID
    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    valor_recebido: Decimal
    recebido_em: datetime
    valor_juros: Decimal
    valor_amortizacao: Decimal
    valor_encargos: Decimal
    valor_devolvido: Decimal
    valor_estornado: Decimal
    valor_sobra: Decimal
    reconciliado: bool
    estado: PagamentoState
    chave_idempotencia: str | None
    memoria: MemoriaCalculo | None


@dataclass(frozen=True)
class SaldoResultado:
    """Saldo financeiro calculado para uma data de referencia."""

    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    data_referencia: date
    principal: Decimal
    juros: Decimal
    encargos: Decimal
    total: Decimal
    memoria: MemoriaCalculo


@dataclass(frozen=True)
class SaldoItemDevedor:
    """Parcela do total por emprestimo, para o consumidor conferir a origem."""

    emprestimo_id: uuid.UUID
    principal: Decimal
    juros: Decimal
    encargos: Decimal
    total: Decimal


@dataclass(frozen=True)
class SaldoDevedorResultado:
    """Saldo somado dos emprestimos ativos de um Devedor (IMP-362).

    Existe para que ninguem fora do Motor precise somar dinheiro. Sem ele, a
    pergunta "quanto o Devedor deve?" obrigaria o frontend — ou pior, um LLM —
    a listar emprestimos e adicionar valores, o que quebraria a regra de que o
    Motor e a autoridade sobre dinheiro.
    """

    devedor_id: uuid.UUID
    tenant_id: uuid.UUID
    data_referencia: date
    principal: Decimal
    juros: Decimal
    encargos: Decimal
    total: Decimal
    emprestimos_considerados: int
    itens: tuple[SaldoItemDevedor, ...]


@dataclass(frozen=True)
class QuitacaoCalculadaResultado:
    """Valor calculado para quitar um Emprestimo."""

    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    valor_quitacao: ValorQuitacao
    memoria: MemoriaCalculo


@dataclass(frozen=True)
class QuitacaoResultado:
    """Resultado da liquidacao final de um Emprestimo."""

    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    estado: EmprestimoState
    pagamento: PagamentoResultado
    memoria_quitacao: MemoriaCalculo


@dataclass(frozen=True)
class RenegociacaoResultado:
    """Resultado do registro logico de uma renegociacao financeira."""

    emprestimo_id: uuid.UUID
    tenant_id: uuid.UUID
    novos_parametros: dict[str, object]
    memoria: MemoriaCalculo


class ConsultaEmprestimoService:
    """Consulta Emprestimos financeiros e suas memorias sem alterar estado."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def consultar(
        self,
        *,
        emprestimo_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> EmprestimoCriadoResultado:
        with self._uow_factory() as uow:
            return _emprestimo_resultado(
                _emprestimo_do_tenant(
                    uow,
                    emprestimo_id=emprestimo_id,
                    tenant_id=tenant_id,
                )
            )

    def listar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID | None,
        devedor_id: uuid.UUID | None,
        estado: EmprestimoState | None,
        pagina: int,
        tamanho: int,
    ) -> EmprestimoListagemResultado:
        with self._uow_factory() as uow:
            resultado = uow.emprestimo.listar_paginado(
                EmprestimoFiltros(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    estado=estado,
                ),
                Paginacao(pagina=pagina, tamanho=tamanho),
            )
            return EmprestimoListagemResultado(
                items=tuple(_emprestimo_resultado(item) for item in resultado.items),
                total=resultado.total,
                pagina=resultado.pagina,
                tamanho=resultado.tamanho,
                paginas=resultado.paginas,
            )

    def consultar_memorias(
        self,
        *,
        emprestimo_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> tuple[MemoriaCalculo, ...]:
        with self._uow_factory() as uow:
            _emprestimo_do_tenant(
                uow,
                emprestimo_id=emprestimo_id,
                tenant_id=tenant_id,
            )
            return tuple(uow.memoria_calculo.find_by_emprestimo_id(emprestimo_id))


class CriacaoEmprestimoService:
    """Cria Emprestimo a partir de contrato liberado para o Motor Financeiro."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def criar_de_contrato(
        self,
        *,
        contrato_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
    ) -> EmprestimoCriadoResultado:
        hash_solicitacao = _solicitacao_hash(
            contrato_id=contrato_id,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
        )
        self._auditoria.registrar(
            "emprestimo",
            None,
            "criar.inicio",
            "iniciado",
            detalhes=json.dumps({"idempotency_key": idempotency_key}),
        )
        try:
            with self._uow_factory() as uow:
                resultado = self._replay_ou_registrar_chave(
                    uow,
                    idempotency_key,
                    hash_solicitacao,
                )
                if resultado is not None:
                    uow.commit()
                    return resultado

                contrato = uow.contrato_credito.find_by_id(contrato_id)
                if contrato is None or contrato.tenant_id != tenant_id:
                    raise ContratoCreditoNaoEncontradoError(contrato_id)
                usuario = uow.usuario.find_by_id(usuario_id)
                if usuario is None or usuario.tenant_id != tenant_id:
                    raise UsuarioNaoEncontradoError(usuario_id)
                if uow.emprestimo.find_by_contrato_id(contrato_id) is not None:
                    raise TransicaoEstadoInvalidaError(
                        contrato_id,
                        "criar_emprestimo",
                        "contrato ja possui emprestimo financeiro",
                    )
                try:
                    emprestimo = Emprestimo.criar_de_contrato_liberado(
                        contrato.gerar_saida_logica()
                    )
                except ViolacaoInvarianteError as exc:
                    raise TransicaoEstadoInvalidaError(
                        contrato_id,
                        "criar_emprestimo",
                        str(exc),
                    ) from exc

                self._auditoria.registrar(
                    "emprestimo",
                    emprestimo.id,
                    "criar.aggregate_criado",
                    "ok",
                    detalhes=json.dumps(
                        {
                            "contrato_id": str(contrato_id),
                            "idempotency_key": idempotency_key,
                        }
                    ),
                )
                for evento in emprestimo.eventos:
                    if hasattr(evento, "to_audit_dict"):
                        self._auditoria.registrar(
                            "emprestimo",
                            emprestimo.id,
                            "criar.evento_criado",
                            "ok",
                            detalhes=json.dumps(evento.to_audit_dict()),
                        )

                uow.emprestimo.save(emprestimo)
                resultado = _emprestimo_resultado(emprestimo)
                uow.idempotencia.concluir(
                    idempotency_key,
                    ESCOPO_IDEMPOTENCIA,
                    _serializar_resultado(resultado),
                )
                uow.commit()

            self._auditoria.registrar(
                "emprestimo",
                resultado.emprestimo_id,
                "criar.sucesso",
                "ok",
                detalhes=json.dumps(
                    {
                        "estado": resultado.estado.value,
                        "idempotency_key": idempotency_key,
                    }
                ),
            )
            return resultado
        except Exception as exc:
            self._auditoria.registrar(
                "emprestimo",
                None,
                "criar.falha",
                "falhou",
                detalhes=f"{type(exc).__name__}: {exc}",
            )
            self._auditoria.registrar("emprestimo", None, "criar.rollback", "rollback_aplicado")
            raise

    def _replay_ou_registrar_chave(
        self,
        uow: UnitOfWork,
        idempotency_key: str,
        hash_solicitacao: str,
    ) -> EmprestimoCriadoResultado | None:
        existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA)
        if existente is None:
            uow.idempotencia.registrar(idempotency_key, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
            return None
        if existente["estado"] != "finished":
            raise IdempotenciaConflitoError(idempotency_key, "criacao de emprestimo em andamento")
        if existente["solicitacao_hash"] != hash_solicitacao:
            raise IdempotenciaConflitoError(idempotency_key, "resultado divergente")
        self._auditoria.registrar(
            "emprestimo",
            None,
            "criar.replay",
            "ok",
            detalhes=json.dumps({"idempotency_key": idempotency_key}),
        )
        return _desserializar_resultado(existente["resultado"])


class PagamentoService:
    """Registra pagamentos usando a distribuicao oficial do Motor Financeiro."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
        motor_factory: Callable[[], MotorFinanceiro] = MotorFinanceiro,
        enfileirar_aviso: Callable[[AvisoSobraPagamento], object] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria
        self._motor_factory = motor_factory
        self._enfileirar_aviso = enfileirar_aviso

    @auditar_escrita("pagamento", "registrar", identificador="emprestimo_id")
    def registrar(
        self,
        *,
        emprestimo_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        valor: Decimal,
        recebido_em: datetime,
        idempotency_key: str,
    ) -> PagamentoResultado:
        solicitacao_hash = _hash_operacao(
            operacao="pagamento",
            emprestimo_id=emprestimo_id,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            valor=_valor_decimal(valor),
            recebido_em=recebido_em.isoformat(),
        )
        with self._uow_factory() as uow:
            emprestimo = _emprestimo_do_tenant(
                uow,
                emprestimo_id=emprestimo_id,
                tenant_id=tenant_id,
            )
            usuario = uow.usuario.find_by_id(usuario_id)
            if usuario is None or usuario.tenant_id != tenant_id:
                raise UsuarioNaoEncontradoError(usuario_id)
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=ESCOPO_IDEMPOTENCIA_PAGAMENTO,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento="pagamento em andamento",
            )
            existente = uow.pagamento.find_by_idempotency_key(
                emprestimo_id,
                idempotency_key,
            )
            if existente is not None:
                _validar_pagamento_replay(
                    existente,
                    idempotency_key=idempotency_key,
                    usuario_id=usuario_id,
                    valor=valor,
                    recebido_em=recebido_em,
                )
                if not replay:
                    uow.idempotencia.concluir(
                        idempotency_key,
                        ESCOPO_IDEMPOTENCIA_PAGAMENTO,
                        _idempotencia_resultado_json("pagamento_id", existente.id),
                    )
                    uow.commit()
                resultado = _pagamento_resultado(
                    emprestimo,
                    existente,
                    _memoria_pagamento_existente(uow, emprestimo_id, existente.id),
                )
                self._enfileirar_aviso_apos_commit(emprestimo, existente)
                return resultado
            if replay:
                raise IdempotenciaConflitoError(idempotency_key, "resultado de pagamento ausente")
            pagamentos = uow.pagamento.find_by_emprestimo_id(emprestimo_id)
            motor = self._motor_factory()
            motor.carregar_historico(
                emprestimo_id=emprestimo_id,
                pagamentos=pagamentos,
            )
            try:
                processado = motor.registrar_pagamento(
                    emprestimo=emprestimo,
                    valor=valor,
                    recebido_em=recebido_em,
                    chave_idempotencia=idempotency_key,
                    usuario_id=usuario_id,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    emprestimo_id,
                    "registrar_pagamento",
                    str(exc),
                ) from exc
            uow.emprestimo.save(emprestimo)
            uow.pagamento.save(processado.pagamento)
            uow.memoria_calculo.save(
                processado.memoria,
                emprestimo.id,
                processado.pagamento.id,
            )
            uow.evento_financeiro.save(processado.evento)
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA_PAGAMENTO,
                _idempotencia_resultado_json("pagamento_id", processado.pagamento.id),
            )
            uow.commit()
            resultado = _pagamento_resultado(
                emprestimo,
                processado.pagamento,
                processado.memoria,
            )
            self._enfileirar_aviso_apos_commit(emprestimo, processado.pagamento)
            return resultado

    def _enfileirar_aviso_apos_commit(
        self,
        emprestimo: Emprestimo,
        pagamento: Pagamento,
    ) -> None:
        if self._enfileirar_aviso is None or pagamento.valor_devolvido <= Decimal("0.00"):
            return
        aviso = AvisoSobraPagamento(
            tenant_id=emprestimo.tenant_id,
            carteira_id=emprestimo.carteira_id,
            devedor_id=emprestimo.devedor_id,
            emprestimo_id=emprestimo.id,
            pagamento_id=pagamento.id,
            valor_recebido=pagamento.valor_recebido,
            valor_distribuido=pagamento.valor_distribuido,
            valor_devolvido=pagamento.valor_devolvido,
        )
        try:
            self._enfileirar_aviso(aviso)
        except Exception:
            logger.exception(
                "aviso_sobra_pagamento_enqueue_failed",
                extra={"pagamento_id": str(pagamento.id)},
            )


class EstornoPagamentoService:
    """Registra a devolucao parcial feita pelo Credor fora do sistema."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def estornar(
        self,
        *,
        pagamento_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        valor: Decimal,
        idempotency_key: str,
    ) -> PagamentoResultado:
        detalhes = {
            "pagamento_id": str(pagamento_id),
            "tenant_id": str(tenant_id),
            "usuario_id": str(usuario_id),
            "valor": _valor_decimal(valor),
            "idempotency_key": idempotency_key,
        }
        self._auditoria.registrar(
            "pagamento",
            pagamento_id,
            "estornar.inicio",
            "iniciado",
            detalhes=json.dumps(detalhes, sort_keys=True),
        )
        try:
            with self._uow_factory() as uow:
                pagamento = uow.pagamento.find_by_id(pagamento_id)
                if pagamento is None:
                    raise PagamentoNaoEncontradoError(pagamento_id)
                emprestimo = _emprestimo_do_tenant(
                    uow,
                    emprestimo_id=pagamento.emprestimo_id,
                    tenant_id=tenant_id,
                )
                _validar_usuario_do_tenant(
                    uow,
                    usuario_id=usuario_id,
                    tenant_id=tenant_id,
                )
                solicitacao_hash = _hash_operacao(
                    operacao="estorno_pagamento",
                    pagamento_id=pagamento_id,
                    tenant_id=tenant_id,
                    usuario_id=usuario_id,
                    valor=_valor_decimal(valor),
                )
                replay = _replay_ou_registrar_chave(
                    uow,
                    idempotency_key=idempotency_key,
                    escopo=ESCOPO_IDEMPOTENCIA_ESTORNO,
                    solicitacao_hash=solicitacao_hash,
                    motivo_em_andamento="estorno de pagamento em andamento",
                )
                if not replay:
                    try:
                        pagamento = pagamento.estornar(valor)
                    except ViolacaoInvarianteError as exc:
                        raise TransicaoEstadoInvalidaError(
                            pagamento_id,
                            "estornar_pagamento",
                            str(exc),
                        ) from exc
                    uow.pagamento.save(pagamento)
                    uow.idempotencia.concluir(
                        idempotency_key,
                        ESCOPO_IDEMPOTENCIA_ESTORNO,
                        _idempotencia_resultado_json("pagamento_id", pagamento.id),
                    )
                    uow.commit()
                resultado = _pagamento_resultado(
                    emprestimo,
                    pagamento,
                    _memoria_pagamento_existente(uow, emprestimo.id, pagamento.id),
                )
            self._auditoria.registrar(
                "pagamento",
                pagamento_id,
                "estornar.replay" if replay else "estornar.sucesso",
                "ok",
                detalhes=json.dumps(
                    {
                        **detalhes,
                        "valor_estornado": _valor_decimal(resultado.valor_estornado),
                        "valor_sobra": _valor_decimal(resultado.valor_sobra),
                        "reconciliado": resultado.reconciliado,
                    },
                    sort_keys=True,
                ),
            )
            return resultado
        except Exception as exc:
            self._auditoria.registrar(
                "pagamento",
                pagamento_id,
                "estornar.falha",
                "falhou",
                detalhes=json.dumps(
                    {**detalhes, "erro_tipo": type(exc).__name__},
                    sort_keys=True,
                ),
            )
            self._auditoria.registrar(
                "pagamento",
                pagamento_id,
                "estornar.rollback",
                "rollback_aplicado",
                detalhes=json.dumps(detalhes, sort_keys=True),
            )
            raise


class ConsultaSaldoService:
    """Consulta saldo devedor sem alterar o estado persistido do Emprestimo."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        motor_factory: Callable[[], MotorFinanceiro] = MotorFinanceiro,
    ) -> None:
        self._uow_factory = uow_factory
        self._motor_factory = motor_factory

    def consultar(
        self,
        *,
        emprestimo_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data_referencia: date,
    ) -> SaldoResultado:
        with self._uow_factory() as uow:
            emprestimo = _emprestimo_do_tenant(
                uow,
                emprestimo_id=emprestimo_id,
                tenant_id=tenant_id,
            )
            motor = self._motor_factory()
            motor.carregar_historico(
                emprestimo_id=emprestimo_id,
                pagamentos=uow.pagamento.find_by_emprestimo_id(emprestimo_id),
            )
            try:
                saldo = motor.consultar_saldo(
                    emprestimo=emprestimo,
                    data_referencia=data_referencia,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    emprestimo_id,
                    "consultar_saldo",
                    str(exc),
                ) from exc
            return SaldoResultado(
                emprestimo_id=emprestimo.id,
                tenant_id=emprestimo.tenant_id,
                data_referencia=data_referencia,
                principal=saldo.principal,
                juros=saldo.juros,
                encargos=saldo.encargos,
                total=saldo.total,
                memoria=saldo.memoria,
            )

    def consultar_por_devedor(
        self,
        *,
        devedor_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data_referencia: date,
    ) -> SaldoDevedorResultado:
        """Soma o saldo dos emprestimos ATIVOS do Devedor (IMP-362).

        A soma acontece aqui, no Motor, e nao no consumidor. Cada parcela vem do
        mesmo `consultar_saldo` que atende a consulta individual, entao o total
        e sempre consistente com o que o extrato do emprestimo mostra.

        Emprestimos quitados e cancelados ficam de fora: a pergunta e quanto o
        Devedor **deve**, nao quanto ja deveu.
        """
        self._exigir_devedor_do_tenant(devedor_id, tenant_id)
        principal = juros = encargos = total = Decimal("0.00")
        itens: list[SaldoItemDevedor] = []
        for emprestimo_id in self._emprestimos_ativos(devedor_id, tenant_id):
            saldo = self.consultar(
                emprestimo_id=emprestimo_id,
                tenant_id=tenant_id,
                data_referencia=data_referencia,
            )
            principal += saldo.principal
            juros += saldo.juros
            encargos += saldo.encargos
            total += saldo.total
            itens.append(
                SaldoItemDevedor(
                    emprestimo_id=saldo.emprestimo_id,
                    principal=saldo.principal,
                    juros=saldo.juros,
                    encargos=saldo.encargos,
                    total=saldo.total,
                )
            )
        return SaldoDevedorResultado(
            devedor_id=devedor_id,
            tenant_id=tenant_id,
            data_referencia=data_referencia,
            principal=principal,
            juros=juros,
            encargos=encargos,
            total=total,
            emprestimos_considerados=len(itens),
            itens=tuple(itens),
        )

    def _exigir_devedor_do_tenant(self, devedor_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """404 para Devedor inexistente, em vez de zero.

        Zero seria mentir: dizer "nao deve nada" sobre alguem que nao existe
        confunde ausencia de divida com ausencia de cadastro. Devedor de outro
        Tenant tambem responde 404, neutro, sem revelar que existe.
        """
        with self._uow_factory() as uow:
            devedor = uow.devedor.find_by_id(devedor_id)
            carteira = uow.carteira.find_by_id(devedor.carteira_id) if devedor is not None else None
            if devedor is None or carteira is None or carteira.tenant_id != tenant_id:
                raise DevedorNaoEncontradoError(devedor_id)

    def _emprestimos_ativos(
        self,
        devedor_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """Ids dos emprestimos ativos do Devedor, paginando ate o fim.

        Pagina em vez de pedir tudo de uma vez porque `listar_paginado` e o
        unico caminho do repositorio; parar na primeira pagina daria um total
        silenciosamente incompleto para quem tiver muitos emprestimos.
        """
        ids: list[uuid.UUID] = []
        pagina = 1
        while True:
            with self._uow_factory() as uow:
                resultado = uow.emprestimo.listar_paginado(
                    EmprestimoFiltros(
                        tenant_id=tenant_id,
                        devedor_id=devedor_id,
                        estado=EmprestimoState.ATIVO,
                    ),
                    Paginacao(pagina=pagina, tamanho=100),
                )
            ids.extend(item.id for item in resultado.items)
            if len(ids) >= resultado.total or not resultado.items:
                return ids
            pagina += 1


class QuitacaoRenegociacaoService:
    """Calcula quitacao, quita Emprestimo e registra renegociacao logica."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
        motor_factory: Callable[[], MotorFinanceiro] = MotorFinanceiro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria
        self._motor_factory = motor_factory

    def calcular_valor_quitacao(
        self,
        *,
        emprestimo_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data_referencia: date,
    ) -> QuitacaoCalculadaResultado:
        with self._uow_factory() as uow:
            emprestimo = _emprestimo_do_tenant(
                uow,
                emprestimo_id=emprestimo_id,
                tenant_id=tenant_id,
            )
            motor = _motor_com_historico(self._motor_factory(), uow, emprestimo_id)
            try:
                quitacao = motor.calcular_valor_quitacao(
                    emprestimo=emprestimo,
                    data_referencia=data_referencia,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    emprestimo_id,
                    "calcular_quitacao",
                    str(exc),
                ) from exc
            return QuitacaoCalculadaResultado(
                emprestimo_id=emprestimo.id,
                tenant_id=emprestimo.tenant_id,
                valor_quitacao=quitacao.valor_quitacao,
                memoria=quitacao.memoria,
            )

    @auditar_escrita("emprestimo", "quitar", identificador="emprestimo_id")
    def quitar(
        self,
        *,
        emprestimo_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        recebido_em: datetime,
        idempotency_key: str,
    ) -> QuitacaoResultado:
        solicitacao_hash = _hash_operacao(
            operacao="quitacao",
            emprestimo_id=emprestimo_id,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            recebido_em=recebido_em.isoformat(),
        )
        with self._uow_factory() as uow:
            emprestimo = _emprestimo_do_tenant(
                uow,
                emprestimo_id=emprestimo_id,
                tenant_id=tenant_id,
            )
            _validar_usuario_do_tenant(uow, usuario_id=usuario_id, tenant_id=tenant_id)
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=ESCOPO_IDEMPOTENCIA_QUITACAO,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento="quitacao em andamento",
            )
            pagamento_existente = uow.pagamento.find_by_idempotency_key(
                emprestimo_id,
                idempotency_key,
            )
            if pagamento_existente is not None:
                _validar_pagamento_replay(
                    pagamento_existente,
                    idempotency_key=idempotency_key,
                    usuario_id=usuario_id,
                    recebido_em=recebido_em,
                )
                memoria_replay = _memoria_quitacao_existente(uow, emprestimo_id)
                if memoria_replay is None:
                    raise IdempotenciaConflitoError(
                        idempotency_key,
                        "resultado de quitacao ausente",
                    )
                if not replay:
                    uow.idempotencia.concluir(
                        idempotency_key,
                        ESCOPO_IDEMPOTENCIA_QUITACAO,
                        _idempotencia_resultado_json("pagamento_id", pagamento_existente.id),
                    )
                    uow.commit()
                return QuitacaoResultado(
                    emprestimo_id=emprestimo.id,
                    tenant_id=emprestimo.tenant_id,
                    estado=emprestimo.estado,
                    pagamento=_pagamento_resultado(
                        emprestimo,
                        pagamento_existente,
                        _memoria_pagamento_existente(uow, emprestimo_id, pagamento_existente.id),
                    ),
                    memoria_quitacao=memoria_replay,
                )
            if replay:
                raise IdempotenciaConflitoError(idempotency_key, "resultado de quitacao ausente")
            # Idem para a quitacao (DR-004): o valor de quitar vem do saldo, e o
            # saldo existe desde o primeiro dia do emprestimo.
            motor = _motor_com_historico(self._motor_factory(), uow, emprestimo_id)
            try:
                calculada = motor.calcular_valor_quitacao(
                    emprestimo=emprestimo,
                    data_referencia=recebido_em.date(),
                )
                resultado = motor.quitar(
                    emprestimo=emprestimo,
                    valor=calculada.valor_total,
                    recebido_em=recebido_em,
                    chave_idempotencia=idempotency_key,
                    usuario_id=usuario_id,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    emprestimo_id,
                    "quitar",
                    str(exc),
                ) from exc
            uow.emprestimo.save(emprestimo)
            uow.pagamento.save(resultado.pagamento)
            uow.memoria_calculo.save(calculada.memoria, emprestimo.id)
            uow.memoria_calculo.save(resultado.memoria, emprestimo.id, resultado.pagamento.id)
            _persistir_eventos_financeiros_novos(uow, emprestimo)
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA_QUITACAO,
                _idempotencia_resultado_json("pagamento_id", resultado.pagamento.id),
            )
            uow.commit()
            return QuitacaoResultado(
                emprestimo_id=emprestimo.id,
                tenant_id=emprestimo.tenant_id,
                estado=emprestimo.estado,
                pagamento=_pagamento_resultado(emprestimo, resultado.pagamento, resultado.memoria),
                memoria_quitacao=calculada.memoria,
            )

    @auditar_escrita("emprestimo", "renegociar", identificador="emprestimo_id")
    def renegociar(
        self,
        *,
        emprestimo_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        novos_parametros: Mapping[str, object],
        renegociado_em: datetime,
        idempotency_key: str,
    ) -> RenegociacaoResultado:
        solicitacao_hash = _hash_operacao(
            operacao="renegociacao",
            emprestimo_id=emprestimo_id,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            novos_parametros=novos_parametros,
            renegociado_em=renegociado_em.isoformat(),
        )
        with self._uow_factory() as uow:
            emprestimo = _emprestimo_do_tenant(
                uow,
                emprestimo_id=emprestimo_id,
                tenant_id=tenant_id,
            )
            _validar_usuario_do_tenant(uow, usuario_id=usuario_id, tenant_id=tenant_id)
            replay = _replay_ou_registrar_chave(
                uow,
                idempotency_key=idempotency_key,
                escopo=ESCOPO_IDEMPOTENCIA_RENEGOCIACAO,
                solicitacao_hash=solicitacao_hash,
                motivo_em_andamento="renegociacao em andamento",
            )
            if replay:
                return _renegociacao_replay(
                    uow,
                    emprestimo=emprestimo,
                    idempotency_key=idempotency_key,
                )
            motor = _motor_com_historico(self._motor_factory(), uow, emprestimo_id)
            try:
                renegociacao = motor.renegociar(
                    emprestimo=emprestimo,
                    novos_parametros=novos_parametros,
                    usuario_id=usuario_id,
                    renegociado_em=renegociado_em,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    emprestimo_id,
                    "renegociar",
                    str(exc),
                ) from exc
            uow.emprestimo.save(emprestimo)
            uow.memoria_calculo.save(renegociacao.memoria, emprestimo.id)
            uow.evento_financeiro.save(renegociacao.evento)
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA_RENEGOCIACAO,
                _idempotencia_resultado_json("memoria_id", renegociacao.memoria.id),
            )
            uow.commit()
            return RenegociacaoResultado(
                emprestimo_id=emprestimo.id,
                tenant_id=emprestimo.tenant_id,
                novos_parametros=dict(renegociacao.novos_parametros),
                memoria=renegociacao.memoria,
            )


def _solicitacao_hash(
    *,
    contrato_id: uuid.UUID,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> str:
    bruto = f"{tenant_id}|{contrato_id}|{usuario_id}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _hash_operacao(**dados: object) -> str:
    bruto = json.dumps(_normalizar_json(dados), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _normalizar_json(valor: object) -> object:
    if isinstance(valor, Decimal):
        return _valor_decimal(valor)
    if isinstance(valor, uuid.UUID):
        return str(valor)
    if isinstance(valor, date | datetime):
        return valor.isoformat()
    if isinstance(valor, Mapping):
        return {
            str(chave): _normalizar_json(item)
            for chave, item in sorted(valor.items(), key=lambda item: str(item[0]))
        }
    if isinstance(valor, tuple | list):
        return [_normalizar_json(item) for item in valor]
    return valor


def _valor_decimal(valor: Decimal) -> str:
    return str(valor.quantize(Decimal("0.01")))


def _replay_ou_registrar_chave(
    uow: UnitOfWork,
    *,
    idempotency_key: str,
    escopo: str,
    solicitacao_hash: str,
    motivo_em_andamento: str,
) -> bool:
    existente = uow.idempotencia.find_by_chave(idempotency_key, escopo)
    if existente is None:
        uow.idempotencia.registrar(idempotency_key, escopo, solicitacao_hash)
        return False
    if existente["estado"] != "finished":
        raise IdempotenciaConflitoError(idempotency_key, motivo_em_andamento)
    if existente["solicitacao_hash"] != solicitacao_hash:
        raise IdempotenciaConflitoError(idempotency_key, "payload divergente")
    return True


def _emprestimo_do_tenant(
    uow: UnitOfWork,
    *,
    emprestimo_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> Emprestimo:
    emprestimo = uow.emprestimo.find_by_id(emprestimo_id)
    if emprestimo is None or emprestimo.tenant_id != tenant_id:
        raise EmprestimoNaoEncontradoError(emprestimo_id)
    return emprestimo


def _validar_usuario_do_tenant(
    uow: UnitOfWork,
    *,
    usuario_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    usuario = uow.usuario.find_by_id(usuario_id)
    if usuario is None or usuario.tenant_id != tenant_id:
        raise UsuarioNaoEncontradoError(usuario_id)


def _motor_com_historico(
    motor: MotorFinanceiro,
    uow: UnitOfWork,
    emprestimo_id: uuid.UUID,
) -> MotorFinanceiro:
    motor.carregar_historico(
        emprestimo_id=emprestimo_id,
        pagamentos=uow.pagamento.find_by_emprestimo_id(emprestimo_id),
    )
    return motor


def _emprestimo_resultado(emprestimo: Emprestimo) -> EmprestimoCriadoResultado:
    hoje = datetime.now(UTC).date()
    return EmprestimoCriadoResultado(
        emprestimo_id=emprestimo.id,
        contrato_id=emprestimo.contrato_id,
        tenant_id=emprestimo.tenant_id,
        carteira_id=emprestimo.carteira_id,
        devedor_id=emprestimo.devedor_id,
        estado=emprestimo.estado,
        principal_original=emprestimo.principal_original,
        moeda=emprestimo.moeda,
        parametros_financeiros=emprestimo.parametros_financeiros,
        criado_em=emprestimo.criado_em,
        dia_de_acerto=emprestimo.dia_de_acerto,
        # Calculado na leitura, e nao lido de coluna: o proximo acerto anda
        # sozinho com o calendario, e uma coluna gravada envelheceria em
        # silencio a cada mes que passa.
        proximo_acerto_em=emprestimo.proximo_acerto_em(hoje),
        acerto_pendente_desde=emprestimo.acerto_sem_pagamento_em(hoje),
    )


def _pagamento_resultado(
    emprestimo: Emprestimo,
    pagamento: Pagamento,
    memoria: MemoriaCalculo | None,
) -> PagamentoResultado:
    return PagamentoResultado(
        pagamento_id=pagamento.id,
        emprestimo_id=pagamento.emprestimo_id,
        tenant_id=emprestimo.tenant_id,
        valor_recebido=pagamento.valor_recebido,
        recebido_em=pagamento.recebido_em,
        valor_juros=pagamento.valor_juros,
        valor_amortizacao=pagamento.valor_amortizacao,
        valor_encargos=pagamento.valor_encargos,
        valor_devolvido=pagamento.valor_devolvido,
        valor_estornado=pagamento.valor_estornado,
        valor_sobra=pagamento.valor_sobra,
        reconciliado=pagamento.reconciliado,
        estado=pagamento.estado,
        chave_idempotencia=pagamento.chave_idempotencia,
        memoria=memoria,
    )


def _memoria_pagamento_existente(
    uow: UnitOfWork,
    emprestimo_id: uuid.UUID,
    pagamento_id: uuid.UUID,
) -> MemoriaCalculo | None:
    memorias = [
        memoria
        for memoria in uow.memoria_calculo.find_by_emprestimo_id(emprestimo_id)
        if memoria.tipo == "pagamento"
    ]
    for memoria in reversed(memorias):
        if memoria.entradas.get("pagamento_id") == str(pagamento_id):
            return memoria
    return memorias[-1] if memorias else None


def _memoria_quitacao_existente(
    uow: UnitOfWork,
    emprestimo_id: uuid.UUID,
) -> MemoriaCalculo | None:
    memorias = [
        memoria
        for memoria in uow.memoria_calculo.find_by_emprestimo_id(emprestimo_id)
        if memoria.tipo == "quitacao"
    ]
    return memorias[-1] if memorias else None


def _renegociacao_replay(
    uow: UnitOfWork,
    *,
    emprestimo: Emprestimo,
    idempotency_key: str,
) -> RenegociacaoResultado:
    memoria = _memoria_renegociacao_existente(uow, emprestimo.id)
    if memoria is None:
        raise IdempotenciaConflitoError(idempotency_key, "resultado de renegociacao ausente")
    novos_parametros = memoria.resultados.get("novos_parametros")
    if not isinstance(novos_parametros, Mapping):
        raise IdempotenciaConflitoError(idempotency_key, "resultado de renegociacao invalido")
    return RenegociacaoResultado(
        emprestimo_id=emprestimo.id,
        tenant_id=emprestimo.tenant_id,
        novos_parametros=dict(novos_parametros),
        memoria=memoria,
    )


def _memoria_renegociacao_existente(
    uow: UnitOfWork,
    emprestimo_id: uuid.UUID,
) -> MemoriaCalculo | None:
    memorias = [
        memoria
        for memoria in uow.memoria_calculo.find_by_emprestimo_id(emprestimo_id)
        if memoria.tipo == "renegociacao"
    ]
    return memorias[-1] if memorias else None


def _validar_pagamento_replay(
    pagamento: Pagamento,
    *,
    idempotency_key: str,
    usuario_id: uuid.UUID,
    recebido_em: datetime,
    valor: Decimal | None = None,
) -> None:
    if pagamento.usuario_id != usuario_id or pagamento.recebido_em != recebido_em:
        raise IdempotenciaConflitoError(idempotency_key, "payload divergente")
    if valor is not None and pagamento.valor_recebido != valor:
        raise IdempotenciaConflitoError(idempotency_key, "payload divergente")


def _persistir_eventos_financeiros_novos(
    uow: UnitOfWork,
    emprestimo: Emprestimo,
) -> None:
    ids_existentes = {
        evento.id for evento in uow.evento_financeiro.find_by_emprestimo_id(emprestimo.id)
    }
    for evento in emprestimo.eventos:
        if isinstance(evento, EventoFinanceiro) and evento.id not in ids_existentes:
            uow.evento_financeiro.save(evento)


def _idempotencia_resultado_json(campo: str, valor: uuid.UUID) -> str:
    return json.dumps({campo: str(valor)})


def _serializar_resultado(resultado: EmprestimoCriadoResultado) -> str:
    return json.dumps(
        {
            "emprestimo_id": str(resultado.emprestimo_id),
            "contrato_id": str(resultado.contrato_id),
            "tenant_id": str(resultado.tenant_id),
            "carteira_id": str(resultado.carteira_id),
            "devedor_id": str(resultado.devedor_id),
            "estado": resultado.estado.value,
            "principal_original": str(resultado.principal_original),
            "moeda": resultado.moeda,
            "parametros_financeiros": resultado.parametros_financeiros,
            "criado_em": resultado.criado_em.isoformat(),
        }
    )


def _desserializar_resultado(conteudo: str | None) -> EmprestimoCriadoResultado:
    if not conteudo:
        raise IdempotenciaConflitoError("?", "resultado ausente no registro")
    dados = json.loads(conteudo)
    bruto = dict(dados["parametros_financeiros"]).get("dia_de_acerto")
    dia_de_acerto = validar_dia_de_acerto(bruto) if bruto is not None else None
    return EmprestimoCriadoResultado(
        emprestimo_id=uuid.UUID(dados["emprestimo_id"]),
        contrato_id=uuid.UUID(dados["contrato_id"]),
        tenant_id=uuid.UUID(dados["tenant_id"]),
        carteira_id=uuid.UUID(dados["carteira_id"]),
        devedor_id=uuid.UUID(dados["devedor_id"]),
        estado=EmprestimoState(dados["estado"]),
        principal_original=Decimal(dados["principal_original"]),
        moeda=dados["moeda"],
        parametros_financeiros=dict(dados["parametros_financeiros"]),
        criado_em=datetime.fromisoformat(dados["criado_em"]),
        # Derivados do calendario, e por isso recalculados no replay em vez de
        # lidos do registro: gravar o proximo acerto o congelaria na data em que
        # a chave foi usada, e um replay meses depois devolveria uma data que ja
        # passou. Nada pendente aqui — este e o resultado de uma criacao.
        dia_de_acerto=dia_de_acerto,
        proximo_acerto_em=(
            proximo_acerto(datetime.now(UTC).date(), dia_de_acerto)
            if dia_de_acerto is not None
            else None
        ),
        acerto_pendente_desde=None,
    )


@dataclass(frozen=True)
class EmprestimoCriadoNoLancamento:
    """Saida do Motor para um lancamento composto (IMP-305, PLAN-027).

    O nome e historico: o plano de parcelas saiu no PLAN-030 e o que sobra e a
    criacao do Emprestimo com a data do primeiro acerto.
    """

    emprestimo_id: uuid.UUID
    primeiro_acerto_em: date
    valor_contratado: Decimal
    moeda: str
    taxa_juros_mensal_percentual: Decimal
    dia_de_acerto: int


def criar_emprestimo_e_plano_em(
    uow: UnitOfWork,
    *,
    saida_logica: object,
    data_referencia: date,
    motor_factory: Callable[[], MotorFinanceiro] = MotorFinanceiro,
) -> EmprestimoCriadoNoLancamento:
    """Cria o Emprestimo e gera o plano dentro de um UnitOfWork ja aberto.

    Existe para que o lancamento composto possa participar da mesma transacao
    sem importar o Motor: quem orquestra recebe esta funcao injetada e nunca
    referencia o modulo financeiro. O calculo continua exclusivo do Motor.
    """
    try:
        emprestimo = Emprestimo.criar_de_contrato_liberado(saida_logica)  # type: ignore[arg-type]
    except ViolacaoInvarianteError as exc:
        raise TransicaoEstadoInvalidaError(uuid.UUID(int=0), "criar_emprestimo", str(exc)) from exc
    uow.emprestimo.save(emprestimo)

    # Emprestimo livre: nao ha plano de parcelas a gerar (DR-004). O que o
    # devedor deve em cada acerto e calculado no momento da consulta, sobre o
    # saldo daquele dia — fixar isso num plano seria congelar um valor que muda
    # a cada amortizacao.
    try:
        primeiro_acerto = emprestimo.proximo_acerto_em(data_referencia)
    except ViolacaoInvarianteError as exc:
        raise TransicaoEstadoInvalidaError(emprestimo.id, "criar_emprestimo", str(exc)) from exc
    if primeiro_acerto is None:
        raise TransicaoEstadoInvalidaError(
            emprestimo.id,
            "criar_emprestimo",
            "dia_de_acerto e obrigatorio no lancamento",
        )
    emprestimo.proximo_vencimento_em = datetime.combine(
        primeiro_acerto, datetime.min.time(), tzinfo=UTC
    )
    uow.emprestimo.save(emprestimo)
    parametros = emprestimo.parametros_financeiros
    try:
        taxa_mensal = TaxaJuros(
            valor=Decimal(str(parametros.get("taxa_juros_mensal"))),
            periodicidade="mensal",
        )
    except (InvalidOperation, ValueError, ViolacaoInvarianteError) as exc:
        raise TransicaoEstadoInvalidaError(
            emprestimo.id,
            "criar_emprestimo",
            "taxa_juros_mensal invalida",
        ) from exc
    dia_de_acerto = emprestimo.dia_de_acerto
    assert dia_de_acerto is not None  # validado ao calcular primeiro_acerto
    return EmprestimoCriadoNoLancamento(
        emprestimo_id=emprestimo.id,
        primeiro_acerto_em=primeiro_acerto,
        valor_contratado=emprestimo.principal_original,
        moeda=emprestimo.moeda,
        taxa_juros_mensal_percentual=taxa_mensal.valor * Decimal("100"),
        dia_de_acerto=dia_de_acerto,
    )
