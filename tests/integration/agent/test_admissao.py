"""Controle de admissão — aceite da Entrega 356-C (IMP-356).

Relógio sempre injetado (nada de sleep): janelas, virada, expiração e
reserva são determinísticos. Concorrência com threads reais no PostgreSQL.
"""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import TenantFactory

from emprestimo.agent.admissao import (
    PADRAO_DIMENSOES,
    ConfiguracaoAdmissao,
    ControleAdmissao,
    DimensaoCota,
)
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.infrastructure.db.orm import SlotExecucaoORM
from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

TENANT = uuid.uuid4()
INSTANCIA = "tianet_teste"
REMETENTE = "5511999999999"
DESCONHECIDO = "5511888888888"
T0 = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)


@pytest.fixture
def tenant_id(session: Session) -> uuid.UUID:
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    session.commit()
    return tenant.id


def _controle() -> ControleAdmissao:
    return ControleAdmissao(ConfiguracaoAdmissao(dimensoes=PADRAO_DIMENSOES))


@pytest.fixture
def controle() -> ControleAdmissao:
    return _controle()


def _avaliar(
    controle: ControleAdmissao,
    session_factory: sessionmaker[Session],
    tenant_id: uuid.UUID,
    *,
    classe: str = "operadora",
    remetente: str = REMETENTE,
    agora: datetime = T0,
    commit: bool = True,
) -> tuple[bool, str, bool]:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        decisao = controle.avaliar(
            uow.admissao,
            tenant_id=tenant_id,
            instancia_ref=INSTANCIA,
            classe=classe,
            remetente=remetente,
            agora=agora,
        )
        if commit:
            uow.commit()
        else:
            uow.rollback()
        return decisao.admitida, decisao.motivo, decisao.avisar


def test_admite_dentro_da_quota_e_consume(
    controle: ControleAdmissao, session_factory: sessionmaker[Session], tenant_id: uuid.UUID
) -> None:
    for _ in range(6):
        admitida, motivo, _ = _avaliar(controle, session_factory, tenant_id)
        assert (admitida, motivo) == (True, "ok")
    admitida, motivo, avisar = _avaliar(controle, session_factory, tenant_id)
    assert admitida is False
    assert motivo == "janela-cheia:operadora-remetente"
    assert avisar is True


def test_aviso_no_maximo_um_por_minuto(
    controle: ControleAdmissao, session_factory: sessionmaker[Session], tenant_id: uuid.UUID
) -> None:
    for _ in range(6):
        _avaliar(controle, session_factory, tenant_id)
    _, _, primeiro = _avaliar(controle, session_factory, tenant_id, agora=T0)
    _, _, segundo = _avaliar(controle, session_factory, tenant_id, agora=T0 + timedelta(seconds=30))
    _, _, terceiro = _avaliar(
        controle, session_factory, tenant_id, agora=T0 + timedelta(seconds=60)
    )
    assert (primeiro, segundo, terceiro) == (True, False, True)


def test_janela_desliza_e_libera_quota(
    controle: ControleAdmissao, session_factory: sessionmaker[Session], tenant_id: uuid.UUID
) -> None:
    for _ in range(6):
        _avaliar(controle, session_factory, tenant_id, agora=T0)
    admitida, _, _ = _avaliar(controle, session_factory, tenant_id, agora=T0)
    assert admitida is False
    admitida, _, _ = _avaliar(
        controle, session_factory, tenant_id, agora=T0 + timedelta(seconds=61)
    )
    assert admitida is True


def test_desconhecido_tem_quota_propria_menor(
    controle: ControleAdmissao, session_factory: sessionmaker[Session], tenant_id: uuid.UUID
) -> None:
    for _ in range(2):
        admitida, _, _ = _avaliar(
            controle,
            session_factory,
            tenant_id,
            classe="pre_cadastro",
            remetente=DESCONHECIDO,
        )
        assert admitida is True
    admitida, motivo, _ = _avaliar(
        controle,
        session_factory,
        tenant_id,
        classe="pre_cadastro",
        remetente=DESCONHECIDO,
    )
    assert (admitida, motivo) == (False, "janela-cheia:desconhecido-remetente")
    # A operadora segue intacta: isolamento por chave, não por contador global.
    admitida, _, _ = _avaliar(controle, session_factory, tenant_id)
    assert admitida is True


def test_config_incompleta_recusa_subir() -> None:
    with pytest.raises(ValueError, match="obrigatorias ausentes"):
        ControleAdmissao(ConfiguracaoAdmissao(dimensoes=(DimensaoCota("instancia", 60, 30),)))
    with pytest.raises(ValueError, match="invalida"):
        ControleAdmissao(
            ConfiguracaoAdmissao(
                dimensoes=(
                    DimensaoCota("instancia", 60, 30),
                    DimensaoCota("operadora-remetente", 60, 0),
                    DimensaoCota("desconhecido-remetente", 60, 2),
                    DimensaoCota("desconhecido-classe", 60, 6),
                )
            )
        )


def _semear_slots(session: Session) -> None:
    session.add_all(
        [
            SlotExecucaoORM(id=1, reservado_operadora=False, dono_sessao=None, expira_em=None),
            SlotExecucaoORM(id=2, reservado_operadora=True, dono_sessao=None, expira_em=None),
        ]
    )
    session.commit()


def test_reserva_e_atomica_entre_threads(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    _semear_slots(session)
    resultados: list[bool] = []
    trava = threading.Lock()

    def tentar(i: int) -> None:
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            ok = uow.admissao.reservar_slot(f"sessao-{i}", operadora=False, agora=T0)
            if ok:
                uow.commit()
            else:
                uow.rollback()
        with trava:
            resultados.append(ok)

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(tentar, range(4)))
    # Desconhecidos disputam 1 vaga compartilhada: exatamente 1 vence.
    assert sorted(resultados) == [False, False, False, True]


def test_desconhecido_nunca_ocupa_reserva_da_operadora(
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    _semear_slots(session)
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.admissao.reservar_slot("desconhecido-1", operadora=False, agora=T0) is True
        # Segunda vaga e reservada: desconhecido nao entra, operadora entra.
        assert uow.admissao.reservar_slot("desconhecido-2", operadora=False, agora=T0) is False
        assert uow.admissao.reservar_slot("operadora-1", operadora=True, agora=T0) is True
        uow.rollback()


def test_slots_ausentes_fecham_em_fail_closed(
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    # O fixture `session` trunca as tabelas: sem linhas semeadas, sem vaga.
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.admissao.reservar_slot("x", operadora=True, agora=T0) is False
        uow.rollback()


def test_expiradas_sao_recolhidas(session: Session, session_factory: sessionmaker[Session]) -> None:
    _semear_slots(session)
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.admissao.reservar_slot("morta", operadora=False, agora=T0) is True
        uow.commit()
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        assert uow.admissao.liberar_expiradas(T0 + timedelta(seconds=121)) == 1
        assert (
            uow.admissao.reservar_slot("nova", operadora=False, agora=T0 + timedelta(seconds=121))
            is True
        )
        uow.rollback()


def test_restart_preserva_contagens(
    controle: ControleAdmissao, session_factory: sessionmaker[Session], tenant_id: uuid.UUID
) -> None:
    for _ in range(6):
        _avaliar(controle, session_factory, tenant_id)
    # "Restart": controle novo, mesmo banco — a quota continua cheia.
    outro = _controle()
    admitida, motivo, _ = _avaliar(outro, session_factory, tenant_id)
    assert (admitida, motivo) == (False, "janela-cheia:operadora-remetente")
