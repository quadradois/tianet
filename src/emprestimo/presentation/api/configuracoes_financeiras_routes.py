"""Rotas REST de Configuracoes Financeiras (EPIC-009/P4)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query

from emprestimo.application.autorizacao import Principal
from emprestimo.application.configuracoes_financeiras import (
    CalendarioFinanceiroService,
    CapturaSnapshotConfiguracaoService,
    ConfiguracaoFinanceiraService,
    ConsultaConfiguracaoVigenteService,
    ModalidadeFinanceiraService,
    ParametroFinanceiroInput,
    TaxaFinanceiraInput,
)
from emprestimo.domain.credit.configuracoes_financeiras import (
    CalendarioFinanceiro,
    ConfiguracaoFinanceira,
    ConfiguracaoFinanceiraState,
    ConfiguracaoFinanceiraVigenteV1,
    ModalidadeFinanceira,
    PoliticaArredondamento,
    SnapshotConfiguracaoContratualV1,
)
from emprestimo.presentation.api.configuracoes_financeiras_schemas import (
    CalendarioFinanceiroCreateRequest,
    CalendarioFinanceiroResponse,
    CapturaSnapshotConfiguracaoRequest,
    ConfiguracaoFinanceiraCreateRequest,
    ConfiguracaoFinanceiraResponse,
    ConfiguracaoFinanceiraVigenteResponse,
    DecisaoConfiguracaoRequest,
    ModalidadeFinanceiraCreateRequest,
    ModalidadeFinanceiraResponse,
    ProgramarConfiguracaoRequest,
    SnapshotConfiguracaoContratualResponse,
)
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_calendario_financeiro_service,
    get_captura_snapshot_configuracao_service,
    get_configuracao_financeira_service,
    get_consulta_configuracao_vigente_service,
    get_modalidade_financeira_service,
    get_principal_atual,
)
from emprestimo.presentation.api.openapi import (
    RESPOSTA_CONFLITO_ESTADO,
    RESPOSTAS_PROTEGIDAS_COM_RECURSO,
    combinar_respostas,
)

PERMISSAO_MODALIDADE_GERIR = "configuracoes_financeiras.modalidade.gerir"
PERMISSAO_CALENDARIO_GERIR = "configuracoes_financeiras.calendario.gerir"
PERMISSAO_CONFIG_GERIR = "configuracoes_financeiras.configuracao.gerir"
PERMISSAO_CONFIG_APROVAR = "configuracoes_financeiras.configuracao.aprovar"
PERMISSAO_CONFIG_ATIVAR = "configuracoes_financeiras.configuracao.ativar"
PERMISSAO_CONFIG_LER = "configuracoes_financeiras.configuracao.ler"
PERMISSAO_SNAPSHOT_CAPTURAR = "configuracoes_financeiras.snapshot.capturar"

router = APIRouter(
    prefix="/credit",
    tags=["financial-configurations"],
    dependencies=[Depends(get_principal_atual)],
    responses=RESPOSTAS_PROTEGIDAS_COM_RECURSO,
)


@router.post(
    "/configuracoes-financeiras/modalidades",
    status_code=201,
    response_model=ModalidadeFinanceiraResponse,
    summary="Criar modalidade financeira",
)
def criar_modalidade_financeira(
    payload: ModalidadeFinanceiraCreateRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_MODALIDADE_GERIR)),
    service: ModalidadeFinanceiraService = Depends(get_modalidade_financeira_service),
) -> ModalidadeFinanceiraResponse:
    modalidade = service.criar(
        tenant_id=principal.tenant_id,
        carteira_id=payload.carteira_id,
        usuario_id=principal.usuario_id,
        codigo=payload.codigo,
        nome=payload.nome,
    )
    return _modalidade_response(modalidade)


@router.get(
    "/configuracoes-financeiras/modalidades",
    response_model=list[ModalidadeFinanceiraResponse],
    summary="Listar modalidades financeiras",
)
def listar_modalidades_financeiras(
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONFIG_LER)),
    service: ModalidadeFinanceiraService = Depends(get_modalidade_financeira_service),
) -> list[ModalidadeFinanceiraResponse]:
    return [_modalidade_response(item) for item in service.listar(tenant_id=principal.tenant_id)]


@router.post(
    "/configuracoes-financeiras/calendarios",
    status_code=201,
    response_model=CalendarioFinanceiroResponse,
    summary="Criar calendario financeiro operacional",
)
def criar_calendario_financeiro(
    payload: CalendarioFinanceiroCreateRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CALENDARIO_GERIR)),
    service: CalendarioFinanceiroService = Depends(get_calendario_financeiro_service),
) -> CalendarioFinanceiroResponse:
    calendario = service.criar(
        tenant_id=principal.tenant_id,
        carteira_id=payload.carteira_id,
        usuario_id=principal.usuario_id,
        codigo=payload.codigo,
        nome=payload.nome,
        feriados=tuple(payload.feriados),
    )
    return _calendario_response(calendario)


@router.get(
    "/configuracoes-financeiras/calendarios",
    response_model=list[CalendarioFinanceiroResponse],
    summary="Listar calendarios financeiros operacionais",
)
def listar_calendarios_financeiros(
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONFIG_LER)),
    service: CalendarioFinanceiroService = Depends(get_calendario_financeiro_service),
) -> list[CalendarioFinanceiroResponse]:
    return [_calendario_response(item) for item in service.listar(tenant_id=principal.tenant_id)]


@router.post(
    "/configuracoes-financeiras",
    status_code=201,
    response_model=ConfiguracaoFinanceiraResponse,
    summary="Criar configuracao financeira em rascunho",
)
def criar_configuracao_financeira(
    payload: ConfiguracaoFinanceiraCreateRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONFIG_GERIR)),
    service: ConfiguracaoFinanceiraService = Depends(get_configuracao_financeira_service),
) -> ConfiguracaoFinanceiraResponse:
    configuracao = service.criar_rascunho(
        tenant_id=principal.tenant_id,
        carteira_id=payload.carteira_id,
        usuario_id=principal.usuario_id,
        calendario_id=payload.calendario_id,
        modalidade=payload.modalidade,
        vigencia_inicio=payload.vigencia_inicio,
        vigencia_fim=payload.vigencia_fim,
        taxas=tuple(
            TaxaFinanceiraInput(
                nome=taxa.nome,
                valor=taxa.valor,
                periodicidade=taxa.periodicidade,
            )
            for taxa in payload.taxas
        ),
        parametros=tuple(
            ParametroFinanceiroInput(parametro.nome, parametro.valor)
            for parametro in payload.parametros
        ),
        politica_arredondamento=PoliticaArredondamento(
            payload.politica_arredondamento.modo,
            payload.politica_arredondamento.escala,
        ),
    )
    return _configuracao_response(configuracao)


@router.get(
    "/configuracoes-financeiras",
    response_model=list[ConfiguracaoFinanceiraResponse],
    summary="Listar configuracoes financeiras",
)
def listar_configuracoes_financeiras(
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONFIG_LER)),
    service: ConfiguracaoFinanceiraService = Depends(get_configuracao_financeira_service),
    carteira_id: uuid.UUID | None = Query(default=None),
    modalidade: str | None = Query(default=None, min_length=1, max_length=80),
    estado: ConfiguracaoFinanceiraState | None = Query(default=None),
    data_referencia: date | None = Query(default=None),
) -> list[ConfiguracaoFinanceiraResponse]:
    configuracoes = service.listar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira_id,
        modalidade=modalidade,
        estado=estado,
        data_referencia=data_referencia,
    )
    return [_configuracao_response(configuracao) for configuracao in configuracoes]


@router.get(
    "/configuracoes-financeiras/vigente",
    response_model=ConfiguracaoFinanceiraVigenteResponse,
    summary="Consultar configuracao financeira vigente",
)
def consultar_configuracao_vigente(
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONFIG_LER)),
    service: ConsultaConfiguracaoVigenteService = Depends(
        get_consulta_configuracao_vigente_service
    ),
    modalidade: str = Query(min_length=1, max_length=80),
    data_referencia: date = Query(),
    carteira_id: uuid.UUID | None = Query(default=None),
) -> ConfiguracaoFinanceiraVigenteResponse:
    vigente = service.consultar(
        tenant_id=principal.tenant_id,
        carteira_id=carteira_id,
        modalidade=modalidade,
        data_referencia=data_referencia,
    )
    return _vigente_response(vigente)


@router.post(
    "/configuracoes-financeiras/snapshots",
    response_model=SnapshotConfiguracaoContratualResponse,
    summary="Capturar snapshot contratual da configuracao financeira",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def capturar_snapshot_configuracao(
    payload: CapturaSnapshotConfiguracaoRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_SNAPSHOT_CAPTURAR)),
    service: CapturaSnapshotConfiguracaoService = Depends(
        get_captura_snapshot_configuracao_service
    ),
) -> SnapshotConfiguracaoContratualResponse:
    snapshot = service.capturar(
        configuracao_id=payload.configuracao_id,
        tenant_id=principal.tenant_id,
        usuario_id=principal.usuario_id,
        motivo=payload.motivo,
    )
    return _snapshot_response(snapshot)


@router.get(
    "/configuracoes-financeiras/{configuracao_id}",
    response_model=ConfiguracaoFinanceiraResponse,
    summary="Consultar configuracao financeira por ID",
)
def consultar_configuracao_financeira(
    configuracao_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONFIG_LER)),
    service: ConfiguracaoFinanceiraService = Depends(get_configuracao_financeira_service),
) -> ConfiguracaoFinanceiraResponse:
    return _configuracao_response(
        service.consultar(
            configuracao_id=configuracao_id,
            tenant_id=principal.tenant_id,
        )
    )


@router.post(
    "/configuracoes-financeiras/{configuracao_id}/aprovar",
    response_model=ConfiguracaoFinanceiraResponse,
    summary="Aprovar configuracao financeira",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def aprovar_configuracao_financeira(
    configuracao_id: uuid.UUID,
    payload: DecisaoConfiguracaoRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONFIG_APROVAR)),
    service: ConfiguracaoFinanceiraService = Depends(get_configuracao_financeira_service),
) -> ConfiguracaoFinanceiraResponse:
    return _configuracao_response(
        service.aprovar(
            configuracao_id=configuracao_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
        )
    )


@router.post(
    "/configuracoes-financeiras/{configuracao_id}/programar",
    response_model=ConfiguracaoFinanceiraResponse,
    summary="Programar ativacao de configuracao financeira",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def programar_configuracao_financeira(
    configuracao_id: uuid.UUID,
    payload: ProgramarConfiguracaoRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONFIG_ATIVAR)),
    service: ConfiguracaoFinanceiraService = Depends(get_configuracao_financeira_service),
) -> ConfiguracaoFinanceiraResponse:
    return _configuracao_response(
        service.programar(
            configuracao_id=configuracao_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
            data_ativacao=payload.data_ativacao,
            motivo=payload.motivo,
        )
    )


@router.post(
    "/configuracoes-financeiras/{configuracao_id}/ativar",
    response_model=ConfiguracaoFinanceiraResponse,
    summary="Ativar configuracao financeira",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def ativar_configuracao_financeira(
    configuracao_id: uuid.UUID,
    payload: DecisaoConfiguracaoRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONFIG_ATIVAR)),
    service: ConfiguracaoFinanceiraService = Depends(get_configuracao_financeira_service),
) -> ConfiguracaoFinanceiraResponse:
    return _configuracao_response(
        service.ativar(
            configuracao_id=configuracao_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
        )
    )


@router.post(
    "/configuracoes-financeiras/{configuracao_id}/inativar",
    response_model=ConfiguracaoFinanceiraResponse,
    summary="Inativar configuracao financeira",
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def inativar_configuracao_financeira(
    configuracao_id: uuid.UUID,
    payload: DecisaoConfiguracaoRequest,
    principal: Principal = Depends(exigir_permissao(PERMISSAO_CONFIG_ATIVAR)),
    service: ConfiguracaoFinanceiraService = Depends(get_configuracao_financeira_service),
) -> ConfiguracaoFinanceiraResponse:
    return _configuracao_response(
        service.inativar(
            configuracao_id=configuracao_id,
            tenant_id=principal.tenant_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
        )
    )


def _modalidade_response(modalidade: ModalidadeFinanceira) -> ModalidadeFinanceiraResponse:
    return ModalidadeFinanceiraResponse(
        id=modalidade.id,
        tenant_id=modalidade.tenant_id,
        carteira_id=modalidade.carteira_id,
        codigo=modalidade.codigo.valor,
        nome=modalidade.nome,
        ativa=modalidade.ativa,
    )


def _calendario_response(calendario: CalendarioFinanceiro) -> CalendarioFinanceiroResponse:
    return CalendarioFinanceiroResponse(
        id=calendario.id,
        tenant_id=calendario.tenant_id,
        carteira_id=calendario.carteira_id,
        codigo=calendario.codigo,
        nome=calendario.nome,
        feriados=list(calendario.feriados),
    )


def _configuracao_response(
    configuracao: ConfiguracaoFinanceira,
) -> ConfiguracaoFinanceiraResponse:
    return ConfiguracaoFinanceiraResponse(
        id=configuracao.id,
        tenant_id=configuracao.tenant_id,
        carteira_id=configuracao.carteira_id,
        modalidade=configuracao.modalidade.valor,
        calendario_id=configuracao.calendario_id,
        estado=configuracao.estado,
        versao=configuracao.versao,
        vigencia_inicio=configuracao.vigencia.inicio,
        vigencia_fim=configuracao.vigencia.fim,
        parametros=configuracao.parametros_normalizados,
        criada_por_usuario_id=configuracao.criada_por_usuario_id,
        criada_em=configuracao.criada_em,
        atualizada_em=configuracao.atualizada_em,
        aprovada_por_usuario_id=configuracao.aprovada_por_usuario_id,
        aprovada_em=configuracao.aprovada_em,
        total_eventos=len(configuracao.eventos),
    )


def _vigente_response(
    vigente: ConfiguracaoFinanceiraVigenteV1,
) -> ConfiguracaoFinanceiraVigenteResponse:
    return ConfiguracaoFinanceiraVigenteResponse(
        configuracao_id=vigente.configuracao_id,
        tenant_id=vigente.tenant_id,
        carteira_id=vigente.carteira_id,
        modalidade=vigente.modalidade,
        versao=vigente.versao,
        parametros=dict(vigente.parametros),
        consultada_em=vigente.consultada_em,
    )


def _snapshot_response(
    snapshot: SnapshotConfiguracaoContratualV1,
) -> SnapshotConfiguracaoContratualResponse:
    dados = snapshot.to_dict()
    return SnapshotConfiguracaoContratualResponse(
        configuracao_id=snapshot.configuracao_id,
        tenant_id=snapshot.tenant_id,
        carteira_id=snapshot.carteira_id,
        modalidade=snapshot.modalidade,
        versao=snapshot.versao,
        parametros=dados["parametros"] if isinstance(dados["parametros"], dict) else {},
        hash_parametros=snapshot.hash_parametros,
        capturado_em=snapshot.capturado_em,
        capturado_por_usuario_id=snapshot.capturado_por_usuario_id,
        motivo=snapshot.motivo,
    )
