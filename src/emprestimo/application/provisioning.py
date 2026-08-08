"""TenantProvisioningService — orquestrador único do caso de uso (IMP-013).

Fluxo (TASK-043):
1. Validar unicidade (IMP-008);
2. Criar Aggregate Tenant;
3. Provisionar Carteira padrão (IMP-010);
4. Provisionar Usuário Administrador (IMP-011);
5. Inicializar Configurações (IMP-012);
6. Registrar trilha de auditoria (IMP-016);
7. Persistir via Unit of Work em transação única (IMP-014, AD-001);
8. Confirmar provisionamento — Tenant Ativo (UC-007).

Idempotência (AD-002, IMP-015): a Idempotency-Key é registrada na mesma
transação; replay com a mesma chave retorna exatamente o mesmo resultado,
e chave com payload divergente responde conflito. O registro de idempotência
e o de auditoria compartilham a transação com os repositórios de domínio,
exceto os eventos de falha/rollback da auditoria, que persistem em sessão
independente (sobrevivem ao rollback).
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
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.unicidade import UnicidadeTenantService

ESCOPO_IDEMPOTENCIA = "tenant-provisioning"
"""Escopo da Idempotency-Key: isola chaves por caso de uso (AD-002)."""

TRILHA_UC006 = (
    "dados_validados",
    "carteira_criada",
    "usuario_administrador_criado",
    "configuracoes_aplicadas",
    "confirmado",
)
"""Passos da trilha append-only do provisionamento (UC-006, IMP-016)."""


@dataclass(frozen=True)
class TenantProvisionado:
    """Resultado do provisionamento (UC-007) — estado final Ativo (IMP-013).

    Dados suficientes para a confirmação na API (IMP-017): identidade,
    dados institucionais, estado final e timestamp de criação.
    """

    tenant_id: uuid.UUID
    identificador_institucional: str
    nome: str
    estado: TenantState
    criado_em: datetime


def _solicitacao_hash(identificador_institucional: str, nome: str, email_administrador: str) -> str:
    """Fingerprint do payload — detecta chave reenviada com resultado divergente."""
    bruto = f"{identificador_institucional.strip()}|{nome.strip()}|{email_administrador.strip()}"
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


class TenantProvisioningService:
    """Orquestra o provisionamento completo de um Tenant (UC-001..UC-007)."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        unicidade: UnicidadeTenantService,
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._unicidade = unicidade
        self._auditoria = auditoria

    def provisionar(
        self,
        identificador_institucional: str,
        nome: str,
        nome_administrador: str,
        email_administrador: str,
        idempotency_key: str,
    ) -> TenantProvisionado:
        """Executa o provisionamento completo em transação única."""
        identificador = identificador_institucional.strip()
        hash_solicitacao = _solicitacao_hash(identificador, nome, email_administrador)

        self._auditoria.registrar(
            "tenant",
            None,
            "provisionar.inicio",
            "iniciado",
            detalhes=json.dumps({"idempotency_key": idempotency_key}),
        )
        try:
            with self._uow_factory() as uow:
                resultado = self._replay_ou_registrar_chave(uow, idempotency_key, hash_solicitacao)
                if resultado is not None:
                    uow.commit()
                    return resultado

                self._unicidade.verificar(identificador)

                tenant = Tenant(identificador_institucional=identificador, nome=nome.strip())
                carteira = tenant.criar_carteira_padrao()
                admin = tenant.criar_usuario_administrador(
                    nome_administrador.strip(), email_administrador.strip()
                )
                configuracoes = tenant.inicializar_configuracoes()

                for passo in TRILHA_UC006:
                    self._auditoria.registrar(
                        "tenant",
                        None,
                        f"provisionar.{passo}",
                        "ok",
                        detalhes=json.dumps(
                            {
                                "tenant_id": str(tenant.id),
                                "idempotency_key": idempotency_key,
                            }
                        ),
                    )

                uow.tenant.save(tenant)
                uow.carteira.save(carteira)
                uow.usuario.save(admin)
                for configuracao in configuracoes:
                    uow.configuracao.save(configuracao)

                tenant.ativar()
                uow.tenant.save(tenant)

                resultado = TenantProvisionado(
                    tenant_id=tenant.id,
                    identificador_institucional=identificador,
                    nome=tenant.nome,
                    estado=TenantState.ATIVO,
                    criado_em=tenant.criado_em,
                )
                uow.idempotencia.concluir(
                    idempotency_key, ESCOPO_IDEMPOTENCIA, _serializar_resultado(resultado)
                )
                uow.commit()

            self._auditoria.registrar(
                "tenant",
                resultado.tenant_id,
                "provisionar.sucesso",
                "ok",
                detalhes=json.dumps(
                    {"estado": resultado.estado.value, "idempotency_key": idempotency_key}
                ),
            )
            return resultado
        except Exception as exc:
            self._auditoria.registrar(
                "tenant",
                None,
                "provisionar.falha",
                "falhou",
                detalhes=f"{type(exc).__name__}: {exc}",
            )
            self._auditoria.registrar("tenant", None, "provisionar.rollback", "rollback_aplicado")
            raise

    def _replay_ou_registrar_chave(
        self, uow: UnitOfWork, idempotency_key: str, hash_solicitacao: str
    ) -> TenantProvisionado | None:
        """Replay seguro (AD-002): mesma chave → mesmo resultado; divergente → conflito."""
        existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA)
        if existente is None:
            uow.idempotencia.registrar(idempotency_key, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
            return None
        # Estado ANTES do hash: se a operação anterior não terminou, esse é o fato
        # dominante — um hash divergente durante operação em curso é sintoma, não
        # causa. Ordem uniforme nos quatro casos de uso (AD-002).
        if existente["estado"] != "finished":
            raise IdempotenciaConflitoError(idempotency_key, "provisionamento em andamento")
        if existente["solicitacao_hash"] != hash_solicitacao:
            raise IdempotenciaConflitoError(idempotency_key, "resultado divergente")
        self._auditoria.registrar(
            "tenant",
            None,
            "provisionar.replay",
            "ok",
            detalhes=json.dumps({"idempotency_key": idempotency_key}),
        )
        return _desserializar_resultado(existente["resultado"])


def _serializar_resultado(resultado: TenantProvisionado) -> str:
    return json.dumps(
        {
            "tenant_id": str(resultado.tenant_id),
            "identificador_institucional": resultado.identificador_institucional,
            "nome": resultado.nome,
            "estado": resultado.estado.value,
            "criado_em": resultado.criado_em.isoformat(),
        }
    )


def _desserializar_resultado(conteudo: str | None) -> TenantProvisionado:
    if not conteudo:
        raise IdempotenciaConflitoError("?", "resultado ausente no registro")
    dados = json.loads(conteudo)
    return TenantProvisionado(
        tenant_id=uuid.UUID(dados["tenant_id"]),
        identificador_institucional=dados["identificador_institucional"],
        nome=dados["nome"],
        estado=TenantState(dados["estado"]),
        criado_em=datetime.fromisoformat(dados["criado_em"]),
    )
