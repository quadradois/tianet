"""Suites de domínio da Operacao Diaria (IMP-171)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.operacao_diaria import (
    AcaoCobranca,
    CanalComunicacao,
    CobrancaCaso,
    CompromissoAgenda,
    EstadoCobranca,
    HistoricoComunicacao,
    Lembrete,
    RegistroComunicacao,
    TipoAcaoCobranca,
)
from emprestimo.domain.credit.promessa import (
    ApropriacaoPagamento,
    PromessaPagamento,
    PromessaPagamentoState,
)

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CARTEIRA_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEVEDOR_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EMPRESTIMO_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
USUARIO_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
Lembrete_ID = uuid.UUID("77777777-7777-7777-7777-777777777777")


def test_caso_sincroniza_reabre_e_encerra_pendencia_financeira() -> None:
    estado_inicial: EstadoCobranca = EstadoCobranca.ENCERRADO
    caso = CobrancaCaso(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        emprestimo_id=EMPRESTIMO_ID,
        titulo="Acerto pendente",
        origem="varredura_diaria",
        estado=estado_inicial,
    )
    instante = datetime.now(UTC)

    caso.sincronizar_pendencia(
        total_pendente=Decimal("123.45"),
        emprestimo_id=EMPRESTIMO_ID,
        agora=instante,
    )

    estado_reaberto: EstadoCobranca = caso.estado
    assert estado_reaberto is EstadoCobranca.PENDENTE
    assert caso.total_pendente == Decimal("123.45")
    assert caso.atualizado_em == instante

    caso.encerrar_por_acerto(agora=instante + timedelta(minutes=1))

    assert caso.estado is EstadoCobranca.ENCERRADO
    assert caso.total_pendente == Decimal("0.00")


def test_acoes_cobranca_validam_contratos_basicos() -> None:
    acao = AcaoCobranca(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        cobranca_caso_id=uuid.UUID("88888888-8888-8888-8888-888888888888"),
        emprestimo_id=EMPRESTIMO_ID,
        criado_por_usuario_id=USUARIO_ID,
        tipo=TipoAcaoCobranca.TELEFONE,
        resultado="ligacao realizada",
        devedor_id=DEVEDOR_ID,
    )

    assert acao.tipo.value == "telefone"
    assert acao.estado.value == "ativo"
    assert acao.resultado == "ligacao realizada"
    assert acao.id is not None


def test_acoes_sem_resultado_falha() -> None:
    with pytest.raises(ViolacaoInvarianteError) as exc:
        AcaoCobranca(
            tenant_id=TENANT_ID,
            carteira_id=CARTEIRA_ID,
            cobranca_caso_id=uuid.UUID("88888888-8888-8888-8888-888888888888"),
            emprestimo_id=EMPRESTIMO_ID,
            criado_por_usuario_id=USUARIO_ID,
            tipo=TipoAcaoCobranca.TELEFONE,
            resultado=" ",
        )

    assert exc.value.codigo == "EPIC-007"


def test_compromisso_pode_reagendar_e_concluir() -> None:
    compromisso = CompromissoAgenda(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        usuario_solicitante_id=USUARIO_ID,
        titulo="ligacao de retorno",
        previsto_para=datetime.now(UTC) + timedelta(days=1),
    )

    novo_horario = datetime.now(UTC) + timedelta(days=2)
    compromisso.reagendar(novo_horario=novo_horario)
    assert compromisso.estado.value == "reagendado"
    assert compromisso.previsto_para == novo_horario

    compromisso.concluir()
    assert compromisso.estado.value == "concluido"


def test_conclusao_de_cancelado_e_remarcacao_invalida() -> None:
    compromisso = CompromissoAgenda(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        usuario_solicitante_id=USUARIO_ID,
        titulo="visita",
        previsto_para=datetime.now(UTC) + timedelta(days=1),
    )

    compromisso.cancelar()
    assert compromisso.estado.value == "cancelado"

    with pytest.raises(ViolacaoInvarianteError) as exc:
        compromisso.reagendar(novo_horario=datetime.now(UTC) + timedelta(days=2))

    assert exc.value.codigo == "EPIC-007"


def test_lembrete_e_historico_de_comunicacao() -> None:
    lembrete = Lembrete(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        compromisso_id=uuid.uuid4(),
        horario=datetime.now(UTC) + timedelta(hours=2),
        enviado_por_usuario_id=USUARIO_ID,
        mensagem="enviar comprovante",
        id=Lembrete_ID,
    )
    lembrete.enviar()
    assert lembrete.estado.value == "enviado"
    registro = RegistroComunicacao(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        responsavel_id=USUARIO_ID,
        canal=CanalComunicacao.TELEFONE,
        ocorrido_em=datetime.now(UTC),
        resumo="telefones em aberto",
        resultado="sem resposta",
        devedor_id=DEVEDOR_ID,
        emprestimo_id=EMPRESTIMO_ID,
    )
    historico = HistoricoComunicacao(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        emprestimo_id=EMPRESTIMO_ID,
        registros=(),
    )
    historico.adicionar(registro)
    assert len(historico.registros) == 1
    assert historico.registros[0].resumo == "telefones em aberto"


def test_whatsapp_e_canal_operacional_valido() -> None:
    assert CanalComunicacao.WHATSAPP.value == "whatsapp"


def test_promessa_cria_em_pendente_e_transiciona_para_pagamento_informado() -> None:
    promessa = PromessaPagamento.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        emprestimo_id=EMPRESTIMO_ID,
        criado_por_usuario_id=USUARIO_ID,
        valor_declarado=Decimal("100.00"),
        data_promessa=(datetime.now(UTC).date() + timedelta(days=3)),
    )
    assert promessa.estado is PromessaPagamentoState.PENDENTE

    promessa.informar_pagamento()
    assert _estado_promessa(promessa) is PromessaPagamentoState.PAGAMENTO_INFORMADO


def test_promessa_cumpre_quando_apropia_valor_adequado() -> None:
    promessa = PromessaPagamento.criar(
        tenant_id=TENANT_ID,
        carteira_id=CARTEIRA_ID,
        devedor_id=DEVEDOR_ID,
        emprestimo_id=EMPRESTIMO_ID,
        criado_por_usuario_id=USUARIO_ID,
        valor_declarado=Decimal("100.00"),
        data_promessa=(datetime.now(UTC).date() + timedelta(days=3)),
    )
    apropriacao = ApropriacaoPagamento(
        promessa_id=promessa.id,
        pagamento_id=uuid.uuid4(),
        valor=Decimal("60.00"),
        realizado_em=datetime.now(UTC),
    )
    promessa.apropriar_pagamento(apropriacao)
    assert promessa.valor_adequado == Decimal("60.00")
    assert promessa.estado is PromessaPagamentoState.PENDENTE

    promessa.apropriar_pagamento(
        ApropriacaoPagamento(
            promessa_id=promessa.id,
            pagamento_id=uuid.uuid4(),
            valor=Decimal("40.00"),
            realizado_em=datetime.now(UTC),
        )
    )
    assert promessa.valor_adequado == Decimal("100.00")
    assert _estado_promessa(promessa) is PromessaPagamentoState.CUMPRIDA


def _estado_promessa(promessa: PromessaPagamento) -> PromessaPagamentoState:
    return promessa.estado
