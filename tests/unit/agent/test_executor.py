"""Executor com deadline e orçamento (IMP-356-F slice 3).

Fakes totais (relógio, slots, LLM, API, auth, métricas): cada limite
isolado — idade, vaga, deadline, orçamentos, reconsulta única, 404,
resposta excedida, ferramenta negada/desabilitada, crash terminal —
mais o caminho feliz de 1 e 2 turnos e a liberação do slot.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from emprestimo.agent.api_client import ApiAutorizacaoError, ApiError
from emprestimo.agent.catalogo import CATALOGO
from emprestimo.agent.conversa import ClasseContexto, SessaoConversa
from emprestimo.agent.executor import (
    RESPOSTA_INDISPONIVEL,
    EntradaExecucao,
    Executor,
    ResultadoExecucao,
)
from emprestimo.agent.llm_client import ChamadaFerramenta, RespostaChat, Uso
from emprestimo.agent.metricas import MetricasIngress, MetricasLlm

T0 = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
CARTEIRA = uuid.uuid4()


class Relogio:
    def __init__(self) -> None:
        self.agora = T0

    def __call__(self) -> datetime:
        return self.agora


class Slots:
    def __init__(self, vaga: bool = True) -> None:
        self.vaga = vaga
        self.donos: set[str] = set()
        self.reservas = 0

    def reservar_slot(self, sessao_ref: str, *, operadora: bool, agora: object) -> bool:
        del operadora, agora
        self.reservas += 1
        if not self.vaga:
            return False
        self.donos.add(sessao_ref)
        return True

    def liberar_slot(self, sessao_ref: str) -> None:
        self.donos.discard(sessao_ref)

    def liberar_expiradas(self, agora: object) -> int:
        del agora
        return 0


class Store:
    def __init__(self) -> None:
        self.mensagens: list[Any] = []
        self.refs: list[Any] = []

    # mensagens
    def adicionar(self, mensagem: Any) -> None:
        self.mensagens.append(mensagem)

    def listar_por_sessao(self, sessao_id: object) -> list[Any]:
        return [m for m in self.mensagens if m.sessao_id == sessao_id]

    # refs
    def listar_refs(self, sessao_id: object) -> list[Any]:
        return [r for r in self.refs if r.sessao_id == sessao_id]


class UowFalso:
    def __init__(self, slots: Slots, store: Store) -> None:
        self.admissao = slots
        self.mensagem_conversa = store
        self.referencia_sessao = _Refs(store)
        self.commits = 0

    def __enter__(self) -> UowFalso:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


class _Refs:
    def __init__(self, store: Store) -> None:
        self._store = store

    def listar_por_sessao(self, sessao_id: object) -> list[Any]:
        return self._store.listar_refs(sessao_id)


class LlmFalso:
    def __init__(self, roteiro: list[Any]) -> None:
        self.roteiro = list(roteiro)
        self.pedidos: list[Any] = []
        self.timeouts: list[Any] = []

    async def chat(self, pedido: Any, timeout_segundos: Any = None) -> Any:
        self.pedidos.append(pedido)
        self.timeouts.append(timeout_segundos)
        item = self.roteiro.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class ApiFalsa:
    def __init__(self, roteiro: list[Any]) -> None:
        # Sem cópia de propósito: o roteiro é consumido em ordem por todos
        # os clientes do turno, como chamadas reais à API.
        self.roteiro = roteiro
        self.chamadas: list[Any] = []
        self.fechada = False

    async def get(self, caminho: str, params: Any = None, timeout_segundos: Any = None) -> Any:
        self.chamadas.append((caminho, dict(params or {}), timeout_segundos))
        item = self.roteiro.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def close(self) -> None:
        self.fechada = True


class AuthFalsa:
    def __init__(self, negar: set[str] | None = None, quebrar_contexto: bool = False) -> None:
        self.negar = negar or set()
        self.quebrar_contexto = quebrar_contexto

    def consultar_contexto(self, principal: Any) -> Any:
        del principal
        if self.quebrar_contexto:
            raise RuntimeError("banco fora")
        return SimpleNamespace(carteira_id=CARTEIRA)

    def exigir_permissao(self, principal: Any, operacao: str) -> None:
        del principal
        if operacao in self.negar:
            from emprestimo.application.errors import AcessoNegadoError

            raise AcessoNegadoError(operacao)


class CredencialFalsa:
    def __init__(self) -> None:
        self.tokens = 0
        self.renovacoes = 0

    def token(self) -> str:
        self.tokens += 1
        return "tok"

    def renovar(self) -> None:
        self.renovacoes += 1


def _resposta(
    texto: str | None = None,
    chamadas: list[ChamadaFerramenta] | None = None,
    uso: Uso | None = Uso(10, 5, 15),
) -> RespostaChat:
    return RespostaChat(texto=texto, chamadas=tuple(chamadas or []), uso=uso)


def _chamada(nome: str, argumentos: str, call_id: str = "call_1") -> ChamadaFerramenta:
    return ChamadaFerramenta(id=call_id, nome=nome, argumentos=argumentos)


def _sessao(classe: ClasseContexto = ClasseContexto.OPERADORA) -> SessaoConversa:
    return SessaoConversa(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        instancia_ref="inst",
        classe=classe,
        remetente_normalizado="5511999999999",
    )


def _montar(
    *,
    roteiro_llm: list[Any],
    roteiro_api: list[Any] | None = None,
    relogio: Relogio | None = None,
    slots: Slots | None = None,
    auth: AuthFalsa | None = None,
    medidor: Any = len,
    habilitadas: frozenset[str] | None = None,
    observadas: list[Any] | None = None,
) -> tuple[
    Executor,
    Relogio,
    Slots,
    LlmFalso,
    list[ApiFalsa],
    CredencialFalsa,
    Store,
    MetricasLlm,
    MetricasIngress,
]:
    relogio = relogio or Relogio()
    slots = slots or Slots()
    store = Store()
    llm = LlmFalso(roteiro_llm)
    apis: list[ApiFalsa] = []
    roteiro_api_compartilhado = list(roteiro_api or [])

    def _criar_api() -> ApiFalsa:
        api = ApiFalsa(roteiro_api_compartilhado)
        apis.append(api)
        return api

    credencial = CredencialFalsa()
    metricas_llm = MetricasLlm()
    metricas = MetricasIngress()
    executor = Executor(
        uow_factory=lambda: UowFalso(slots, store),
        credencial=credencial,  # type: ignore[arg-type]
        llm=llm,  # type: ignore[arg-type]
        criar_api=_criar_api,  # type: ignore[arg-type]
        autorizacao=auth or AuthFalsa(),
        principal=SimpleNamespace(),
        modelo="gpt-4o-mini",
        medidor_tokens=medidor,
        relogio=relogio,
        ferramentas_habilitadas=habilitadas if habilitadas is not None else frozenset(CATALOGO),
        observador_tool=(observadas.append if observadas is not None else None),
        metricas_llm=metricas_llm,
        metricas=metricas,
    )
    return executor, relogio, slots, llm, apis, credencial, store, metricas_llm, metricas


def _entrada(sessao: SessaoConversa, texto: str = "como está a carteira?") -> EntradaExecucao:
    return EntradaExecucao(inbox_id=uuid.uuid4(), sessao=sessao, texto=texto, recebido_em=T0)


def _executar(executor: Executor, entrada: EntradaExecucao) -> ResultadoExecucao:
    return asyncio.run(executor.executar(entrada))


ACERTOS_DTO = {
    "tenant_id": "t",
    "carteira_id": "c",
    "data_referencia": "2026-09-15",
    "itens": [],
    "total": 0,
}


def test_pre_cadastro_resposta_fixa_sem_llm() -> None:
    executor, _, slots, llm, _, _, store, _, _ = _montar(roteiro_llm=[])
    sessao = _sessao(ClasseContexto.PRE_CADASTRO)
    resultado = _executar(executor, _entrada(sessao))
    assert resultado.estado == "concluida" and "TiaNet" in resultado.texto
    assert llm.pedidos == [] and resultado.chamadas_llm == 0
    assert str(sessao.id) not in slots.donos
    assert len(store.mensagens) == 2


def test_operadora_uma_tool_conclui_e_libera_slot() -> None:
    observadas: list[Any] = []
    executor, _, slots, llm, apis, _, store, _, _ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[ACERTOS_DTO],
        observadas=observadas,
    )
    sessao = _sessao()
    resultado = _executar(executor, _entrada(sessao))
    assert resultado.estado == "concluida"
    assert (resultado.chamadas_llm, resultado.tools, resultado.https) == (1, 1, 1)
    assert "pendente" in resultado.texto
    assert str(sessao.id) not in slots.donos
    assert apis[0].fechada and len(store.mensagens) == 2
    assert len(observadas) == 1 and observadas[0].ferramenta == "consultar_acertos"
    assert llm.timeouts[0] == 15.0
    assert apis[0].chamadas[0][2] == 5.0


def test_dois_turnos_localizar_saldo() -> None:
    from datetime import timedelta

    from emprestimo.agent.conversa import ReferenciaSessao

    executor, _, _, _, apis, _, store, _, _ = _montar(
        roteiro_llm=[
            _resposta(chamadas=[_chamada("localizar_devedor", '{"nome": "ana"}')]),
            _resposta(
                chamadas=[
                    _chamada(
                        "consultar_saldo_devedor",
                        '{"devedor_ref": "ref-9"}',
                        "call_2",
                    )
                ]
            ),
        ],
        roteiro_api=[
            {"items": [], "total": 0, "page": 1, "size": 20, "pages": 0},
            {
                "devedor_id": "d",
                "tenant_id": "t",
                "data_referencia": "2026-09-15",
                "principal": "0.00",
                "juros": "0.00",
                "encargos": "0.00",
                "total": "0.00",
                "emprestimos_considerados": 0,
                "itens": [],
            },
        ],
    )
    sessao = _sessao()
    store.refs.append(
        ReferenciaSessao(
            id=uuid.uuid4(),
            sessao_id=sessao.id,
            ref="ref-9",
            devedor_id=uuid.uuid4(),
            expira_em=T0 + timedelta(minutes=5),
            criado_em=T0,
        )
    )
    resultado = _executar(executor, _entrada(sessao))
    assert resultado.estado == "concluida"
    assert (resultado.chamadas_llm, resultado.tools, resultado.https) == (2, 2, 2)
    assert apis[0].fechada


def test_terceira_tool_recusada_em_codigo() -> None:
    executor, *_ = _montar(
        roteiro_llm=[
            _resposta(
                chamadas=[
                    _chamada("consultar_acertos", "{}", "c1"),
                    _chamada("consultar_acertos", "{}", "c2"),
                    _chamada("consultar_acertos", "{}", "c3"),
                ]
            )
        ],
        roteiro_api=[ACERTOS_DTO, ACERTOS_DTO],
    )
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "incompleta" and resultado.motivo == "orcamento"
    assert resultado.tools == 2


def test_entrada_vencida_nao_consulta_nem_reserva() -> None:
    slots = Slots()
    executor, *_ = _montar(roteiro_llm=[], slots=slots)
    entrada = EntradaExecucao(
        inbox_id=uuid.uuid4(),
        sessao=_sessao(),
        texto="oi",
        recebido_em=T0 - timedelta(seconds=121),
    )
    resultado = _executar(executor, entrada)
    assert resultado.estado == "recusada" and resultado.motivo == "vencida"
    assert slots.reservas == 0


def test_sem_vaga_recusa() -> None:
    executor, *_ = _montar(roteiro_llm=[], slots=Slots(vaga=False))
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "recusada" and resultado.motivo == "sem_vaga"


def test_sem_medidor_inferencia_desabilitada() -> None:
    executor, _, _, llm, _, _, _, _, _ = _montar(roteiro_llm=[], medidor=None)
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "recusada"
    assert resultado.motivo == "inferencia_desabilitada"
    assert llm.pedidos == []


def test_contexto_excedido_recusa_antes_da_rede() -> None:
    executor, _, _, llm, _, _, _, _, _ = _montar(roteiro_llm=[], medidor=lambda s: 8001)
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "recusada" and resultado.motivo == "contexto_excedido"
    assert llm.pedidos == []


def test_deadline_estourado_nao_chama_provedor() -> None:
    # O claim zera o relógio por desenho; o deadline só estoura no meio do
    # turno: primeira leitura T0 (claim), depois T0+46s.
    tempos = [T0, T0 + timedelta(seconds=46)]
    chamadas = {"n": 0}

    def _avancar() -> datetime:
        chamadas["n"] += 1
        return tempos[0] if chamadas["n"] == 1 else tempos[1]

    executor, _, _, llm, _, _, _, _, _ = _montar(roteiro_llm=[])
    executor._relogio = _avancar
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "incompleta" and resultado.motivo == "deadline"
    assert llm.pedidos == []


def test_chamada_invalida_encerra() -> None:
    executor, *_ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("prever_lucro", "{}")])],
        roteiro_api=[],
    )
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "incompleta" and resultado.motivo == "chamada_invalida"


def test_ferramenta_negada_ou_desabilitada_encerra() -> None:
    executor, *_ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[],
        auth=AuthFalsa(negar={"relatorios.operacionais.ler"}),
    )
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "incompleta" and resultado.motivo == "ferramenta_negada"
    executor2, *_ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[],
        habilitadas=frozenset({"localizar_devedor"}),
    )
    resultado2 = _executar(executor2, _entrada(_sessao()))
    assert resultado2.estado == "incompleta"
    assert resultado2.motivo == "ferramenta_negada"


def test_reconsulta_unica_recupera_e_segunda_falha_encerra() -> None:
    executor, *_ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[ApiError("falha"), ACERTOS_DTO],
    )
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "concluida" and resultado.https == 2
    executor2, _, _, _, _, credencial, _, _, _ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[ApiError("falha"), ApiError("falha")],
    )
    resultado2 = _executar(executor2, _entrada(_sessao()))
    assert resultado2.estado == "incompleta" and resultado2.motivo == "provedor"
    assert credencial.renovacoes == 1


def test_ausencia_vira_texto_neutro_concluido() -> None:
    from emprestimo.agent.api_client import ApiAusenciaError

    executor, *_ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[ApiAusenciaError("ausente")],
    )
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "concluida"
    assert resultado.texto == "Acertos indisponíveis no momento."


def test_resposta_excedida_recusa() -> None:
    grande = dict(ACERTOS_DTO)
    grande["itens"] = [{"x": "y"} for _ in range(101)]
    executor, *_ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[grande],
    )
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "incompleta"
    assert resultado.motivo == "resposta_excedida"


def test_401_terminal_como_revogada() -> None:
    executor, _, _, _, _, credencial, _, _, _ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[ApiAutorizacaoError("negado")],
    )
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "incompleta" and resultado.motivo == "revogada"
    assert credencial.renovacoes == 0


def test_crash_nao_propaga_e_terminal() -> None:
    executor, *_ = _montar(roteiro_llm=[RuntimeError("bug inesperado")])
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "incompleta"
    assert resultado.texto == RESPOSTA_INDISPONIVEL
    assert resultado.motivo == "falha_interna"


def test_contexto_quebrado_encerra_sem_propagar() -> None:
    executor, *_ = _montar(roteiro_llm=[], auth=AuthFalsa(quebrar_contexto=True))
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "incompleta"
    assert resultado.motivo == "contexto"


def test_metrica_registra_chamada_e_recusa() -> None:
    executor, _, _, _, _, _, _, metricas_llm, _ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[ACERTOS_DTO],
    )
    _executar(executor, _entrada(_sessao()))
    retrato = metricas_llm.retrato()
    assert retrato["chamadas"] == 1 and retrato["tokens_entrada"] == 10
    executor2, _, _, _, _, _, _, _, metricas2 = _montar(roteiro_llm=[], slots=Slots(vaga=False))
    _executar(executor2, _entrada(_sessao()))
    assert metricas2.retrato()["recusas_por_motivo"] == {"sem_vaga": 1}


def test_enviador_chamado_so_em_concluida() -> None:
    enviadas: list[tuple[str, object]] = []

    def _enviador(entrada: object, texto: str, contexto: object) -> None:
        enviadas.append((texto, contexto))

    executor, *_ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[ACERTOS_DTO],
    )
    executor._enviador = _enviador
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "concluida"
    assert len(enviadas) == 1 and "pendente" in enviadas[0][0]

    executor2, *_ = _montar(roteiro_llm=[], slots=Slots(vaga=False))
    executor2._enviador = _enviador
    resultado2 = _executar(executor2, _entrada(_sessao()))
    assert resultado2.estado == "recusada"
    assert len(enviadas) == 1


def test_enviador_com_falha_nao_quebra_turno() -> None:
    def _quebrar(entrada: object, texto: str, contexto: object) -> None:
        raise RuntimeError("fio cortado")

    executor, *_ = _montar(
        roteiro_llm=[_resposta(chamadas=[_chamada("consultar_acertos", "{}")])],
        roteiro_api=[ACERTOS_DTO],
    )
    executor._enviador = _quebrar
    resultado = _executar(executor, _entrada(_sessao()))
    assert resultado.estado == "concluida"
