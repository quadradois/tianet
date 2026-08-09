from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from emprestimo.application.bootstrap_plataforma import (
    CHAVE_IDEMPOTENCIA_BOOTSTRAP,
    ESCOPO_IDEMPOTENCIA_BOOTSTRAP,
    AdministradorPlataformaBootstrap,
    AdministradorPlataformaBootstrapService,
)
from emprestimo.application.errors import IdempotenciaConflitoError, PerfilConflitoError
from emprestimo.application.ports import AuditoriaRegistro, IdempotenciaRegistro, UnitOfWork
from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.tenant import TenantState


@dataclass
class _IdempotenciaFake(IdempotenciaRegistro):
    registros: dict[tuple[str, str], dict[str, object]] = field(default_factory=dict)

    def registrar(self, chave: str, escopo: str, solicitacao_hash: str) -> None:
        self.registros[(chave, escopo)] = {
            "estado": "running",
            "solicitacao_hash": solicitacao_hash,
            "resultado": None,
        }

    def find_by_chave(self, chave: str, escopo: str) -> dict[str, object] | None:
        return self.registros.get((chave, escopo))

    def concluir(self, chave: str, escopo: str, resultado: str) -> None:
        self.registros[(chave, escopo)]["estado"] = "finished"
        self.registros[(chave, escopo)]["resultado"] = resultado


@dataclass
class _AuditoriaFake(AuditoriaRegistro):
    eventos: list[tuple[str, str, str | None]] = field(default_factory=list)

    def registrar(
        self,
        entidade: str,
        entidade_id: uuid.UUID | None,
        acao: str,
        status: str,
        detalhes: str | None = None,
    ) -> None:
        del entidade, entidade_id
        self.eventos.append((acao, status, detalhes))


@dataclass
class _RepoFake:
    salvos: list[Any] = field(default_factory=list)
    atribuicoes: list[tuple[uuid.UUID, uuid.UUID]] = field(default_factory=list)
    tenant_existente: object | None = None
    permissao_existente: bool = False

    def save(self, entidade: object) -> None:
        self.salvos.append(entidade)

    def atribuir_usuario(self, usuario_id: uuid.UUID, perfil_id: uuid.UUID) -> None:
        self.atribuicoes.append((usuario_id, perfil_id))

    def find_by_identificador_institucional(self, identificador: str) -> object | None:
        del identificador
        return self.tenant_existente

    def exists_with_permission(self, codigo: str) -> bool:
        assert codigo == "tenant.criar"
        return self.permissao_existente

    def tenant_has_permission(self, tenant_id: uuid.UUID, codigo: str) -> bool:
        del tenant_id, codigo
        return self.permissao_existente

    def find_by_id(self, entidade_id: uuid.UUID) -> Any | None:
        return next((item for item in reversed(self.salvos) if item.id == entidade_id), None)

    def find_by_usuario_id(self, usuario_id: uuid.UUID) -> Any | None:
        direto = next(
            (
                item
                for item in reversed(self.salvos)
                if getattr(item, "usuario_id", None) == usuario_id
            ),
            None,
        )
        if direto is not None:
            return direto
        perfil_id = next(
            (perfil for usuario, perfil in self.atribuicoes if usuario == usuario_id),
            None,
        )
        return self.find_by_id(perfil_id) if perfil_id is not None else None


@dataclass
class _UoWFake(UnitOfWork):
    idempotencia: _IdempotenciaFake = field(default_factory=_IdempotenciaFake)
    tenant: _RepoFake = field(default_factory=_RepoFake)  # type: ignore[assignment]
    usuario: _RepoFake = field(default_factory=_RepoFake)  # type: ignore[assignment]
    configuracao: _RepoFake = field(default_factory=_RepoFake)  # type: ignore[assignment]
    carteira: _RepoFake = field(default_factory=_RepoFake)  # type: ignore[assignment]
    perfil_acesso: _RepoFake = field(default_factory=_RepoFake)  # type: ignore[assignment]
    credencial: _RepoFake = field(default_factory=_RepoFake)  # type: ignore[assignment]
    token_ativacao: _RepoFake = field(default_factory=_RepoFake)  # type: ignore[assignment]
    commit_count: int = 0
    rollback_count: int = 0
    falhar_commit: bool = False

    def commit(self) -> None:
        if self.falhar_commit:
            raise RuntimeError("commit recusado")
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        return None


def _executar(
    service: AdministradorPlataformaBootstrapService,
    *,
    email: str = "root@plataforma.local",
    segredo: str = "Credencial Inicial Forte 123",
) -> AdministradorPlataformaBootstrap:
    return service.executar(
        identificador_institucional="PLATAFORMA-CONTROLE",
        nome_tenant="Controle da Plataforma",
        nome_administrador="Administrador Raiz",
        email_administrador=email,
        segredo_inicial=segredo,
    )


def _contexto() -> tuple[_UoWFake, _AuditoriaFake, AdministradorPlataformaBootstrapService]:
    uow = _UoWFake()
    auditoria = _AuditoriaFake()
    return uow, auditoria, AdministradorPlataformaBootstrapService(lambda: uow, auditoria)


def test_bootstrap_cria_raiz_com_permissoes_exclusivas_de_plataforma() -> None:
    uow, auditoria, service = _contexto()

    resultado = _executar(service)

    assert resultado.estado is TenantState.ATIVO
    assert resultado.criado_agora
    usuario = uow.usuario.salvos[0]
    perfil = uow.perfil_acesso.salvos[0]
    assert usuario.perfil_acesso == "administrador_plataforma"
    assert usuario.ativo
    assert uow.credencial.salvos[0].verificar("Credencial Inicial Forte 123")
    assert {item.codigo for item in perfil.permissoes} == {
        "tenant.criar",
        "tenant.ler",
        "tenant.atualizar",
        "tenant.inativar",
        "tenant.reativar",
    }
    assert uow.perfil_acesso.atribuicoes == [(usuario.id, perfil.id)]
    assert uow.commit_count == 1
    assert "bootstrap_plataforma.sucesso" in {evento[0] for evento in auditoria.eventos}


def test_replay_nao_reexpoe_token_nem_duplica_entidades() -> None:
    uow, _, service = _contexto()

    primeiro = _executar(service)
    segundo = _executar(service)

    assert segundo.usuario_id == primeiro.usuario_id
    assert not segundo.criado_agora
    assert len(uow.usuario.salvos) == 1
    registro = uow.idempotencia.registros[
        (CHAVE_IDEMPOTENCIA_BOOTSTRAP, ESCOPO_IDEMPOTENCIA_BOOTSTRAP)
    ]
    assert "Credencial Inicial Forte 123" not in str(registro)


def test_segunda_execucao_com_payload_diferente_falha_fechado() -> None:
    _, auditoria, service = _contexto()
    _executar(service)

    with pytest.raises(IdempotenciaConflitoError):
        _executar(service, email="outro@plataforma.local")

    assert "bootstrap_plataforma.falha" in {evento[0] for evento in auditoria.eventos}


def test_registro_em_andamento_recusa_execucao_concorrente() -> None:
    uow, _, service = _contexto()
    uow.idempotencia.registros[(CHAVE_IDEMPOTENCIA_BOOTSTRAP, ESCOPO_IDEMPOTENCIA_BOOTSTRAP)] = {
        "estado": "running",
        "solicitacao_hash": "qualquer",
        "resultado": None,
    }

    with pytest.raises(IdempotenciaConflitoError, match="em andamento"):
        _executar(service)


def test_perfil_privilegiado_preexistente_falha_fechado() -> None:
    uow, _, service = _contexto()
    uow.perfil_acesso.permissao_existente = True

    with pytest.raises(PerfilConflitoError, match="ja inicializado"):
        _executar(service)

    assert uow.usuario.salvos == []


def test_falha_no_commit_aplica_rollback_e_nao_audita_segredos() -> None:
    uow, auditoria, service = _contexto()
    uow.falhar_commit = True

    with pytest.raises(RuntimeError):
        _executar(service)

    assert uow.rollback_count == 1
    assert "bootstrap_plataforma.rollback" in {evento[0] for evento in auditoria.eventos}
    assert all("Credencial Inicial Forte 123" not in str(evento) for evento in auditoria.eventos)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("identificador_institucional", " "),
        ("nome_tenant", "x" * 201),
        ("nome_administrador", ""),
        ("email_administrador", "email-invalido"),
    ],
)
def test_entrada_invalida_falha_antes_de_iniciar_uow(campo: str, valor: str) -> None:
    uow, auditoria, service = _contexto()
    payload = {
        "identificador_institucional": "PLATAFORMA-CONTROLE",
        "nome_tenant": "Controle da Plataforma",
        "nome_administrador": "Administrador Raiz",
        "email_administrador": "root@plataforma.local",
        "segredo_inicial": "Credencial Inicial Forte 123",
    }
    payload[campo] = valor

    with pytest.raises(ViolacaoInvarianteError):
        service.executar(**payload)

    assert uow.idempotencia.registros == {}
    assert auditoria.eventos == []


def test_credencial_inicial_fraca_falha_antes_de_iniciar_uow() -> None:
    uow, auditoria, service = _contexto()

    with pytest.raises(ViolacaoInvarianteError, match="pelo menos 12"):
        _executar(service, segredo="curta")

    assert uow.idempotencia.registros == {}
    assert auditoria.eventos == []


def test_replay_recusa_estado_privilegiado_corrompido() -> None:
    uow, _, service = _contexto()
    _executar(service)
    uow.credencial.salvos.clear()

    with pytest.raises(PerfilConflitoError, match="inconsistente"):
        _executar(service)


def test_falha_da_auditoria_pos_commit_nao_registra_rollback_falso() -> None:
    uow = _UoWFake()

    class _AuditoriaFalhaNoSucesso(_AuditoriaFake):
        def registrar(
            self,
            entidade: str,
            entidade_id: uuid.UUID | None,
            acao: str,
            status: str,
            detalhes: str | None = None,
        ) -> None:
            super().registrar(entidade, entidade_id, acao, status, detalhes)
            if acao == "bootstrap_plataforma.sucesso":
                raise RuntimeError("auditoria indisponivel")

    auditoria = _AuditoriaFalhaNoSucesso()
    service = AdministradorPlataformaBootstrapService(lambda: uow, auditoria)

    with pytest.raises(RuntimeError, match="auditoria indisponivel"):
        _executar(service)

    assert uow.commit_count == 1
    assert uow.rollback_count == 0
    acoes = {evento[0] for evento in auditoria.eventos}
    assert "bootstrap_plataforma.falha" not in acoes
    assert "bootstrap_plataforma.rollback" not in acoes
