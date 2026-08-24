"""API operacional das FEATURE-010 e FEATURE-011."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import APIRouter, Depends, Header, HTTPException

from emprestimo.application.autorizacao import AutorizacaoService, Principal
from emprestimo.application.credenciais import CredenciaisService
from emprestimo.application.iam_catalogo import (
    CATALOGO_PERMISSOES,
    CATALOGO_PERMISSOES_VERSAO,
)
from emprestimo.application.perfis_acesso import (
    PerfilResultado,
    PerfisAcessoService,
    PermissoesEfetivasResultado,
)
from emprestimo.presentation.api.dependencies import (
    exigir_permissao,
    get_autorizacao_service,
    get_credenciais_service,
    get_perfis_acesso_service,
    get_principal_atual,
)
from emprestimo.presentation.api.openapi import (
    RESPOSTA_CONFLITO_ESTADO,
    RESPOSTA_RECURSO_NAO_ENCONTRADO,
    RESPOSTAS_PROTEGIDAS,
    combinar_respostas,
)
from emprestimo.presentation.api.schemas import (
    AlterarCredencialRequest,
    ContextoCarteiraResponse,
    ContextoOperacionalResponse,
    ContextoPerfilResponse,
    ContextoTenantResponse,
    ContextoUsuarioResponse,
    CredencialResponse,
    PerfilCreateRequest,
    PerfilResponse,
    PerfilUpdateRequest,
    PermissaoCatalogoItemResponse,
    PermissoesCatalogoResponse,
    PermissoesEfetivasResponse,
    RedefinirCredencialRequest,
)

router = APIRouter(
    prefix="/iam",
    tags=["iam"],
    dependencies=[Depends(get_principal_atual)],
    responses=RESPOSTAS_PROTEGIDAS,
)


def _chave(valor: str | None) -> str:
    if valor is None or not valor.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "codigo": "idempotency_key_ausente",
                "mensagem": "Idempotency-Key obrigatoria",
            },
        )
    return valor.strip()


def _perfil(resultado: PerfilResultado) -> PerfilResponse:
    return PerfilResponse(
        id=resultado.id,
        tenant_id=resultado.tenant_id,
        nome=resultado.nome,
        estado=resultado.estado,
        permissoes=list(resultado.permissoes),
    )


def _permissoes(resultado: PermissoesEfetivasResultado) -> PermissoesEfetivasResponse:
    return PermissoesEfetivasResponse(
        usuario_id=resultado.usuario_id,
        perfil_id=resultado.perfil_id,
        perfil_nome=resultado.perfil_nome,
        permissoes=list(resultado.permissoes),
    )


@router.get(
    "/contexto-atual",
    response_model=ContextoOperacionalResponse,
    responses=combinar_respostas(RESPOSTA_CONFLITO_ESTADO),
)
def consultar_contexto_atual(
    principal: Principal = Depends(get_principal_atual),
    service: AutorizacaoService = Depends(get_autorizacao_service),
) -> ContextoOperacionalResponse:
    resultado = service.consultar_contexto(principal)
    perfil = (
        ContextoPerfilResponse(id=resultado.perfil_id, nome=resultado.perfil_nome)
        if resultado.perfil_id is not None and resultado.perfil_nome is not None
        else None
    )
    return ContextoOperacionalResponse(
        usuario=ContextoUsuarioResponse(
            id=resultado.usuario_id,
            nome=resultado.usuario_nome,
            email=resultado.usuario_email,
        ),
        tenant=ContextoTenantResponse(
            id=resultado.tenant_id,
            nome=resultado.tenant_nome,
            identificador_institucional=resultado.tenant_identificador_institucional,
        ),
        carteira_padrao=ContextoCarteiraResponse(
            id=resultado.carteira_id,
            nome=resultado.carteira_nome,
        ),
        perfil=perfil,
        permissoes=list(resultado.permissoes),
    )


@router.get("/permissoes", response_model=PermissoesCatalogoResponse)
def consultar_catalogo_permissoes(
    _: Principal = Depends(exigir_permissao("perfil.ler")),
) -> PermissoesCatalogoResponse:
    return PermissoesCatalogoResponse(
        versao=CATALOGO_PERMISSOES_VERSAO,
        itens=[
            PermissaoCatalogoItemResponse(
                codigo=permissao.codigo,
                descricao=permissao.descricao,
                grupo=permissao.codigo.split(".", maxsplit=1)[0],
            )
            for permissao in sorted(CATALOGO_PERMISSOES, key=lambda item: item.codigo)
        ],
    )


def _exigir_permissao_perfil(
    operacao: str,
) -> Callable[[uuid.UUID, Principal, PerfisAcessoService, AutorizacaoService], Principal]:
    def dependencia(
        perfil_id: uuid.UUID,
        principal: Principal = Depends(get_principal_atual),
        service: PerfisAcessoService = Depends(get_perfis_acesso_service),
        autorizacao: AutorizacaoService = Depends(get_autorizacao_service),
    ) -> Principal:
        service.consultar(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            perfil_id=perfil_id,
        )
        autorizacao.exigir_permissao(principal, operacao)
        return principal

    return dependencia


def _exigir_permissao_usuario(
    operacao: str,
) -> Callable[[uuid.UUID, Principal, PerfisAcessoService, AutorizacaoService], Principal]:
    def dependencia(
        usuario_id: uuid.UUID,
        principal: Principal = Depends(get_principal_atual),
        service: PerfisAcessoService = Depends(get_perfis_acesso_service),
        autorizacao: AutorizacaoService = Depends(get_autorizacao_service),
    ) -> Principal:
        service.permissoes_efetivas(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            usuario_id=usuario_id,
        )
        autorizacao.exigir_permissao(principal, operacao)
        return principal

    return dependencia


@router.patch(
    "/credencial",
    response_model=CredencialResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def alterar_credencial(
    payload: AlterarCredencialRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(get_principal_atual),
    service: CredenciaisService = Depends(get_credenciais_service),
) -> CredencialResponse:
    resultado = service.alterar_propria(
        tenant_id=principal.tenant_id,
        usuario_id=principal.usuario_id,
        segredo_atual=payload.segredo_atual,
        novo_segredo=payload.novo_segredo,
        idempotency_key=_chave(idempotency_key),
    )
    return CredencialResponse(
        usuario_id=resultado.usuario_id,
        tenant_id=resultado.tenant_id,
        estado=resultado.estado,
    )


@router.post(
    "/usuarios/{usuario_id}/credencial/redefinir",
    response_model=CredencialResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def redefinir_credencial(
    usuario_id: uuid.UUID,
    payload: RedefinirCredencialRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(_exigir_permissao_usuario("credencial.redefinir")),
    service: CredenciaisService = Depends(get_credenciais_service),
) -> CredencialResponse:
    resultado = service.redefinir_usuario(
        tenant_id=principal.tenant_id,
        solicitante_id=principal.usuario_id,
        usuario_id=usuario_id,
        novo_segredo=payload.novo_segredo,
        idempotency_key=_chave(idempotency_key),
    )
    return CredencialResponse(
        usuario_id=resultado.usuario_id,
        tenant_id=resultado.tenant_id,
        estado=resultado.estado,
    )


@router.post("/perfis", status_code=201, response_model=PerfilResponse)
def criar_perfil(
    payload: PerfilCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(exigir_permissao("perfil.gerir")),
    service: PerfisAcessoService = Depends(get_perfis_acesso_service),
) -> PerfilResponse:
    return _perfil(
        service.criar(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            nome=payload.nome,
            idempotency_key=_chave(idempotency_key),
        )
    )


@router.get("/perfis", response_model=list[PerfilResponse])
def listar_perfis(
    principal: Principal = Depends(exigir_permissao("perfil.ler")),
    service: PerfisAcessoService = Depends(get_perfis_acesso_service),
) -> list[PerfilResponse]:
    return [_perfil(item) for item in service.listar(tenant_id=principal.tenant_id)]


@router.get(
    "/perfis/{perfil_id}",
    response_model=PerfilResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def consultar_perfil(
    perfil_id: uuid.UUID,
    principal: Principal = Depends(_exigir_permissao_perfil("perfil.ler")),
    service: PerfisAcessoService = Depends(get_perfis_acesso_service),
) -> PerfilResponse:
    return _perfil(
        service.consultar(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            perfil_id=perfil_id,
        )
    )


@router.patch(
    "/perfis/{perfil_id}",
    response_model=PerfilResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def renomear_perfil(
    perfil_id: uuid.UUID,
    payload: PerfilUpdateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(_exigir_permissao_perfil("perfil.gerir")),
    service: PerfisAcessoService = Depends(get_perfis_acesso_service),
) -> PerfilResponse:
    return _perfil(
        service.renomear(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            perfil_id=perfil_id,
            nome=payload.nome,
            idempotency_key=_chave(idempotency_key),
        )
    )


@router.post(
    "/perfis/{perfil_id}/inativar",
    response_model=PerfilResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def inativar_perfil(
    perfil_id: uuid.UUID,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(_exigir_permissao_perfil("perfil.gerir")),
    service: PerfisAcessoService = Depends(get_perfis_acesso_service),
) -> PerfilResponse:
    return _perfil(
        service.inativar(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            perfil_id=perfil_id,
            idempotency_key=_chave(idempotency_key),
        )
    )


@router.put(
    "/perfis/{perfil_id}/permissoes/{codigo}",
    response_model=PerfilResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def associar_permissao(
    perfil_id: uuid.UUID,
    codigo: str,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(_exigir_permissao_perfil("perfil.gerir")),
    service: PerfisAcessoService = Depends(get_perfis_acesso_service),
) -> PerfilResponse:
    return _perfil(
        service.associar_permissao(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            perfil_id=perfil_id,
            codigo=codigo,
            idempotency_key=_chave(idempotency_key),
        )
    )


@router.delete(
    "/perfis/{perfil_id}/permissoes/{codigo}",
    response_model=PerfilResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def remover_permissao(
    perfil_id: uuid.UUID,
    codigo: str,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(_exigir_permissao_perfil("perfil.gerir")),
    service: PerfisAcessoService = Depends(get_perfis_acesso_service),
) -> PerfilResponse:
    return _perfil(
        service.remover_permissao(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            perfil_id=perfil_id,
            codigo=codigo,
            idempotency_key=_chave(idempotency_key),
        )
    )


@router.put(
    "/usuarios/{usuario_id}/perfil/{perfil_id}",
    response_model=PermissoesEfetivasResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def atribuir_perfil(
    usuario_id: uuid.UUID,
    perfil_id: uuid.UUID,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(_exigir_permissao_usuario("perfil.gerir")),
    service: PerfisAcessoService = Depends(get_perfis_acesso_service),
) -> PermissoesEfetivasResponse:
    return _permissoes(
        service.atribuir_perfil(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            usuario_id=usuario_id,
            perfil_id=perfil_id,
            idempotency_key=_chave(idempotency_key),
        )
    )


@router.delete(
    "/usuarios/{usuario_id}/perfil",
    response_model=PermissoesEfetivasResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def remover_perfil_usuario(
    usuario_id: uuid.UUID,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=255),
    principal: Principal = Depends(_exigir_permissao_usuario("perfil.gerir")),
    service: PerfisAcessoService = Depends(get_perfis_acesso_service),
) -> PermissoesEfetivasResponse:
    return _permissoes(
        service.remover_perfil(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            usuario_id=usuario_id,
            idempotency_key=_chave(idempotency_key),
        )
    )


@router.get(
    "/usuarios/{usuario_id}/permissoes",
    response_model=PermissoesEfetivasResponse,
    responses=combinar_respostas(RESPOSTA_RECURSO_NAO_ENCONTRADO),
)
def permissoes_efetivas(
    usuario_id: uuid.UUID,
    principal: Principal = Depends(_exigir_permissao_usuario("perfil.ler")),
    service: PerfisAcessoService = Depends(get_perfis_acesso_service),
) -> PermissoesEfetivasResponse:
    return _permissoes(
        service.permissoes_efetivas(
            tenant_id=principal.tenant_id,
            executor_id=principal.usuario_id,
            usuario_id=usuario_id,
        )
    )
