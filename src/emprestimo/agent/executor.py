"""Executor do copiloto (IMP-356-F slice 3).

Um turno completo sob deadline e orçamento enforcement em código: claim
de slot, sessão e contexto uma vez, até 2 chamadas LLM e 2 tools lógicas
em 6 HTTP, reconsulta única com reautorização, lease com fencing via
slots, e estado terminal em qualquer falha — sem reinício de orçamento,
sem reenvio. Resposta com dado vem só de apresentador; prosa do modelo
só é entregue quando nenhuma ferramenta foi usada.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from emprestimo.agent.api_client import (
    ApiAusenciaError,
    ApiAutorizacaoError,
    ApiError,
    ClienteApi,
    ProtocoloClienteApi,
)
from emprestimo.agent.apresentadores import mensagem_ausencia, renderizar
from emprestimo.agent.catalogo import CATALOGO, CATALOGO_VERSAO
from emprestimo.agent.conversa import (
    ClasseContexto,
    MensagemConversa,
    PapelMensagem,
    SessaoConversa,
)
from emprestimo.agent.credencial import CredencialError, ProvedorTokenCopilot
from emprestimo.agent.custo import estimar_custo_usd
from emprestimo.agent.dispatcher import (
    ArgumentoInvalidoError,
    ContextoFerramentas,
    FerramentaDesconhecidaError,
    executar_ferramenta,
)
from emprestimo.agent.intencao import interpretar_chamada
from emprestimo.agent.llm_client import (
    LlmClient,
    LlmError,
    Mensagem,
    PedidoChat,
    RespostaChat,
    montar_tools,
)
from emprestimo.agent.metricas import METRICAS, METRICAS_LLM
from emprestimo.agent.prompts import RESPOSTA_FIXA_PRE_CADASTRO, montar_sistema_operadora

logger = logging.getLogger(__name__)

DEADLINE_SEGUNDOS = 45
MAX_CHAMADAS_LLM = 2
MAX_TOOLS_LOGICAS = 2
MAX_HTTP_TOTAL = 6
IDADE_MAXIMA_SEGUNDOS = 120
MAX_TOKENS_ENTRADA = 8000
TIMEOUT_LLM_SEGUNDOS = 15.0
TIMEOUT_API_SEGUNDOS = 5.0
MAX_RESPOSTA_BYTES = 256 * 1024
MAX_RESPOSTA_ITENS = 100
MAX_MSG_CANAL = 3000
MENSAGENS_CONTEXTO = 10
JANELA_CONTEXTO_MINUTOS = 30

RESPOSTA_INDISPONIVEL = "A informação está indisponível no momento."


@dataclass(frozen=True)
class EntradaExecucao:
    inbox_id: uuid.UUID
    sessao: SessaoConversa
    texto: str
    recebido_em: datetime
    correlation_id: str = ""


@dataclass(frozen=True)
class ResultadoExecucao:
    estado: str  # "concluida" | "incompleta" | "recusada"
    texto: str
    motivo: str | None
    chamadas_llm: int = 0
    tools: int = 0
    https: int = 0


@dataclass
class _OrcamentoTurno:
    chamadas_llm: int = 0
    tools: int = 0
    https: int = 0
    reconsulta_usada: bool = False


class _TerminalError(Exception):
    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


class _ReconsultaError(Exception):
    """Falha transitória: uma única tentativa adicional, com reautorização."""


class Executor:
    """Um turno do copiloto; construído por chamada, sem estado global."""

    def __init__(
        self,
        uow_factory: Callable[[], Any],
        credencial: ProvedorTokenCopilot,
        llm: LlmClient,
        criar_api: Callable[[], ClienteApi],
        autorizacao: Any,
        principal: Any,
        modelo: str,
        medidor_tokens: Callable[[str], int] | None,
        relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
        ferramentas_habilitadas: frozenset[str] = frozenset(CATALOGO),
        observador_tool: Callable[[Any], None] | None = None,
        metricas_llm: Any | None = None,
        metricas: Any | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._credencial = credencial
        self._llm = llm
        self._criar_api = criar_api
        self._autorizacao = autorizacao
        self._principal = principal
        self._modelo = modelo
        self._medidor_tokens = medidor_tokens
        self._relogio = relogio
        self._habilitadas = ferramentas_habilitadas
        self._observador_tool = observador_tool
        self._metricas_llm = metricas_llm if metricas_llm is not None else METRICAS_LLM
        self._metricas = metricas if metricas is not None else METRICAS

    async def executar(self, entrada: EntradaExecucao) -> ResultadoExecucao:
        try:
            resultado = await self._executar(entrada)
        except Exception:  # terminal: registra e não propaga
            logger.exception("falha interna do executor")
            self._metricas_llm.registrar_chamada(None, None, "crash")
            self._metricas.registrar_recusa("falha_interna")
            return ResultadoExecucao("incompleta", RESPOSTA_INDISPONIVEL, "falha_interna")
        logger.info(
            "turno %s estado=%s motivo=%s llm=%d tools=%d https=%d",
            entrada.correlation_id or "-",
            resultado.estado,
            resultado.motivo or "-",
            resultado.chamadas_llm,
            resultado.tools,
            resultado.https,
        )
        return resultado

    async def _executar(self, entrada: EntradaExecucao) -> ResultadoExecucao:
        agora = self._relogio()
        if (agora - entrada.recebido_em).total_seconds() > IDADE_MAXIMA_SEGUNDOS:
            self._metricas.registrar_recusa("vencida")
            return ResultadoExecucao("recusada", RESPOSTA_INDISPONIVEL, "vencida")
        sessao_ref = str(entrada.sessao.id)
        with self._uow_factory() as uow:
            vaga = uow.admissao.reservar_slot(
                sessao_ref,
                operadora=entrada.sessao.classe == ClasseContexto.OPERADORA,
                agora=agora,
            )
            uow.commit()
            if not vaga:
                self._metricas.registrar_recusa("sem_vaga")
                return ResultadoExecucao("recusada", RESPOSTA_INDISPONIVEL, "sem_vaga")
        try:
            return await self._turno(entrada, agora)
        finally:
            with self._uow_factory() as uow:
                uow.admissao.liberar_slot(sessao_ref)
                uow.commit()

    def _restante(self, primeiro_claim: datetime) -> float:
        return (
            primeiro_claim + timedelta(seconds=DEADLINE_SEGUNDOS) - self._relogio()
        ).total_seconds()

    def _texto_para_medir(
        self,
        sistema: str,
        historico: list[MensagemConversa],
        texto: str,
        ferramentas: list[dict[str, Any]],
    ) -> str:
        partes = [sistema, texto, json.dumps(ferramentas, default=str)]
        partes.extend(m.texto for m in historico)
        return "\n".join(partes)

    async def _turno(self, entrada: EntradaExecucao, primeiro_claim: datetime) -> ResultadoExecucao:
        orcamento = _OrcamentoTurno()
        if entrada.sessao.classe != ClasseContexto.OPERADORA:
            self._salvar_turno(entrada, RESPOSTA_FIXA_PRE_CADASTRO)
            return ResultadoExecucao("concluida", RESPOSTA_FIXA_PRE_CADASTRO, None)
        if self._medidor_tokens is None:
            self._metricas.registrar_recusa("inferencia_desabilitada")
            return ResultadoExecucao("recusada", RESPOSTA_INDISPONIVEL, "inferencia_desabilitada")
        try:
            contexto_resultado = self._autorizacao.consultar_contexto(self._principal)
            contexto = ContextoFerramentas(
                carteira_id=str(contexto_resultado.carteira_id),
                resolvedor_devedor=self._resolvedor(entrada.sessao.id),
                hoje=primeiro_claim.date(),
            )
        except Exception as exc:
            raise _TerminalError("contexto") from exc
        sistema = montar_sistema_operadora(contexto.hoje)
        ferramentas = montar_tools()
        historico = self._historico(entrada.sessao.id, primeiro_claim)
        if (
            self._medidor_tokens(
                self._texto_para_medir(sistema, historico, entrada.texto, ferramentas)
            )
            > MAX_TOKENS_ENTRADA
        ):
            self._metricas.registrar_recusa("contexto_excedido")
            return ResultadoExecucao("recusada", RESPOSTA_INDISPONIVEL, "contexto_excedido")
        mensagens = self._mensagens(sistema, historico, entrada.texto)
        apresentacoes: list[str] = []
        prosa_final: str | None = None
        continuar = True
        while orcamento.chamadas_llm < MAX_CHAMADAS_LLM and continuar:
            continuar = False
            restante = self._restante(primeiro_claim)
            if restante <= 0:
                return self._incompleta(entrada, apresentacoes, orcamento, "deadline")
            orcamento.chamadas_llm += 1
            try:
                async with asyncio.timeout(restante):
                    resposta = await self._llm.chat(
                        PedidoChat(mensagens=mensagens, ferramentas=tuple(ferramentas)),
                        timeout_segundos=min(TIMEOUT_LLM_SEGUNDOS, restante),
                    )
            except (LlmError, TimeoutError):
                return self._incompleta(entrada, apresentacoes, orcamento, "provedor")
            self._contabilizar(resposta)
            if not resposta.chamadas:
                prosa_final = resposta.texto
                break
            try:
                trechos, nomes = await self._fase_tools(
                    entrada, contexto, resposta, orcamento, primeiro_claim
                )
            except _TerminalError as terminal:
                return self._incompleta(entrada, apresentacoes, orcamento, terminal.motivo)
            apresentacoes.extend(trechos)
            # Só localizar habilita encadeamento (refs opacas alimentam o
            # saldo); demais ferramentas são terminais. Sem isso, cada
            # pergunta de 1 turno custaria uma chamada inútil.
            continuar = "localizar_devedor" in nomes and orcamento.tools < MAX_TOOLS_LOGICAS
            mensagens = (
                *mensagens,
                Mensagem(papel="user", conteudo="Resultados:\n" + "\n".join(trechos)),
            )
        texto = "\n".join(apresentacoes) if apresentacoes else prosa_final or RESPOSTA_INDISPONIVEL
        if len(texto) > MAX_MSG_CANAL:
            return self._incompleta(entrada, [], orcamento, "resposta_excedida")
        self._salvar_turno(entrada, texto)
        estado = "concluida" if (apresentacoes or prosa_final) else "incompleta"
        return ResultadoExecucao(
            estado,
            texto,
            None if estado == "concluida" else "sem_resposta",
            orcamento.chamadas_llm,
            orcamento.tools,
            orcamento.https,
        )

    async def _fase_tools(
        self,
        entrada: EntradaExecucao,
        contexto: ContextoFerramentas,
        resposta: RespostaChat,
        orcamento: _OrcamentoTurno,
        primeiro_claim: datetime,
    ) -> tuple[list[str], list[str]]:
        trechos: list[str] = []
        nomes: list[str] = []
        api = self._criar_api()
        try:
            for chamada in resposta.chamadas:
                if orcamento.tools >= MAX_TOOLS_LOGICAS:
                    raise _TerminalError("orcamento")
                try:
                    intencao = interpretar_chamada(chamada, contexto.hoje)
                except (FerramentaDesconhecidaError, ArgumentoInvalidoError):
                    raise _TerminalError("chamada_invalida") from None
                if intencao.nome not in self._habilitadas:
                    raise _TerminalError("ferramenta_negada") from None
                try:
                    self._autorizacao.exigir_permissao(
                        self._principal, CATALOGO[intencao.nome].permissao
                    )
                except Exception:
                    raise _TerminalError("ferramenta_negada") from None
                try:
                    inicio_chamada = time.monotonic()
                    dto = await self._chamar_com_reconsulta(
                        api,
                        contexto,
                        intencao.nome,
                        intencao.argumentos,
                        orcamento,
                        primeiro_claim,
                    )
                except (FerramentaDesconhecidaError, ArgumentoInvalidoError):
                    raise _TerminalError("chamada_invalida") from None
                except ApiAusenciaError:
                    orcamento.tools += 1
                    nomes.append(intencao.nome)
                    trechos.append(mensagem_ausencia(intencao.nome))
                    self._observar(
                        entrada,
                        chamada.id,
                        intencao.nome,
                        intencao.argumentos,
                        self._latencia_ms(inicio_chamada),
                        {"estado": "ausente"},
                    )
                    continue
                self._guardar_resposta(dto)
                orcamento.tools += 1
                nomes.append(intencao.nome)
                self._observar(
                    entrada,
                    chamada.id,
                    intencao.nome,
                    intencao.argumentos,
                    self._latencia_ms(inicio_chamada),
                    {"estado": "ok"},
                )
                try:
                    trechos.append(renderizar(intencao.nome, dto))
                except ValueError:
                    raise _TerminalError("resposta_invalida") from None
        finally:
            await api.close()
        return trechos, nomes

    async def _chamar_com_reconsulta(
        self,
        api: ProtocoloClienteApi,
        contexto: ContextoFerramentas,
        nome: str,
        argumentos: dict[str, str],
        orcamento: _OrcamentoTurno,
        primeiro_claim: datetime,
    ) -> dict[str, Any]:
        try:
            return await self._chamar(api, contexto, nome, argumentos, orcamento, primeiro_claim)
        except _ReconsultaError:
            if orcamento.reconsulta_usada:
                raise _TerminalError("provedor") from None
            orcamento.reconsulta_usada = True
            try:
                self._credencial.renovar()
            except CredencialError as exc:
                raise _TerminalError("revogada") from exc
            try:
                return await self._chamar(
                    api, contexto, nome, argumentos, orcamento, primeiro_claim
                )
            except _ReconsultaError:
                raise _TerminalError("provedor") from None

    async def _chamar(
        self,
        api: ProtocoloClienteApi,
        contexto: ContextoFerramentas,
        nome: str,
        argumentos: dict[str, str],
        orcamento: _OrcamentoTurno,
        primeiro_claim: datetime,
    ) -> dict[str, Any]:
        if orcamento.https >= MAX_HTTP_TOTAL:
            raise _TerminalError("orcamento")
        restante = self._restante(primeiro_claim)
        if restante <= 0:
            raise _TerminalError("deadline")
        orcamento.https += 1
        try:
            async with asyncio.timeout(restante):
                return await executar_ferramenta(
                    api,
                    contexto,
                    nome,
                    argumentos,
                    timeout_segundos=min(TIMEOUT_API_SEGUNDOS, restante),
                )
        except TimeoutError as exc:
            raise _ReconsultaError() from exc
        except ApiAusenciaError:
            raise
        except ApiAutorizacaoError as exc:
            raise _TerminalError("revogada") from exc
        except ApiError as exc:
            raise _ReconsultaError() from exc

    @staticmethod
    def _latencia_ms(inicio: float) -> int:
        return max(0, int((time.monotonic() - inicio) * 1000))

    def _observar(
        self,
        entrada: EntradaExecucao,
        call_id: str,
        ferramenta: str,
        argumentos: dict[str, str],
        latencia_ms: int,
        resultado: dict[str, str],
    ) -> None:
        if self._observador_tool is None:
            return
        from emprestimo.agent.conversa import ToolCallExec

        self._observador_tool(
            ToolCallExec(
                id=uuid.uuid4(),
                sessao_id=entrada.sessao.id,
                inbox_id=entrada.inbox_id,
                call_id=call_id,
                ferramenta=ferramenta,
                schema_versao=CATALOGO_VERSAO,
                parametros=dict(argumentos),
                resultado=dict(resultado),
                latencia_ms=latencia_ms,
                completa=True,
                criado_em=self._relogio(),
                correlation_id=entrada.correlation_id,
            )
        )

    def _guardar_resposta(self, dto: dict[str, Any]) -> None:
        try:
            tamanho = len(json.dumps(dto, default=str))
        except (TypeError, ValueError):
            raise _TerminalError("resposta_excedida") from None
        itens = dto.get("itens") or dto.get("items") or dto.get("pagamentos") or []
        if tamanho > MAX_RESPOSTA_BYTES or len(itens) > MAX_RESPOSTA_ITENS:
            raise _TerminalError("resposta_excedida") from None

    def _contabilizar(self, resposta: RespostaChat) -> None:
        uso = resposta.uso
        custo = None
        if uso is not None:
            custo = estimar_custo_usd(self._modelo, uso.prompt_tokens, uso.completion_tokens)
        self._metricas_llm.registrar_chamada(uso, custo, None)

    def _registrar_falha(self, motivo: str) -> None:
        if motivo in ("provedor", "deadline", "chamada_invalida", "ferramenta_negada"):
            self._metricas_llm.registrar_chamada(None, None, motivo)
        else:
            self._metricas.registrar_recusa(motivo)

    def _incompleta(
        self,
        entrada: EntradaExecucao,
        apresentacoes: list[str],
        orcamento: _OrcamentoTurno,
        motivo: str,
    ) -> ResultadoExecucao:
        self._registrar_falha(motivo)
        texto = "\n".join(apresentacoes) or RESPOSTA_INDISPONIVEL
        self._salvar_turno(entrada, texto)
        return ResultadoExecucao(
            "incompleta",
            texto,
            motivo,
            orcamento.chamadas_llm,
            orcamento.tools,
            orcamento.https,
        )

    def _resolvedor(self, sessao_id: uuid.UUID) -> Callable[[str], str | None]:
        def _resolver(ref: str) -> str | None:
            from emprestimo.agent.conversa import resolver_referencia

            with self._uow_factory() as uow:
                refs = uow.referencia_sessao.listar_por_sessao(sessao_id)
            devedor = resolver_referencia(refs, sessao_id, ref, self._relogio())
            return str(devedor) if devedor is not None else None

        return _resolver

    def _historico(self, sessao_id: uuid.UUID, agora: datetime) -> list[MensagemConversa]:
        with self._uow_factory() as uow:
            mensagens = uow.mensagem_conversa.listar_por_sessao(sessao_id)
        corte = agora - timedelta(minutes=JANELA_CONTEXTO_MINUTOS)
        recentes = [m for m in mensagens if m.criado_em >= corte]
        return recentes[-MENSAGENS_CONTEXTO:]

    def _mensagens(
        self, sistema: str, historico: list[MensagemConversa], texto: str
    ) -> tuple[Mensagem, ...]:
        montadas: list[Mensagem] = [Mensagem(papel="system", conteudo=sistema)]
        for mensagem in historico:
            papel = "user" if mensagem.papel == PapelMensagem.USUARIO else "assistant"
            montadas.append(Mensagem(papel=papel, conteudo=mensagem.texto))
        montadas.append(Mensagem(papel="user", conteudo=texto))
        return tuple(montadas)

    def _salvar_turno(self, entrada: EntradaExecucao, texto: str) -> None:
        try:
            with self._uow_factory() as uow:
                existentes = uow.mensagem_conversa.listar_por_sessao(entrada.sessao.id)
                base = max([m.indice for m in existentes], default=-1) + 1
                agora = self._relogio()
                uow.mensagem_conversa.adicionar(
                    MensagemConversa(
                        id=uuid.uuid4(),
                        sessao_id=entrada.sessao.id,
                        inbox_id=entrada.inbox_id,
                        indice=base,
                        papel=PapelMensagem.USUARIO,
                        texto=entrada.texto,
                        criado_em=agora,
                    )
                )
                uow.mensagem_conversa.adicionar(
                    MensagemConversa(
                        id=uuid.uuid4(),
                        sessao_id=entrada.sessao.id,
                        inbox_id=entrada.inbox_id,
                        indice=base + 1,
                        papel=PapelMensagem.ASSISTENTE,
                        texto=texto,
                        criado_em=agora,
                    )
                )
                uow.commit()
        except Exception:
            # Sem traceback de propósito: tracebacks de banco ecoam os
            # parâmetros do INSERT (texto com PII) para o log.
            logger.error("turno sem persistencia de memoria")


__all__ = [
    "DEADLINE_SEGUNDOS",
    "MAX_CHAMADAS_LLM",
    "MAX_HTTP_TOTAL",
    "MAX_TOOLS_LOGICAS",
    "EntradaExecucao",
    "Executor",
    "RESPOSTA_INDISPONIVEL",
    "ResultadoExecucao",
]
