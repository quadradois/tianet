from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from emprestimo.application.bootstrap_plataforma import (
    AdministradorPlataformaBootstrap,
    AdministradorPlataformaBootstrapService,
)
from emprestimo.application.errors import AcessoNegadoError, IdempotenciaConflitoError
from emprestimo.application.estado import TenantEstadoService
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.orm import (
    AuditoriaLogORM,
    CredencialORM,
    IdempotencyKeyORM,
    PerfilAcessoORM,
    UsuarioORM,
)
from emprestimo.infrastructure.repositories import SqlAlchemyPerfilAcessoRepository
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def _service(
    session_factory: sessionmaker[Session],
) -> AdministradorPlataformaBootstrapService:
    return AdministradorPlataformaBootstrapService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )


def _executar(
    service: AdministradorPlataformaBootstrapService,
) -> AdministradorPlataformaBootstrap:
    return service.executar(
        identificador_institucional="PLATAFORMA-CONTROLE",
        nome_tenant="Controle da Plataforma",
        nome_administrador="Administrador Raiz",
        email_administrador="ROOT@PLATAFORMA.LOCAL",
        segredo_inicial="Credencial Inicial Forte 123",
    )


def test_bootstrap_persiste_perfil_credencial_e_replay_seguro(
    session_factory: sessionmaker[Session],
    session: Session,
) -> None:
    del session
    service = _service(session_factory)

    primeiro = _executar(service)
    segundo = _executar(service)

    assert primeiro.criado_agora
    assert not segundo.criado_agora
    with session_factory() as session:
        usuario = session.get(UsuarioORM, primeiro.usuario_id)
        perfil = session.get(PerfilAcessoORM, primeiro.perfil_id)
        credencial = session.scalar(select(CredencialORM))
        registro = session.scalar(select(IdempotencyKeyORM))
        assert usuario is not None and usuario.email == "root@plataforma.local"
        assert perfil is not None and perfil.nome == "administrador_plataforma"
        carregado = SqlAlchemyPerfilAcessoRepository(session).find_by_usuario_id(usuario.id)
        assert carregado is not None and carregado.permite("tenant.criar")
        assert not carregado.permite("devedor.criar")
        assert credencial is not None
        assert "Credencial Inicial Forte 123" not in credencial.hash_credencial
        assert registro is not None
        assert "Credencial Inicial Forte 123" not in (registro.resultado or "")
        assert session.scalar(select(func.count()).select_from(UsuarioORM)) == 1


def test_auditoria_nao_contem_credencial_inicial(
    session_factory: sessionmaker[Session],
    session: Session,
) -> None:
    del session
    resultado = _executar(_service(session_factory))

    with session_factory() as session:
        detalhes = session.scalars(select(AuditoriaLogORM.detalhes)).all()
        assert resultado.criado_agora
        assert all("Credencial Inicial Forte 123" not in (item or "") for item in detalhes)


def test_execucoes_concorrentes_criam_uma_unica_identidade(
    session_factory: sessionmaker[Session],
    session: Session,
) -> None:
    del session
    iniciar = Event()

    def executar() -> AdministradorPlataformaBootstrap | Exception:
        iniciar.wait()
        try:
            return _executar(_service(session_factory))
        except Exception as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = [executor.submit(executar) for _ in range(2)]
        iniciar.set()
        resultados = [futuro.result(timeout=30) for futuro in futuros]

    sucessos = [item for item in resultados if isinstance(item, AdministradorPlataformaBootstrap)]
    falhas = [item for item in resultados if isinstance(item, Exception)]
    assert len(sucessos) == 1
    assert sucessos[0].criado_agora
    assert len(falhas) == 1
    assert isinstance(falhas[0], IdempotenciaConflitoError)
    with session_factory() as consulta:
        assert consulta.scalar(select(func.count()).select_from(UsuarioORM)) == 1
        assert consulta.scalar(select(func.count()).select_from(PerfilAcessoORM)) == 1


def test_tenant_de_controle_nao_pode_ser_inativado_pela_aplicacao(
    session_factory: sessionmaker[Session],
    session: Session,
) -> None:
    del session
    resultado = _executar(_service(session_factory))
    service = TenantEstadoService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
    )

    with pytest.raises(AcessoNegadoError):
        service.inativar(resultado.tenant_id)
