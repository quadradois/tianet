"""Casos de uso da FEATURE-011 - perfis, permissoes e atribuicoes."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

from emprestimo.application.errors import (
    AcessoNegadoError,
    IdempotenciaConflitoError,
    PerfilConflitoError,
    PerfilNaoEncontradoError,
    UsuarioNaoEncontradoError,
)
from emprestimo.application.iam_catalogo import CATALOGO_POR_CODIGO, PERMISSOES_PLATAFORMA
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.perfil import PerfilAcesso, PerfilState
from emprestimo.domain.platform.usuario import Usuario


def _auditar_escrita(acao: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: PerfisAcessoService, *args: Any, **kwargs: Any) -> Any:
            tenant_id = kwargs["tenant_id"]
            executor_id = kwargs["executor_id"]
            detalhes = json.dumps({"tenant_id": str(tenant_id), "executor_id": str(executor_id)})
            self._auditoria.registrar(
                "iam", executor_id, f"{acao}.inicio", "iniciado", detalhes=detalhes
            )
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                falha = json.dumps(
                    {
                        "tenant_id": str(tenant_id),
                        "executor_id": str(executor_id),
                        "erro": type(exc).__name__,
                    }
                )
                self._auditoria.registrar(
                    "iam", executor_id, f"{acao}.falha", "falhou", detalhes=falha
                )
                self._auditoria.registrar(
                    "iam",
                    executor_id,
                    f"{acao}.rollback",
                    "rollback_aplicado",
                    detalhes=detalhes,
                )
                raise

        return wrapper

    return decorator


@dataclass(frozen=True)
class PerfilResultado:
    id: uuid.UUID
    tenant_id: uuid.UUID
    nome: str
    estado: PerfilState
    permissoes: tuple[str, ...]


@dataclass(frozen=True)
class PermissoesEfetivasResultado:
    usuario_id: uuid.UUID
    perfil_id: uuid.UUID | None
    perfil_nome: str | None
    permissoes: tuple[str, ...]


class PerfisAcessoService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    @_auditar_escrita("perfil.criar")
    def criar(
        self,
        *,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID,
        nome: str,
        idempotency_key: str,
    ) -> PerfilResultado:
        scope = self._scope("perfil-criar", tenant_id)
        with self._uow_factory() as uow:
            replay = self._replay(uow, idempotency_key, scope, tenant_id, nome)
            if replay is not None:
                uow.commit()
                return _perfil_de_json(replay)
            if uow.perfil_acesso.find_by_tenant_nome(tenant_id, nome) is not None:
                raise PerfilConflitoError("Perfil de Acesso ja existente no Tenant")
            perfil = PerfilAcesso(tenant_id=tenant_id, nome=nome)
            uow.perfil_acesso.save(perfil)
            resultado = _resultado(perfil)
            self._concluir(uow, idempotency_key, scope, resultado)
            uow.commit()
        self._auditar("perfil.criado", resultado, executor_id, usuario_alvo_id=None)
        return resultado

    def listar(self, *, tenant_id: uuid.UUID) -> list[PerfilResultado]:
        with self._uow_factory() as uow:
            return [_resultado(perfil) for perfil in uow.perfil_acesso.find_by_tenant_id(tenant_id)]

    def consultar(
        self, *, tenant_id: uuid.UUID, executor_id: uuid.UUID, perfil_id: uuid.UUID
    ) -> PerfilResultado:
        with self._uow_factory() as uow:
            return _resultado(self._perfil_do_tenant(uow, perfil_id, tenant_id, executor_id))

    @_auditar_escrita("perfil.renomear")
    def renomear(
        self,
        *,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID,
        perfil_id: uuid.UUID,
        nome: str,
        idempotency_key: str,
    ) -> PerfilResultado:
        scope = self._scope("perfil-renomear", tenant_id)
        with self._uow_factory() as uow:
            replay = self._replay(uow, idempotency_key, scope, tenant_id, perfil_id, nome)
            if replay is not None:
                uow.commit()
                return _perfil_de_json(replay)
            perfil = self._perfil_do_tenant(uow, perfil_id, tenant_id, executor_id)
            existente = uow.perfil_acesso.find_by_tenant_nome(tenant_id, nome)
            if existente is not None and existente.id != perfil.id:
                raise PerfilConflitoError("Perfil de Acesso ja existente no Tenant")
            nome_anterior = perfil.nome
            perfil.renomear(nome)
            uow.perfil_acesso.save(perfil)
            for usuario in uow.usuario.find_by_tenant_id(tenant_id):
                if usuario.perfil_acesso == nome_anterior:
                    usuario.perfil_acesso = perfil.nome
                    uow.usuario.save(usuario)
            resultado = _resultado(perfil)
            self._concluir(uow, idempotency_key, scope, resultado)
            uow.commit()
        self._auditar("perfil.renomeado", resultado, executor_id, usuario_alvo_id=None)
        return resultado

    @_auditar_escrita("perfil.inativar")
    def inativar(
        self,
        *,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID,
        perfil_id: uuid.UUID,
        idempotency_key: str,
    ) -> PerfilResultado:
        scope = self._scope("perfil-inativar", tenant_id)
        with self._uow_factory() as uow:
            replay = self._replay(uow, idempotency_key, scope, tenant_id, perfil_id)
            if replay is not None:
                uow.commit()
                return _perfil_de_json(replay)
            perfil = self._perfil_do_tenant(uow, perfil_id, tenant_id, executor_id)
            if uow.perfil_acesso.count_usuarios(perfil.id):
                raise PerfilConflitoError("Perfil de Acesso possui Usuarios vinculados")
            perfil.inativar()
            uow.perfil_acesso.save(perfil)
            resultado = _resultado(perfil)
            self._concluir(uow, idempotency_key, scope, resultado)
            uow.commit()
        self._auditar("perfil.inativado", resultado, executor_id, usuario_alvo_id=None)
        return resultado

    @_auditar_escrita("perfil.permissao_associar")
    def associar_permissao(
        self,
        *,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID,
        perfil_id: uuid.UUID,
        codigo: str,
        idempotency_key: str,
    ) -> PerfilResultado:
        return self._alterar_permissao(
            tenant_id=tenant_id,
            executor_id=executor_id,
            perfil_id=perfil_id,
            codigo=codigo,
            idempotency_key=idempotency_key,
            remover=False,
        )

    @_auditar_escrita("perfil.permissao_remover")
    def remover_permissao(
        self,
        *,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID,
        perfil_id: uuid.UUID,
        codigo: str,
        idempotency_key: str,
    ) -> PerfilResultado:
        return self._alterar_permissao(
            tenant_id=tenant_id,
            executor_id=executor_id,
            perfil_id=perfil_id,
            codigo=codigo,
            idempotency_key=idempotency_key,
            remover=True,
        )

    @_auditar_escrita("usuario.perfil_atribuir")
    def atribuir_perfil(
        self,
        *,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        perfil_id: uuid.UUID,
        idempotency_key: str,
    ) -> PermissoesEfetivasResultado:
        scope = self._scope("usuario-perfil-atribuir", tenant_id)
        with self._uow_factory() as uow:
            replay = self._replay(uow, idempotency_key, scope, tenant_id, usuario_id, perfil_id)
            if replay is not None:
                uow.commit()
                return _permissoes_de_json(replay)
            usuario = self._usuario_do_tenant(uow, usuario_id, tenant_id, executor_id)
            perfil = self._perfil_do_tenant(uow, perfil_id, tenant_id, executor_id)
            if perfil.estado is not PerfilState.ATIVO:
                raise PerfilConflitoError("Perfil de Acesso inativo")
            uow.perfil_acesso.atribuir_usuario(usuario.id, perfil.id)
            usuario.perfil_acesso = perfil.nome
            uow.usuario.save(usuario)
            resultado = _permissoes(usuario.id, perfil)
            self._concluir_permissoes(uow, idempotency_key, scope, resultado)
            uow.commit()
        self._auditar(
            "usuario.perfil_atribuido",
            _resultado(perfil),
            executor_id,
            usuario_alvo_id=usuario.id,
        )
        return resultado

    @_auditar_escrita("usuario.perfil_remover")
    def remover_perfil(
        self,
        *,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
    ) -> PermissoesEfetivasResultado:
        scope = self._scope("usuario-perfil-remover", tenant_id)
        with self._uow_factory() as uow:
            replay = self._replay(uow, idempotency_key, scope, tenant_id, usuario_id)
            if replay is not None:
                uow.commit()
                return _permissoes_de_json(replay)
            usuario = self._usuario_do_tenant(uow, usuario_id, tenant_id, executor_id)
            uow.perfil_acesso.remover_usuario(usuario.id)
            usuario.perfil_acesso = None
            uow.usuario.save(usuario)
            resultado = PermissoesEfetivasResultado(usuario.id, None, None, ())
            self._concluir_permissoes(uow, idempotency_key, scope, resultado)
            uow.commit()
        self._auditoria.registrar(
            "usuario",
            usuario.id,
            "usuario.perfil_removido",
            "ok",
            detalhes=json.dumps(
                {
                    "tenant_id": str(tenant_id),
                    "executor_id": str(executor_id),
                    "usuario_alvo_id": str(usuario.id),
                }
            ),
        )
        return resultado

    def permissoes_efetivas(
        self, *, tenant_id: uuid.UUID, executor_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> PermissoesEfetivasResultado:
        with self._uow_factory() as uow:
            usuario = self._usuario_do_tenant(uow, usuario_id, tenant_id, executor_id)
            perfil = uow.perfil_acesso.find_by_usuario_id(usuario.id)
            return _permissoes(usuario.id, perfil)

    def _alterar_permissao(
        self,
        *,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID,
        perfil_id: uuid.UUID,
        codigo: str,
        idempotency_key: str,
        remover: bool,
    ) -> PerfilResultado:
        scope = self._scope(
            "perfil-permissao-remover" if remover else "perfil-permissao-associar",
            tenant_id,
        )
        codigo_normalizado = codigo.strip().lower()
        permissao = CATALOGO_POR_CODIGO.get(codigo_normalizado)
        if permissao is None:
            raise ViolacaoInvarianteError("FEATURE-011", "Permissao fora do catalogo")
        if permissao in PERMISSOES_PLATAFORMA:
            raise AcessoNegadoError(codigo_normalizado)
        with self._uow_factory() as uow:
            replay = self._replay(
                uow, idempotency_key, scope, tenant_id, perfil_id, codigo_normalizado
            )
            if replay is not None:
                uow.commit()
                return _perfil_de_json(replay)
            perfil = self._perfil_do_tenant(uow, perfil_id, tenant_id, executor_id)
            if perfil.estado is not PerfilState.ATIVO:
                raise PerfilConflitoError("Perfil de Acesso inativo")
            if remover:
                perfil.remover_permissao(codigo_normalizado)
            else:
                perfil.adicionar_permissao(permissao)
            uow.perfil_acesso.save(perfil)
            resultado = _resultado(perfil)
            self._concluir(uow, idempotency_key, scope, resultado)
            uow.commit()
        self._auditar(
            "perfil.permissao_removida" if remover else "perfil.permissao_associada",
            resultado,
            executor_id,
            usuario_alvo_id=None,
        )
        return resultado

    def _perfil_do_tenant(
        self,
        uow: UnitOfWork,
        perfil_id: uuid.UUID,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID | None = None,
    ) -> PerfilAcesso:
        perfil = uow.perfil_acesso.find_by_id(perfil_id)
        if perfil is None or perfil.tenant_id != tenant_id:
            self._auditoria.registrar(
                "perfil_acesso",
                perfil_id,
                "perfil.acesso_negado",
                "negado",
                detalhes=json.dumps(
                    {
                        "tenant_id": str(tenant_id),
                        "executor_id": str(executor_id) if executor_id else None,
                    }
                ),
            )
            raise PerfilNaoEncontradoError(perfil_id)
        return perfil

    @staticmethod
    def _scope(operacao: str, tenant_id: uuid.UUID) -> str:
        codigos = {
            "perfil-criar": "pc",
            "perfil-renomear": "pr",
            "perfil-inativar": "pi",
            "usuario-perfil-atribuir": "upa",
            "usuario-perfil-remover": "upr",
            "perfil-permissao-remover": "ppr",
            "perfil-permissao-associar": "ppa",
        }
        return f"{codigos[operacao]}:{tenant_id}"

    def _usuario_do_tenant(
        self,
        uow: UnitOfWork,
        usuario_id: uuid.UUID,
        tenant_id: uuid.UUID,
        executor_id: uuid.UUID,
    ) -> Usuario:
        usuario = uow.usuario.find_by_id(usuario_id)
        if usuario is None or usuario.tenant_id != tenant_id:
            self._auditoria.registrar(
                "usuario",
                usuario_id,
                "usuario.acesso_negado",
                "negado",
                detalhes=json.dumps({"tenant_id": str(tenant_id), "executor_id": str(executor_id)}),
            )
            raise UsuarioNaoEncontradoError(usuario_id)
        return usuario

    def _replay(self, uow: UnitOfWork, chave: str, escopo: str, *partes: object) -> str | None:
        fingerprint = hashlib.sha256("|".join(map(str, partes)).encode()).hexdigest()
        existente = uow.idempotencia.find_by_chave(chave, escopo)
        if existente is None:
            uow.idempotencia.registrar(chave, escopo, fingerprint)
            return None
        if existente["estado"] != "finished":
            raise IdempotenciaConflitoError(chave, "operacao em andamento")
        if existente["solicitacao_hash"] != fingerprint:
            raise IdempotenciaConflitoError(chave, "resultado divergente")
        resultado = existente.get("resultado")
        if not isinstance(resultado, str):
            raise IdempotenciaConflitoError(chave, "resultado ausente")
        return resultado

    def _concluir(
        self, uow: UnitOfWork, chave: str, escopo: str, resultado: PerfilResultado
    ) -> None:
        uow.idempotencia.concluir(chave, escopo, _perfil_json(resultado))

    def _concluir_permissoes(
        self,
        uow: UnitOfWork,
        chave: str,
        escopo: str,
        resultado: PermissoesEfetivasResultado,
    ) -> None:
        uow.idempotencia.concluir(
            chave,
            escopo,
            json.dumps(
                {
                    "usuario_id": str(resultado.usuario_id),
                    "perfil_id": str(resultado.perfil_id) if resultado.perfil_id else None,
                    "perfil_nome": resultado.perfil_nome,
                    "permissoes": list(resultado.permissoes),
                }
            ),
        )

    def _auditar(
        self,
        acao: str,
        resultado: PerfilResultado,
        executor_id: uuid.UUID,
        *,
        usuario_alvo_id: uuid.UUID | None,
    ) -> None:
        self._auditoria.registrar(
            "perfil_acesso",
            resultado.id,
            acao,
            "ok",
            detalhes=json.dumps(
                {
                    "tenant_id": str(resultado.tenant_id),
                    "executor_id": str(executor_id),
                    "usuario_alvo_id": str(usuario_alvo_id) if usuario_alvo_id else None,
                }
            ),
        )


def _resultado(perfil: PerfilAcesso) -> PerfilResultado:
    return PerfilResultado(
        perfil.id,
        perfil.tenant_id,
        perfil.nome,
        perfil.estado,
        tuple(permissao.codigo for permissao in perfil.permissoes),
    )


def _permissoes(usuario_id: uuid.UUID, perfil: PerfilAcesso | None) -> PermissoesEfetivasResultado:
    if perfil is None:
        return PermissoesEfetivasResultado(usuario_id, None, None, ())
    return PermissoesEfetivasResultado(
        usuario_id,
        perfil.id,
        perfil.nome,
        (
            tuple(permissao.codigo for permissao in perfil.permissoes)
            if perfil.estado is PerfilState.ATIVO
            else ()
        ),
    )


def _perfil_json(resultado: PerfilResultado) -> str:
    return json.dumps(
        {
            "id": str(resultado.id),
            "tenant_id": str(resultado.tenant_id),
            "nome": resultado.nome,
            "estado": resultado.estado.value,
            "permissoes": list(resultado.permissoes),
        }
    )


def _perfil_de_json(conteudo: str) -> PerfilResultado:
    dados = json.loads(conteudo)
    return PerfilResultado(
        uuid.UUID(dados["id"]),
        uuid.UUID(dados["tenant_id"]),
        dados["nome"],
        PerfilState(dados["estado"]),
        tuple(dados["permissoes"]),
    )


def _permissoes_de_json(conteudo: str) -> PermissoesEfetivasResultado:
    dados = json.loads(conteudo)
    return PermissoesEfetivasResultado(
        uuid.UUID(dados["usuario_id"]),
        uuid.UUID(dados["perfil_id"]) if dados["perfil_id"] else None,
        dados["perfil_nome"],
        tuple(dados["permissoes"]),
    )
