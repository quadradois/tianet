"""Servicos de aplicacao do contexto Contratos (EPIC-004/P4)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from emprestimo.application.auditoria_escrita import auditar_escrita
from emprestimo.application.errors import (
    CarteiraNaoEncontradaError,
    ContratoCreditoNaoEncontradoError,
    DevedorNaoEncontradoError,
    PropostaComercialNaoEncontradaError,
    TransicaoEstadoInvalidaError,
    UsuarioNaoEncontradoError,
)
from emprestimo.application.idempotencia import (
    concluir_idempotencia,
    dataclass_do_resultado,
    iniciar_idempotencia,
    resultado_de_dataclass,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contrato_credito import ContratoCredito
from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.domain.credit.contrato_liberado import ContratoLiberadoLogico
from emprestimo.domain.credit.decisao_contrato import DecisaoContrato
from emprestimo.domain.credit.devedor import DevedorState
from emprestimo.domain.credit.ports import (
    ContratoCreditoFiltros,
    ContratoCreditoResultadoPaginado,
    Paginacao,
)

ESCOPO_CONTRATO_CRIAR = "contrato-criar"


@dataclass(frozen=True)
class ContratoCreditoResultado:
    contrato_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    proposta_comercial_id: uuid.UUID
    criado_por_usuario_id: uuid.UUID
    estado: ContratoCreditoState
    parametros: dict[str, object]
    criado_em: datetime
    atualizado_em: datetime | None
    formalizado_por_usuario_id: uuid.UUID | None
    formalizado_em: datetime | None
    assinado_por_usuario_id: uuid.UUID | None
    assinado_em: datetime | None
    liberado_por_usuario_id: uuid.UUID | None
    liberado_em: datetime | None
    motivo_encerramento: str | None
    total_eventos: int


class FormalizacaoContratoService:
    """Cria contrato de credito a partir de proposta aprovada."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("contrato_credito", "criar", identificador="proposta_id")
    def criar_de_proposta(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        proposta_comercial_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> ContratoCreditoResultado:
        with self._uow_factory() as uow:
            _validar_carteira_usuario(
                uow,
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                usuario_id=usuario_id,
            )
            proposta = uow.proposta_comercial.find_by_id(proposta_comercial_id)
            if (
                proposta is None
                or proposta.tenant_id != tenant_id
                or proposta.carteira_id != carteira_id
            ):
                raise PropostaComercialNaoEncontradaError(proposta_comercial_id)
            _validar_devedor_ativo(
                uow,
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                devedor_id=proposta.devedor_id,
            )
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=ESCOPO_CONTRATO_CRIAR,
                solicitacao={
                    "tenant_id": tenant_id,
                    "carteira_id": carteira_id,
                    "proposta_comercial_id": proposta_comercial_id,
                    "usuario_id": usuario_id,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    ContratoCreditoResultado,
                    chave=idempotency_key,
                )
            if uow.contrato_credito.find_by_proposta_id(proposta_comercial_id) is not None:
                raise TransicaoEstadoInvalidaError(
                    proposta_comercial_id,
                    "criar_contrato",
                    "proposta ja possui contrato de credito",
                )
            try:
                proposta_aprovada = proposta.gerar_contrato_logico()
                contrato = ContratoCredito.criar_de_proposta_aprovada(
                    proposta=proposta_aprovada,
                    criado_por_usuario_id=usuario_id,
                )
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    proposta_comercial_id, "criar_contrato", str(exc)
                ) from exc
            uow.contrato_credito.save(contrato)
            resultado = _contrato_resultado(contrato)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=ESCOPO_CONTRATO_CRIAR,
                resultado=resultado_de_dataclass(resultado),
            )
            uow.commit()
            return resultado


class ConsultaContratoService:
    """Consulta contratos e historico contratual."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def consultar_contrato(
        self, *, contrato_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ContratoCreditoResultado:
        with self._uow_factory() as uow:
            return _contrato_resultado(
                _contrato_do_tenant(uow, contrato_id=contrato_id, tenant_id=tenant_id)
            )

    def consultar_historico(
        self, *, contrato_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> tuple[DecisaoContrato, ...]:
        with self._uow_factory() as uow:
            contrato = _contrato_do_tenant(uow, contrato_id=contrato_id, tenant_id=tenant_id)
            return contrato.decisoes

    def listar_contratos(
        self,
        *,
        tenant_id: uuid.UUID,
        pagina: int = 1,
        tamanho: int = 20,
        carteira_id: uuid.UUID | None = None,
        devedor_id: uuid.UUID | None = None,
        estado: ContratoCreditoState | None = None,
    ) -> ContratoCreditoResultadoPaginado:
        with self._uow_factory() as uow:
            return uow.contrato_credito.listar_paginado(
                ContratoCreditoFiltros(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    estado=estado,
                ),
                Paginacao(pagina, tamanho),
            )


class AssinaturaContratoService:
    """Registra formalizacao e assinatura contratual."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("contrato_credito", "formalizar", identificador="contrato_id")
    def formalizar(
        self,
        *,
        contrato_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> ContratoCreditoResultado:
        return self._decidir(contrato_id, tenant_id, usuario_id, "formalizar", idempotency_key)

    @auditar_escrita("contrato_credito", "assinar", identificador="contrato_id")
    def assinar(
        self,
        *,
        contrato_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> ContratoCreditoResultado:
        return self._decidir(contrato_id, tenant_id, usuario_id, "assinar", idempotency_key)

    def _decidir(
        self,
        contrato_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        acao: str,
        idempotency_key: str | None = None,
    ) -> ContratoCreditoResultado:
        with self._uow_factory() as uow:
            contrato = _contrato_do_tenant(uow, contrato_id=contrato_id, tenant_id=tenant_id)
            _validar_usuario(uow, tenant_id=tenant_id, usuario_id=usuario_id)
            escopo = f"contrato-{acao}"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "contrato_id": contrato_id,
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    ContratoCreditoResultado,
                    chave=idempotency_key,
                )
            try:
                if acao == "formalizar":
                    contrato.formalizar(usuario_id=usuario_id)
                else:
                    if contrato.estado is ContratoCreditoState.RASCUNHO:
                        contrato.formalizar(usuario_id=usuario_id)
                    contrato.assinar(usuario_id=usuario_id)
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(contrato.id, acao, str(exc)) from exc
            uow.contrato_credito.save(contrato)
            resultado = _contrato_resultado(contrato)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(resultado),
            )
            uow.commit()
            return resultado


class LiberacaoContratoService:
    """Entrega contrato liberado como saida logica para Motor futuro."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("contrato_credito", "liberar", identificador="contrato_id")
    def liberar_para_motor(
        self,
        *,
        contrato_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> ContratoLiberadoLogico:
        with self._uow_factory() as uow:
            contrato = _contrato_do_tenant(uow, contrato_id=contrato_id, tenant_id=tenant_id)
            _validar_usuario(uow, tenant_id=tenant_id, usuario_id=usuario_id)
            escopo = "contrato-liberar-para-motor"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "contrato_id": contrato_id,
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    ContratoLiberadoLogico,
                    chave=idempotency_key,
                )
            try:
                saida = contrato.liberar_para_motor(usuario_id=usuario_id)
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(contrato.id, "liberar", str(exc)) from exc
            uow.contrato_credito.save(contrato)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(saida),
            )
            uow.commit()
            return saida


class CancelamentoEncerramentoContratoService:
    """Cancela ou encerra contratos conforme estado."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("contrato_credito", "cancelar", identificador="contrato_id")
    def cancelar(
        self,
        *,
        contrato_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> ContratoCreditoResultado:
        return self._decidir(
            contrato_id,
            tenant_id,
            usuario_id,
            "cancelar",
            motivo=motivo,
            idempotency_key=idempotency_key,
        )

    @auditar_escrita("contrato_credito", "encerrar", identificador="contrato_id")
    def encerrar(
        self,
        *,
        contrato_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> ContratoCreditoResultado:
        return self._decidir(
            contrato_id,
            tenant_id,
            usuario_id,
            "encerrar",
            motivo=motivo,
            idempotency_key=idempotency_key,
        )

    def _decidir(
        self,
        contrato_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        acao: str,
        *,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> ContratoCreditoResultado:
        with self._uow_factory() as uow:
            contrato = _contrato_do_tenant(uow, contrato_id=contrato_id, tenant_id=tenant_id)
            _validar_usuario(uow, tenant_id=tenant_id, usuario_id=usuario_id)
            escopo = f"contrato-{acao}"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "contrato_id": contrato_id,
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                    "motivo": motivo,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    ContratoCreditoResultado,
                    chave=idempotency_key,
                )
            try:
                if acao == "cancelar":
                    contrato.cancelar(usuario_id=usuario_id, motivo=motivo)
                else:
                    contrato.encerrar(usuario_id=usuario_id, motivo=motivo)
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(contrato.id, acao, str(exc)) from exc
            uow.contrato_credito.save(contrato)
            resultado = _contrato_resultado(contrato)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(resultado),
            )
            uow.commit()
            return resultado


def _validar_carteira_usuario(
    uow: UnitOfWork,
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> None:
    carteira = uow.carteira.find_by_id(carteira_id)
    if carteira is None or carteira.tenant_id != tenant_id:
        raise CarteiraNaoEncontradaError(carteira_id)
    _validar_usuario(uow, tenant_id=tenant_id, usuario_id=usuario_id)


def _validar_usuario(uow: UnitOfWork, *, tenant_id: uuid.UUID, usuario_id: uuid.UUID) -> None:
    usuario = uow.usuario.find_by_id(usuario_id)
    if usuario is None or usuario.tenant_id != tenant_id:
        raise UsuarioNaoEncontradoError(usuario_id)


def _validar_devedor_ativo(
    uow: UnitOfWork,
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    devedor_id: uuid.UUID,
) -> None:
    devedor = uow.devedor.find_by_id(devedor_id)
    if devedor is None or devedor.carteira_id != carteira_id:
        raise DevedorNaoEncontradoError(devedor_id)
    carteira = uow.carteira.find_by_id(carteira_id)
    if carteira is None or carteira.tenant_id != tenant_id:
        raise CarteiraNaoEncontradaError(carteira_id)
    if devedor.estado is not DevedorState.ATIVO:
        raise ViolacaoInvarianteError(
            "US-054",
            "Devedor inativo nao pode originar contrato de credito",
        )


def _contrato_do_tenant(
    uow: UnitOfWork, *, contrato_id: uuid.UUID, tenant_id: uuid.UUID
) -> ContratoCredito:
    contrato = uow.contrato_credito.find_by_id(contrato_id)
    if contrato is None or contrato.tenant_id != tenant_id:
        raise ContratoCreditoNaoEncontradoError(contrato_id)
    return contrato


def _contrato_resultado(contrato: ContratoCredito) -> ContratoCreditoResultado:
    return ContratoCreditoResultado(
        contrato_id=contrato.id,
        tenant_id=contrato.tenant_id,
        carteira_id=contrato.carteira_id,
        devedor_id=contrato.devedor_id,
        proposta_comercial_id=contrato.proposta_comercial_id,
        criado_por_usuario_id=contrato.criado_por_usuario_id,
        estado=contrato.estado,
        parametros=contrato.parametros,
        criado_em=contrato.criado_em,
        atualizado_em=contrato.atualizado_em,
        formalizado_por_usuario_id=contrato.formalizado_por_usuario_id,
        formalizado_em=contrato.formalizado_em,
        assinado_por_usuario_id=contrato.assinado_por_usuario_id,
        assinado_em=contrato.assinado_em,
        liberado_por_usuario_id=contrato.liberado_por_usuario_id,
        liberado_em=contrato.liberado_em,
        motivo_encerramento=contrato.motivo_encerramento,
        total_eventos=len(contrato.decisoes),
    )
