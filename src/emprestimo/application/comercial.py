"""Servicos de aplicacao do contexto Comercial (EPIC-003/P4)."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

from emprestimo.application.auditoria_escrita import auditar_escrita
from emprestimo.application.errors import (
    CarteiraNaoEncontradaError,
    DevedorNaoEncontradoError,
    PropostaComercialNaoEncontradaError,
    SimulacaoComercialNaoEncontradaError,
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
from emprestimo.domain.credit.devedor import DevedorState
from emprestimo.domain.credit.ports import (
    Paginacao,
    PropostaComercialFiltros,
    PropostaComercialResultadoPaginado,
)
from emprestimo.domain.credit.proposta_aprovada import PropostaAprovadaLogica
from emprestimo.domain.credit.proposta_comercial import PropostaComercial
from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState
from emprestimo.domain.credit.simulacao_comercial import SimulacaoComercial

ESCOPO_SIMULACAO = "comercial-simulacao-criar"
ESCOPO_PROPOSTA_CRIAR = "comercial-proposta-criar"
ESCOPO_PROPOSTA_ATUALIZAR = "comercial-proposta-atualizar"


@dataclass(frozen=True)
class SimulacaoComercialResultado:
    simulacao_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    criada_por_usuario_id: uuid.UUID
    parametros: dict[str, object]
    criado_em: datetime


@dataclass(frozen=True)
class PropostaComercialResultado:
    proposta_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    criada_por_usuario_id: uuid.UUID
    simulacao_id: uuid.UUID | None
    estado: PropostaComercialState
    parametros: dict[str, object]
    criado_em: datetime
    atualizado_em: datetime | None
    aprovada_por_usuario_id: uuid.UUID | None
    aprovada_em: datetime | None
    total_decisoes: int


class SimulacaoComercialService:
    """Cria simulacoes comerciais nao vinculantes."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("simulacao_comercial", "criar")
    def criar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        parametros: Mapping[str, object],
        idempotency_key: str | None = None,
    ) -> SimulacaoComercialResultado:
        with self._uow_factory() as uow:
            _validar_contexto(
                uow,
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                devedor_id=devedor_id,
                usuario_id=usuario_id,
            )
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=ESCOPO_SIMULACAO,
                solicitacao={
                    "tenant_id": tenant_id,
                    "carteira_id": carteira_id,
                    "devedor_id": devedor_id,
                    "usuario_id": usuario_id,
                    "parametros": parametros,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    SimulacaoComercialResultado,
                    chave=idempotency_key,
                )
            simulacao = SimulacaoComercial.criar(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                devedor_id=devedor_id,
                criada_por_usuario_id=usuario_id,
                parametros=parametros,
            )
            uow.simulacao_comercial.save(simulacao)
            resultado = _simulacao_resultado(simulacao)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=ESCOPO_SIMULACAO,
                resultado=resultado_de_dataclass(resultado),
            )
            uow.commit()
            return resultado


class PropostaComercialService:
    """Cria e atualiza propostas comerciais antes do estado terminal."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("proposta_comercial", "criar")
    def criar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        parametros: Mapping[str, object],
        simulacao_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> PropostaComercialResultado:
        with self._uow_factory() as uow:
            _validar_contexto(
                uow,
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                devedor_id=devedor_id,
                usuario_id=usuario_id,
            )
            if simulacao_id is not None:
                simulacao = _simulacao_do_contexto(
                    uow,
                    simulacao_id=simulacao_id,
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                )
                parametros = parametros if parametros else simulacao.parametros
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=ESCOPO_PROPOSTA_CRIAR,
                solicitacao={
                    "tenant_id": tenant_id,
                    "carteira_id": carteira_id,
                    "devedor_id": devedor_id,
                    "usuario_id": usuario_id,
                    "parametros": parametros,
                    "simulacao_id": simulacao_id,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    PropostaComercialResultado,
                    chave=idempotency_key,
                )
            proposta = PropostaComercial.criar(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                devedor_id=devedor_id,
                criada_por_usuario_id=usuario_id,
                parametros=parametros,
                simulacao_id=simulacao_id,
            )
            uow.proposta_comercial.save(proposta)
            resultado = _proposta_resultado(proposta)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=ESCOPO_PROPOSTA_CRIAR,
                resultado=resultado_de_dataclass(resultado),
            )
            uow.commit()
            return resultado

    @auditar_escrita("proposta_comercial", "atualizar_parametros", identificador="proposta_id")
    def atualizar_parametros(
        self,
        *,
        proposta_id: uuid.UUID,
        tenant_id: uuid.UUID,
        parametros: Mapping[str, object],
        idempotency_key: str | None = None,
    ) -> PropostaComercialResultado:
        with self._uow_factory() as uow:
            proposta = _proposta_do_tenant(uow, proposta_id=proposta_id, tenant_id=tenant_id)
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=ESCOPO_PROPOSTA_ATUALIZAR,
                solicitacao={
                    "proposta_id": proposta_id,
                    "tenant_id": tenant_id,
                    "parametros": parametros,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    PropostaComercialResultado,
                    chave=idempotency_key,
                )
            proposta.atualizar_parametros(parametros)
            uow.proposta_comercial.save(proposta)
            resultado = _proposta_resultado(proposta)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=ESCOPO_PROPOSTA_ATUALIZAR,
                resultado=resultado_de_dataclass(resultado),
            )
            uow.commit()
            return resultado


class ConsultaComercialService:
    """Consulta simulacoes e propostas comerciais."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def consultar_simulacao(
        self, *, simulacao_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SimulacaoComercialResultado:
        with self._uow_factory() as uow:
            simulacao = uow.simulacao_comercial.find_by_id(simulacao_id)
            if simulacao is None or simulacao.tenant_id != tenant_id:
                raise SimulacaoComercialNaoEncontradaError(simulacao_id)
            return _simulacao_resultado(simulacao)

    def consultar_proposta(
        self, *, proposta_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PropostaComercialResultado:
        with self._uow_factory() as uow:
            return _proposta_resultado(
                _proposta_do_tenant(uow, proposta_id=proposta_id, tenant_id=tenant_id)
            )

    def listar_propostas(
        self,
        *,
        tenant_id: uuid.UUID,
        pagina: int = 1,
        tamanho: int = 20,
        carteira_id: uuid.UUID | None = None,
        devedor_id: uuid.UUID | None = None,
        estado: PropostaComercialState | None = None,
    ) -> PropostaComercialResultadoPaginado:
        with self._uow_factory() as uow:
            return uow.proposta_comercial.listar_paginado(
                PropostaComercialFiltros(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor_id,
                    estado=estado,
                ),
                Paginacao(pagina, tamanho),
            )


class DecisaoComercialService:
    """Orquestra decisoes de fluxo de proposta comercial."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("proposta_comercial", "enviar_para_analise", identificador="proposta_id")
    def enviar_para_analise(
        self,
        *,
        proposta_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> PropostaComercialResultado:
        return self._decidir(
            proposta_id, tenant_id, usuario_id, "enviar", idempotency_key=idempotency_key
        )

    @auditar_escrita("proposta_comercial", "aprovar", identificador="proposta_id")
    def aprovar(
        self,
        *,
        proposta_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> PropostaComercialResultado:
        return self._decidir(
            proposta_id, tenant_id, usuario_id, "aprovar", idempotency_key=idempotency_key
        )

    @auditar_escrita("proposta_comercial", "recusar", identificador="proposta_id")
    def recusar(
        self,
        *,
        proposta_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> PropostaComercialResultado:
        return self._decidir(
            proposta_id,
            tenant_id,
            usuario_id,
            "recusar",
            motivo=motivo,
            idempotency_key=idempotency_key,
        )

    @auditar_escrita("proposta_comercial", "cancelar", identificador="proposta_id")
    def cancelar(
        self,
        *,
        proposta_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> PropostaComercialResultado:
        return self._decidir(
            proposta_id,
            tenant_id,
            usuario_id,
            "cancelar",
            motivo=motivo,
            idempotency_key=idempotency_key,
        )

    @auditar_escrita("proposta_comercial", "expirar", identificador="proposta_id")
    def expirar(
        self,
        *,
        proposta_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> PropostaComercialResultado:
        return self._decidir(
            proposta_id, tenant_id, usuario_id, "expirar", idempotency_key=idempotency_key
        )

    def _decidir(
        self,
        proposta_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        acao: str,
        *,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> PropostaComercialResultado:
        with self._uow_factory() as uow:
            proposta = _proposta_do_tenant(uow, proposta_id=proposta_id, tenant_id=tenant_id)
            usuario = uow.usuario.find_by_id(usuario_id)
            if usuario is None or usuario.tenant_id != tenant_id:
                raise UsuarioNaoEncontradoError(usuario_id)
            escopo = f"comercial-proposta-{acao}"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "proposta_id": proposta_id,
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                    "motivo": motivo,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    PropostaComercialResultado,
                    chave=idempotency_key,
                )
            try:
                if acao == "enviar":
                    proposta.enviar_para_analise(usuario_id=usuario_id)
                elif acao == "aprovar":
                    proposta.aprovar(usuario_id=usuario_id)
                elif acao == "recusar":
                    proposta.recusar(usuario_id=usuario_id, motivo=motivo)
                elif acao == "cancelar":
                    proposta.cancelar(usuario_id=usuario_id, motivo=motivo)
                else:
                    proposta.expirar(usuario_id=usuario_id)
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(proposta.id, acao, str(exc)) from exc
            uow.proposta_comercial.save(proposta)
            resultado = _proposta_resultado(proposta)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(resultado),
            )
            uow.commit()
            return resultado


class IntegracaoPropostaAprovadaService:
    """Entrega o contrato logico de uma proposta aprovada para integracao futura."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def gerar_contrato_logico(
        self, *, proposta_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> PropostaAprovadaLogica:
        with self._uow_factory() as uow:
            proposta = _proposta_do_tenant(uow, proposta_id=proposta_id, tenant_id=tenant_id)
            return proposta.gerar_contrato_logico()


def _validar_contexto(
    uow: UnitOfWork,
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    devedor_id: uuid.UUID,
    usuario_id: uuid.UUID,
) -> None:
    carteira = uow.carteira.find_by_id(carteira_id)
    if carteira is None or carteira.tenant_id != tenant_id:
        raise CarteiraNaoEncontradaError(carteira_id)
    devedor = uow.devedor.find_by_id(devedor_id)
    if devedor is None or devedor.carteira_id != carteira_id:
        raise DevedorNaoEncontradoError(devedor_id)
    if devedor.estado is not DevedorState.ATIVO:
        raise ViolacaoInvarianteError(
            "US-046",
            "Devedor inativo nao pode originar simulacao ou proposta comercial",
        )
    usuario = uow.usuario.find_by_id(usuario_id)
    if usuario is None or usuario.tenant_id != tenant_id:
        raise UsuarioNaoEncontradoError(usuario_id)


def _simulacao_do_contexto(
    uow: UnitOfWork,
    *,
    simulacao_id: uuid.UUID,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID,
    devedor_id: uuid.UUID,
) -> SimulacaoComercial:
    simulacao = uow.simulacao_comercial.find_by_id(simulacao_id)
    if (
        simulacao is None
        or simulacao.tenant_id != tenant_id
        or simulacao.carteira_id != carteira_id
        or simulacao.devedor_id != devedor_id
    ):
        raise SimulacaoComercialNaoEncontradaError(simulacao_id)
    return simulacao


def _proposta_do_tenant(
    uow: UnitOfWork, *, proposta_id: uuid.UUID, tenant_id: uuid.UUID
) -> PropostaComercial:
    proposta = uow.proposta_comercial.find_by_id(proposta_id)
    if proposta is None or proposta.tenant_id != tenant_id:
        raise PropostaComercialNaoEncontradaError(proposta_id)
    return proposta


def _simulacao_resultado(simulacao: SimulacaoComercial) -> SimulacaoComercialResultado:
    return SimulacaoComercialResultado(
        simulacao_id=simulacao.id,
        tenant_id=simulacao.tenant_id,
        carteira_id=simulacao.carteira_id,
        devedor_id=simulacao.devedor_id,
        criada_por_usuario_id=simulacao.criada_por_usuario_id,
        parametros=simulacao.parametros,
        criado_em=simulacao.criado_em,
    )


def _proposta_resultado(proposta: PropostaComercial) -> PropostaComercialResultado:
    return PropostaComercialResultado(
        proposta_id=proposta.id,
        tenant_id=proposta.tenant_id,
        carteira_id=proposta.carteira_id,
        devedor_id=proposta.devedor_id,
        criada_por_usuario_id=proposta.criada_por_usuario_id,
        simulacao_id=proposta.simulacao_id,
        estado=proposta.estado,
        parametros=proposta.parametros,
        criado_em=proposta.criado_em,
        atualizado_em=proposta.atualizado_em,
        aprovada_por_usuario_id=proposta.aprovada_por_usuario_id,
        aprovada_em=proposta.aprovada_em,
        total_decisoes=len(proposta.decisoes),
    )
