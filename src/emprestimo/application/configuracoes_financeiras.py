"""Servicos de aplicacao de Configuracoes Financeiras (EPIC-009/P3)."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from emprestimo.application.auditoria_escrita import auditar_escrita
from emprestimo.application.errors import (
    CalendarioFinanceiroNaoEncontradoError,
    CarteiraNaoEncontradaError,
    ConfiguracaoFinanceiraNaoEncontradaError,
    IdempotenciaConflitoError,
    ModalidadeFinanceiraNaoEncontradaError,
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
from emprestimo.domain.credit.configuracoes_financeiras import (
    CalendarioFinanceiro,
    CodigoModalidadeFinanceira,
    ConfiguracaoFinanceira,
    ConfiguracaoFinanceiraState,
    ConfiguracaoFinanceiraVigenteV1,
    JanelaVigencia,
    ModalidadeFinanceira,
    ParametroFinanceiroConfigurado,
    PoliticaArredondamento,
    SnapshotConfiguracaoContratualV1,
    TaxaFinanceiraConfigurada,
)
from emprestimo.domain.credit.ports import ConfiguracaoFinanceiraFiltros


@dataclass(frozen=True)
class TaxaFinanceiraInput:
    nome: str
    valor: Decimal
    periodicidade: str


@dataclass(frozen=True)
class ParametroFinanceiroInput:
    nome: str
    valor: object


class ModalidadeFinanceiraService:
    """Cria, lista e valida modalidades permitidas por tenant/carteira."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("modalidade_financeira", "criar")
    def criar(
        self,
        *,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        codigo: str,
        nome: str,
        carteira_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> ModalidadeFinanceira:
        with self._uow_factory() as uow:
            _validar_contexto(uow, tenant_id=tenant_id, usuario_id=usuario_id)
            _validar_carteira(uow, tenant_id=tenant_id, carteira_id=carteira_id)
            escopo = "configuracao-financeira-modalidade-criar"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                    "codigo": codigo,
                    "nome": nome,
                    "carteira_id": carteira_id,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    ModalidadeFinanceira,
                    chave=idempotency_key,
                )
            modalidade = ModalidadeFinanceira(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                codigo=CodigoModalidadeFinanceira(codigo),
                nome=nome,
            )
            uow.modalidade_financeira.save(modalidade)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(modalidade),
            )
            uow.commit()
            return modalidade

    def listar(self, *, tenant_id: uuid.UUID) -> list[ModalidadeFinanceira]:
        with self._uow_factory() as uow:
            return uow.modalidade_financeira.listar(tenant_id)

    def validar_existente(self, *, modalidade_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        with self._uow_factory() as uow:
            modalidade = uow.modalidade_financeira.find_by_id(modalidade_id)
            if modalidade is None or modalidade.tenant_id != tenant_id:
                raise ModalidadeFinanceiraNaoEncontradaError(modalidade_id)


class CalendarioFinanceiroService:
    """Administra calendarios e resolve periodos operacionais."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("calendario_financeiro", "criar")
    def criar(
        self,
        *,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        codigo: str,
        nome: str,
        feriados: tuple[date, ...] = (),
        carteira_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> CalendarioFinanceiro:
        with self._uow_factory() as uow:
            _validar_contexto(uow, tenant_id=tenant_id, usuario_id=usuario_id)
            _validar_carteira(uow, tenant_id=tenant_id, carteira_id=carteira_id)
            escopo = "configuracao-financeira-calendario-criar"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                    "codigo": codigo,
                    "nome": nome,
                    "feriados": feriados,
                    "carteira_id": carteira_id,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    CalendarioFinanceiro,
                    chave=idempotency_key,
                )
            calendario = CalendarioFinanceiro(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                codigo=codigo,
                nome=nome,
                feriados=feriados,
            )
            uow.calendario_financeiro.save(calendario)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(calendario),
            )
            uow.commit()
            return calendario

    def resolver_periodo(
        self,
        *,
        calendario_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data_referencia: date,
    ) -> dict[str, object]:
        with self._uow_factory() as uow:
            calendario = _calendario_do_tenant(
                uow,
                calendario_id=calendario_id,
                tenant_id=tenant_id,
            )
            return calendario.resolver_periodo(data_referencia)

    def listar(self, *, tenant_id: uuid.UUID) -> list[CalendarioFinanceiro]:
        with self._uow_factory() as uow:
            return uow.calendario_financeiro.listar(tenant_id)


class ConfiguracaoFinanceiraService:
    """Orquestra ciclo de vida da configuracao financeira."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("configuracao_financeira", "criar_rascunho")
    def criar_rascunho(
        self,
        *,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        calendario_id: uuid.UUID,
        modalidade: str,
        vigencia_inicio: date,
        taxas: tuple[TaxaFinanceiraInput, ...],
        parametros: tuple[ParametroFinanceiroInput, ...],
        politica_arredondamento: PoliticaArredondamento,
        carteira_id: uuid.UUID | None = None,
        vigencia_fim: date | None = None,
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> ConfiguracaoFinanceira:
        with self._uow_factory() as uow:
            _validar_contexto(uow, tenant_id=tenant_id, usuario_id=usuario_id)
            _validar_carteira(uow, tenant_id=tenant_id, carteira_id=carteira_id)
            _calendario_do_tenant(uow, calendario_id=calendario_id, tenant_id=tenant_id)
            escopo = "configuracao-financeira-criar"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                    "calendario_id": calendario_id,
                    "modalidade": modalidade,
                    "vigencia_inicio": vigencia_inicio,
                    "vigencia_fim": vigencia_fim,
                    "taxas": [taxa.__dict__ for taxa in taxas],
                    "parametros": [parametro.__dict__ for parametro in parametros],
                    "politica_arredondamento": {
                        "modo": politica_arredondamento.modo,
                        "escala": politica_arredondamento.escala,
                    },
                    "carteira_id": carteira_id,
                    "correlation_id": correlation_id,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    ConfiguracaoFinanceira,
                    chave=idempotency_key,
                )
            configuracao = ConfiguracaoFinanceira.criar_rascunho(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                modalidade=CodigoModalidadeFinanceira(modalidade),
                calendario_id=calendario_id,
                vigencia=JanelaVigencia(vigencia_inicio, vigencia_fim),
                taxas=tuple(
                    TaxaFinanceiraConfigurada(
                        nome=taxa.nome,
                        valor=taxa.valor,
                        periodicidade=taxa.periodicidade,
                    )
                    for taxa in taxas
                ),
                parametros=tuple(
                    ParametroFinanceiroConfigurado(parametro.nome, parametro.valor)
                    for parametro in parametros
                ),
                politica_arredondamento=politica_arredondamento,
                criada_por_usuario_id=usuario_id,
                correlation_id=correlation_id,
            )
            uow.configuracao_financeira.save(configuracao)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(configuracao),
            )
            uow.commit()
            return configuracao

    @auditar_escrita("configuracao_financeira", "aprovar", identificador="configuracao_id")
    def aprovar(
        self,
        *,
        configuracao_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> ConfiguracaoFinanceira:
        return self._decidir(
            configuracao_id=configuracao_id,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            acao="aprovar",
            motivo=motivo,
            idempotency_key=idempotency_key,
        )

    @auditar_escrita("configuracao_financeira", "programar", identificador="configuracao_id")
    def programar(
        self,
        *,
        configuracao_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        data_ativacao: date,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> ConfiguracaoFinanceira:
        return self._decidir(
            configuracao_id=configuracao_id,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            acao="programar",
            data_ativacao=data_ativacao,
            motivo=motivo,
            idempotency_key=idempotency_key,
        )

    @auditar_escrita("configuracao_financeira", "ativar", identificador="configuracao_id")
    def ativar(
        self,
        *,
        configuracao_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> ConfiguracaoFinanceira:
        return self._decidir(
            configuracao_id=configuracao_id,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            acao="ativar",
            motivo=motivo,
            idempotency_key=idempotency_key,
        )

    @auditar_escrita("configuracao_financeira", "substituir", identificador="configuracao_id")
    def substituir(
        self,
        *,
        configuracao_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> ConfiguracaoFinanceira:
        return self._decidir(
            configuracao_id=configuracao_id,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            acao="substituir",
            motivo=motivo,
            idempotency_key=idempotency_key,
        )

    @auditar_escrita("configuracao_financeira", "inativar", identificador="configuracao_id")
    def inativar(
        self,
        *,
        configuracao_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> ConfiguracaoFinanceira:
        return self._decidir(
            configuracao_id=configuracao_id,
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            acao="inativar",
            motivo=motivo,
            idempotency_key=idempotency_key,
        )

    def consultar(
        self,
        *,
        configuracao_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ConfiguracaoFinanceira:
        with self._uow_factory() as uow:
            return _configuracao_do_tenant(
                uow,
                configuracao_id=configuracao_id,
                tenant_id=tenant_id,
            )

    def listar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID | None = None,
        modalidade: str | None = None,
        estado: ConfiguracaoFinanceiraState | None = None,
        data_referencia: date | None = None,
    ) -> list[ConfiguracaoFinanceira]:
        with self._uow_factory() as uow:
            modalidade_normalizada = (
                CodigoModalidadeFinanceira(modalidade).valor if modalidade is not None else None
            )
            return uow.configuracao_financeira.listar(
                ConfiguracaoFinanceiraFiltros(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    modalidade=modalidade_normalizada,
                    estado=estado,
                    data_referencia=data_referencia,
                )
            )

    def _decidir(
        self,
        *,
        configuracao_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        acao: str,
        motivo: str | None = None,
        data_ativacao: date | None = None,
        idempotency_key: str | None = None,
    ) -> ConfiguracaoFinanceira:
        with self._uow_factory() as uow:
            configuracao = _configuracao_do_tenant(
                uow,
                configuracao_id=configuracao_id,
                tenant_id=tenant_id,
            )
            _validar_contexto(uow, tenant_id=tenant_id, usuario_id=usuario_id)
            escopo = f"configuracao-financeira-{acao}"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "configuracao_id": configuracao_id,
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                    "motivo": motivo,
                    "data_ativacao": data_ativacao,
                },
            )
            if replay is not None:
                return dataclass_do_resultado(
                    replay,
                    ConfiguracaoFinanceira,
                    chave=idempotency_key,
                )
            try:
                if acao == "aprovar":
                    configuracao.aprovar(usuario_id=usuario_id, motivo=motivo)
                elif acao == "programar":
                    if data_ativacao is None:
                        raise ValueError("data_ativacao obrigatoria")
                    configuracao.programar(
                        usuario_id=usuario_id,
                        data_ativacao=data_ativacao,
                        motivo=motivo,
                    )
                elif acao == "ativar":
                    configuracao.ativar(usuario_id=usuario_id, motivo=motivo)
                elif acao == "substituir":
                    configuracao.substituir(usuario_id=usuario_id, motivo=motivo)
                elif acao == "inativar":
                    configuracao.inativar(usuario_id=usuario_id, motivo=motivo)
                else:
                    raise ValueError(f"acao desconhecida: {acao}")
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(configuracao_id, acao, str(exc)) from exc
            uow.configuracao_financeira.save(configuracao)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado=resultado_de_dataclass(configuracao),
            )
            uow.commit()
            return configuracao


class ConsultaConfiguracaoVigenteService:
    """Consulta configuracao vigente por data de referencia."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def consultar(
        self,
        *,
        tenant_id: uuid.UUID,
        modalidade: str,
        data_referencia: date,
        carteira_id: uuid.UUID | None = None,
    ) -> ConfiguracaoFinanceiraVigenteV1:
        with self._uow_factory() as uow:
            encontradas = uow.configuracao_financeira.listar(
                ConfiguracaoFinanceiraFiltros(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    modalidade=CodigoModalidadeFinanceira(modalidade).valor,
                    estado=ConfiguracaoFinanceiraState.ATIVA,
                    data_referencia=data_referencia,
                )
            )
            if not encontradas:
                raise ConfiguracaoFinanceiraNaoEncontradaError(uuid.UUID(int=0))
            if len(encontradas) > 1:
                raise TransicaoEstadoInvalidaError(
                    encontradas[0].id,
                    "consultar_vigente",
                    "mais de uma configuracao vigente encontrada",
                )
            return encontradas[0].gerar_vigente()


class CapturaSnapshotConfiguracaoService:
    """Produz e persiste snapshot contratual imutavel."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork], auditoria: AuditoriaRegistro) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @auditar_escrita("snapshot_configuracao_financeira", "capturar")
    def capturar(
        self,
        *,
        configuracao_id: uuid.UUID,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        motivo: str | None = None,
        idempotency_key: str | None = None,
    ) -> SnapshotConfiguracaoContratualV1:
        with self._uow_factory() as uow:
            _validar_contexto(uow, tenant_id=tenant_id, usuario_id=usuario_id)
            configuracao = _configuracao_do_tenant(
                uow,
                configuracao_id=configuracao_id,
                tenant_id=tenant_id,
            )
            escopo = "configuracao-financeira-snapshot-capturar"
            replay = iniciar_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                solicitacao={
                    "configuracao_id": configuracao_id,
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                    "motivo": motivo,
                },
            )
            if replay is not None:
                return _snapshot_do_resultado(replay, chave=idempotency_key)
            try:
                snapshot = configuracao.capturar_snapshot(usuario_id=usuario_id, motivo=motivo)
            except ViolacaoInvarianteError as exc:
                raise TransicaoEstadoInvalidaError(
                    configuracao_id,
                    "capturar_snapshot",
                    str(exc),
                ) from exc
            uow.configuracao_financeira.save(configuracao)
            uow.configuracao_financeira.save_snapshot(snapshot)
            concluir_idempotencia(
                uow,
                chave=idempotency_key,
                escopo=escopo,
                resultado={"snapshot": snapshot.to_dict()},
            )
            uow.commit()
            return snapshot


class IntegracaoConfiguracaoContratoService:
    """Prepara parametros congelados para Contratos sem chamar Motor."""

    def montar_parametros_contratuais(
        self,
        *,
        snapshot: SnapshotConfiguracaoContratualV1,
        parametros_operacionais: Mapping[str, object],
    ) -> dict[str, object]:
        dados = dict(parametros_operacionais)
        dados["configuracao_financeira_id"] = str(snapshot.configuracao_id)
        dados["snapshot_configuracao_contratual"] = snapshot.to_dict()
        return dados


def _validar_contexto(uow: UnitOfWork, *, tenant_id: uuid.UUID, usuario_id: uuid.UUID) -> None:
    usuario = uow.usuario.find_by_id(usuario_id)
    if usuario is None or usuario.tenant_id != tenant_id:
        raise UsuarioNaoEncontradoError(usuario_id)


def _validar_carteira(
    uow: UnitOfWork,
    *,
    tenant_id: uuid.UUID,
    carteira_id: uuid.UUID | None,
) -> None:
    if carteira_id is None:
        return
    carteira = uow.carteira.find_by_id(carteira_id)
    if carteira is None or carteira.tenant_id != tenant_id:
        raise CarteiraNaoEncontradaError(carteira_id)


def _calendario_do_tenant(
    uow: UnitOfWork,
    *,
    calendario_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> CalendarioFinanceiro:
    calendario = uow.calendario_financeiro.find_by_id(calendario_id)
    if calendario is None or calendario.tenant_id != tenant_id:
        raise CalendarioFinanceiroNaoEncontradoError(calendario_id)
    return calendario


def _configuracao_do_tenant(
    uow: UnitOfWork,
    *,
    configuracao_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ConfiguracaoFinanceira:
    configuracao = uow.configuracao_financeira.find_by_id(configuracao_id)
    if configuracao is None or configuracao.tenant_id != tenant_id:
        raise ConfiguracaoFinanceiraNaoEncontradaError(configuracao_id)
    return configuracao


def _snapshot_do_resultado(
    resultado: Mapping[str, object], *, chave: str | None
) -> SnapshotConfiguracaoContratualV1:
    dados = resultado.get("snapshot")
    if not isinstance(dados, Mapping):
        raise IdempotenciaConflitoError(chave or "<ausente>", "resultado de snapshot ausente")
    try:
        carteira_raw = dados.get("carteira_id")
        parametros = dados["parametros"]
        if not isinstance(parametros, Mapping):
            raise TypeError
        return SnapshotConfiguracaoContratualV1(
            configuracao_id=uuid.UUID(str(dados["configuracao_id"])),
            tenant_id=uuid.UUID(str(dados["tenant_id"])),
            carteira_id=uuid.UUID(str(carteira_raw)) if carteira_raw else None,
            modalidade=str(dados["modalidade"]),
            versao=int(str(dados["versao"])),
            parametros=parametros,
            hash_parametros=str(dados["hash_parametros"]),
            capturado_em=datetime.fromisoformat(str(dados["capturado_em"])),
            capturado_por_usuario_id=uuid.UUID(str(dados["capturado_por_usuario_id"])),
            motivo=str(dados["motivo"]) if dados.get("motivo") is not None else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise IdempotenciaConflitoError(
            chave or "<ausente>", "resultado de snapshot invalido"
        ) from exc
