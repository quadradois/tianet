import uuid
from datetime import UTC, datetime, timedelta

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.notifications import (
    EstadoPreferenciaNotificacao,
    EstadoSolicitacaoNotificacao,
    PreferenciaNotificacao,
    ResultadoCanal,
    ResultadoEnvio,
    SolicitacaoNotificacao,
    TemplateNotificacao,
)


def test_preferencia_default_deny_e_opt_in_explicito() -> None:
    preferencia = PreferenciaNotificacao(
        tenant_id=uuid.uuid4(),
        carteira_id=uuid.uuid4(),
        contato_id=uuid.uuid4(),
        estado=EstadoPreferenciaNotificacao.OPT_OUT,
        evidencia="formulario-v1",
        origem="cadastro",
        ator_id=uuid.uuid4(),
        registrada_em=datetime.now(UTC),
    )
    assert not preferencia.permite_envio


def test_template_exige_aprovacao_antes_da_ativacao() -> None:
    template = TemplateNotificacao(
        tenant_id=uuid.uuid4(),
        codigo="lembrete_operacional_v1",
        versao=1,
        assunto="Lembrete",
        corpo="Atendimento em {data_hora} por {canal_atendimento}",
        parametros_permitidos=("data_hora", "canal_atendimento"),
        criado_por_usuario_id=uuid.uuid4(),
    )
    with pytest.raises(ViolacaoInvarianteError, match="aprovado"):
        template.ativar(agora=datetime.now(UTC))
    template.aprovar(usuario_id=uuid.uuid4(), motivo="template inicial", agora=datetime.now(UTC))
    template.ativar(agora=datetime.now(UTC))
    assert len(template.hash_conteudo) == 64


def test_template_rejeita_placeholder_fora_da_allowlist() -> None:
    with pytest.raises(ViolacaoInvarianteError, match="allowlist"):
        TemplateNotificacao(
            tenant_id=uuid.uuid4(),
            codigo="lembrete_operacional_v1",
            versao=1,
            assunto="Ola {cliente}",
            corpo="Atendimento em {data_hora} por {canal_atendimento}",
            parametros_permitidos=("data_hora", "canal_atendimento"),
            criado_por_usuario_id=uuid.uuid4(),
        )


def test_resultado_desconhecido_exige_conciliacao_conclusiva() -> None:
    ids = [uuid.uuid4() for _ in range(7)]
    solicitacao = SolicitacaoNotificacao.preparar(
        tenant_id=ids[0],
        carteira_id=ids[1],
        lembrete_id=ids[2],
        job_id=ids[3],
        tentativa_job_id=ids[4],
        contato_id=ids[5],
        template_id=ids[6],
        chave_idempotente="notification-key-1",
        payload={"data_hora": "2026-08-11T10:00:00Z"},
    )
    solicitacao.registrar_resultado(ResultadoEnvio(ResultadoCanal.DESCONHECIDO))
    assert solicitacao.estado is EstadoSolicitacaoNotificacao.RESULTADO_DESCONHECIDO
    with pytest.raises(ViolacaoInvarianteError, match="evidencia conclusiva"):
        solicitacao.conciliar(
            ResultadoEnvio(ResultadoCanal.DESCONHECIDO),
            idempotency_key="reconcile-1",
        )


def test_retry_temporario_reabre_mesma_solicitacao_na_janela() -> None:
    agora = datetime.now(UTC)
    ids = [uuid.uuid4() for _ in range(7)]
    solicitacao = SolicitacaoNotificacao.preparar(
        tenant_id=ids[0],
        carteira_id=ids[1],
        lembrete_id=ids[2],
        job_id=ids[3],
        tentativa_job_id=ids[4],
        contato_id=ids[5],
        template_id=ids[6],
        chave_idempotente="notification/retry-key",
        payload={"data_hora": "2026-08-11T10:00:00Z"},
    )
    solicitacao.preparada_em = agora
    solicitacao.registrar_resultado(ResultadoEnvio(ResultadoCanal.FALHA_TEMPORARIA))
    nova_tentativa = uuid.uuid4()

    solicitacao.preparar_retry(
        tentativa_job_id=nova_tentativa,
        agora=agora + timedelta(minutes=1),
    )
    solicitacao.registrar_resultado(
        ResultadoEnvio(
            ResultadoCanal.ACEITA,
            provider_message_id="msg-retry",
            chave_idempotente=solicitacao.chave_idempotente,
        )
    )

    assert solicitacao.estado is EstadoSolicitacaoNotificacao.ACEITA
    assert solicitacao.tentativa_job_id == nova_tentativa


def test_conciliacao_exige_identidade_e_replay_identico_e_idempotente() -> None:
    ids = [uuid.uuid4() for _ in range(7)]
    solicitacao = SolicitacaoNotificacao.preparar(
        tenant_id=ids[0],
        carteira_id=ids[1],
        lembrete_id=ids[2],
        job_id=ids[3],
        tentativa_job_id=ids[4],
        contato_id=ids[5],
        template_id=ids[6],
        chave_idempotente="notification/evidence-key",
        payload={"data_hora": "2026-08-11T10:00:00Z"},
    )
    solicitacao.registrar_resultado(ResultadoEnvio(ResultadoCanal.DESCONHECIDO))
    divergente = ResultadoEnvio(
        ResultadoCanal.ACEITA,
        provider_message_id="msg-1",
        chave_idempotente="notification/other",
    )
    with pytest.raises(ViolacaoInvarianteError, match="nao pertence"):
        solicitacao.conciliar(divergente, idempotency_key="reconcile-1")

    evidencia = ResultadoEnvio(
        ResultadoCanal.ACEITA,
        provider_message_id="msg-1",
        chave_idempotente=solicitacao.chave_idempotente,
    )
    assert solicitacao.conciliar(evidencia, idempotency_key="reconcile-1")
    assert not solicitacao.conciliar(evidencia, idempotency_key="reconcile-1")
