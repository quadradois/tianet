"""Servicos de aplicacao para autenticacao IAM (IMP-088)."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from emprestimo.application.errors import AutenticacaoRecusadaError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.sessao import Sessao
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState

ACCESS_TOKEN_MINUTOS = 15
TOKEN_TIPO_ACCESS = "access"


@dataclass(frozen=True)
class AccessTokenEmitido:
    """Access token autocontido e seu vencimento."""

    token: str
    expira_em: datetime


@dataclass(frozen=True)
class AccessTokenClaims:
    """Claims essenciais carregadas pelo access token."""

    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    perfil_acesso: str | None
    expira_em: datetime


class AccessTokenIssuer(Protocol):
    """Contrato de emissao/verificacao de access token autocontido."""

    def emitir(self, usuario: Usuario, agora: datetime | None = None) -> AccessTokenEmitido: ...

    def verificar(self, token: str, agora: datetime | None = None) -> AccessTokenClaims: ...


@dataclass(frozen=True)
class AutenticacaoResultado:
    """Resultado seguro do login/refresh, sem credencial em texto legivel."""

    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    access_token: str
    access_token_expira_em: datetime
    refresh_token: str
    refresh_token_expira_em: datetime


@dataclass(frozen=True)
class RenovacaoResultado:
    """Resultado da renovacao por refresh token."""

    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    access_token: str
    access_token_expira_em: datetime


class HmacAccessTokenService:
    """Emite token autocontido assinado com HMAC-SHA256 usando biblioteca padrao."""

    def __init__(self, segredo_assinatura: str) -> None:
        if not segredo_assinatura.strip():
            raise ValueError("segredo_assinatura nao pode ser vazio")
        self._segredo = segredo_assinatura.encode("utf-8")

    def emitir(self, usuario: Usuario, agora: datetime | None = None) -> AccessTokenEmitido:
        referencia = _agora_utc(agora)
        expira_em = referencia + timedelta(minutes=ACCESS_TOKEN_MINUTOS)
        payload = {
            "typ": TOKEN_TIPO_ACCESS,
            "sub": str(usuario.id),
            "tenant_id": str(usuario.tenant_id),
            "perfil_acesso": usuario.perfil_acesso,
            "iat": int(referencia.timestamp()),
            "exp": int(expira_em.timestamp()),
        }
        return AccessTokenEmitido(token=self._assinar(payload), expira_em=expira_em)

    def verificar(self, token: str, agora: datetime | None = None) -> AccessTokenClaims:
        try:
            header_b64, payload_b64, assinatura_b64 = token.split(".", 2)
            assinatura_esperada = self._assinatura(f"{header_b64}.{payload_b64}")
            assinatura_recebida = _b64decode(assinatura_b64)
            if not hmac.compare_digest(assinatura_recebida, assinatura_esperada):
                raise AutenticacaoRecusadaError()
            payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
            if payload.get("typ") != TOKEN_TIPO_ACCESS:
                raise AutenticacaoRecusadaError()
            expira_em = datetime.fromtimestamp(int(payload["exp"]), UTC)
            if _agora_utc(agora) >= expira_em:
                raise AutenticacaoRecusadaError()
            return AccessTokenClaims(
                usuario_id=uuid.UUID(payload["sub"]),
                tenant_id=uuid.UUID(payload["tenant_id"]),
                perfil_acesso=payload.get("perfil_acesso"),
                expira_em=expira_em,
            )
        except (binascii.Error, KeyError, ValueError, json.JSONDecodeError):
            raise AutenticacaoRecusadaError() from None

    def _assinar(self, payload: Mapping[str, object]) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        assinatura_b64 = _b64encode(self._assinatura(f"{header_b64}.{payload_b64}"))
        return f"{header_b64}.{payload_b64}.{assinatura_b64}"

    def _assinatura(self, conteudo: str) -> bytes:
        return hmac.new(self._segredo, conteudo.encode("ascii"), hashlib.sha256).digest()


class AutenticacaoService:
    """Orquestra login, refresh e logout sem expor o motivo da recusa."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
        access_tokens: AccessTokenIssuer,
        refresh_secret_factory: Callable[[], str] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria
        self._access_tokens = access_tokens
        self._refresh_secret_factory = refresh_secret_factory or (lambda: secrets.token_urlsafe(32))

    def login(
        self,
        *,
        identificador_institucional: str,
        email: str,
        segredo: str,
        agora: datetime | None = None,
    ) -> AutenticacaoResultado:
        identificador = identificador_institucional.strip()
        email_normalizado = email.strip()
        self._registrar("login.inicio", "iniciado", None, identificador=identificador)
        try:
            with self._uow_factory() as uow:
                usuario = self._usuario_autenticavel(uow, identificador, email_normalizado)
                credencial = uow.credencial.find_by_usuario_id(usuario.id)
                if credencial is None or not credencial.verificar(segredo):
                    raise AutenticacaoRecusadaError()

                access_token = self._access_tokens.emitir(usuario, agora)
                refresh_token, sessao = self._nova_sessao(usuario, agora)
                uow.sessao.save(sessao)
                uow.commit()

            self._registrar("login.sucesso", "ok", usuario.id, tenant_id=usuario.tenant_id)
            return AutenticacaoResultado(
                usuario_id=usuario.id,
                tenant_id=usuario.tenant_id,
                access_token=access_token.token,
                access_token_expira_em=access_token.expira_em,
                refresh_token=refresh_token,
                refresh_token_expira_em=sessao.expira_em,
            )
        except Exception as exc:
            self._registrar_recusa("login", exc, identificador=identificador)
            raise

    def refresh(
        self,
        *,
        refresh_token: str,
        agora: datetime | None = None,
    ) -> RenovacaoResultado:
        self._registrar("refresh.inicio", "iniciado", None)
        try:
            with self._uow_factory() as uow:
                sessao = self._sessao_por_refresh(uow, refresh_token, agora, exigir_ativa=True)
                usuario = uow.usuario.find_by_id(sessao.usuario_id)
                tenant = uow.tenant.find_by_id(sessao.tenant_id)
                if (
                    usuario is None
                    or usuario.estado is not UsuarioState.ATIVO
                    or usuario.tenant_id != sessao.tenant_id
                    or tenant is None
                    or tenant.estado is not TenantState.ATIVO
                ):
                    raise AutenticacaoRecusadaError()

                access_token = self._access_tokens.emitir(usuario, agora)
                uow.commit()

            self._registrar("refresh.sucesso", "ok", usuario.id, tenant_id=usuario.tenant_id)
            return RenovacaoResultado(
                usuario_id=usuario.id,
                tenant_id=usuario.tenant_id,
                access_token=access_token.token,
                access_token_expira_em=access_token.expira_em,
            )
        except Exception as exc:
            self._registrar_recusa("refresh", exc)
            raise

    def logout(
        self,
        *,
        refresh_token: str,
        agora: datetime | None = None,
    ) -> None:
        self._registrar("logout.inicio", "iniciado", None)
        try:
            with self._uow_factory() as uow:
                sessao = self._sessao_por_refresh(uow, refresh_token, agora, exigir_ativa=False)
                sessao.revogar(_agora_utc(agora))
                uow.sessao.save(sessao)
                uow.commit()

            self._registrar("logout.sucesso", "ok", sessao.usuario_id, tenant_id=sessao.tenant_id)
        except Exception as exc:
            self._registrar_recusa("logout", exc)
            raise

    def _usuario_autenticavel(
        self,
        uow: UnitOfWork,
        identificador_institucional: str,
        email: str,
    ) -> Usuario:
        tenant = uow.tenant.find_by_identificador_institucional(identificador_institucional)
        if tenant is None or tenant.estado is not TenantState.ATIVO:
            raise AutenticacaoRecusadaError()
        usuarios = [
            usuario
            for usuario in uow.usuario.find_by_tenant_id(tenant.id)
            if usuario.email == email
        ]
        if len(usuarios) != 1 or usuarios[0].estado is not UsuarioState.ATIVO:
            raise AutenticacaoRecusadaError()
        return usuarios[0]

    def _nova_sessao(self, usuario: Usuario, agora: datetime | None) -> tuple[str, Sessao]:
        sessao_id = uuid.uuid4()
        refresh_token = f"{sessao_id}.{self._refresh_secret_factory()}"
        referencia = _agora_utc(agora)
        sessao = Sessao.iniciar(
            usuario_id=usuario.id,
            tenant_id=usuario.tenant_id,
            refresh_token=refresh_token,
            agora=referencia,
        )
        sessao.id = sessao_id
        return refresh_token, sessao

    def _sessao_por_refresh(
        self,
        uow: UnitOfWork,
        refresh_token: str,
        agora: datetime | None,
        *,
        exigir_ativa: bool,
    ) -> Sessao:
        try:
            sessao_id_raw, _ = refresh_token.split(".", 1)
            sessao_id = uuid.UUID(sessao_id_raw)
        except ValueError:
            raise AutenticacaoRecusadaError() from None
        sessao = uow.sessao.find_by_id(sessao_id)
        if sessao is None or not sessao.corresponde_refresh_token(refresh_token):
            raise AutenticacaoRecusadaError()
        if exigir_ativa and not sessao.ativa(_agora_utc(agora)):
            raise AutenticacaoRecusadaError()
        if sessao.expirada(_agora_utc(agora)):
            raise AutenticacaoRecusadaError()
        return sessao

    def _registrar(
        self,
        acao: str,
        status: str,
        usuario_id: uuid.UUID | None,
        *,
        tenant_id: uuid.UUID | None = None,
        identificador: str | None = None,
    ) -> None:
        detalhes = {
            "tenant_id": str(tenant_id) if tenant_id else None,
            "identificador": identificador,
        }
        self._auditoria.registrar(
            "autenticacao",
            usuario_id,
            acao,
            status,
            detalhes=json.dumps(detalhes),
        )

    def _registrar_recusa(
        self,
        acao: str,
        exc: Exception,
        *,
        identificador: str | None = None,
    ) -> None:
        self._auditoria.registrar(
            "autenticacao",
            None,
            f"{acao}.recusado",
            "recusado",
            detalhes=json.dumps(
                {
                    "identificador": identificador,
                    "erro": type(exc).__name__,
                }
            ),
        )
        if isinstance(exc, AutenticacaoRecusadaError):
            raise exc


def _agora_utc(agora: datetime | None = None) -> datetime:
    if agora is None:
        return datetime.now(UTC)
    if agora.tzinfo is None:
        return agora.replace(tzinfo=UTC)
    return agora.astimezone(UTC)


def _b64encode(conteudo: bytes) -> str:
    return base64.urlsafe_b64encode(conteudo).rstrip(b"=").decode("ascii")


def _b64decode(conteudo: str) -> bytes:
    padding = "=" * (-len(conteudo) % 4)
    return base64.urlsafe_b64decode(f"{conteudo}{padding}")
