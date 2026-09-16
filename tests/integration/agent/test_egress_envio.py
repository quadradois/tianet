"""Runner de egress com canal falso contador (IMP-356-E slice 3).

Estados, retry único temporário, replay sem nova chamada, conflito
terminal, desconhecido sem reenvio, deadline recusado e exceção
pós-transmissão como desconhecida — tudo contra repositório real.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from tests.factories import TenantFactory

from emprestimo.agent.egress import (
    ConflitoEgressError,
    ContextoEnvio,
    EstadoEgress,
    enviar_texto,
)
from emprestimo.domain.credit.notifications import ResultadoCanal, ResultadoEnvio
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.infrastructure.db.orm import InboxConversaORM, SessaoConversaORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyEgressRepository,
    SqlAlchemyTenantRepository,
)

T0 = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


class CanalFalso:
    def __init__(self, roteiro: list[object]) -> None:
        self.roteiro = list(roteiro)
        self.chamadas = 0

    def enviar(
        self, *, destinatario: str, assunto: str, corpo: str, chave_idempotente: str
    ) -> ResultadoEnvio:
        self.chamadas += 1
        item = self.roteiro.pop(0)
        if isinstance(item, Exception):
            raise item
        assert isinstance(item, ResultadoEnvio)
        return item

    def consultar_status(self, provider_message_id: str) -> ResultadoEnvio:
        raise NotImplementedError


def _aceito(id: str = "WA-1") -> ResultadoEnvio:
    return ResultadoEnvio(
        resultado=ResultadoCanal.ACEITA,
        provider_message_id=id,
        codigo="accepted",
        chave_idempotente="k",
        ocorrido_em=T0,
    )


def _temp(codigo: str = "rate_limited") -> ResultadoEnvio:
    return ResultadoEnvio(
        resultado=ResultadoCanal.FALHA_TEMPORARIA,
        provider_message_id=None,
        codigo=codigo,
        chave_idempotente="k",
        ocorrido_em=T0,
    )


def _perm() -> ResultadoEnvio:
    return ResultadoEnvio(
        resultado=ResultadoCanal.FALHA_PERMANENTE,
        provider_message_id=None,
        codigo="auth_invalid",
        chave_idempotente="k",
        ocorrido_em=T0,
    )


def _desconhecido() -> ResultadoEnvio:
    return ResultadoEnvio(
        resultado=ResultadoCanal.DESCONHECIDO,
        provider_message_id=None,
        codigo="provider_5xx",
        chave_idempotente="k",
        ocorrido_em=T0,
    )


@pytest.fixture
def base(session: Session) -> dict[str, object]:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    inbox_id, sessao_id = uuid.uuid4(), uuid.uuid4()
    session.add(
        InboxConversaORM(
            id=inbox_id,
            tenant_id=tenant.id,
            instancia_ref="inst",
            envelope_instance_id="env",
            provider_input_id="pid-1",
            remetente_normalizado="5511999999999",
            classe="operadora",
            texto="oi",
            estado="recebida",
        )
    )
    session.add(
        SessaoConversaORM(
            id=sessao_id,
            tenant_id=tenant.id,
            instancia_ref="inst",
            classe="operadora",
            remetente_normalizado="5511999999999",
        )
    )
    session.commit()
    return {"tenant_id": tenant.id, "inbox_id": inbox_id, "sessao_id": sessao_id}


def _contexto(base: dict[str, object], indice: int = 0) -> ContextoEnvio:
    assert isinstance(base["tenant_id"], uuid.UUID)
    assert isinstance(base["inbox_id"], uuid.UUID)
    assert isinstance(base["sessao_id"], uuid.UUID)
    return ContextoEnvio(
        inbox_id=base["inbox_id"],
        sessao_id=base["sessao_id"],
        tenant_id=base["tenant_id"],
        carteira_id=uuid.uuid4(),
        instancia_ref="inst",
        classe="operadora",
        principal_id=uuid.uuid4(),
        remetente="5511999999999",
        provider_input_id="pid-1",
        correlation_id="corr-1",
        indice=indice,
    )


def _repo(session: Session) -> SqlAlchemyEgressRepository:
    return SqlAlchemyEgressRepository(session)


def test_aceite_persiste_sem_alegar_entrega(session: Session, base: dict) -> None:
    canal = CanalFalso([_aceito()])
    saida = enviar_texto(_repo(session), canal, _contexto(base), "texto")
    session.commit()
    assert saida.estado == EstadoEgress.ACEITO
    assert saida.provider_id == "WA-1"
    assert canal.chamadas == 1


def test_temporario_retenta_uma_vez_e_para(session: Session, base: dict) -> None:
    canal = CanalFalso([_temp(), _aceito()])
    saida = enviar_texto(_repo(session), canal, _contexto(base), "texto")
    session.commit()
    assert saida.estado == EstadoEgress.ACEITO and canal.chamadas == 2
    canal2 = CanalFalso([_temp(), _temp()])
    saida2 = enviar_texto(_repo(session), canal2, _contexto(base, indice=1), "outro")
    session.commit()
    assert saida2.estado == EstadoEgress.FALHA and canal2.chamadas == 2


def test_permanente_e_desconhecido_sem_retry(session: Session, base: dict) -> None:
    canal = CanalFalso([_perm()])
    saida = enviar_texto(_repo(session), canal, _contexto(base), "texto")
    assert saida.estado == EstadoEgress.FALHA and canal.chamadas == 1
    canal2 = CanalFalso([_desconhecido()])
    saida2 = enviar_texto(_repo(session), canal2, _contexto(base, indice=1), "texto")
    assert saida2.estado == EstadoEgress.DESCONHECIDO and canal2.chamadas == 1
    session.commit()


def test_excecao_pos_transmissao_e_desconhecida(session: Session, base: dict) -> None:
    canal = CanalFalso([RuntimeError("socket caiu")])
    saida = enviar_texto(_repo(session), canal, _contexto(base), "texto")
    session.commit()
    assert saida.estado == EstadoEgress.DESCONHECIDO
    assert saida.codigo == "excecao_envio"
    assert canal.chamadas == 1


def test_replay_nao_retransmite_e_conflito_encerra(session: Session, base: dict) -> None:
    canal = CanalFalso([_aceito()])
    primeira = enviar_texto(_repo(session), canal, _contexto(base), "texto")
    session.commit()
    segunda = enviar_texto(_repo(session), canal, _contexto(base), "texto")
    assert segunda.id == primeira.id and canal.chamadas == 1
    with pytest.raises(ConflitoEgressError):
        enviar_texto(_repo(session), canal, _contexto(base), "texto divergente")
    assert canal.chamadas == 1
    session.rollback()


def test_terminal_nao_sai_do_lugar_nem_com_deadline(session: Session, base: dict) -> None:
    canal = CanalFalso([_aceito()])
    saida = enviar_texto(_repo(session), canal, _contexto(base), "texto")
    session.commit()
    de_novo = enviar_texto(_repo(session), canal, _contexto(base), "texto")
    assert de_novo.id == saida.id and canal.chamadas == 1
    recusada = enviar_texto(
        _repo(session), canal, _contexto(base, indice=1), "texto", prazo_restante_s=0
    )
    assert recusada.estado == EstadoEgress.FALHA and recusada.codigo == "deadline"
    assert canal.chamadas == 1
    session.commit()
