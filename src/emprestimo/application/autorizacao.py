"""Servicos de aplicacao para autorizacao IAM (IMP-089)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from emprestimo.application.autenticacao import AccessTokenIssuer
from emprestimo.application.errors import (
    AcessoNegadoError,
    AutenticacaoRecusadaError,
    ContextoOperacionalIncompletoError,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.perfil import PerfilAcesso, PerfilState
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.domain.platform.usuario import UsuarioState


@dataclass(frozen=True)
class Principal:
    """Usuario e Tenant resolvidos a partir do access token validado."""

    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    perfil_acesso: str | None
    access_token_expira_em: datetime
    administrador_plataforma: bool = False


@dataclass(frozen=True)
class ContextoOperacionalResultado:
    """Contexto corrente derivado exclusivamente do Principal autenticado."""

    usuario_id: uuid.UUID
    usuario_nome: str
    usuario_email: str
    tenant_id: uuid.UUID
    tenant_nome: str
    tenant_identificador_institucional: str
    carteira_id: uuid.UUID
    carteira_nome: str
    perfil_id: uuid.UUID | None
    perfil_nome: str | None
    permissoes: tuple[str, ...]


class RecursoDeOutroTenantError(LookupError):
    """Recurso inexistente para o Principal, incluindo cross-tenant (IMP-089)."""

    def __init__(self) -> None:
        super().__init__("Recurso nao encontrado")


class AutorizacaoService:
    """Resolve Principal e autoriza operacoes por RBAC sem efeitos de negocio."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
        access_tokens: AccessTokenIssuer,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria
        self._access_tokens = access_tokens

    def resolver_principal(
        self,
        token: str,
        *,
        agora: datetime | None = None,
    ) -> Principal:
        try:
            claims = self._access_tokens.verificar(token, agora)
            with self._uow_factory() as uow:
                usuario = uow.usuario.find_by_id(claims.usuario_id)
                tenant = uow.tenant.find_by_id(claims.tenant_id)
                if (
                    usuario is None
                    or usuario.estado is not UsuarioState.ATIVO
                    or usuario.tenant_id != claims.tenant_id
                    or tenant is None
                    or tenant.estado is not TenantState.ATIVO
                ):
                    raise AutenticacaoRecusadaError()
                perfil_vinculado = uow.perfil_acesso.find_by_usuario_id(usuario.id)
                if (
                    isinstance(perfil_vinculado, PerfilAcesso)
                    and perfil_vinculado.tenant_id != usuario.tenant_id
                ):
                    raise AutenticacaoRecusadaError()
                uow.commit()

            principal = Principal(
                usuario_id=usuario.id,
                tenant_id=usuario.tenant_id,
                perfil_acesso=(
                    perfil_vinculado.nome if isinstance(perfil_vinculado, PerfilAcesso) else None
                ),
                access_token_expira_em=claims.expira_em,
                administrador_plataforma=(
                    isinstance(perfil_vinculado, PerfilAcesso)
                    and perfil_vinculado.permite("tenant.criar")
                ),
            )
            return principal
        except Exception as exc:
            self._registrar_recusa_autenticacao(exc)
            raise

    def recusar_principal_ausente(self) -> None:
        """Audita a ausencia/malformacao do Bearer antes de recusar a requisicao."""
        self._registrar_recusa_autenticacao(AutenticacaoRecusadaError())

    def consultar_contexto(self, principal: Principal) -> ContextoOperacionalResultado:
        """Resolve o contexto do proprio Principal sem aceitar IDs externos."""
        try:
            with self._uow_factory() as uow:
                usuario = uow.usuario.find_by_id(principal.usuario_id)
                tenant = uow.tenant.find_by_id(principal.tenant_id)
                if (
                    usuario is None
                    or usuario.estado is not UsuarioState.ATIVO
                    or usuario.tenant_id != principal.tenant_id
                    or tenant is None
                    or tenant.estado is not TenantState.ATIVO
                ):
                    raise AutenticacaoRecusadaError()
                perfil = uow.perfil_acesso.find_by_usuario_id(principal.usuario_id)
                if isinstance(perfil, PerfilAcesso) and perfil.tenant_id != principal.tenant_id:
                    raise AutenticacaoRecusadaError()
                carteiras = uow.carteira.find_by_tenant_id(principal.tenant_id)
                if len(carteiras) != 1:
                    raise ContextoOperacionalIncompletoError()
                carteira = carteiras[0]
                uow.commit()
        except AutenticacaoRecusadaError as exc:
            self._registrar_recusa_autenticacao(exc)
            raise AssertionError("unreachable") from exc

        return ContextoOperacionalResultado(
            usuario_id=usuario.id,
            usuario_nome=usuario.nome,
            usuario_email=usuario.email,
            tenant_id=tenant.id,
            tenant_nome=tenant.nome,
            tenant_identificador_institucional=tenant.identificador_institucional,
            carteira_id=carteira.id,
            carteira_nome=carteira.nome,
            perfil_id=perfil.id if isinstance(perfil, PerfilAcesso) else None,
            perfil_nome=perfil.nome if isinstance(perfil, PerfilAcesso) else None,
            permissoes=(
                tuple(sorted(permissao.codigo for permissao in perfil.permissoes))
                if isinstance(perfil, PerfilAcesso) and perfil.estado is PerfilState.ATIVO
                else ()
            ),
        )

    def exigir_permissao(self, principal: Principal, operacao: str) -> None:
        try:
            with self._uow_factory() as uow:
                perfil = uow.perfil_acesso.find_by_usuario_id(principal.usuario_id)
                if (
                    not isinstance(perfil, PerfilAcesso)
                    or perfil.tenant_id != principal.tenant_id
                    or not perfil.permite(operacao)
                ):
                    raise AcessoNegadoError(operacao)
                uow.commit()
        except Exception as exc:
            self._registrar_negacao_autorizacao(principal, operacao, exc)
            raise

    def exigir_tenant_do_recurso(
        self,
        principal: Principal,
        *,
        recurso_id: uuid.UUID | str,
        recurso_tenant_id: uuid.UUID | None,
        recurso_tipo: str,
    ) -> None:
        if recurso_tenant_id == principal.tenant_id:
            return
        self._auditoria.registrar(
            "autorizacao",
            principal.usuario_id,
            "cross_tenant.negado",
            "negado",
            detalhes=json.dumps(
                {
                    "tenant_id": str(principal.tenant_id),
                    "recurso_tipo": recurso_tipo,
                    "recurso_id": str(recurso_id),
                }
            ),
        )
        raise RecursoDeOutroTenantError()

    def autorizar_operacao(
        self,
        principal: Principal,
        *,
        operacao: str,
        recurso_id: uuid.UUID | str | None = None,
        recurso_tenant_id: uuid.UUID | None = None,
        recurso_tipo: str | None = None,
    ) -> None:
        if recurso_id is not None or recurso_tenant_id is not None or recurso_tipo is not None:
            if recurso_id is None or recurso_tipo is None:
                raise ValueError("recurso_id e recurso_tipo sao obrigatorios para validar recurso")
            self.exigir_tenant_do_recurso(
                principal,
                recurso_id=recurso_id,
                recurso_tenant_id=recurso_tenant_id,
                recurso_tipo=recurso_tipo,
            )
        self.exigir_permissao(principal, operacao)

    def _registrar_recusa_autenticacao(self, exc: Exception) -> None:
        self._auditoria.registrar(
            "autorizacao",
            None,
            "principal.recusado",
            "recusado",
            detalhes=json.dumps({"erro": type(exc).__name__}),
        )
        if isinstance(exc, AutenticacaoRecusadaError):
            raise exc

    def _registrar_negacao_autorizacao(
        self,
        principal: Principal,
        operacao: str,
        exc: Exception,
    ) -> None:
        self._auditoria.registrar(
            "autorizacao",
            principal.usuario_id,
            "operacao.negada",
            "negado",
            detalhes=json.dumps(
                {
                    "tenant_id": str(principal.tenant_id),
                    "operacao": operacao,
                    "erro": type(exc).__name__,
                }
            ),
        )
        if isinstance(exc, AcessoNegadoError):
            raise exc
