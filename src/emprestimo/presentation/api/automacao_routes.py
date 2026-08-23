"""Rotas administrativas do EPIC-010."""

from __future__ import annotations

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from emprestimo.application.automacao import AutomacaoAdminService
from emprestimo.application.autorizacao import Principal
from emprestimo.application.notifications import (
    NotificationService,
    TemplateNotificacaoService,
)
from emprestimo.domain.credit.automacao_ports import AutomacaoFiltros
from emprestimo.domain.credit.notifications import (
    SolicitacaoNotificacao,
    TemplateNotificacao,
)
from emprestimo.domain.credit.scheduler import JobAgendado
from emprestimo.presentation.api.automacao_schemas import (
    ConciliacaoRequest,
    JobListResponse,
    JobResponse,
    MotivoRequest,
    NotificacaoListResponse,
    NotificacaoResponse,
    TemplateCreateRequest,
    TemplateListResponse,
    TemplateResponse,
)
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_automacao_admin_service,
    get_notification_service,
    get_principal_atual,
    get_template_notificacao_service,
)
from emprestimo.presentation.api.openapi import (
    RESPOSTA_CONFLITO_ESTADO,
    RESPOSTA_PAYLOAD_INVALIDO,
    RESPOSTA_RECURSO_NAO_ENCONTRADO,
    RESPOSTAS_PROTEGIDAS,
    combinar_respostas,
)

router = APIRouter(
    prefix="/credit",
    tags=["Automacao"],
    dependencies=[Depends(get_principal_atual)],
    responses=combinar_respostas(RESPOSTAS_PROTEGIDAS, RESPOSTA_PAYLOAD_INVALIDO),
)
Page = Annotated[int, Query(ge=1)]
Size = Annotated[int, Query(ge=1, le=100)]


@router.get("/automacao/jobs", response_model=JobListResponse)
def listar_jobs(
    page: Page = 1,
    size: Size = 20,
    carteira_id: uuid.UUID | None = None,
    principal: Principal = Depends(exigir_permissao("automacao.job.consultar")),
    service: AutomacaoAdminService = Depends(get_automacao_admin_service),
) -> JobListResponse:
    result = service.listar(AutomacaoFiltros(principal.tenant_id, carteira_id, page, size))
    return JobListResponse(
        items=[_job_response(item) for item in result.items],
        total=result.total,
        page=page,
        size=size,
        pages=math.ceil(result.total / size) if result.total else 0,
    )


@router.get(
    "/automacao/jobs/{job_id}",
    response_model=JobResponse,
    responses=RESPOSTA_RECURSO_NAO_ENCONTRADO,
)
def obter_job(
    job_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao("automacao.job.consultar")),
    service: AutomacaoAdminService = Depends(get_automacao_admin_service),
) -> JobResponse:
    return _job_response(service.obter(tenant_id=principal.tenant_id, job_id=job_id))


@router.post(
    "/automacao/jobs/{job_id}/cancelar",
    response_model=JobResponse,
    status_code=202,
    responses=combinar_respostas(
        RESPOSTA_RECURSO_NAO_ENCONTRADO,
        RESPOSTA_PAYLOAD_INVALIDO,
        RESPOSTA_CONFLITO_ESTADO,
    ),
)
def cancelar_job(
    job_id: uuid.UUID,
    payload: MotivoRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao("automacao.job.cancelar")),
    service: AutomacaoAdminService = Depends(get_automacao_admin_service),
) -> JobResponse:
    return _job_response(
        service.cancelar(
            tenant_id=principal.tenant_id,
            job_id=job_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
            idempotency_key=idempotency_key,
        )
    )


@router.post(
    "/automacao/jobs/{job_id}/retry",
    response_model=JobResponse,
    status_code=202,
    responses=combinar_respostas(
        RESPOSTA_RECURSO_NAO_ENCONTRADO,
        RESPOSTA_PAYLOAD_INVALIDO,
        RESPOSTA_CONFLITO_ESTADO,
    ),
)
def retry_job(
    job_id: uuid.UUID,
    payload: MotivoRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao("automacao.job.retry")),
    service: AutomacaoAdminService = Depends(get_automacao_admin_service),
) -> JobResponse:
    return _job_response(
        service.retry(
            tenant_id=principal.tenant_id,
            job_id=job_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
            idempotency_key=idempotency_key,
        )
    )


@router.get("/notificacoes", response_model=NotificacaoListResponse)
def listar_notificacoes(
    page: Page = 1,
    size: Size = 20,
    carteira_id: uuid.UUID | None = None,
    principal: Principal = Depends(exigir_permissao("notificacao.consultar")),
    service: NotificationService = Depends(get_notification_service),
) -> NotificacaoListResponse:
    result = service.listar(AutomacaoFiltros(principal.tenant_id, carteira_id, page, size))
    return NotificacaoListResponse(
        items=[_notificacao_response(item) for item in result.items],
        total=result.total,
        page=page,
        size=size,
        pages=math.ceil(result.total / size) if result.total else 0,
    )


@router.get("/notificacoes/templates", response_model=TemplateListResponse)
def listar_templates(
    page: Page = 1,
    size: Size = 20,
    principal: Principal = Depends(exigir_permissao("notificacao.template.gerir")),
    service: TemplateNotificacaoService = Depends(get_template_notificacao_service),
) -> TemplateListResponse:
    result = service.listar(AutomacaoFiltros(principal.tenant_id, None, page, size))
    return TemplateListResponse(
        items=[_template_response(item) for item in result.items],
        total=result.total,
        page=page,
        size=size,
        pages=math.ceil(result.total / size) if result.total else 0,
    )


@router.post(
    "/notificacoes/templates",
    response_model=TemplateResponse,
    status_code=201,
    responses=RESPOSTA_CONFLITO_ESTADO,
)
def criar_template(
    payload: TemplateCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao("notificacao.template.gerir")),
    service: TemplateNotificacaoService = Depends(get_template_notificacao_service),
) -> TemplateResponse:
    item = TemplateNotificacao(
        tenant_id=principal.tenant_id,
        codigo=payload.codigo,
        versao=payload.versao,
        assunto=payload.assunto,
        corpo=payload.corpo,
        parametros_permitidos=payload.parametros_permitidos,
        criado_por_usuario_id=principal.usuario_id,
    )
    return _template_response(service.criar(item, idempotency_key=idempotency_key))


@router.post(
    "/notificacoes/templates/{template_id}/aprovar",
    response_model=TemplateResponse,
    responses=combinar_respostas(
        RESPOSTA_RECURSO_NAO_ENCONTRADO,
        RESPOSTA_PAYLOAD_INVALIDO,
        RESPOSTA_CONFLITO_ESTADO,
    ),
)
def aprovar_template(
    template_id: uuid.UUID,
    payload: MotivoRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao("notificacao.template.gerir")),
    service: TemplateNotificacaoService = Depends(get_template_notificacao_service),
) -> TemplateResponse:
    return _template_response(
        service.aprovar(
            tenant_id=principal.tenant_id,
            template_id=template_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
            idempotency_key=idempotency_key,
        )
    )


@router.post(
    "/notificacoes/templates/{template_id}/ativar",
    response_model=TemplateResponse,
    responses=combinar_respostas(
        RESPOSTA_RECURSO_NAO_ENCONTRADO,
        RESPOSTA_CONFLITO_ESTADO,
    ),
)
def ativar_template(
    template_id: uuid.UUID,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao("notificacao.template.gerir")),
    service: TemplateNotificacaoService = Depends(get_template_notificacao_service),
) -> TemplateResponse:
    return _template_response(
        service.ativar(
            tenant_id=principal.tenant_id,
            template_id=template_id,
            idempotency_key=idempotency_key,
        )
    )


@router.get(
    "/notificacoes/{notification_id}",
    response_model=NotificacaoResponse,
    responses=RESPOSTA_RECURSO_NAO_ENCONTRADO,
)
def obter_notificacao(
    notification_id: uuid.UUID,
    principal: Principal = Depends(exigir_permissao("notificacao.consultar")),
    service: NotificationService = Depends(get_notification_service),
) -> NotificacaoResponse:
    return _notificacao_response(
        service.obter(tenant_id=principal.tenant_id, solicitacao_id=notification_id)
    )


@router.post(
    "/notificacoes/{notification_id}/conciliar",
    response_model=NotificacaoResponse,
    responses=combinar_respostas(
        RESPOSTA_RECURSO_NAO_ENCONTRADO,
        RESPOSTA_PAYLOAD_INVALIDO,
        RESPOSTA_CONFLITO_ESTADO,
    ),
)
def conciliar_notificacao(
    notification_id: uuid.UUID,
    payload: ConciliacaoRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao("notificacao.conciliar")),
    service: NotificationService = Depends(get_notification_service),
) -> NotificacaoResponse:
    return _notificacao_response(
        service.conciliar(
            tenant_id=principal.tenant_id,
            solicitacao_id=notification_id,
            provider_message_id=payload.provider_message_id,
            usuario_id=principal.usuario_id,
            motivo=payload.motivo,
            idempotency_key=idempotency_key,
        )
    )


def _job_response(item: JobAgendado) -> JobResponse:
    return JobResponse(
        id=item.id,
        carteira_id=item.carteira_id,
        tipo=item.tipo,
        origem_tipo=item.origem_tipo,
        origem_id=item.origem_id,
        estado=item.estado,
        executar_em=item.executar_em,
        proxima_execucao_em=item.proxima_execucao_em,
        tentativas=item.tentativas,
        max_tentativas=item.max_tentativas,
        cancelamento_solicitado=item.cancelamento_solicitado,
        correlation_id=item.correlation_id,
    )


def _notificacao_response(item: SolicitacaoNotificacao) -> NotificacaoResponse:
    return NotificacaoResponse(
        id=item.id,
        carteira_id=item.carteira_id,
        lembrete_id=item.lembrete_id,
        job_id=item.job_id,
        estado=item.estado,
        provider_message_id=item.provider_message_id,
        resultado_em=item.resultado_em,
        codigo_resultado=item.codigo_resultado,
    )


def _template_response(item: TemplateNotificacao) -> TemplateResponse:
    return TemplateResponse(
        id=item.id,
        codigo=item.codigo,
        versao=item.versao,
        estado=item.estado,
        hash_conteudo=item.hash_conteudo,
        aprovado_em=item.aprovado_em,
        ativado_em=item.ativado_em,
    )
