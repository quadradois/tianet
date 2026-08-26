"""Servicos de aplicacao para gestao de credenciais IAM (IMP-087)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from emprestimo.application.errors import (
    AcessoNegadoError,
    CredencialInvalidaError,
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
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.usuario import Usuario, UsuarioState

OPERACAO_REDEFINIR_CREDENCIAL = "credencial.redefinir"


@dataclass(frozen=True)
class CredencialResultado:
    """Resultado seguro da gestao de credenciais, sem hash nem segredo."""

    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    estado: UsuarioState


class CredenciaisService:
    """Orquestra US-032, US-033 e US-034 sem expor segredo em respostas/auditoria."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def alterar_propria(
        self,
        *,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        segredo_atual: str,
        novo_segredo: str,
        idempotency_key: str | None = None,
    ) -> CredencialResultado:
        """Altera a propria credencial exigindo a credencial atual vigente."""
        self._registrar_inicio("alterar_propria", usuario_id, tenant_id=tenant_id)
        try:
            with self._uow_factory() as uow:
                usuario = self._usuario_do_tenant(uow, usuario_id, tenant_id)
                if usuario.estado is not UsuarioState.ATIVO:
                    raise CredencialInvalidaError()

                escopo = "iam-credencial-alterar-propria"
                replay = iniciar_idempotencia(
                    uow,
                    chave=idempotency_key,
                    escopo=escopo,
                    solicitacao={
                        "tenant_id": tenant_id,
                        "usuario_id": usuario_id,
                        "segredo_atual": segredo_atual,
                        "novo_segredo": novo_segredo,
                    },
                )
                if replay is not None:
                    return dataclass_do_resultado(
                        replay,
                        CredencialResultado,
                        chave=idempotency_key,
                    )

                credencial = uow.credencial.find_by_usuario_id(usuario.id)
                if credencial is None or not credencial.verificar(segredo_atual):
                    raise CredencialInvalidaError()

                credencial.redefinir(novo_segredo)
                uow.credencial.save(credencial)
                self._revogar_sessoes(uow, usuario.id)
                resultado = CredencialResultado(usuario.id, usuario.tenant_id, usuario.estado)
                concluir_idempotencia(
                    uow,
                    chave=idempotency_key,
                    escopo=escopo,
                    resultado=resultado_de_dataclass(resultado),
                )
                uow.commit()

            self._registrar_sucesso("alterar_propria", usuario_id, tenant_id=tenant_id)
            return resultado
        except Exception as exc:
            self._registrar_falha("alterar_propria", usuario_id, exc, tenant_id=tenant_id)
            raise

    def redefinir_usuario(
        self,
        *,
        tenant_id: uuid.UUID,
        solicitante_id: uuid.UUID,
        usuario_id: uuid.UUID,
        novo_segredo: str,
        idempotency_key: str | None = None,
    ) -> CredencialResultado:
        """Redefine credencial de Usuario do mesmo Tenant.

        A resolucao completa do Principal pertence ao IMP-089; neste passo a
        permissao e avaliada pelo Perfil de Acesso persistido do solicitante.
        """
        self._registrar_inicio(
            "redefinir_usuario",
            usuario_id,
            tenant_id=tenant_id,
            solicitante_id=solicitante_id,
        )
        try:
            if solicitante_id == usuario_id:
                raise AcessoNegadoError(OPERACAO_REDEFINIR_CREDENCIAL)
            with self._uow_factory() as uow:
                solicitante = self._usuario_do_tenant(uow, solicitante_id, tenant_id)
                if solicitante.estado is not UsuarioState.ATIVO:
                    raise AcessoNegadoError(OPERACAO_REDEFINIR_CREDENCIAL)
                self._autorizar_redefinicao(uow, solicitante)

                usuario = self._usuario_do_tenant(uow, usuario_id, tenant_id)
                self._validar_usuario_ativo_para_redefinicao(usuario.id, usuario.estado)
                escopo = "iam-credencial-redefinir"
                replay = iniciar_idempotencia(
                    uow,
                    chave=idempotency_key,
                    escopo=escopo,
                    solicitacao={
                        "tenant_id": tenant_id,
                        "solicitante_id": solicitante_id,
                        "usuario_id": usuario_id,
                        "novo_segredo": novo_segredo,
                    },
                )
                if replay is not None:
                    return dataclass_do_resultado(
                        replay,
                        CredencialResultado,
                        chave=idempotency_key,
                    )
                credencial = uow.credencial.find_by_usuario_id(usuario.id)
                if credencial is None:
                    credencial = Credencial.definir(usuario_id=usuario.id, segredo=novo_segredo)
                else:
                    credencial.redefinir(novo_segredo)

                uow.credencial.save(credencial)
                self._revogar_sessoes(uow, usuario.id)
                resultado = CredencialResultado(usuario.id, usuario.tenant_id, usuario.estado)
                concluir_idempotencia(
                    uow,
                    chave=idempotency_key,
                    escopo=escopo,
                    resultado=resultado_de_dataclass(resultado),
                )
                uow.commit()

            self._registrar_sucesso(
                "redefinir_usuario",
                usuario_id,
                tenant_id=tenant_id,
                solicitante_id=solicitante_id,
            )
            return resultado
        except Exception as exc:
            self._registrar_falha(
                "redefinir_usuario",
                usuario_id,
                exc,
                tenant_id=tenant_id,
                solicitante_id=solicitante_id,
            )
            raise

    def _usuario_do_tenant(
        self, uow: UnitOfWork, usuario_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Usuario:
        usuario = uow.usuario.find_by_id(usuario_id)
        if usuario is None or usuario.tenant_id != tenant_id:
            raise UsuarioNaoEncontradoError(usuario_id)
        return usuario

    def _autorizar_redefinicao(self, uow: UnitOfWork, solicitante: Usuario) -> None:
        perfil = uow.perfil_acesso.find_by_usuario_id(solicitante.id)
        if not isinstance(perfil, PerfilAcesso) or not perfil.permite(
            OPERACAO_REDEFINIR_CREDENCIAL
        ):
            raise AcessoNegadoError(OPERACAO_REDEFINIR_CREDENCIAL)

    def _validar_usuario_ativo_para_redefinicao(
        self, usuario_id: uuid.UUID, estado: UsuarioState
    ) -> None:
        if estado is not UsuarioState.ATIVO:
            raise TransicaoEstadoInvalidaError(
                usuario_id,
                "redefinir_credencial",
                f"estado atual '{estado.value}' nao permite redefinir credencial",
            )

    def _revogar_sessoes(self, uow: UnitOfWork, usuario_id: uuid.UUID) -> None:
        for sessao in uow.sessao.find_by_usuario_id(usuario_id):
            sessao.revogar()
            uow.sessao.save(sessao)

    def _registrar_inicio(
        self,
        acao: str,
        usuario_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID,
        solicitante_id: uuid.UUID | None = None,
    ) -> None:
        self._auditoria.registrar(
            "credencial",
            usuario_id,
            f"{acao}.inicio",
            "iniciado",
            detalhes=self._detalhes(tenant_id, solicitante_id),
        )

    def _registrar_sucesso(
        self,
        acao: str,
        usuario_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID,
        solicitante_id: uuid.UUID | None = None,
    ) -> None:
        self._auditoria.registrar(
            "credencial",
            usuario_id,
            f"{acao}.sucesso",
            "ok",
            detalhes=self._detalhes(tenant_id, solicitante_id),
        )

    def _registrar_falha(
        self,
        acao: str,
        usuario_id: uuid.UUID,
        exc: Exception,
        *,
        tenant_id: uuid.UUID,
        solicitante_id: uuid.UUID | None = None,
    ) -> None:
        self._auditoria.registrar(
            "credencial",
            usuario_id,
            f"{acao}.falha",
            "falhou",
            detalhes=json.dumps(
                {
                    "tenant_id": str(tenant_id),
                    "solicitante_id": str(solicitante_id) if solicitante_id else None,
                    "erro": type(exc).__name__,
                }
            ),
        )
        self._auditoria.registrar(
            "credencial",
            usuario_id,
            f"{acao}.rollback",
            "rollback_aplicado",
            detalhes=self._detalhes(tenant_id, solicitante_id),
        )

    def _detalhes(self, tenant_id: uuid.UUID, solicitante_id: uuid.UUID | None = None) -> str:
        return json.dumps(
            {
                "tenant_id": str(tenant_id),
                "solicitante_id": str(solicitante_id) if solicitante_id else None,
            }
        )
