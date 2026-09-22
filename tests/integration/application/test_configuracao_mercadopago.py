"""Interruptor do Mercado Pago ponta a ponta (IMP-388).

O que este arquivo protege: a integracao nasce desligada, so liga com
credencial testada, e **desligar nao invalida dinheiro em transito**.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.repositories.test_operacao_diaria_repositories import _contexto_operacao

from emprestimo.application.configuracao_mercadopago import (
    ConfiguracaoMercadoPagoResultado,
    ConfiguracaoMercadoPagoService,
    MercadoPagoDesabilitadoError,
    VerificacaoCredencialError,
)
from emprestimo.domain.credit.cobranca_pix import CobrancaPix, CobrancaPixState, OrigemCobrancaPix
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.cifra import CifraToken
from emprestimo.infrastructure.mercadopago import ResultadoVerificacao
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

TOKEN = "APP_USR-token"
SECRET = "segredo-do-webhook"
AGORA = datetime(2026, 9, 22, 15, 0, tzinfo=UTC)


def _service(
    session_factory: sessionmaker[Session],
    *,
    valido: bool = True,
    detalhe: str = "ok",
) -> ConfiguracaoMercadoPagoService:
    chave = CifraToken.gerar_chave()
    return ConfiguracaoMercadoPagoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
        cifra_factory=lambda: CifraToken(chave),
        verificador=lambda _token: ResultadoVerificacao(valido=valido, detalhe=detalhe),
        agora=lambda: AGORA,
    )


def _ligar(
    service: ConfiguracaoMercadoPagoService, tenant_id: uuid.UUID, usuario_id: uuid.UUID
) -> ConfiguracaoMercadoPagoResultado:
    service.definir_credenciais(
        tenant_id=tenant_id,
        access_token=TOKEN,
        webhook_secret=SECRET,
        usuario_id=usuario_id,
        idempotency_key=f"cred-{uuid.uuid4()}",
    )
    service.testar(tenant_id=tenant_id, usuario_id=usuario_id)
    return service.habilitar(
        tenant_id=tenant_id, usuario_id=usuario_id, idempotency_key=f"on-{uuid.uuid4()}"
    )


def test_tenant_sem_linha_responde_desligado_em_vez_de_erro(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)

    resultado = _service(session_factory).consultar(tenant_id=contexto.tenant_id)

    assert resultado.habilitado is False
    assert resultado.credencial_configurada is False


def test_ciclo_completo_liga_a_integracao(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    service = _service(session_factory)

    resultado = _ligar(service, contexto.tenant_id, contexto.usuario_id)

    assert resultado.habilitado is True
    assert resultado.testado_em == AGORA
    assert resultado.credencial_configurada is True
    assert resultado.assinatura_configurada is True


def test_dto_nunca_devolve_o_segredo(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    service = _service(session_factory)
    _ligar(service, contexto.tenant_id, contexto.usuario_id)

    texto = repr(service.consultar(tenant_id=contexto.tenant_id))

    assert TOKEN not in texto
    assert SECRET not in texto


def test_habilitar_sem_teste_e_recusado(session_factory: sessionmaker[Session]) -> None:
    from emprestimo.domain.common.errors import ViolacaoInvarianteError

    with session_factory() as session:
        contexto = _contexto_operacao(session)
    service = _service(session_factory)
    service.definir_credenciais(
        tenant_id=contexto.tenant_id,
        access_token=TOKEN,
        webhook_secret=SECRET,
        usuario_id=contexto.usuario_id,
        idempotency_key=f"cred-{uuid.uuid4()}",
    )

    with pytest.raises(ViolacaoInvarianteError) as excinfo:
        service.habilitar(
            tenant_id=contexto.tenant_id,
            usuario_id=contexto.usuario_id,
            idempotency_key=f"on-{uuid.uuid4()}",
        )

    assert excinfo.value.codigo == "INV-002"


def test_provedor_recusa_a_credencial_e_a_integracao_nao_liga(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    service = _service(session_factory, valido=False, detalhe="credencial_recusada")
    service.definir_credenciais(
        tenant_id=contexto.tenant_id,
        access_token=TOKEN,
        webhook_secret=SECRET,
        usuario_id=contexto.usuario_id,
        idempotency_key=f"cred-{uuid.uuid4()}",
    )

    with pytest.raises(VerificacaoCredencialError) as excinfo:
        service.testar(tenant_id=contexto.tenant_id, usuario_id=contexto.usuario_id)

    assert excinfo.value.detalhe == "credencial_recusada"
    assert service.consultar(tenant_id=contexto.tenant_id).testado_em is None


def test_desligar_preserva_cobranca_pendente_porque_o_dinheiro_esta_em_transito(
    session_factory: sessionmaker[Session],
) -> None:
    """Regra do PLAN-045 §3.12: desligar impede emissao nova, nao invalida Pix vivo."""
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    service = _service(session_factory)
    _ligar(service, contexto.tenant_id, contexto.usuario_id)

    cobranca = CobrancaPix.criar(
        tenant_id=contexto.tenant_id,
        carteira_id=contexto.carteira_id,
        emprestimo_id=contexto.emprestimo_id,
        devedor_id=contexto.devedor_id,
        valor=Decimal("300.00"),
        juro_periodo=Decimal("100.00"),
        quitacao=Decimal("5000.00"),
        origem=OrigemCobrancaPix.COPILOT_DEVEDOR,
        criado_por=contexto.usuario_id,
        agora=AGORA,
    )
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.cobranca_pix.save(cobranca)
        uow.commit()

    service.desabilitar(
        tenant_id=contexto.tenant_id,
        usuario_id=contexto.usuario_id,
        idempotency_key=f"off-{uuid.uuid4()}",
    )

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        viva = uow.cobranca_pix.find_by_id(cobranca.id)
        with pytest.raises(MercadoPagoDesabilitadoError):
            service.exigir_habilitado(uow, contexto.tenant_id)

    assert viva is not None
    assert viva.estado is CobrancaPixState.PENDENTE


def test_religar_nao_exige_redigitar_credencial(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    service = _service(session_factory)
    _ligar(service, contexto.tenant_id, contexto.usuario_id)
    service.desabilitar(
        tenant_id=contexto.tenant_id,
        usuario_id=contexto.usuario_id,
        idempotency_key=f"off-{uuid.uuid4()}",
    )

    resultado = service.habilitar(
        tenant_id=contexto.tenant_id,
        usuario_id=contexto.usuario_id,
        idempotency_key=f"on2-{uuid.uuid4()}",
    )

    assert resultado.habilitado is True


def test_replay_da_mesma_chave_converge_sem_duplicar(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    service = _service(session_factory)
    _ligar(service, contexto.tenant_id, contexto.usuario_id)
    chave = f"off-{uuid.uuid4()}"

    primeiro = service.desabilitar(
        tenant_id=contexto.tenant_id, usuario_id=contexto.usuario_id, idempotency_key=chave
    )
    segundo = service.desabilitar(
        tenant_id=contexto.tenant_id, usuario_id=contexto.usuario_id, idempotency_key=chave
    )

    assert primeiro.habilitado is False
    assert segundo.habilitado is False


def test_trocar_credencial_derruba_o_teste_e_exige_novo(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    service = _service(session_factory)
    _ligar(service, contexto.tenant_id, contexto.usuario_id)

    service.definir_credenciais(
        tenant_id=contexto.tenant_id,
        access_token="APP_USR-outro",
        webhook_secret=SECRET,
        usuario_id=contexto.usuario_id,
        idempotency_key=f"cred2-{uuid.uuid4()}",
    )

    assert service.consultar(tenant_id=contexto.tenant_id).testado_em is None
