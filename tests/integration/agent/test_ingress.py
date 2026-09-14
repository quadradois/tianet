"""Ingress duravel do agente — aceite da Entrega 356-A (IMP-356).

Tudo contra PostgreSQL real: unicidade, replay, isolamento de classe e
recuperacao sem estado em memoria. Nenhum LLM, ferramenta ou envio existe
neste slice — o que se prova e persistencia antes do ACK e classificacao.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient
from tests.factories import TenantFactory

from emprestimo.agent.conversa import ClasseContexto, ConfiguracaoIngress
from emprestimo.agent.ingress import create_ingress_app
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.infrastructure.db.session import get_session_factory
from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

INSTANCIA_ID = "035eaa43-0000-4000-8000-aaaaaaaaaaaa"
INSTANCIA_REF = "tianet_teste"
OPERADORA_NUMERO = "5511999999999"


def _config(
    tenant_id: uuid.UUID, allowlist: frozenset[str] = frozenset({OPERADORA_NUMERO})
) -> ConfiguracaoIngress:
    return ConfiguracaoIngress(
        tenant_id=tenant_id,
        instancia_ref=INSTANCIA_REF,
        allowlist_operadora=allowlist,
    )


@pytest.fixture
def tenant_id(session: Session) -> uuid.UUID:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    session.commit()
    return tenant.id


@pytest.fixture
def app(tenant_id: uuid.UUID) -> Iterator[TestClient]:
    session_factory = get_session_factory()
    application = create_ingress_app(
        _config(tenant_id),
        lambda: SqlAlchemyUnitOfWork(session_factory),
        INSTANCIA_ID,
    )
    with TestClient(application) as client:
        yield client


def _envelope(
    *,
    event: str = "Message",
    instance_id: str = INSTANCIA_ID,
    info_id: str | None = "3EB0TESTE0001",
    sender: str = f"{OPERADORA_NUMERO}@s.whatsapp.net",
    is_from_me: bool = False,
    is_group: bool = False,
    texto: str | None = "qual e o saldo?",
) -> dict[str, Any]:
    info: dict[str, Any] = {"Sender": sender, "IsFromMe": is_from_me, "IsGroup": is_group}
    if info_id is not None:
        info["ID"] = info_id
    mensagem: dict[str, Any] = {}
    if texto is not None:
        mensagem = {"conversation": texto}
    return {
        "event": event,
        "instanceId": instance_id,
        "instanceToken": "token-nao-confiavel",
        "instanceName": "nome-nao-confiavel",
        "data": {"Info": info, "Message": mensagem},
    }


def _contar(tenant_id: uuid.UUID) -> int:
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        total = uow.inbox_conversa.contar(tenant_id)
        uow.commit()
        return total


def test_aceita_e_persiste_operadora(app: TestClient, tenant_id: uuid.UUID) -> None:
    resposta = app.post("/whatsapp/webhook", json=_envelope())
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo == {"message": "accepted", "duplicada": False, "classe": "operadora"}
    assert _contar(tenant_id) == 1
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        linha = uow.inbox_conversa.buscar_por_chave(tenant_id, INSTANCIA_REF, "3EB0TESTE0001")
        assert linha is not None
        assert linha.estado == "recebida"
        assert linha.texto == "qual e o saldo?"
        assert linha.classe is ClasseContexto.OPERADORA
        assert linha.envelope_instance_id == INSTANCIA_ID
        sessao = uow.sessao_conversa.buscar(
            tenant_id, INSTANCIA_REF, ClasseContexto.OPERADORA, OPERADORA_NUMERO
        )
        assert sessao is not None
        uow.commit()


def test_replay_nao_duplica_nem_reprocessa(app: TestClient, tenant_id: uuid.UUID) -> None:
    primeira = app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0REPLAY01"))
    assert primeira.json()["duplicada"] is False
    segunda = app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0REPLAY01"))
    assert segunda.status_code == 200
    assert segunda.json() == {"message": "accepted", "duplicada": True, "classe": "operadora"}
    assert _contar(tenant_id) == 1


def test_mesmo_id_em_outra_instancia_nao_colide(
    app: TestClient, tenant_id: uuid.UUID, session_factory: sessionmaker[Session]
) -> None:
    assert app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0MESMOID")).status_code == 200
    outra = create_ingress_app(
        ConfiguracaoIngress(
            tenant_id=tenant_id,
            instancia_ref="tianet_outra",
            allowlist_operadora=frozenset({OPERADORA_NUMERO}),
        ),
        lambda: SqlAlchemyUnitOfWork(session_factory),
        "ffffffff-0000-4000-8000-bbbbbbbbbbbb",
    )
    with TestClient(outra) as outra_client:
        resposta = outra_client.post(
            "/whatsapp/webhook",
            json=_envelope(
                info_id="3EB0MESMOID",
                instance_id="ffffffff-0000-4000-8000-bbbbbbbbbbbb",
            ),
        )
    assert resposta.status_code == 200
    assert resposta.json()["duplicada"] is False
    assert _contar(tenant_id) == 2


@pytest.mark.parametrize(
    ("ajuste", "motivo"),
    [
        ({"is_from_me": True}, "propria"),
        ({"is_group": True}, "grupo"),
        ({"sender": "5511999999999-123456@g.us"}, "grupo"),
        ({"info_id": None}, "sem-id"),
        ({"event": "HistorySync"}, "evento-nao-suportado"),
        ({"event": "Receipt"}, "evento-nao-suportado"),
        ({"instance_id": "desconhecida"}, "instancia-desconhecida"),
    ],
)
def test_descartes_respondem_2xx_sem_persistir(
    app: TestClient, tenant_id: uuid.UUID, ajuste: dict[str, Any], motivo: str
) -> None:
    resposta = app.post("/whatsapp/webhook", json=_envelope(**ajuste))
    assert resposta.status_code == 200
    assert resposta.json() == {"message": "discarded", "motivo": motivo}
    assert _contar(tenant_id) == 0


def test_desconhecido_vira_pre_cadastro_sem_leitura_de_carteira(
    app: TestClient, tenant_id: uuid.UUID
) -> None:
    resposta = app.post(
        "/whatsapp/webhook",
        json=_envelope(info_id="3EB0DESCONHECIDO", sender="5511888888888@s.whatsapp.net"),
    )
    assert resposta.json() == {"message": "accepted", "duplicada": False, "classe": "pre_cadastro"}
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        linha = uow.inbox_conversa.buscar_por_chave(tenant_id, INSTANCIA_REF, "3EB0DESCONHECIDO")
        assert linha is not None
        assert linha.classe is ClasseContexto.PRE_CADASTRO
        uow.commit()


def test_lid_nunca_e_operadora_mesmo_com_numero_na_allowlist(
    app: TestClient, tenant_id: uuid.UUID
) -> None:
    resposta = app.post(
        "/whatsapp/webhook",
        json=_envelope(info_id="3EB0LID01", sender=f"{OPERADORA_NUMERO}@lid"),
    )
    assert resposta.json()["classe"] == "pre_cadastro"


def test_contextos_nunca_compartilham_sessao(app: TestClient, tenant_id: uuid.UUID) -> None:
    app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0S1"))
    app.post(
        "/whatsapp/webhook",
        json=_envelope(info_id="3EB0S2", sender="5511888888888@s.whatsapp.net"),
    )
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        operadora = uow.sessao_conversa.buscar(
            tenant_id, INSTANCIA_REF, ClasseContexto.OPERADORA, OPERADORA_NUMERO
        )
        pre = uow.sessao_conversa.buscar(
            tenant_id, INSTANCIA_REF, ClasseContexto.PRE_CADASTRO, "5511888888888"
        )
        assert operadora is not None
        assert pre is not None
        assert operadora.id != pre.id
        uow.commit()


def test_recuperacao_apos_crash_nao_duplica(app: TestClient, tenant_id: uuid.UUID) -> None:
    # O servidor nao guarda nada em memoria: a prova de recuperacao e
    # reenviar o mesmo ID e observar deduplicacao pelo banco.
    primeira = app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0CRASH01"))
    assert primeira.json()["duplicada"] is False
    del primeira
    segunda = app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0CRASH01"))
    assert segunda.json()["duplicada"] is True
    assert _contar(tenant_id) == 1
