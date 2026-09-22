"""Recuperacao operacional de credencial: o unico administrador esqueceu a senha.

Sem isto, `POST /iam/usuarios/{id}/credencial/redefinir` exige alguem logado
com `credencial.redefinir` — o unico administrador fica trancado por fora.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.application.bootstrap_plataforma import AdministradorPlataformaBootstrapService
from emprestimo.application.credenciais import CredenciaisService
from emprestimo.application.errors import UsuarioNaoEncontradoError
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

SEGREDO_ANTIGO = "Credencial Inicial Forte 123"
SEGREDO_NOVO = "Nova Credencial Ainda Mais Forte 456"


def _bootstrap(session_factory: sessionmaker[Session], email: str) -> uuid.UUID:
    resultado = AdministradorPlataformaBootstrapService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    ).executar(
        identificador_institucional=f"TENANT-{uuid.uuid4().hex[:8]}",
        nome_tenant="Tenant de teste",
        nome_administrador="Administradora",
        email_administrador=email,
        segredo_inicial=SEGREDO_ANTIGO,
    )
    return resultado.usuario_id


def _credencial(session_factory: sessionmaker[Session], usuario_id: uuid.UUID) -> Credencial:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        credencial = uow.credencial.find_by_usuario_id(usuario_id)
    assert credencial is not None
    return credencial


def test_recuperacao_operacional_troca_a_credencial_pelo_email(
    session_factory: sessionmaker[Session],
) -> None:
    email = f"admin-{uuid.uuid4().hex[:6]}@tianet.local"
    usuario_id = _bootstrap(session_factory, email)
    assert _credencial(session_factory, usuario_id).verificar(SEGREDO_ANTIGO)

    service = CredenciaisService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )
    resultado = service.recuperar_operacional(email=email.upper(), novo_segredo=SEGREDO_NOVO)

    assert resultado.usuario_id == usuario_id
    credencial = _credencial(session_factory, usuario_id)
    assert credencial.verificar(SEGREDO_NOVO)
    assert not credencial.verificar(SEGREDO_ANTIGO)


def test_recuperacao_operacional_recusa_email_desconhecido(
    session_factory: sessionmaker[Session],
) -> None:
    service = CredenciaisService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )
    with pytest.raises(UsuarioNaoEncontradoError):
        service.recuperar_operacional(email="ninguem@tianet.local", novo_segredo=SEGREDO_NOVO)
