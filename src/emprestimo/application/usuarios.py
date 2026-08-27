"""Cadastro de Usuario por um administrador do Tenant (IMP-355).

Ate 2026-08-27 nao existia caminho nenhum para criar Usuario: o `Tenant` nascia
com seu administrador pela CLI de bootstrap, e o IAM so oferecia gestao de
perfis e credenciais. Na pratica, cada Tenant estava limitado a exatamente um
usuario para sempre.

O Usuario nasce **ja ativo, com credencial definida na criacao** — nao ha token
de ativacao, removido pelo IMP-351 junto com o provisionamento por API. E o
mesmo caminho que a CLI de bootstrap usa: criar, definir credencial, ativar, na
mesma transacao.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.usuario import Usuario, UsuarioState

ESCOPO_IDEMPOTENCIA = "iam-usuario-criar"
"""Escopo da Idempotency-Key deste caso de uso (AD-002)."""


class UsuarioJaExisteError(Exception):
    """E-mail ja usado por outro Usuario."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"e-mail ja cadastrado: {email}")


@dataclass(frozen=True)
class UsuarioCriado:
    """Resultado do cadastro — nunca carrega segredo nem hash."""

    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    email: str
    estado: UsuarioState
    perfil_acesso: str | None
    criado_em: datetime


class UsuarioCadastroService:
    """Cria Usuario com credencial inicial, em transacao unica."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def criar(
        self,
        *,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID,
        nome: str,
        email: str,
        segredo: str,
        idempotency_key: str,
    ) -> UsuarioCriado:
        email_normalizado = email.strip().lower()
        detalhes = {
            "tenant_id": str(tenant_id),
            "executor_id": str(executor_id),
            "idempotency_key": idempotency_key,
        }
        self._auditoria.registrar(
            "iam_usuario",
            None,
            "usuario.criar.inicio",
            "iniciado",
            detalhes=json.dumps(detalhes, sort_keys=True),
        )
        try:
            resultado = self._criar(
                tenant_id=tenant_id,
                nome=nome.strip(),
                email=email_normalizado,
                segredo=segredo,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            self._auditoria.registrar(
                "iam_usuario",
                None,
                "usuario.criar.falha",
                "falhou",
                detalhes=json.dumps(
                    {**detalhes, "erro_tipo": type(exc).__name__},
                    sort_keys=True,
                ),
            )
            raise
        # IMP-361 antecipado aqui: a autoria e do executor, e fica no evento de
        # sucesso para a trilha distinguir quem criou quem.
        self._auditoria.registrar(
            "iam_usuario",
            resultado.usuario_id,
            "usuario.criar.sucesso",
            "ok",
            detalhes=json.dumps(
                {**detalhes, "usuario_id": str(resultado.usuario_id)},
                sort_keys=True,
            ),
        )
        return resultado

    def _criar(
        self,
        *,
        tenant_id: uuid.UUID,
        nome: str,
        email: str,
        segredo: str,
        idempotency_key: str,
    ) -> UsuarioCriado:
        with self._uow_factory() as uow:
            replay = self._replay_ou_registrar(uow, idempotency_key, tenant_id, email)
            if replay is not None:
                uow.commit()
                return replay

            existente = uow.usuario.find_by_email(email)
            if existente is not None:
                raise UsuarioJaExisteError(email)

            usuario = Usuario(tenant_id=tenant_id, nome=nome, email=email)
            # A credencial valida a politica minima do IMP-342 no dominio; se o
            # segredo for fraco, a excecao sobe antes de qualquer persistencia.
            credencial = Credencial.definir(usuario_id=usuario.id, segredo=segredo)
            usuario.ativar()

            uow.usuario.save(usuario)
            uow.credencial.save(credencial)
            resultado = _resultado(usuario)
            uow.idempotencia.concluir(
                idempotency_key,
                ESCOPO_IDEMPOTENCIA,
                json.dumps(_serializar(resultado), sort_keys=True),
            )
            uow.commit()
        return resultado

    def _replay_ou_registrar(
        self,
        uow: UnitOfWork,
        idempotency_key: str,
        tenant_id: uuid.UUID,
        email: str,
    ) -> UsuarioCriado | None:
        # `solicitacao_hash` e String(64): guarda **hash**, nao valor bruto.
        # Concatenar tenant e e-mail estourava a coluna com DataError — o mesmo
        # tipo de defeito que o IMP-350 achou no `audit_log.status`.
        bruto = f"{tenant_id}|{email}"
        hash_solicitacao = hashlib.sha256(bruto.encode("utf-8")).hexdigest()
        existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA)
        if existente is None:
            uow.idempotencia.registrar(idempotency_key, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
            return None
        if existente["estado"] != "finished":
            raise IdempotenciaConflitoError(idempotency_key, "cadastro em andamento")
        if existente["solicitacao_hash"] != hash_solicitacao:
            raise IdempotenciaConflitoError(idempotency_key, "resultado divergente")
        resultado = existente.get("resultado")
        if not isinstance(resultado, str):
            raise IdempotenciaConflitoError(idempotency_key, "resultado ausente")
        return _desserializar(resultado)


def _resultado(usuario: Usuario) -> UsuarioCriado:
    return UsuarioCriado(
        usuario_id=usuario.id,
        tenant_id=usuario.tenant_id,
        nome=usuario.nome,
        email=usuario.email,
        estado=usuario.estado,
        perfil_acesso=usuario.perfil_acesso,
        criado_em=usuario.criado_em,
    )


def _serializar(resultado: UsuarioCriado) -> dict[str, str | None]:
    return {
        "usuario_id": str(resultado.usuario_id),
        "tenant_id": str(resultado.tenant_id),
        "nome": resultado.nome,
        "email": resultado.email,
        "estado": resultado.estado.value,
        "perfil_acesso": resultado.perfil_acesso,
        "criado_em": resultado.criado_em.isoformat(),
    }


def _desserializar(conteudo: str) -> UsuarioCriado:
    dados = json.loads(conteudo)
    return UsuarioCriado(
        usuario_id=uuid.UUID(dados["usuario_id"]),
        tenant_id=uuid.UUID(dados["tenant_id"]),
        nome=dados["nome"],
        email=dados["email"],
        estado=UsuarioState(dados["estado"]),
        perfil_acesso=dados["perfil_acesso"],
        criado_em=datetime.fromisoformat(dados["criado_em"]),
    )
