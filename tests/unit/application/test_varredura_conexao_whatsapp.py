"""Varredura de conexao do WhatsApp pelo worker (IMP-370).

O selo da barra lateral le o BANCO. Antes desta varredura, o banco so mudava
quando alguem abria a tela de conexao — entao o selo podia ficar verde por dias
depois de o WhatsApp cair no celular. Estes testes guardam o que a varredura
promete e, principalmente, o que ela NAO grava.
"""

from __future__ import annotations

import uuid

from emprestimo.application.conexao_whatsapp import SincronizarConexoesWhatsApp
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp, EstadoPareamento
from emprestimo.domain.platform.ports import (
    ConexaoWhatsAppRepository,
    ProvedorWhatsApp,
    TenantFiltro,
    TenantOrdenacao,
    TenantPaginado,
    TenantRepository,
)
from emprestimo.domain.platform.tenant import Tenant


class _ProvedorFake(ProvedorWhatsApp):
    def __init__(
        self,
        estado: EstadoPareamento | None = None,
        erro: Exception | None = None,
    ) -> None:
        self._estado = estado or EstadoPareamento(
            conectado=True, pareado=True, nome_exibicao="Barbosa", numero="556299999999"
        )
        self._erro = erro
        self.consultas = 0

    def instancia_existente(self, nome: str) -> tuple[str, str] | None:  # pragma: no cover
        return None

    def criar_instancia(self, nome: str) -> tuple[str, str]:  # pragma: no cover
        raise AssertionError("varredura nao cria instancia")

    def conectar(self, token: str) -> None:  # pragma: no cover
        raise AssertionError("varredura nao conecta")

    def qrcode(self, token: str) -> str:  # pragma: no cover
        raise AssertionError("varredura nunca pede QR: ele e credencial")

    def estado(self, token: str, instancia_id: str) -> EstadoPareamento:
        self.consultas += 1
        if self._erro is not None:
            raise self._erro
        return self._estado

    def desconectar(self, token: str) -> None:  # pragma: no cover
        raise AssertionError("varredura nao desconecta")

    def excluir_instancia(self, instancia_id: str) -> None:  # pragma: no cover
        raise AssertionError("varredura nao exclui")


class _RepoConexaoFake(ConexaoWhatsAppRepository):
    def __init__(self, conexao: ConexaoWhatsApp | None = None, token: str | None = "tok") -> None:
        self.conexao = conexao
        self.token = token
        self.salvas: list[ConexaoWhatsApp] = []
        self.bloqueios: list[uuid.UUID] = []

    def exigir_disponibilidade(self) -> None: ...

    def bloquear_tenant(self, tenant_id: uuid.UUID) -> None:
        self.bloqueios.append(tenant_id)

    def save(self, conexao: ConexaoWhatsApp, *, token: str | None = None) -> None:
        self.conexao = conexao
        self.salvas.append(conexao)

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> ConexaoWhatsApp | None:
        return self.conexao

    def find_token(self, tenant_id: uuid.UUID) -> str | None:
        return self.token

    def delete(self, tenant_id: uuid.UUID) -> None: ...


class _RepoTenantFake(TenantRepository):
    def __init__(self, tenants: list[Tenant]) -> None:
        self._tenants = tenants

    def save(self, tenant: Tenant) -> None: ...

    def find_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:  # pragma: no cover
        return None

    def find_by_identificador_institucional(self, identificador: str) -> Tenant | None:
        return None  # pragma: no cover

    def find_all(self) -> list[Tenant]:
        return list(self._tenants)

    def find_all_paginated(
        self,
        page: int = 1,
        size: int = 20,
        ordenacao: TenantOrdenacao | None = None,
        filtro: TenantFiltro | None = None,
    ) -> TenantPaginado:  # pragma: no cover
        raise AssertionError("varredura nao pagina")


class _UoWFake(UnitOfWork):
    """Herda a ABC de proposito: o gate roda `mypy src tests`."""

    def __init__(self, conexao_whatsapp: _RepoConexaoFake, tenant: _RepoTenantFake) -> None:
        self.conexao_whatsapp = conexao_whatsapp
        self.tenant = tenant
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None: ...

    def close(self) -> None: ...

    def __enter__(self) -> _UoWFake:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            self.rollback()
        self.close()


class _AuditoriaFake(AuditoriaRegistro):
    def __init__(self) -> None:
        self.eventos: list[tuple[str, str]] = []

    def registrar(
        self,
        entidade: str,
        entidade_id: uuid.UUID | None,
        acao: str,
        status: str,
        detalhes: str | None = None,
    ) -> None:
        self.eventos.append((acao, status))


def _tenant() -> Tenant:
    return Tenant(identificador_institucional="ACME", nome="Instituicao ACME")


def _conexao(numero: str | None = None) -> ConexaoWhatsApp:
    base = ConexaoWhatsApp.criar(
        tenant_id=uuid.uuid4(), instancia_id="instancia-1", instancia_nome="tianet"
    )
    return base.parear(numero) if numero else base


def _montar(
    repo: _RepoConexaoFake, provedor: _ProvedorFake
) -> tuple[SincronizarConexoesWhatsApp, _UoWFake, _AuditoriaFake]:
    uow = _UoWFake(repo, _RepoTenantFake([_tenant()]))
    auditoria = _AuditoriaFake()
    return SincronizarConexoesWhatsApp(lambda: uow, provedor, auditoria), uow, auditoria


def test_queda_de_pareamento_e_devolvida_para_quem_chamou() -> None:
    """A queda e o insumo do aviso ativo. Sem devolve-la, o selo muda calado."""

    repo = _RepoConexaoFake(_conexao("556299999999"))
    provedor = _ProvedorFake(
        EstadoPareamento(conectado=False, pareado=False, nome_exibicao=None, numero=None)
    )
    varredura, _, _ = _montar(repo, provedor)

    quedas = varredura.executar()

    assert len(quedas) == 1
    assert quedas[0].numero_anterior == "556299999999"
    assert repo.conexao is not None and repo.conexao.pareada is False


def test_pareada_que_segue_pareada_nao_e_queda() -> None:
    """Sem isto, o aviso dispararia a cada varredura de uma conexao saudavel."""

    repo = _RepoConexaoFake(_conexao("556299999999"))
    varredura, _, _ = _montar(repo, _ProvedorFake())

    assert varredura.executar() == []


def test_pareamento_novo_e_gravado_sem_ser_queda() -> None:
    """O caminho de volta: o operador reconecta e o selo precisa acompanhar."""

    repo = _RepoConexaoFake(_conexao())
    varredura, uow, auditoria = _montar(repo, _ProvedorFake())

    quedas = varredura.executar()

    assert quedas == []
    assert repo.conexao is not None and repo.conexao.pareada is True
    assert uow.commits == 1
    assert ("varredura.pareamento", "sucesso") in auditoria.eventos


def test_falha_do_provedor_registra_na_trilha_e_nao_propaga() -> None:
    """Um provedor fora do ar nao pode derrubar o ciclo do worker."""

    repo = _RepoConexaoFake(_conexao("556299999999"))
    provedor = _ProvedorFake(erro=RuntimeError("provedor fora do ar"))
    varredura, _, auditoria = _montar(repo, provedor)

    assert varredura.executar() == []
    assert ("varredura.falha", "falha") in auditoria.eventos
    # E nao gravou nada: falha nao pode virar "desparelhamento".
    assert repo.salvas == []


def test_conexao_sem_token_e_pulada_sem_falhar() -> None:
    """Registro orfao existe e nao fala com o provedor. Pular, nao derrubar."""

    repo = _RepoConexaoFake(_conexao("556299999999"), token=None)
    provedor = _ProvedorFake()
    varredura, _, _ = _montar(repo, provedor)

    assert varredura.executar() == []
    assert provedor.consultas == 0


def test_tenant_sem_conexao_nao_consulta_o_provedor() -> None:
    """Sem conexao nao ha o que sincronizar, e a chamada externa custa."""

    repo = _RepoConexaoFake(None)
    provedor = _ProvedorFake()
    varredura, _, _ = _montar(repo, provedor)

    assert varredura.executar() == []
    assert provedor.consultas == 0


def test_varredura_bloqueia_o_tenant_antes_de_ler() -> None:
    """Mesmo lock do caminho da tela: sem ele, varredura e `connect` do operador
    gravam por cima um do outro."""

    repo = _RepoConexaoFake(_conexao("556299999999"))
    varredura, _, _ = _montar(repo, _ProvedorFake())

    varredura.executar()

    assert len(repo.bloqueios) == 1
