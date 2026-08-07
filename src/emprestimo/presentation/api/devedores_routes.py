"""Rotas da API do Credit Context — Devedor (IMP-057, IMP-058, IMP-059).

A camada Presentation apenas: valida entrada (header/body/query), monta DTOs,
chama os casos de uso da Application e converte o resultado em resposta HTTP.
Nenhuma regra de negócio existe aqui — erros de domínio/aplicação são
traduzidos por exception handlers registrados no app (main.py).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from emprestimo.application.atualizacao_devedor import DevedorAtualizacaoService
from emprestimo.application.cadastro_devedor import DevedorCadastroService
from emprestimo.application.consulta_devedor import (
    DevedorConsultaPorDocumentoService,
    DevedorConsultaService,
    DevedorListagemService,
)
from emprestimo.application.estado_devedor import DevedorEstadoService
from emprestimo.application.historico_devedor import DevedorHistoricoService
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.ports import DevedorFiltros
from emprestimo.presentation.api.dependencies import (
    get_devedor_atualizacao_service,
    get_devedor_cadastro_service,
    get_devedor_consulta_por_documento_service,
    get_devedor_consulta_service,
    get_devedor_da_carteira,
    get_devedor_estado_service,
    get_devedor_historico_service,
    get_devedor_listagem_service,
)
from emprestimo.presentation.api.devedores_schemas import (
    ContatoResponse,
    DevedorCreateRequest,
    DevedorHistoricoResponse,
    DevedorListagemParams,
    DevedorListagemResponse,
    DevedorResponse,
    DevedorUpdateRequest,
    EventoHistoricoResponse,
)

router = APIRouter(prefix="/credit", tags=["credit"])


def _exigir_idempotency_key(idempotency_key: str | None) -> str:
    """Valida a presença do header Idempotency-Key em operações de escrita (AD-002)."""
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "codigo": "idempotency_key_ausente",
                "mensagem": "Header Idempotency-Key é obrigatório",
            },
        )
    return idempotency_key.strip()


def _nao_encontrado() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"codigo": "devedor_nao_encontrado", "mensagem": "Devedor inexistente"},
    )


def _de_aggregate(devedor: Devedor) -> DevedorResponse:
    """Converte o Aggregate em DTO público (RA-012)."""
    return DevedorResponse(
        id=devedor.id,
        carteira_id=devedor.carteira_id,
        documento=devedor.documento.valor,
        nome=devedor.nome,
        contatos=[
            ContatoResponse(tipo=c.tipo, valor=c.valor, preferencial=c.preferencial)
            for c in devedor.contatos
        ],
        estado=devedor.estado,
        criado_em=devedor.criado_em,
        atualizado_em=devedor.atualizado_em,
    )


@router.post(
    "/carteiras/{carteira_id}/devedores",
    status_code=201,
    response_model=DevedorResponse,
    summary="Cadastrar um Devedor na Carteira (IMP-057, US-015..US-020)",
)
def criar_devedor(
    carteira_id: uuid.UUID,
    payload: DevedorCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: DevedorCadastroService = Depends(get_devedor_cadastro_service),
) -> DevedorResponse:
    """Cadastra um Devedor na Carteira (FEATURE-005, AD-002).

    Documento duplicado na Carteira responde 409 ``devedor_ja_existe``; violação
    de regra cadastral responde 422 ``regra_violada`` (handlers do main.py).
    """
    chave = _exigir_idempotency_key(idempotency_key)
    resultado = service.criar(
        carteira_id=carteira_id,
        documento=payload.documento,
        nome=payload.nome,
        contatos=[c.model_dump() for c in payload.contatos],
        idempotency_key=chave,
    )
    return DevedorResponse(
        id=resultado.devedor_id,
        carteira_id=resultado.carteira_id,
        documento=resultado.documento,
        nome=resultado.nome,
        contatos=[ContatoResponse(**c) for c in resultado.contatos],
        estado=resultado.estado,
        criado_em=resultado.criado_em,
    )


@router.get(
    "/carteiras/{carteira_id}/devedores",
    response_model=DevedorListagemResponse | DevedorResponse,
    summary="Consultar por documento (IMP-058, US-022) ou listar (US-023)",
)
def consultar_ou_listar_devedores(
    carteira_id: uuid.UUID,
    documento: str | None = Query(
        default=None,
        min_length=1,
        max_length=20,
        description="Consulta exata por documento na Carteira (US-022)",
    ),
    params: DevedorListagemParams = Depends(),
    service_documento: DevedorConsultaPorDocumentoService = Depends(
        get_devedor_consulta_por_documento_service
    ),
    service_listagem: DevedorListagemService = Depends(get_devedor_listagem_service),
) -> DevedorListagemResponse | DevedorResponse:
    """Consulta exata por documento (200/404) ou listagem paginada da Carteira."""
    if documento is not None:
        devedor = service_documento.consultar_por_documento(carteira_id, documento.strip())
        if devedor is None:
            raise _nao_encontrado()
        return _de_aggregate(devedor)

    filtros = DevedorFiltros(
        nome=params.nome,
        estado=params.estado.value if params.estado else None,
    )
    resultado = service_listagem.listar(
        carteira_id=carteira_id,
        pagina=params.page,
        tamanho=params.size,
        filtros=filtros,
    )
    return DevedorListagemResponse(
        items=[_de_aggregate(d) for d in resultado.items],
        total=resultado.total,
        page=resultado.pagina,
        size=resultado.tamanho,
        pages=resultado.paginas,
    )


@router.get(
    "/carteiras/{carteira_id}/devedores/{devedor_id}",
    response_model=DevedorResponse,
    summary="Consultar um Devedor por ID (IMP-058, US-021)",
)
def obter_devedor_por_id(
    devedor: Devedor = Depends(get_devedor_da_carteira),
) -> DevedorResponse:
    """Retorna o Devedor com seus contatos e estado (leitura, sem auditoria).

    A dependência já resolveu o Devedor e validou a pertinência à Carteira
    (ADR-018); nada resta ao handler além da conversão para DTO.
    """
    return _de_aggregate(devedor)


@router.get(
    "/carteiras/{carteira_id}/devedores/{devedor_id}/historico",
    response_model=DevedorHistoricoResponse,
    summary="Consultar o histórico cadastral do Devedor (IMP-059, US-027)",
)
def obter_historico_devedor(
    devedor: Devedor = Depends(get_devedor_da_carteira),
    service: DevedorHistoricoService = Depends(get_devedor_historico_service),
) -> DevedorHistoricoResponse:
    """Trilha de auditoria do Devedor em ordem cronológica (FEATURE-006).

    Consulta pura: não gera trilha (ADR-002 — somente escrita é auditada).
    """
    eventos = service.consultar(devedor.id)
    if eventos is None:
        raise _nao_encontrado()
    return DevedorHistoricoResponse(
        devedor_id=devedor.id,
        eventos=[
            EventoHistoricoResponse(
                acao=e.acao,
                status=e.status,
                detalhes=e.detalhes,
                criado_em=e.criado_em,
            )
            for e in eventos
        ],
    )


@router.patch(
    "/carteiras/{carteira_id}/devedores/{devedor_id}",
    response_model=DevedorResponse,
    summary="Atualizar dados cadastrais do Devedor (IMP-059, US-024)",
)
def atualizar_devedor(
    payload: DevedorUpdateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    devedor: Devedor = Depends(get_devedor_da_carteira),
    service: DevedorAtualizacaoService = Depends(get_devedor_atualizacao_service),
    consulta: DevedorConsultaService = Depends(get_devedor_consulta_service),
) -> DevedorResponse:
    """Atualização parcial de nome e/ou contatos (FEATURE-007).

    O documento é imutável (INV-003) e não é aceito no payload. Quando
    ``contatos`` é informado, substitui a coleção inteira.
    """
    chave = _exigir_idempotency_key(idempotency_key)
    service.atualizar(
        devedor.id,
        chave,
        nome=payload.nome,
        contatos=(
            [c.model_dump() for c in payload.contatos] if payload.contatos is not None else None
        ),
    )
    return _reler_devedor(devedor.id, consulta)


@router.post(
    "/carteiras/{carteira_id}/devedores/{devedor_id}/inativar",
    response_model=DevedorResponse,
    summary="Inativar um Devedor (IMP-059, US-025)",
)
def inativar_devedor(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    devedor: Devedor = Depends(get_devedor_da_carteira),
    service: DevedorEstadoService = Depends(get_devedor_estado_service),
    consulta: DevedorConsultaService = Depends(get_devedor_consulta_service),
) -> DevedorResponse:
    """Transição Ativo → Inativo (FEATURE-008).

    Sem corpo de request. Transição inválida responde 422 ``regra_violada``
    (INV-005, decidida no Aggregate).
    """
    chave = _exigir_idempotency_key(idempotency_key)
    service.inativar(devedor.id, chave)
    return _reler_devedor(devedor.id, consulta)


@router.post(
    "/carteiras/{carteira_id}/devedores/{devedor_id}/reativar",
    response_model=DevedorResponse,
    summary="Reativar um Devedor (IMP-059, US-026)",
)
def reativar_devedor(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    devedor: Devedor = Depends(get_devedor_da_carteira),
    service: DevedorEstadoService = Depends(get_devedor_estado_service),
    consulta: DevedorConsultaService = Depends(get_devedor_consulta_service),
) -> DevedorResponse:
    """Transição Inativo → Ativo (FEATURE-008).

    Sem corpo de request. Transição inválida responde 422 ``regra_violada``
    (INV-005, decidida no Aggregate).
    """
    chave = _exigir_idempotency_key(idempotency_key)
    service.reativar(devedor.id, chave)
    return _reler_devedor(devedor.id, consulta)


def _reler_devedor(devedor_id: uuid.UUID, consulta: DevedorConsultaService) -> DevedorResponse:
    """Relê o Devedor para responder o DTO único completo (RA-012).

    Os resultados de atualização e de transição de estado não carregam todos
    os campos do DTO (contatos, ``criado_em``); a releitura mantém o contrato
    de resposta idêntico ao dos demais endpoints em vez de inventar valores.
    """
    devedor = consulta.consultar_por_id(devedor_id)
    if devedor is None:
        raise _nao_encontrado()
    return _de_aggregate(devedor)
