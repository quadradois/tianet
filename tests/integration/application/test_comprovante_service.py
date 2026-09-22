"""Registro do comprovante (IMP-390): deduplicacao por conteudo e recusas."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.repositories.test_operacao_diaria_repositories import _contexto_operacao

from emprestimo.application.comprovante_pagamento import (
    TAMANHO_MAXIMO_BYTES,
    ComprovantePagamentoService,
    MidiaComprovanteRecusadaError,
)
from emprestimo.application.errors import EmprestimoNaoEncontradoError
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

CONTEUDO = b"comprovante-em-jpeg"
AGORA = datetime(2026, 9, 22, 14, 0, tzinfo=UTC)


def _service(session_factory: sessionmaker[Session]) -> ComprovantePagamentoService:
    return ComprovantePagamentoService(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        SqlAlchemyAuditoriaRegistro(session_factory),
        agora=lambda: AGORA,
    )


def test_registra_com_hash_do_conteudo_e_devedor_do_emprestimo(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)

    resultado = _service(session_factory).registrar(
        tenant_id=contexto.tenant_id,
        emprestimo_id=contexto.emprestimo_id,
        conteudo=CONTEUDO,
        tipo_midia="image/jpeg",
        valor_extraido=Decimal("1627.00"),
        valor_informado=Decimal("1627.00"),
    )

    assert resultado.sha256 == hashlib.sha256(CONTEUDO).hexdigest()
    assert resultado.devedor_id == contexto.devedor_id
    assert resultado.duplicado is False
    assert resultado.divergente is False


def test_mesmo_arquivo_reenviado_converge_para_o_mesmo_registro(
    session_factory: sessionmaker[Session],
) -> None:
    """Sem Idempotency-Key: o devedor reenvia a imagem, nao uma requisicao."""
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    service = _service(session_factory)

    primeiro = service.registrar(
        tenant_id=contexto.tenant_id,
        emprestimo_id=contexto.emprestimo_id,
        conteudo=CONTEUDO,
        tipo_midia="image/jpeg",
    )
    segundo = service.registrar(
        tenant_id=contexto.tenant_id,
        emprestimo_id=contexto.emprestimo_id,
        conteudo=CONTEUDO,
        tipo_midia="image/jpeg",
    )

    assert segundo.id == primeiro.id
    assert segundo.duplicado is True
    assert (
        len(service.listar(tenant_id=contexto.tenant_id, emprestimo_id=contexto.emprestimo_id)) == 1
    )


def test_valores_divergentes_ficam_marcados_sem_o_servico_escolher(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)

    resultado = _service(session_factory).registrar(
        tenant_id=contexto.tenant_id,
        emprestimo_id=contexto.emprestimo_id,
        conteudo=CONTEUDO,
        tipo_midia="image/jpeg",
        valor_extraido=Decimal("1627.00"),
        valor_informado=Decimal("1600.00"),
    )

    assert resultado.divergente is True
    assert resultado.valor_extraido == Decimal("1627.00")
    assert resultado.valor_informado == Decimal("1600.00")


@pytest.mark.parametrize(
    ("conteudo", "tipo", "motivo"),
    [
        (b"", "image/jpeg", "conteudo_vazio"),
        (b"x" * (TAMANHO_MAXIMO_BYTES + 1), "image/jpeg", "tamanho_excedido"),
        (CONTEUDO, "video/mp4", "tipo_nao_aceito"),
        (CONTEUDO, "text/plain", "tipo_nao_aceito"),
    ],
)
def test_recusas_sao_nomeadas_e_nao_persistem(
    session_factory: sessionmaker[Session], conteudo: bytes, tipo: str, motivo: str
) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)
    service = _service(session_factory)

    with pytest.raises(MidiaComprovanteRecusadaError) as excinfo:
        service.registrar(
            tenant_id=contexto.tenant_id,
            emprestimo_id=contexto.emprestimo_id,
            conteudo=conteudo,
            tipo_midia=tipo,
        )

    assert excinfo.value.motivo == motivo
    assert service.listar(tenant_id=contexto.tenant_id, emprestimo_id=contexto.emprestimo_id) == []


def test_emprestimo_de_outro_tenant_nao_existe(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)

    with pytest.raises(EmprestimoNaoEncontradoError):
        _service(session_factory).registrar(
            tenant_id=uuid.uuid4(),
            emprestimo_id=contexto.emprestimo_id,
            conteudo=CONTEUDO,
            tipo_midia="image/jpeg",
        )


def test_resultado_nunca_carrega_o_binario(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        contexto = _contexto_operacao(session)

    resultado = _service(session_factory).registrar(
        tenant_id=contexto.tenant_id,
        emprestimo_id=contexto.emprestimo_id,
        conteudo=CONTEUDO,
        tipo_midia="image/jpeg",
    )

    assert "comprovante-em-jpeg" not in repr(resultado)
