"""Bootstrap operacional do primeiro Administrador da Plataforma (IMP-099)."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from emprestimo.application.errors import IdempotenciaConflitoError, PerfilConflitoError
from emprestimo.application.iam_catalogo import CATALOGO_PERMISSOES
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.common.errors import TenantJaExisteError, ViolacaoInvarianteError
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import UsuarioState

ESCOPO_IDEMPOTENCIA_BOOTSTRAP = "platform-admin-bootstrap"
CHAVE_IDEMPOTENCIA_BOOTSTRAP = "v1"


@dataclass(frozen=True)
class AdministradorPlataformaBootstrap:
    tenant_id: uuid.UUID
    usuario_id: uuid.UUID
    perfil_id: uuid.UUID
    identificador_institucional: str
    estado: TenantState
    criado_em: datetime
    criado_agora: bool = True


class AdministradorPlataformaBootstrapService:
    """Cria uma unica raiz administrativa em transacao atomica."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria

    def executar(
        self,
        *,
        identificador_institucional: str,
        nome_tenant: str,
        nome_administrador: str,
        email_administrador: str,
        segredo_inicial: str,
    ) -> AdministradorPlataformaBootstrap:
        identificador = identificador_institucional.strip()
        nome = nome_tenant.strip()
        nome_admin = nome_administrador.strip()
        email = email_administrador.strip().lower()
        _validar_entrada(identificador, nome, nome_admin, email)
        if len(segredo_inicial.strip()) < 12:
            raise ViolacaoInvarianteError(
                "IMP-099",
                "credencial inicial deve possuir pelo menos 12 caracteres",
            )
        solicitacao_hash = _solicitacao_hash(identificador, nome, nome_admin, email)

        self._auditoria.registrar(
            "iam_bootstrap",
            None,
            "bootstrap_plataforma.inicio",
            "iniciado",
        )
        try:
            with self._uow_factory() as uow:
                replay = self._replay_ou_registrar(uow, solicitacao_hash)
                if replay is not None:
                    self._validar_estado_do_replay(uow, replay)
                    uow.commit()
                    return replay

                if uow.perfil_acesso.exists_with_permission("tenant.criar"):
                    raise PerfilConflitoError("Administrador da Plataforma ja inicializado")
                if uow.tenant.find_by_identificador_institucional(identificador) is not None:
                    raise TenantJaExisteError(identificador)

                tenant = Tenant(identificador_institucional=identificador, nome=nome)
                carteira = tenant.criar_carteira_padrao()
                usuario = tenant.criar_usuario_administrador_plataforma(nome_admin, email)
                configuracoes = tenant.inicializar_configuracoes()
                perfil = PerfilAcesso(tenant_id=tenant.id, nome="administrador_plataforma")
                # IMP-363: o catalogo INTEIRO, nao so as permissoes `tenant.*`.
                #
                # Ate 2026-08-27 este perfil recebia apenas PERMISSOES_PLATAFORMA, e
                # quem concedia as operacionais era o provisionamento por API — que o
                # IMP-351 removeu. O resultado, observado em stack real: o sistema
                # subia, autenticava, e o unico usuario existente tomava 403 em tudo,
                # inclusive em `perfil.gerir`, entao nao havia nem como se autoconceder
                # permissao. Deadlock completo.
                #
                # Decisao do fundador em 2026-08-27: o sistema e de uso pessoal, com um
                # Tenant e um usuario. Separar papeis administrativo e operacional so
                # faria sentido com mais de uma pessoa; aqui produziria exatamente o
                # deadlock acima.
                for permissao in CATALOGO_PERMISSOES:
                    perfil.adicionar_permissao(permissao)

                credencial = Credencial.definir(
                    usuario_id=usuario.id,
                    segredo=segredo_inicial,
                )
                usuario.ativar()

                uow.tenant.save(tenant)
                uow.carteira.save(carteira)
                uow.usuario.save(usuario)
                uow.credencial.save(credencial)
                uow.perfil_acesso.save(perfil)
                uow.perfil_acesso.atribuir_usuario(usuario.id, perfil.id)
                for configuracao in configuracoes:
                    uow.configuracao.save(configuracao)
                tenant.ativar()
                uow.tenant.save(tenant)

                resultado = AdministradorPlataformaBootstrap(
                    tenant_id=tenant.id,
                    usuario_id=usuario.id,
                    perfil_id=perfil.id,
                    identificador_institucional=identificador,
                    estado=TenantState.ATIVO,
                    criado_em=tenant.criado_em,
                )
                uow.idempotencia.concluir(
                    CHAVE_IDEMPOTENCIA_BOOTSTRAP,
                    ESCOPO_IDEMPOTENCIA_BOOTSTRAP,
                    _serializar_resultado(resultado),
                )
                uow.commit()

        except Exception as exc:
            self._auditoria.registrar(
                "iam_bootstrap",
                None,
                "bootstrap_plataforma.falha",
                "falhou",
                detalhes=json.dumps({"erro": type(exc).__name__}),
            )
            self._auditoria.registrar(
                "iam_bootstrap",
                None,
                "bootstrap_plataforma.rollback",
                "rollback_aplicado",
            )
            raise

        self._auditoria.registrar(
            "iam_bootstrap",
            resultado.usuario_id,
            "bootstrap_plataforma.sucesso",
            "ok",
            detalhes=json.dumps({"tenant_id": str(resultado.tenant_id)}),
        )
        return resultado

    def _replay_ou_registrar(
        self,
        uow: UnitOfWork,
        solicitacao_hash: str,
    ) -> AdministradorPlataformaBootstrap | None:
        registro = uow.idempotencia.find_by_chave(
            CHAVE_IDEMPOTENCIA_BOOTSTRAP,
            ESCOPO_IDEMPOTENCIA_BOOTSTRAP,
        )
        if registro is None:
            uow.idempotencia.registrar(
                CHAVE_IDEMPOTENCIA_BOOTSTRAP,
                ESCOPO_IDEMPOTENCIA_BOOTSTRAP,
                solicitacao_hash,
            )
            return None
        if registro["estado"] != "finished":
            raise IdempotenciaConflitoError(
                CHAVE_IDEMPOTENCIA_BOOTSTRAP,
                "bootstrap em andamento",
            )
        if registro["solicitacao_hash"] != solicitacao_hash:
            raise IdempotenciaConflitoError(
                CHAVE_IDEMPOTENCIA_BOOTSTRAP,
                "Administrador da Plataforma ja inicializado com outros dados",
            )
        self._auditoria.registrar(
            "iam_bootstrap",
            None,
            "bootstrap_plataforma.replay",
            "ok",
        )
        return _desserializar_resultado(registro["resultado"])

    @staticmethod
    def _validar_estado_do_replay(
        uow: UnitOfWork,
        resultado: AdministradorPlataformaBootstrap,
    ) -> None:
        tenant = uow.tenant.find_by_id(resultado.tenant_id)
        usuario = uow.usuario.find_by_id(resultado.usuario_id)
        perfil = uow.perfil_acesso.find_by_usuario_id(resultado.usuario_id)
        credencial = uow.credencial.find_by_usuario_id(resultado.usuario_id)
        if (
            tenant is None
            or tenant.estado is not TenantState.ATIVO
            or usuario is None
            or usuario.tenant_id != resultado.tenant_id
            or usuario.estado is not UsuarioState.ATIVO
            or perfil is None
            or perfil.id != resultado.perfil_id
            or perfil.tenant_id != resultado.tenant_id
            or not perfil.permite("tenant.criar")
            or credencial is None
        ):
            raise PerfilConflitoError("estado do bootstrap da plataforma esta inconsistente")


def _solicitacao_hash(
    identificador: str,
    nome_tenant: str,
    nome_administrador: str,
    email_administrador: str,
) -> str:
    payload = json.dumps(
        {
            "email_administrador": email_administrador,
            "identificador_institucional": identificador,
            "nome_administrador": nome_administrador,
            "nome_tenant": nome_tenant,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validar_entrada(
    identificador: str,
    nome_tenant: str,
    nome_administrador: str,
    email_administrador: str,
) -> None:
    limites = (
        (identificador, 120, "identificador institucional"),
        (nome_tenant, 200, "nome do Tenant"),
        (nome_administrador, 200, "nome do administrador"),
    )
    for valor, limite, campo in limites:
        if not valor or len(valor) > limite:
            raise ViolacaoInvarianteError(
                "IMP-099",
                f"{campo} deve possuir entre 1 e {limite} caracteres",
            )
    if (
        len(email_administrador) < 3
        or len(email_administrador) > 254
        or "@" not in email_administrador
        or email_administrador.startswith("@")
        or email_administrador.endswith("@")
    ):
        raise ViolacaoInvarianteError("IMP-099", "e-mail do administrador invalido")


def _serializar_resultado(resultado: AdministradorPlataformaBootstrap) -> str:
    return json.dumps(
        {
            "tenant_id": str(resultado.tenant_id),
            "usuario_id": str(resultado.usuario_id),
            "perfil_id": str(resultado.perfil_id),
            "identificador_institucional": resultado.identificador_institucional,
            "estado": resultado.estado.value,
            "criado_em": resultado.criado_em.isoformat(),
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _desserializar_resultado(conteudo: str | None) -> AdministradorPlataformaBootstrap:
    if not conteudo:
        raise IdempotenciaConflitoError(
            CHAVE_IDEMPOTENCIA_BOOTSTRAP,
            "resultado ausente no registro",
        )
    dados = json.loads(conteudo)
    return AdministradorPlataformaBootstrap(
        tenant_id=uuid.UUID(dados["tenant_id"]),
        usuario_id=uuid.UUID(dados["usuario_id"]),
        perfil_id=uuid.UUID(dados["perfil_id"]),
        identificador_institucional=dados["identificador_institucional"],
        estado=TenantState(dados["estado"]),
        criado_em=datetime.fromisoformat(dados["criado_em"]),
        criado_agora=False,
    )
