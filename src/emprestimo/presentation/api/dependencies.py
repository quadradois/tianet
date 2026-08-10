"""Dependências da API — montagem do caso de uso (IMP-017/018/025/026/027).

A Presentation apenas compõe as peças da camada de Aplicação/Infrastructure
e expõe os serviços. A sessão de leitura é criada por requisição e fechada ao final.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Generator
from importlib import import_module
from typing import Any

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from emprestimo.application.atualizacao import TenantAtualizacaoService
from emprestimo.application.atualizacao_devedor import DevedorAtualizacaoService
from emprestimo.application.autenticacao import AutenticacaoService, HmacAccessTokenService
from emprestimo.application.autorizacao import (
    AutorizacaoService,
    Principal,
    RecursoDeOutroTenantError,
)
from emprestimo.application.cadastro_devedor import DevedorCadastroService
from emprestimo.application.comercial import (
    ConsultaComercialService,
    DecisaoComercialService,
    IntegracaoPropostaAprovadaService,
    PropostaComercialService,
    SimulacaoComercialService,
)
from emprestimo.application.consulta import (
    TenantConsultaPorIdService,
    TenantConsultaService,
    TenantListagemService,
)
from emprestimo.application.consulta_devedor import (
    DevedorConsultaPorDocumentoService,
    DevedorConsultaService,
    DevedorListagemService,
)
from emprestimo.application.contratos import (
    AssinaturaContratoService,
    CancelamentoEncerramentoContratoService,
    ConsultaContratoService,
    FormalizacaoContratoService,
    LiberacaoContratoService,
)
from emprestimo.application.credenciais import CredenciaisService
from emprestimo.application.estado import TenantEstadoService
from emprestimo.application.estado_devedor import DevedorEstadoService
from emprestimo.application.historico_devedor import DevedorHistoricoService
from emprestimo.application.perfis_acesso import PerfisAcessoService
from emprestimo.application.provisioning import TenantProvisioningService
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.ports import CarteiraRepository
from emprestimo.domain.credit.unicidade_devedor import UnicidadeDevedorService
from emprestimo.domain.platform.ports import TenantRepository
from emprestimo.domain.platform.unicidade import UnicidadeTenantService
from emprestimo.infrastructure.auditoria import (
    SqlAlchemyAuditoriaConsulta,
    SqlAlchemyAuditoriaRegistro,
)
from emprestimo.infrastructure.db.session import create_session, get_session_factory
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyTenantRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

JWT_SECRET_ENV = "JWT_SECRET_KEY"
BEARER_SECURITY = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Access token IAM no esquema Bearer.",
)


def _get_session() -> Generator[Session, None, None]:
    """Sessão de leitura por requisição (fechada ao final)."""
    session = create_session()
    try:
        yield session
    finally:
        session.close()


def get_tenant_provisioning_service(
    session: Session = Depends(_get_session),
) -> TenantProvisioningService:
    """Monta o serviço de provisionamento (IMP-013..016)."""
    session_factory = get_session_factory()
    return TenantProvisioningService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        unicidade=UnicidadeTenantService(SqlAlchemyTenantRepository(session)),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_autenticacao_service() -> AutenticacaoService:
    """Monta o servico de autenticacao IAM (IMP-090)."""
    session_factory = get_session_factory()
    return AutenticacaoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
        access_tokens=HmacAccessTokenService(_jwt_secret()),
    )


def get_autorizacao_service() -> AutorizacaoService:
    """Monta o servico de autorizacao IAM (IMP-091)."""
    session_factory = get_session_factory()
    return AutorizacaoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
        access_tokens=HmacAccessTokenService(_jwt_secret()),
    )


def get_credenciais_service() -> CredenciaisService:
    session_factory = get_session_factory()
    return CredenciaisService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_perfis_acesso_service() -> PerfisAcessoService:
    session_factory = get_session_factory()
    return PerfisAcessoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_principal_atual(
    credentials: HTTPAuthorizationCredentials | None = Security(BEARER_SECURITY),
    autorizacao: AutorizacaoService = Depends(get_autorizacao_service),
) -> Principal:
    """Resolve o Principal autenticado a partir do bearer token da requisicao."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        autorizacao.recusar_principal_ausente()
        raise AssertionError("recusa do Principal deveria interromper a requisicao") from None
    return autorizacao.resolver_principal(credentials.credentials)


def exigir_permissao(operacao: str) -> Callable[[Principal, AutorizacaoService], Principal]:
    """Cria uma dependencia que exige permissao RBAC para a operacao."""

    def _dependencia(
        principal: Principal = Depends(get_principal_atual),
        autorizacao: AutorizacaoService = Depends(get_autorizacao_service),
    ) -> Principal:
        autorizacao.exigir_permissao(principal, operacao)
        return principal

    return _dependencia


def _jwt_secret() -> str:
    segredo = os.environ.get(JWT_SECRET_ENV, "").strip()
    if not segredo:
        raise RuntimeError(f"{JWT_SECRET_ENV} nao configurado")
    return segredo


def get_tenant_repository(session: Session = Depends(_get_session)) -> TenantRepository:
    """Repositório de consulta de Tenant (IMP-018/024/025/026)."""
    return SqlAlchemyTenantRepository(session)


def get_carteira_repository(session: Session = Depends(_get_session)) -> CarteiraRepository:
    """Repositorio de consulta de Carteira para isolamento cross-tenant."""
    return SqlAlchemyCarteiraRepository(session)


def get_tenant_consulta_service(
    session: Session = Depends(_get_session),
) -> TenantConsultaService:
    """Serviço de consulta por identificador institucional (IMP-025)."""
    session_factory = get_session_factory()
    return TenantConsultaService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_tenant_consulta_por_id_service(
    session: Session = Depends(_get_session),
) -> TenantConsultaPorIdService:
    """Serviço de consulta por ID (IMP-026)."""
    session_factory = get_session_factory()
    return TenantConsultaPorIdService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_tenant_listagem_service(
    session: Session = Depends(_get_session),
) -> TenantListagemService:
    """Serviço de listagem paginada de Tenants (IMP-027)."""
    session_factory = get_session_factory()
    return TenantListagemService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_tenant_atualizacao_service(
    session: Session = Depends(_get_session),
) -> TenantAtualizacaoService:
    """Serviço de atualização cadastral de Tenants (IMP-030/031/032)."""
    session_factory = get_session_factory()
    return TenantAtualizacaoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_tenant_estado_service(
    session: Session = Depends(_get_session),
) -> TenantEstadoService:
    """Serviço de transições de estado de Tenants (IMP-034/035/036)."""
    session_factory = get_session_factory()
    return TenantEstadoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


# --- Credit Context — Devedor (IMP-056) ---


def get_devedor_cadastro_service(
    session: Session = Depends(_get_session),
) -> DevedorCadastroService:
    """Serviço de cadastro de Devedor (IMP-051)."""
    session_factory = get_session_factory()
    return DevedorCadastroService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        unicidade=UnicidadeDevedorService(SqlAlchemyDevedorRepository(session)),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_devedor_consulta_service(
    session: Session = Depends(_get_session),
) -> DevedorConsultaService:
    """Serviço de consulta de Devedor por ID (IMP-052)."""
    session_factory = get_session_factory()
    return DevedorConsultaService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_devedor_consulta_por_documento_service(
    session: Session = Depends(_get_session),
) -> DevedorConsultaPorDocumentoService:
    """Serviço de consulta de Devedor por documento na Carteira (IMP-052)."""
    session_factory = get_session_factory()
    return DevedorConsultaPorDocumentoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_devedor_listagem_service(
    session: Session = Depends(_get_session),
) -> DevedorListagemService:
    """Serviço de listagem paginada de Devedores (IMP-053)."""
    session_factory = get_session_factory()
    return DevedorListagemService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
    )


def get_devedor_atualizacao_service(
    session: Session = Depends(_get_session),
) -> DevedorAtualizacaoService:
    """Serviço de atualização cadastral de Devedor (IMP-054)."""
    session_factory = get_session_factory()
    return DevedorAtualizacaoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        unicidade=UnicidadeDevedorService(SqlAlchemyDevedorRepository(session)),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_devedor_estado_service(
    session: Session = Depends(_get_session),
) -> DevedorEstadoService:
    """Serviço de transições de estado de Devedor (IMP-055)."""
    session_factory = get_session_factory()
    return DevedorEstadoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_simulacao_comercial_service(
    session: Session = Depends(_get_session),
) -> SimulacaoComercialService:
    session_factory = get_session_factory()
    return SimulacaoComercialService(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_proposta_comercial_service(
    session: Session = Depends(_get_session),
) -> PropostaComercialService:
    session_factory = get_session_factory()
    return PropostaComercialService(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_consulta_comercial_service(
    session: Session = Depends(_get_session),
) -> ConsultaComercialService:
    session_factory = get_session_factory()
    return ConsultaComercialService(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_decisao_comercial_service(
    session: Session = Depends(_get_session),
) -> DecisaoComercialService:
    session_factory = get_session_factory()
    return DecisaoComercialService(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_integracao_proposta_aprovada_service(
    session: Session = Depends(_get_session),
) -> IntegracaoPropostaAprovadaService:
    session_factory = get_session_factory()
    return IntegracaoPropostaAprovadaService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory)
    )


def get_formalizacao_contrato_service(
    session: Session = Depends(_get_session),
) -> FormalizacaoContratoService:
    session_factory = get_session_factory()
    return FormalizacaoContratoService(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_consulta_contrato_service(
    session: Session = Depends(_get_session),
) -> ConsultaContratoService:
    session_factory = get_session_factory()
    return ConsultaContratoService(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_assinatura_contrato_service(
    session: Session = Depends(_get_session),
) -> AssinaturaContratoService:
    session_factory = get_session_factory()
    return AssinaturaContratoService(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_liberacao_contrato_service(
    session: Session = Depends(_get_session),
) -> LiberacaoContratoService:
    session_factory = get_session_factory()
    return LiberacaoContratoService(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_cancelamento_encerramento_contrato_service(
    session: Session = Depends(_get_session),
) -> CancelamentoEncerramentoContratoService:
    session_factory = get_session_factory()
    return CancelamentoEncerramentoContratoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory)
    )


def get_criacao_emprestimo_service(
    session: Session = Depends(_get_session),
) -> Any:
    session_factory = get_session_factory()
    service_cls = _motor_service_class("CriacaoEmprestimoService")
    return service_cls(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def get_consulta_emprestimo_service(
    session: Session = Depends(_get_session),
) -> Any:
    session_factory = get_session_factory()
    service_cls = _motor_service_class("ConsultaEmprestimoService")
    return service_cls(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_plano_parcelas_service(
    session: Session = Depends(_get_session),
) -> Any:
    session_factory = get_session_factory()
    service_cls = _motor_service_class("PlanoParcelasService")
    return service_cls(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_pagamento_service(
    session: Session = Depends(_get_session),
) -> Any:
    session_factory = get_session_factory()
    service_cls = _motor_service_class("PagamentoService")
    return service_cls(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_consulta_saldo_service(
    session: Session = Depends(_get_session),
) -> Any:
    session_factory = get_session_factory()
    service_cls = _motor_service_class("ConsultaSaldoService")
    return service_cls(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def get_quitacao_renegociacao_service(
    session: Session = Depends(_get_session),
) -> Any:
    session_factory = get_session_factory()
    service_cls = _motor_service_class("QuitacaoRenegociacaoService")
    return service_cls(uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory))


def _motor_service_class(nome: str) -> Any:
    modulo = import_module("emprestimo.application." + "motor" + "_financeiro")
    return getattr(modulo, nome)


def get_carteira_do_principal(
    carteira_id: uuid.UUID,
    principal: Principal = Depends(get_principal_atual),
    repo: CarteiraRepository = Depends(get_carteira_repository),
    autorizacao: AutorizacaoService = Depends(get_autorizacao_service),
) -> Carteira:
    """Resolve a Carteira da rota dentro do Tenant do Principal autenticado."""
    carteira = repo.find_by_id(carteira_id)
    if carteira is None or carteira.tenant_id != principal.tenant_id:
        try:
            autorizacao.exigir_tenant_do_recurso(
                principal,
                recurso_id=carteira_id,
                recurso_tenant_id=carteira.tenant_id if carteira else None,
                recurso_tipo="carteira",
            )
        except RecursoDeOutroTenantError:
            raise HTTPException(
                status_code=404,
                detail={
                    "codigo": "carteira_nao_encontrada",
                    "mensagem": "Carteira inexistente",
                },
            ) from None
    assert carteira is not None
    return carteira


def get_devedor_da_carteira(
    devedor_id: uuid.UUID,
    carteira: Carteira = Depends(get_carteira_do_principal),
    service: DevedorConsultaService = Depends(get_devedor_consulta_service),
) -> Devedor:
    """Resolve o Devedor validando a pertinência à Carteira da rota (ADR-018).

    Ponto único de validação de pertinência: toda rota aninhada por ID a declara
    como dependência, em vez de repetir a checagem no handler.

    Devedor inexistente e Devedor de outra Carteira respondem o mesmo
    ``404 devedor_nao_encontrado``. A indistinguibilidade é intencional (ADR-018):
    um código distinto confirmaria a existência do identificador em outra
    Carteira, vazando informação através da fronteira de isolamento.
    """
    devedor = service.consultar_por_id(devedor_id)
    if devedor is None or devedor.carteira_id != carteira.id:
        raise HTTPException(
            status_code=404,
            detail={
                "codigo": "devedor_nao_encontrado",
                "mensagem": "Devedor inexistente",
            },
        )
    return devedor


def get_devedor_historico_service(
    session: Session = Depends(_get_session),
) -> DevedorHistoricoService:
    """Serviço de consulta do histórico cadastral do Devedor (US-027)."""
    session_factory = get_session_factory()
    return DevedorHistoricoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria_consulta=SqlAlchemyAuditoriaConsulta(session),
    )
