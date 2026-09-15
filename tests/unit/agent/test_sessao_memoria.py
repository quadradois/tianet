"""Memória da sessão e resolvedor de refs (IMP-356-F slice 1) — puro.

Sem banco, sem rede: ciclo de vida do domínio e as quatro recusas do
resolvedor (outra sessão, expirada, revogada, ausente). Relógio sempre
injetado.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from emprestimo.agent.conversa import (
    ClasseContexto,
    MensagemConversa,
    PapelMensagem,
    ReferenciaSessao,
    SessaoConversa,
    ToolCallExec,
    resolver_referencia,
)

T0 = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)
SESSAO = uuid.uuid4()
OUTRA_SESSAO = uuid.uuid4()
DEVEDOR = uuid.uuid4()


def _ref(**rabes: object) -> ReferenciaSessao:
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "sessao_id": SESSAO,
        "ref": "ref-1",
        "devedor_id": DEVEDOR,
        "expira_em": T0 + timedelta(minutes=5),
        "revogada_em": None,
        "criado_em": T0,
    }
    base.update(rabes)
    return ReferenciaSessao(**base)  # type: ignore[arg-type]


def test_resolve_quando_valida() -> None:
    assert resolver_referencia([_ref()], SESSAO, "ref-1", T0) == DEVEDOR


def test_recusa_outra_sessao_expirada_revogada_e_ausente() -> None:
    valida = _ref()
    assert resolver_referencia([valida], OUTRA_SESSAO, "ref-1", T0) is None
    assert resolver_referencia([_ref(expira_em=T0)], SESSAO, "ref-1", T0) is None
    assert resolver_referencia([_ref(revogada_em=T0)], SESSAO, "ref-1", T0) is None
    assert resolver_referencia([valida], SESSAO, "outra-ref", T0) is None
    assert resolver_referencia([], SESSAO, "ref-1", T0) is None


def test_sessao_nasce_sem_referencia_pendente() -> None:
    sessao = SessaoConversa(
        id=SESSAO,
        tenant_id=uuid.uuid4(),
        instancia_ref="inst",
        classe=ClasseContexto.OPERADORA,
        remetente_normalizado="5511999999999",
    )
    assert sessao.referencia_pendente is None
    assert sessao.expira_em is None


def test_mensagem_e_tool_call_carregam_identidade_minima() -> None:
    mensagem = MensagemConversa(
        id=uuid.uuid4(),
        sessao_id=SESSAO,
        inbox_id=None,
        indice=0,
        papel=PapelMensagem.USUARIO,
        texto="quanto devo?",
        criado_em=T0,
    )
    assert mensagem.indice == 0
    tool = ToolCallExec(
        id=uuid.uuid4(),
        sessao_id=SESSAO,
        inbox_id=uuid.uuid4(),
        call_id="call_1",
        ferramenta="consultar_acertos",
        schema_versao="consulta_operadora_v1",
        parametros={},
        resultado={"status": "ok", "itens": "0"},
        latencia_ms=120,
        completa=True,
        criado_em=T0,
    )
    assert tool.completa is True
    assert "total" not in tool.resultado
