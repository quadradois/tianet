"""Lancamento composto de emprestimo em transacao unica (IMP-305, PLAN-027).

O Credor individual decide devedor, valor, taxa e dia de acerto de uma
vez so. A cadeia Proposta -> Contrato -> Emprestimo -> Parcelas continua sendo
percorrida integralmente pelos metodos de agregado, com registro de decisao a
cada transicao: as invariantes sao executadas, nunca contornadas. O que
desaparece e o operador ter de disparar seis chamadas sucessivas.

Tudo acontece sob um unico `UnitOfWork`. Falha em qualquer passo desfaz o
conjunto, o que elimina a classe de estado orfao que o caminho HTTP em oito
etapas produz hoje (ver PLAN-027 e o Discovery correspondente).
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from emprestimo.application.auditoria_escrita import auditar_escrita
from emprestimo.application.comprovante import ComprovanteLancamento
from emprestimo.application.errors import (
    CarteiraNaoEncontradaError,
    DevedorNaoEncontradoError,
    IdempotenciaConflitoError,
    TransicaoEstadoInvalidaError,
    UsuarioNaoEncontradoError,
)
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.contrato_credito import ContratoCredito
from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.proposta_comercial import PropostaComercial

ESCOPO_IDEMPOTENCIA = "credit.lancamento"
logger = logging.getLogger(__name__)


class ResultadoFinanceiro(Protocol):
    """O que o Motor devolve ao lancamento.

    Propriedades somente-leitura para aceitar dataclass congelada do lado do
    Motor sem que este modulo precise conhecer o tipo concreto.
    """

    @property
    def emprestimo_id(self) -> uuid.UUID: ...

    @property
    def primeiro_acerto_em(self) -> date: ...

    @property
    def valor_contratado(self) -> Decimal: ...

    @property
    def moeda(self) -> str: ...

    @property
    def taxa_juros_mensal_percentual(self) -> Decimal: ...

    @property
    def dia_de_acerto(self) -> int: ...


class CriadorDeEmprestimo(Protocol):
    """Porta para a etapa financeira do lancamento.

    O lancamento orquestra Cadastro, Comercial e Contratos, e delega a criacao
    do Emprestimo. Recebe a operacao por injecao para nao
    importar o Motor: o calculo permanece exclusivo dele, e o guardrail de
    exclusividade continua valendo sem excecao para este modulo.
    """

    def __call__(
        self, uow: UnitOfWork, *, saida_logica: object, data_referencia: date
    ) -> ResultadoFinanceiro: ...


@dataclass(frozen=True)
class DevedorNovo:
    """Dados do Devedor quando o wizard cadastra em vez de reutilizar."""

    documento: str
    nome: str
    contato_whatsapp: str


@dataclass(frozen=True)
class CondicoesLancamento:
    """Os tres parametros que o Credor digita no ato (DR-004).

    Sao repassados ao Motor exatamente como recebidos. Nenhum valor padrao e
    inventado aqui: o Credor define cada um deles.
    """

    valor_contratado: str
    taxa_juros_mensal: str
    dia_de_acerto: int
    moeda: str = "BRL"

    def como_parametros(self) -> Mapping[str, object]:
        return {
            "valor_contratado": self.valor_contratado,
            "taxa_juros_mensal": self.taxa_juros_mensal,
            "dia_de_acerto": self.dia_de_acerto,
            "moeda": self.moeda,
        }


@dataclass(frozen=True)
class LancamentoResultado:
    """Identificadores gerados pela cadeia, para navegacao e comprovante."""

    devedor_id: uuid.UUID
    proposta_id: uuid.UUID
    contrato_id: uuid.UUID
    emprestimo_id: uuid.UUID
    primeiro_acerto_em: date
    comprovante: ComprovanteLancamento | None = None


class LancamentoService:
    """Executa a cadeia completa de lancamento sob um unico commit."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        criar_emprestimo: CriadorDeEmprestimo,
        enfileirar_comprovante: Callable[[ComprovanteLancamento], object],
        auditoria: AuditoriaRegistro,
    ) -> None:
        self._uow_factory = uow_factory
        self._criar_emprestimo = criar_emprestimo
        self._enfileirar_comprovante = enfileirar_comprovante
        self._auditoria = auditoria

    @auditar_escrita("lancamento", "lancar")
    def lancar(
        self,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        usuario_id: uuid.UUID,
        condicoes: CondicoesLancamento,
        data_referencia: date,
        idempotency_key: str,
        devedor_id: uuid.UUID | None = None,
        devedor_novo: DevedorNovo | None = None,
    ) -> LancamentoResultado:
        if (devedor_id is None) == (devedor_novo is None):
            raise ViolacaoInvarianteError(
                "PLAN-027",
                "informe exatamente um entre devedor existente e devedor novo",
            )
        hash_solicitacao = _solicitacao_hash(
            carteira_id=carteira_id,
            usuario_id=usuario_id,
            condicoes=condicoes,
            devedor_id=devedor_id,
            devedor_novo=devedor_novo,
        )

        with self._uow_factory() as uow:
            replay = self._replay_ou_registrar_chave(uow, idempotency_key, hash_solicitacao)
            if replay is not None:
                uow.commit()
                resultado = replay
            else:
                self._validar_contexto(
                    uow, tenant_id=tenant_id, carteira_id=carteira_id, usuario_id=usuario_id
                )
                devedor = (
                    self._devedor_existente(uow, devedor_id=devedor_id, carteira_id=carteira_id)
                    if devedor_id is not None
                    else self._criar_devedor(uow, carteira_id=carteira_id, dados=devedor_novo)
                )
                destinatario_whatsapp = _contato_whatsapp(devedor)

                proposta = self._proposta_aprovada(
                    uow,
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor.id,
                    usuario_id=usuario_id,
                    condicoes=condicoes,
                )
                contrato = self._contrato_liberado(uow, proposta=proposta, usuario_id=usuario_id)
                financeiro = self._criar_emprestimo(
                    uow,
                    saida_logica=contrato.gerar_saida_logica(),
                    data_referencia=data_referencia,
                )

                comprovante = ComprovanteLancamento(
                    tenant_id=tenant_id,
                    carteira_id=carteira_id,
                    devedor_id=devedor.id,
                    nome_devedor=devedor.nome,
                    destinatario_whatsapp=destinatario_whatsapp,
                    emprestimo_id=financeiro.emprestimo_id,
                    valor_contratado=financeiro.valor_contratado,
                    moeda=financeiro.moeda,
                    taxa_juros_mensal_percentual=financeiro.taxa_juros_mensal_percentual,
                    dia_de_acerto=financeiro.dia_de_acerto,
                    primeiro_acerto_em=financeiro.primeiro_acerto_em,
                )
                resultado = LancamentoResultado(
                    devedor_id=devedor.id,
                    proposta_id=proposta.id,
                    contrato_id=contrato.id,
                    emprestimo_id=financeiro.emprestimo_id,
                    primeiro_acerto_em=financeiro.primeiro_acerto_em,
                    comprovante=comprovante,
                )
                uow.idempotencia.concluir(
                    idempotency_key, ESCOPO_IDEMPOTENCIA, _serializar(resultado)
                )
                uow.commit()

        self._enfileirar_apos_commit(resultado)
        return resultado

    def _enfileirar_apos_commit(self, resultado: LancamentoResultado) -> None:
        if resultado.comprovante is None:
            return
        try:
            self._enfileirar_comprovante(resultado.comprovante)
        except Exception:
            # A fila e deliberadamente posterior ao commit do lancamento. Uma
            # indisponibilidade operacional pode ser reparada pelo replay da
            # chave idempotente, mas nunca deve transformar sucesso financeiro
            # persistido em erro/rollback para o usuario.
            logger.exception(
                "comprovante_enqueue_failed",
                extra={"emprestimo_id": str(resultado.emprestimo_id)},
            )

    def _replay_ou_registrar_chave(
        self, uow: UnitOfWork, idempotency_key: str, hash_solicitacao: str
    ) -> LancamentoResultado | None:
        """Replay seguro (AD-002): mesma chave, mesmo resultado; divergente, conflito."""
        existente = uow.idempotencia.find_by_chave(idempotency_key, ESCOPO_IDEMPOTENCIA)
        if existente is None:
            uow.idempotencia.registrar(idempotency_key, ESCOPO_IDEMPOTENCIA, hash_solicitacao)
            return None
        if existente["estado"] != "finished":
            raise IdempotenciaConflitoError(idempotency_key, "lancamento em andamento")
        if existente["solicitacao_hash"] != hash_solicitacao:
            raise IdempotenciaConflitoError(idempotency_key, "resultado divergente")
        return _desserializar(existente["resultado"])

    # -- passos ------------------------------------------------------------

    def _validar_contexto(
        self,
        uow: UnitOfWork,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        usuario_id: uuid.UUID,
    ) -> None:
        carteira = uow.carteira.find_by_id(carteira_id)
        if carteira is None or carteira.tenant_id != tenant_id:
            raise CarteiraNaoEncontradaError(carteira_id)
        usuario = uow.usuario.find_by_id(usuario_id)
        if usuario is None or usuario.tenant_id != tenant_id:
            raise UsuarioNaoEncontradoError(usuario_id)

    def _devedor_existente(
        self, uow: UnitOfWork, *, devedor_id: uuid.UUID, carteira_id: uuid.UUID
    ) -> Devedor:
        devedor = uow.devedor.find_by_id(devedor_id)
        if devedor is None or devedor.carteira_id != carteira_id:
            raise DevedorNaoEncontradoError(devedor_id)
        return devedor

    def _criar_devedor(
        self, uow: UnitOfWork, *, carteira_id: uuid.UUID, dados: DevedorNovo | None
    ) -> Devedor:
        assert dados is not None  # garantido pela validacao de entrada
        documento = Documento.from_str(dados.documento)
        if uow.devedor.find_by_documento_carteira(documento, carteira_id) is not None:
            raise ViolacaoInvarianteError(
                "RN-003",
                f"documento '{documento}' ja cadastrado nesta Carteira",
            )
        devedor = Devedor.criar(
            carteira_id=carteira_id,
            documento=documento,
            nome=dados.nome,
            contatos=(
                Contato(
                    devedor_id=uuid.UUID(int=0),
                    tipo=TipoContato.WHATSAPP,
                    valor=dados.contato_whatsapp,
                    preferencial=True,
                ),
            ),
        )
        uow.devedor.save(devedor)
        for contato in devedor.contatos:
            uow.contato.save(contato)
        return devedor

    def _proposta_aprovada(
        self,
        uow: UnitOfWork,
        *,
        tenant_id: uuid.UUID,
        carteira_id: uuid.UUID,
        devedor_id: uuid.UUID,
        usuario_id: uuid.UUID,
        condicoes: CondicoesLancamento,
    ) -> PropostaComercial:
        proposta = PropostaComercial.criar(
            tenant_id=tenant_id,
            carteira_id=carteira_id,
            devedor_id=devedor_id,
            criada_por_usuario_id=usuario_id,
            parametros=condicoes.como_parametros(),
        )
        # O Credor origina e decide no mesmo ato; as duas transicoes existem para
        # a origem do agente de IA (FOUNDATION-001 §3.1) e ficam registradas
        # igualmente aqui.
        proposta.enviar_para_analise(usuario_id=usuario_id)
        proposta.aprovar(usuario_id=usuario_id)
        uow.proposta_comercial.save(proposta)
        return proposta

    def _contrato_liberado(
        self, uow: UnitOfWork, *, proposta: PropostaComercial, usuario_id: uuid.UUID
    ) -> ContratoCredito:
        try:
            contrato = ContratoCredito.criar_de_proposta_aprovada(
                proposta=proposta.gerar_contrato_logico(),
                criado_por_usuario_id=usuario_id,
            )
            if contrato.estado is ContratoCreditoState.RASCUNHO:
                contrato.formalizar(usuario_id=usuario_id)
            contrato.assinar(usuario_id=usuario_id)
            contrato.liberar_para_motor(usuario_id=usuario_id)
        except ViolacaoInvarianteError as exc:
            raise TransicaoEstadoInvalidaError(proposta.id, "lancar_contrato", str(exc)) from exc
        uow.contrato_credito.save(contrato)
        return contrato


def _solicitacao_hash(
    *,
    carteira_id: uuid.UUID,
    usuario_id: uuid.UUID,
    condicoes: CondicoesLancamento,
    devedor_id: uuid.UUID | None,
    devedor_novo: DevedorNovo | None,
) -> str:
    """Impressao da intencao: mesma intencao, mesma chave; intencao nova, chave nova."""
    corpo = json.dumps(
        {
            "carteira_id": str(carteira_id),
            "usuario_id": str(usuario_id),
            "condicoes": dict(condicoes.como_parametros()),
            "devedor_id": str(devedor_id) if devedor_id else None,
            "devedor_novo": (
                None
                if devedor_novo is None
                else {
                    "documento": devedor_novo.documento,
                    "nome": devedor_novo.nome,
                    "contato_whatsapp": devedor_novo.contato_whatsapp,
                }
            ),
        },
        sort_keys=True,
    )
    return hashlib.sha256(corpo.encode("utf-8")).hexdigest()


def _serializar(resultado: LancamentoResultado) -> str:
    return json.dumps(
        {
            "devedor_id": str(resultado.devedor_id),
            "proposta_id": str(resultado.proposta_id),
            "contrato_id": str(resultado.contrato_id),
            "emprestimo_id": str(resultado.emprestimo_id),
            "primeiro_acerto_em": resultado.primeiro_acerto_em.isoformat(),
            "comprovante": _serializar_comprovante(resultado.comprovante),
        },
        sort_keys=True,
    )


def _desserializar(conteudo: str | None) -> LancamentoResultado:
    if not conteudo:
        raise IdempotenciaConflitoError("?", "resultado ausente no registro")
    dados = json.loads(conteudo)
    return LancamentoResultado(
        devedor_id=uuid.UUID(dados["devedor_id"]),
        proposta_id=uuid.UUID(dados["proposta_id"]),
        contrato_id=uuid.UUID(dados["contrato_id"]),
        emprestimo_id=uuid.UUID(dados["emprestimo_id"]),
        primeiro_acerto_em=date.fromisoformat(str(dados["primeiro_acerto_em"])),
        comprovante=_desserializar_comprovante(dados.get("comprovante")),
    )


def _contato_whatsapp(devedor: Devedor) -> str:
    contatos = [contato for contato in devedor.contatos if contato.tipo is TipoContato.WHATSAPP]
    preferencial = next((contato for contato in contatos if contato.preferencial), None)
    escolhido = preferencial or next(iter(contatos), None)
    if escolhido is None:
        raise ViolacaoInvarianteError(
            "PLAN-027",
            "devedor precisa de contato WhatsApp para receber o comprovante",
        )
    return escolhido.valor


def _serializar_comprovante(
    comprovante: ComprovanteLancamento | None,
) -> dict[str, object] | None:
    if comprovante is None:
        return None
    return {
        "tenant_id": str(comprovante.tenant_id),
        "carteira_id": str(comprovante.carteira_id),
        "devedor_id": str(comprovante.devedor_id),
        "nome_devedor": comprovante.nome_devedor,
        "destinatario_whatsapp": comprovante.destinatario_whatsapp,
        "emprestimo_id": str(comprovante.emprestimo_id),
        "valor_contratado": str(comprovante.valor_contratado),
        "moeda": comprovante.moeda,
        "taxa_juros_mensal_percentual": str(comprovante.taxa_juros_mensal_percentual),
        "dia_de_acerto": comprovante.dia_de_acerto,
        "primeiro_acerto_em": comprovante.primeiro_acerto_em.isoformat(),
    }


def _desserializar_comprovante(dados: object) -> ComprovanteLancamento | None:
    if not isinstance(dados, dict):
        return None
    return ComprovanteLancamento(
        tenant_id=uuid.UUID(str(dados["tenant_id"])),
        carteira_id=uuid.UUID(str(dados["carteira_id"])),
        devedor_id=uuid.UUID(str(dados["devedor_id"])),
        nome_devedor=str(dados["nome_devedor"]),
        destinatario_whatsapp=str(dados["destinatario_whatsapp"]),
        emprestimo_id=uuid.UUID(str(dados["emprestimo_id"])),
        valor_contratado=Decimal(str(dados["valor_contratado"])),
        moeda=str(dados["moeda"]),
        taxa_juros_mensal_percentual=Decimal(str(dados["taxa_juros_mensal_percentual"])),
        dia_de_acerto=int(dados["dia_de_acerto"]),
        primeiro_acerto_em=date.fromisoformat(str(dados["primeiro_acerto_em"])),
    )
