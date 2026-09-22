"""Casos de uso do interruptor do Mercado Pago (IMP-388, PLAN-045 §3.12).

Ligar a integracao custa 0,99% por recebimento, e a Credora ja tem o caminho
sem taxa. Por isso o desligado e o padrao e a decisao e dela, no painel.

Os segredos entram claros e saem **cifrados** daqui; o DTO devolvido nunca
carrega valor de segredo — so se a credencial existe, quando foi testada e se
esta ligada.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from emprestimo.application.errors import IdempotenciaConflitoError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.configuracao_mercadopago import ConfiguracaoMercadoPago
from emprestimo.infrastructure.cifra import CifraToken
from emprestimo.infrastructure.mercadopago import ResultadoVerificacao, verificar_credencial

__all__ = [
    "ConfiguracaoMercadoPagoResultado",
    "ConfiguracaoMercadoPagoService",
    "MercadoPagoDesabilitadoError",
    "VerificacaoCredencialError",
]

ESCOPO_IDEMPOTENCIA = "platform-mercadopago-configuracao"
RECURSO_AUDITORIA = "configuracao_mercadopago"


class MercadoPagoDesabilitadoError(Exception):
    """A integracao esta desligada para este Tenant (PLAN-045 §4.8-b).

    Nomeada porque desligado nao e falta de credencial nem erro do provedor: e
    uma escolha da Credora, e quem chamar precisa distinguir para responder
    direito ao devedor.
    """

    def __init__(self, tenant_id: uuid.UUID) -> None:
        super().__init__(f"recebimento por Pix desabilitado para o tenant {tenant_id}")
        self.tenant_id = tenant_id
        self.codigo = "mercadopago_desabilitado"


class VerificacaoCredencialError(Exception):
    """O provedor recusou a credencial ou nao respondeu."""

    def __init__(self, detalhe: str) -> None:
        super().__init__(f"teste da credencial falhou: {detalhe}")
        self.detalhe = detalhe


@dataclass(frozen=True)
class ConfiguracaoMercadoPagoResultado:
    """Estado visivel da integracao. **Nunca carrega segredo.**"""

    tenant_id: uuid.UUID
    habilitado: bool
    credencial_configurada: bool
    assinatura_configurada: bool
    testado_em: datetime | None
    atualizado_em: datetime
    atualizado_por: uuid.UUID | None


def _resultado(config: ConfiguracaoMercadoPago) -> ConfiguracaoMercadoPagoResultado:
    return ConfiguracaoMercadoPagoResultado(
        tenant_id=config.tenant_id,
        habilitado=config.habilitado,
        credencial_configurada=config.access_token_cifrado is not None,
        assinatura_configurada=config.webhook_secret_cifrado is not None,
        testado_em=config.testado_em,
        atualizado_em=config.atualizado_em,
        atualizado_por=config.atualizado_por,
    )


class ConfiguracaoMercadoPagoService:
    """Consulta, credenciais, teste e interruptor."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
        cifra_factory: Callable[[], CifraToken],
        verificador: Callable[[str], ResultadoVerificacao] | None = None,
        agora: Callable[[], datetime] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria
        self._cifra_factory = cifra_factory
        # Resolvido aqui, e nao como default do parametro: default e ligado na
        # definicao da funcao, o que deixaria o dublê de teste sem efeito.
        self._verificador = verificador or verificar_credencial
        self._agora = agora or (lambda: datetime.now(UTC))

    def consultar(self, *, tenant_id: uuid.UUID) -> ConfiguracaoMercadoPagoResultado:
        """Tenant sem linha e desligado — ausencia nao e erro."""
        with self._uow_factory() as uow:
            config = uow.configuracao_mercadopago.find_by_tenant_id(tenant_id)
        if config is None:
            config = ConfiguracaoMercadoPago.nova(tenant_id=tenant_id, agora=self._agora())
        return _resultado(config)

    def definir_credenciais(
        self,
        *,
        tenant_id: uuid.UUID,
        access_token: str,
        webhook_secret: str,
        usuario_id: uuid.UUID,
        idempotency_key: str,
    ) -> ConfiguracaoMercadoPagoResultado:
        cifra = self._cifra_factory()
        agora = self._agora()
        # O hash cobre o conteudo dos segredos sem guarda-los: replay com o
        # mesmo par converge, replay com par diferente e conflito.
        hash_solicitacao = hashlib.sha256(
            f"{tenant_id}:{access_token}:{webhook_secret}".encode()
        ).hexdigest()
        with self._uow_factory() as uow:
            if self._idempotencia(uow, idempotency_key, hash_solicitacao):
                return _resultado(self._carregar(uow, tenant_id, agora))
            config = self._carregar(uow, tenant_id, agora)
            config.definir_credenciais(
                access_token_cifrado=cifra.cifrar(access_token),
                webhook_secret_cifrado=cifra.cifrar(webhook_secret),
                usuario_id=usuario_id,
                agora=agora,
            )
            uow.configuracao_mercadopago.save(config)
            uow.idempotencia.concluir(
                idempotency_key, ESCOPO_IDEMPOTENCIA, json.dumps({"definidas": True})
            )
            uow.commit()
        self._auditar("definir_credenciais", tenant_id, usuario_id)
        return _resultado(config)

    def testar(
        self, *, tenant_id: uuid.UUID, usuario_id: uuid.UUID
    ) -> ConfiguracaoMercadoPagoResultado:
        """Leitura autenticada no provedor, sem criar cobranca."""
        cifra = self._cifra_factory()
        agora = self._agora()
        with self._uow_factory() as uow:
            config = self._carregar(uow, tenant_id, agora)
            if config.access_token_cifrado is None:
                raise VerificacaoCredencialError("credencial_ausente")
            token = cifra.decifrar(config.access_token_cifrado)

        resultado = self._verificador(token)
        if not resultado.valido:
            self._auditar("testar.falha", tenant_id, usuario_id, detalhe=resultado.detalhe)
            raise VerificacaoCredencialError(resultado.detalhe)

        with self._uow_factory() as uow:
            config = self._carregar(uow, tenant_id, agora)
            config.registrar_teste_bem_sucedido(agora=agora)
            uow.configuracao_mercadopago.save(config)
            uow.commit()
        self._auditar("testar.sucesso", tenant_id, usuario_id)
        return _resultado(config)

    def habilitar(
        self, *, tenant_id: uuid.UUID, usuario_id: uuid.UUID, idempotency_key: str
    ) -> ConfiguracaoMercadoPagoResultado:
        return self._alternar(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            ligar=True,
        )

    def desabilitar(
        self, *, tenant_id: uuid.UUID, usuario_id: uuid.UUID, idempotency_key: str
    ) -> ConfiguracaoMercadoPagoResultado:
        """Impede emissao nova; **nao** invalida CobrancaPix pendente."""
        return self._alternar(
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            idempotency_key=idempotency_key,
            ligar=False,
        )

    def exigir_habilitado(self, uow: UnitOfWork, tenant_id: uuid.UUID) -> None:
        """Guarda de caso de uso: quem emite Pix chama isto antes.

        Vive aqui, e nao na UI, porque o agente tambem emite — e a checagem
        precisa valer para os dois chamadores.
        """
        config = uow.configuracao_mercadopago.find_by_tenant_id(tenant_id)
        if config is None or not config.habilitado:
            raise MercadoPagoDesabilitadoError(tenant_id)

    def _alternar(
        self,
        *,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        idempotency_key: str,
        ligar: bool,
    ) -> ConfiguracaoMercadoPagoResultado:
        agora = self._agora()
        acao = "habilitar" if ligar else "desabilitar"
        hash_solicitacao = hashlib.sha256(f"{tenant_id}:{acao}".encode()).hexdigest()
        with self._uow_factory() as uow:
            if self._idempotencia(uow, idempotency_key, hash_solicitacao):
                return _resultado(self._carregar(uow, tenant_id, agora))
            config = self._carregar(uow, tenant_id, agora)
            if ligar:
                config.habilitar(usuario_id=usuario_id, agora=agora)
            else:
                config.desabilitar(usuario_id=usuario_id, agora=agora)
            uow.configuracao_mercadopago.save(config)
            uow.idempotencia.concluir(
                idempotency_key, ESCOPO_IDEMPOTENCIA, json.dumps({"habilitado": ligar})
            )
            uow.commit()
        self._auditar(acao, tenant_id, usuario_id)
        return _resultado(config)

    def _carregar(
        self, uow: UnitOfWork, tenant_id: uuid.UUID, agora: datetime
    ) -> ConfiguracaoMercadoPago:
        config = uow.configuracao_mercadopago.find_by_tenant_id(tenant_id)
        if config is None:
            config = ConfiguracaoMercadoPago.nova(tenant_id=tenant_id, agora=agora)
        return config

    @staticmethod
    def _idempotencia(uow: UnitOfWork, chave: str, hash_solicitacao: str) -> bool:
        """True quando a chave ja concluiu com a MESMA solicitacao (replay)."""
        existente = uow.idempotencia.find_by_chave(chave, ESCOPO_IDEMPOTENCIA)
        if existente is not None:
            if existente["estado"] != "finished":
                raise IdempotenciaConflitoError(chave, "operacao em andamento")
            if existente["solicitacao_hash"] != hash_solicitacao:
                raise IdempotenciaConflitoError(chave, "solicitacao divergente")
            return True
        uow.idempotencia.registrar(chave, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
        return False

    def _auditar(
        self,
        acao: str,
        tenant_id: uuid.UUID,
        usuario_id: uuid.UUID,
        detalhe: str | None = None,
    ) -> None:
        self._auditoria.registrar(
            RECURSO_AUDITORIA,
            tenant_id,
            acao,
            "ok",
            detalhes=json.dumps(
                {"usuario_id": str(usuario_id), "detalhe": detalhe}, sort_keys=True
            ),
        )
