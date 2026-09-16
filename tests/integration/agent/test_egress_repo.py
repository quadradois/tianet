"""Egress durável em PostgreSQL real (IMP-356-E slice 2).

Preparar idempotente (replay devolve, divergência conflita), corrida
resolve para o vencedor e transições terminais não saem do lugar.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from tests.factories import TenantFactory

from emprestimo.agent.conversa import ClasseContexto
from emprestimo.agent.egress import (
    ConflitoEgressError,
    EgressConversa,
    EstadoEgress,
    IntencaoEgress,
    derivar_chave,
    payload_canonico,
)
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.infrastructure.db.orm import InboxConversaORM, SessaoConversaORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyEgressRepository,
    SqlAlchemyTenantRepository,
)

T0 = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


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


def _intencao(base: dict[str, object], texto: str = "texto") -> EgressConversa:
    assert isinstance(base["tenant_id"], uuid.UUID)
    assert isinstance(base["inbox_id"], uuid.UUID)
    assert isinstance(base["sessao_id"], uuid.UUID)
    intencao = IntencaoEgress(
        tenant_id=base["tenant_id"],
        carteira_id=uuid.uuid4(),
        instancia_ref="inst",
        classe=ClasseContexto.OPERADORA.value,
        principal_id=uuid.uuid4(),
        destinatario="5511999999999",
        provider_input_id="pid-1",
        indice=0,
        ferramenta="consultar_acertos",
        call_id="call_1",
        texto=texto,
    )
    payload = payload_canonico(
        {
            "texto": texto,
            "destinatario": intencao.destinatario,
            "indice": intencao.indice,
        }
    )
    return EgressConversa(
        id=uuid.uuid4(),
        inbox_id=base["inbox_id"],
        sessao_id=base["sessao_id"],
        indice=0,
        chave=derivar_chave(intencao),
        payload_canonico=payload,
        payload_hash=hashlib.sha256(payload.encode()).hexdigest(),
        tenant_id=base["tenant_id"],
        carteira_id=intencao.carteira_id,
        instancia_ref="inst",
        classe="operadora",
        principal_id=intencao.principal_id,
        destinatario=intencao.destinatario,
        ferramenta=intencao.ferramenta,
        call_id=intencao.call_id,
        estado=EstadoEgress.PREPARADO,
        tentativas=0,
        criado_em=T0,
    )


def test_preparar_replay_e_conflito(session: Session, base: dict[str, object]) -> None:
    repo = SqlAlchemyEgressRepository(session)
    primeiro = repo.preparar(_intencao(base))
    session.commit()
    repetido = repo.preparar(_intencao(base))
    assert repetido.id == primeiro.id
    with pytest.raises(ConflitoEgressError):
        repo.preparar(_intencao(base, texto="outro"))
    assert repo.buscar_por_chave(primeiro.chave) is not None
    assert repo.buscar_por_chave("egress/v1/inexistente") is None


def test_transicoes_e_terminal(session: Session, base: dict[str, object]) -> None:
    repo = SqlAlchemyEgressRepository(session)
    egresso = repo.preparar(_intencao(base))
    session.commit()
    em_envio = repo.marcar_estado(egresso.id, EstadoEgress.EM_ENVIO)
    assert em_envio.estado == EstadoEgress.EM_ENVIO and em_envio.tentativas == 1
    aceito = repo.marcar_estado(
        egresso.id, EstadoEgress.ACEITO, provider_id="WA-1", codigo="accepted"
    )
    assert aceito.provider_id == "WA-1"
    with pytest.raises(ConflitoEgressError):
        repo.marcar_estado(egresso.id, EstadoEgress.EM_ENVIO)
    session.commit()
