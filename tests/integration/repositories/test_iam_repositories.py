"""Testes de integracao dos repositories IAM (IMP-086)."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from time import sleep

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.domain.common.errors import PerfilJaExisteError, ViolacaoInvarianteError
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso, PerfilState
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.sessao import Sessao
from emprestimo.domain.platform.token_ativacao import TokenAtivacao
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCredencialRepository,
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyPermissaoRepository,
    SqlAlchemySessaoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyTokenAtivacaoRepository,
    SqlAlchemyUsuarioRepository,
)


def test_credencial_repository_round_trip(session: Session) -> None:
    tenant_id, usuario_id = _usuario_persistido(session)
    repo = SqlAlchemyCredencialRepository(session)
    credencial = Credencial.definir(usuario_id=usuario_id, segredo="Senha forte 123")

    repo.save(credencial)
    session.commit()

    por_id = repo.find_by_id(credencial.id)
    por_usuario = repo.find_by_usuario_id(usuario_id)

    assert por_id is not None
    assert por_id.usuario_id == usuario_id
    assert por_id.verificar("Senha forte 123")
    assert por_usuario is not None
    assert por_usuario.id == credencial.id
    assert tenant_id is not None


def test_credencial_repository_usuario_unico(session: Session) -> None:
    _, usuario_id = _usuario_persistido(session)
    repo = SqlAlchemyCredencialRepository(session)
    repo.save(Credencial.definir(usuario_id=usuario_id, segredo="Senha forte 123"))
    session.commit()

    with pytest.raises(IntegrityError):
        repo.save(Credencial.definir(usuario_id=usuario_id, segredo="Outra senha forte 123"))
    session.rollback()


def test_sessao_repository_round_trip_e_buscas(session: Session) -> None:
    tenant_id, usuario_id = _usuario_persistido(session)
    agora = datetime(2026, 8, 8, 12, tzinfo=UTC)
    repo = SqlAlchemySessaoRepository(session)
    sessao = Sessao.iniciar(
        usuario_id=usuario_id,
        tenant_id=tenant_id,
        refresh_token="refresh-token",
        agora=agora,
    )
    sessao.revogar(agora + timedelta(hours=1))

    repo.save(sessao)
    session.commit()

    por_id = repo.find_by_id(sessao.id)
    por_usuario = repo.find_by_usuario_id(usuario_id)
    por_tenant = repo.find_by_tenant_id(tenant_id)

    assert por_id is not None
    assert por_id.revogado_em == agora + timedelta(hours=1)
    assert not por_id.ativa(agora + timedelta(hours=2))
    assert [s.id for s in por_usuario] == [sessao.id]
    assert [s.id for s in por_tenant] == [sessao.id]


def test_permissao_repository_round_trip(session: Session) -> None:
    repo = SqlAlchemyPermissaoRepository(session)
    permissao = Permissao(codigo="DEVEDOR.LER", descricao="Consultar devedores")

    repo.save(permissao)
    session.commit()

    carregada = repo.find_by_codigo("devedor.ler")

    assert carregada == Permissao(codigo="devedor.ler", descricao="Consultar devedores")
    assert repo.find_all() == [carregada]


def test_perfil_acesso_repository_round_trip_com_permissoes(session: Session) -> None:
    tenant_id, _ = _usuario_persistido(session)
    repo = SqlAlchemyPerfilAcessoRepository(session)
    perfil = PerfilAcesso(tenant_id=tenant_id, nome="Administrador")
    perfil.adicionar_permissao(Permissao(codigo="tenant.ler", descricao="Consultar tenants"))
    perfil.adicionar_permissao(Permissao(codigo="usuario.gerir", descricao="Gerir usuarios"))

    repo.save(perfil)
    session.commit()

    carregado = repo.find_by_tenant_nome(tenant_id, "Administrador")

    assert carregado is not None
    assert carregado.id == perfil.id
    assert carregado.estado is PerfilState.ATIVO
    assert {p.codigo for p in carregado.permissoes} == {"tenant.ler", "usuario.gerir"}
    assert carregado.permite("tenant.ler")
    assert [p.id for p in repo.find_by_tenant_id(tenant_id)] == [perfil.id]


def test_perfil_acesso_repository_substitui_permissoes(session: Session) -> None:
    tenant_id, _ = _usuario_persistido(session)
    repo = SqlAlchemyPerfilAcessoRepository(session)
    perfil = PerfilAcesso(tenant_id=tenant_id, nome="Operador")
    perfil.adicionar_permissao(Permissao(codigo="devedor.ler", descricao="Consultar devedores"))
    perfil.adicionar_permissao(Permissao(codigo="devedor.criar", descricao="Criar devedores"))
    repo.save(perfil)
    session.commit()

    perfil.remover_permissao("devedor.criar")
    repo.save(perfil)
    session.commit()

    carregado = repo.find_by_id(perfil.id)

    assert carregado is not None
    assert [p.codigo for p in carregado.permissoes] == ["devedor.ler"]


def test_perfil_acesso_repository_isola_por_tenant(session: Session) -> None:
    tenant_a, _ = _usuario_persistido(session)
    tenant_b, _ = _usuario_persistido(session)
    repo = SqlAlchemyPerfilAcessoRepository(session)
    perfil_a = PerfilAcesso(tenant_id=tenant_a, nome="Operador")
    perfil_b = PerfilAcesso(tenant_id=tenant_b, nome="Operador")

    repo.save(perfil_a)
    repo.save(perfil_b)
    session.commit()

    assert repo.find_by_tenant_nome(tenant_a, "Operador") is not None
    assert repo.find_by_tenant_nome(tenant_b, "Operador") is not None
    assert {p.id for p in repo.find_by_tenant_id(tenant_a)} == {perfil_a.id}


def test_perfil_acesso_repository_traduz_colisao_de_nome(session: Session) -> None:
    tenant_id, _ = _usuario_persistido(session)
    repo = SqlAlchemyPerfilAcessoRepository(session)
    repo.save(PerfilAcesso(tenant_id=tenant_id, nome="Operador"))
    session.commit()

    with pytest.raises(PerfilJaExisteError):
        repo.save(PerfilAcesso(tenant_id=tenant_id, nome="Operador"))
    session.rollback()


def test_perfil_acesso_repository_rejeita_vinculo_cross_tenant(session: Session) -> None:
    _, usuario_id = _usuario_persistido(session)
    outro_tenant_id, _ = _usuario_persistido(session)
    repo = SqlAlchemyPerfilAcessoRepository(session)
    perfil = PerfilAcesso(tenant_id=outro_tenant_id, nome="Operador")
    repo.save(perfil)
    session.commit()

    with pytest.raises(ViolacaoInvarianteError, match="mesmo Tenant"):
        repo.atribuir_usuario(usuario_id, perfil.id)

    assert repo.find_by_usuario_id(usuario_id) is None


def test_token_ativacao_so_pode_ser_consumido_por_uma_transacao(
    session: Session,
    session_factory: sessionmaker[Session],
) -> None:
    tenant_id, usuario_id = _usuario_persistido(session)
    token = TokenAtivacao.emitir(
        usuario_id=usuario_id,
        tenant_id=tenant_id,
        segredo="segredo-descartavel",
    )
    SqlAlchemyTokenAtivacaoRepository(session).save(token)
    session.commit()

    primeira_bloqueou = Event()
    liberar_primeira = Event()
    segunda_iniciou_leitura = Event()

    def consumir_primeiro() -> bool:
        with session_factory() as sessao_worker:
            repo = SqlAlchemyTokenAtivacaoRepository(sessao_worker)
            carregado = repo.find_by_id(token.id)
            assert carregado is not None
            assert carregado.valido("segredo-descartavel")
            primeira_bloqueou.set()
            assert liberar_primeira.wait(timeout=5)
            carregado.utilizar()
            repo.save(carregado)
            sessao_worker.commit()
            return True

    def consumir_segundo() -> bool:
        assert primeira_bloqueou.wait(timeout=5)
        with session_factory() as sessao_worker:
            repo = SqlAlchemyTokenAtivacaoRepository(sessao_worker)
            segunda_iniciou_leitura.set()
            carregado = repo.find_by_id(token.id)
            assert carregado is not None
            return carregado.valido("segredo-descartavel")

    with ThreadPoolExecutor(max_workers=2) as executor:
        primeiro = executor.submit(consumir_primeiro)
        segundo = executor.submit(consumir_segundo)
        assert segunda_iniciou_leitura.wait(timeout=5)
        sleep(0.2)
        assert not segundo.done()
        liberar_primeira.set()

    assert primeiro.result() is True
    assert segundo.result() is False


def test_iam_repositories_respeitam_fks(session: Session) -> None:
    repo = SqlAlchemySessaoRepository(session)
    sessao = Sessao.iniciar(
        usuario_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        refresh_token="refresh-token",
    )

    with pytest.raises(IntegrityError):
        repo.save(sessao)
    session.rollback()


def _usuario_persistido(session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(tenant_id=tenant.id)
    SqlAlchemyUsuarioRepository(session).save(usuario)
    session.commit()
    return tenant.id, usuario.id
