"""Testes do lancamento composto (IMP-305, PLAN-027)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import CarteiraFactory, TenantFactory, UsuarioFactory

from emprestimo.application.errors import (
    IdempotenciaConflitoError,
    TransicaoEstadoInvalidaError,
)
from emprestimo.application.lancamento import CondicoesLancamento, DevedorNovo, LancamentoService
from emprestimo.application.motor_financeiro import criar_emprestimo_e_plano_em
from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@dataclass(frozen=True)
class _Ambiente:
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    usuario_id: uuid.UUID


def _ambiente(session_factory: sessionmaker[Session]) -> _Ambiente:
    with session_factory() as session:
        tenant = TenantFactory.build()
        SqlAlchemyTenantRepository(session).save(tenant)
        carteira = CarteiraFactory.build(tenant_id=tenant.id)
        SqlAlchemyCarteiraRepository(session).save(carteira)
        usuario = UsuarioFactory.build(tenant_id=tenant.id)
        SqlAlchemyUsuarioRepository(session).save(usuario)
        session.commit()
        return _Ambiente(tenant_id=tenant.id, carteira_id=carteira.id, usuario_id=usuario.id)


def _cpf() -> str:
    digitos = [int(d) for d in f"{uuid.uuid4().int % 10**9:09d}"]
    for _ in range(2):
        peso = len(digitos) + 1
        soma = sum(d * (peso - i) for i, d in enumerate(digitos))
        resto = (soma * 10) % 11
        digitos.append(0 if resto == 10 else resto)
    return "".join(str(d) for d in digitos)


def _condicoes(**overrides: object) -> CondicoesLancamento:
    base: dict[str, object] = {
        "valor_contratado": "6000.00",
        "taxa_juros_mensal": "0.0300",
        "quantidade_parcelas": 3,
        "primeiro_vencimento": date(2026, 9, 20),
    }
    base.update(overrides)
    return CondicoesLancamento(**base)  # type: ignore[arg-type]


def _servico(session_factory: sessionmaker[Session]) -> LancamentoService:
    return LancamentoService(
        lambda: SqlAlchemyUnitOfWork(session_factory), criar_emprestimo_e_plano_em
    )


def test_lancamento_cria_devedor_e_toda_a_cadeia_em_uma_transacao(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    documento = _cpf()

    resultado = _servico(session_factory).lancar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        usuario_id=ambiente.usuario_id,
        devedor_novo=DevedorNovo(
            documento=documento,
            nome="Cliente do Wizard",
            contato_whatsapp="(11) 98888-7766",
        ),
        condicoes=_condicoes(),
        data_referencia=date(2026, 8, 16),
        idempotency_key=str(uuid.uuid4()),
    )

    with session_factory() as session:
        uow = SqlAlchemyUnitOfWork(lambda: session)
        proposta = uow.proposta_comercial.find_by_id(resultado.proposta_id)
        contrato = uow.contrato_credito.find_by_id(resultado.contrato_id)
        emprestimo = uow.emprestimo.find_by_id(resultado.emprestimo_id)
        parcelas = uow.parcela.find_by_emprestimo_id(resultado.emprestimo_id)

    assert proposta is not None and proposta.estado is PropostaComercialState.APROVADA
    assert contrato is not None
    assert contrato.estado is ContratoCreditoState.LIBERADO_PARA_MOTOR
    assert emprestimo is not None
    assert len(parcelas) == 3
    assert resultado.devedor_id is not None


def test_lancamento_reutiliza_devedor_existente(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    servico = _servico(session_factory)
    primeiro = servico.lancar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        usuario_id=ambiente.usuario_id,
        devedor_novo=DevedorNovo(
            documento=_cpf(), nome="Cliente Recorrente", contato_whatsapp="(11) 97777-6655"
        ),
        condicoes=_condicoes(),
        data_referencia=date(2026, 8, 16),
        idempotency_key=str(uuid.uuid4()),
    )

    segundo = servico.lancar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        usuario_id=ambiente.usuario_id,
        devedor_id=primeiro.devedor_id,
        condicoes=_condicoes(valor_contratado="1500.00", quantidade_parcelas=2),
        data_referencia=date(2026, 8, 16),
        idempotency_key=str(uuid.uuid4()),
    )

    assert segundo.devedor_id == primeiro.devedor_id
    assert segundo.emprestimo_id != primeiro.emprestimo_id


def test_falha_no_motor_desfaz_o_devedor_criado_na_mesma_transacao(
    session_factory: sessionmaker[Session],
) -> None:
    """A razao de existir da operacao composta.

    Com oito chamadas HTTP separadas, uma falha tardia deixa Devedor, Proposta e
    Contrato orfaos. Aqui nada pode sobreviver.
    """
    ambiente = _ambiente(session_factory)
    documento = _cpf()

    with pytest.raises(TransicaoEstadoInvalidaError):
        _servico(session_factory).lancar(
            tenant_id=ambiente.tenant_id,
            carteira_id=ambiente.carteira_id,
            usuario_id=ambiente.usuario_id,
            devedor_novo=DevedorNovo(
                documento=documento,
                nome="Nao Deve Persistir",
                contato_whatsapp="(11) 96666-5544",
            ),
            # quantidade_parcelas invalida derruba o Motor no ultimo passo
            condicoes=_condicoes(quantidade_parcelas=0),
            data_referencia=date(2026, 8, 16),
            idempotency_key=str(uuid.uuid4()),
        )

    with session_factory() as session:
        uow = SqlAlchemyUnitOfWork(lambda: session)
        encontrado = uow.devedor.find_by_documento_carteira(
            Documento.from_str(documento), ambiente.carteira_id
        )
        assert encontrado is None


def test_replay_com_a_mesma_chave_nao_lanca_duas_vezes(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    servico = _servico(session_factory)
    chave = str(uuid.uuid4())
    argumentos = {
        "tenant_id": ambiente.tenant_id,
        "carteira_id": ambiente.carteira_id,
        "usuario_id": ambiente.usuario_id,
        "devedor_novo": DevedorNovo(
            documento=_cpf(), nome="Cliente Idempotente", contato_whatsapp="(11) 95555-4433"
        ),
        "condicoes": _condicoes(),
        "data_referencia": date(2026, 8, 16),
        "idempotency_key": chave,
    }

    primeiro = servico.lancar(**argumentos)  # type: ignore[arg-type]
    segundo = servico.lancar(**argumentos)  # type: ignore[arg-type]

    assert segundo == primeiro


def test_mesma_chave_com_intencao_diferente_e_conflito(
    session_factory: sessionmaker[Session],
) -> None:
    ambiente = _ambiente(session_factory)
    servico = _servico(session_factory)
    chave = str(uuid.uuid4())
    servico.lancar(
        tenant_id=ambiente.tenant_id,
        carteira_id=ambiente.carteira_id,
        usuario_id=ambiente.usuario_id,
        devedor_novo=DevedorNovo(
            documento=_cpf(), nome="Primeira Intencao", contato_whatsapp="(11) 94444-3322"
        ),
        condicoes=_condicoes(),
        data_referencia=date(2026, 8, 16),
        idempotency_key=chave,
    )

    with pytest.raises(IdempotenciaConflitoError):
        servico.lancar(
            tenant_id=ambiente.tenant_id,
            carteira_id=ambiente.carteira_id,
            usuario_id=ambiente.usuario_id,
            devedor_novo=DevedorNovo(
                documento=_cpf(), nome="Outra Intencao", contato_whatsapp="(11) 93333-2211"
            ),
            condicoes=_condicoes(valor_contratado="99999.00"),
            data_referencia=date(2026, 8, 16),
            idempotency_key=chave,
        )
