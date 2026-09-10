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


def _estado_queda() -> EstadoPareamento:
    return EstadoPareamento(conectado=False, pareado=False, nome_exibicao=None, numero=None)


def test_varredura_queda_persiste_instante_antes_do_commit() -> None:
    """Borda observada pelo worker grava número None e instante na mesma UoW."""

    repo = _RepoConexaoFake(_conexao("556299999999"))
    varredura, uow, _ = _montar(repo, _ProvedorFake(_estado_queda()))

    quedas = varredura.executar()

    assert len(quedas) == 1
    assert repo.conexao is not None
    assert repo.conexao.numero_pareado is None
    assert repo.conexao.queda_detectada_em is not None
    assert repo.conexao.queda_detectada_em.tzinfo is not None
    assert len(repo.salvas) == 1
    assert repo.salvas[0].queda_detectada_em is not None
    assert uow.commits == 1


def test_varredura_observa_ordem_lock_leitura_save_commit() -> None:
    """A queda é salva sob o lock e antes do commit, nunca depois."""

    repo = _RepoConexaoFake(_conexao("556299999999"))
    provedor = _ProvedorFake(_estado_queda())
    varredura, uow, _ = _montar(repo, provedor)
    eventos: list[str] = []
    bloquear_orig = repo.bloquear_tenant
    estado_orig = provedor.estado
    save_orig = repo.save
    commit_orig = uow.commit

    def bloquear(tenant_id: uuid.UUID) -> None:
        eventos.append("lock")
        bloquear_orig(tenant_id)

    def estado(token: str, instancia_id: str) -> EstadoPareamento:
        eventos.append("leitura")
        return estado_orig(token, instancia_id)

    def save(conexao: ConexaoWhatsApp, *, token: str | None = None) -> None:
        eventos.append("save")
        save_orig(conexao, token=token)

    def commit() -> None:
        eventos.append("commit")
        commit_orig()

    repo.bloquear_tenant = bloquear  # type: ignore[method-assign]
    provedor.estado = estado  # type: ignore[method-assign]
    repo.save = save  # type: ignore[method-assign]
    uow.commit = commit  # type: ignore[method-assign]

    varredura.executar()

    assert eventos == ["lock", "leitura", "save", "commit"]


def test_varredura_permanencia_preserva_primeiro_instante_sem_reemitir() -> None:
    """Segundo ciclo desconectado não move o instante nem devolve nova queda."""

    repo = _RepoConexaoFake(_conexao("556299999999"))
    provedor = _ProvedorFake(_estado_queda())
    varredura, _, _ = _montar(repo, provedor)

    assert len(varredura.executar()) == 1
    assert repo.conexao is not None
    primeiro = repo.conexao.queda_detectada_em
    assert primeiro is not None

    assert varredura.executar() == []
    assert repo.conexao is not None
    assert repo.conexao.queda_detectada_em == primeiro
    assert len(repo.salvas) == 1


def test_varredura_recuperacao_limpa_o_alerta() -> None:
    """Pareamento confirmado no ciclo limpa o instante automaticamente."""

    base = _conexao("556299999999").registrar_queda()
    assert base.queda_detectada_em is not None
    repo = _RepoConexaoFake(base)
    varredura, _, _ = _montar(repo, _ProvedorFake())

    assert varredura.executar() == []
    assert repo.conexao is not None
    assert repo.conexao.pareada is True
    assert repo.conexao.queda_detectada_em is None
    assert len(repo.salvas) == 1


def test_varredura_falha_nao_cria_nem_limpa_alerta() -> None:
    """Provedor fora do ar não inventa queda nem apaga a existente."""

    repo_sem = _RepoConexaoFake(_conexao("556299999999"))
    varredura_sem, _, _ = _montar(repo_sem, _ProvedorFake(erro=RuntimeError("fora")))
    assert varredura_sem.executar() == []
    assert repo_sem.salvas == []
    assert repo_sem.conexao is not None
    assert repo_sem.conexao.queda_detectada_em is None

    base = _conexao("556299999999").registrar_queda()
    instante = base.queda_detectada_em
    repo_com = _RepoConexaoFake(base)
    varredura_com, _, _ = _montar(repo_com, _ProvedorFake(erro=RuntimeError("fora")))
    assert varredura_com.executar() == []
    assert repo_com.salvas == []
    assert repo_com.conexao is not None
    assert repo_com.conexao.queda_detectada_em == instante


def test_varredura_isola_queda_por_tenant() -> None:
    """Queda de um tenant não marca nem desmarca o outro."""

    tenants = [_tenant(), _tenant()]
    ids = [t.id for t in tenants]
    numero_ok = "556288888888"
    conexoes: dict[uuid.UUID, ConexaoWhatsApp] = {
        ids[0]: ConexaoWhatsApp.criar(
            tenant_id=ids[0], instancia_id="inst-queda", instancia_nome="tianet"
        ).parear("556299999999"),
        ids[1]: ConexaoWhatsApp.criar(
            tenant_id=ids[1], instancia_id="inst-ok", instancia_nome="tianet"
        ).parear(numero_ok),
    }
    tokens: dict[uuid.UUID, str] = {ids[0]: "tok-queda", ids[1]: "tok-ok"}
    repo = _RepoConexaoFake(conexoes[ids[0]])
    provedor = _ProvedorFake()

    def find(tenant_id: uuid.UUID) -> ConexaoWhatsApp | None:
        return conexoes.get(tenant_id)

    def find_token(tenant_id: uuid.UUID) -> str | None:
        return tokens.get(tenant_id)

    def save(conexao: ConexaoWhatsApp, *, token: str | None = None) -> None:
        conexoes[conexao.tenant_id] = conexao
        repo.salvas.append(conexao)
        repo.conexao = conexao

    def estado(token: str, instancia_id: str) -> EstadoPareamento:
        provedor.consultas += 1
        if instancia_id == "inst-queda":
            return _estado_queda()
        return EstadoPareamento(
            conectado=True, pareado=True, nome_exibicao="Barbosa", numero=numero_ok
        )

    repo.find_by_tenant_id = find  # type: ignore[method-assign]
    repo.find_token = find_token  # type: ignore[method-assign]
    repo.save = save  # type: ignore[method-assign]
    provedor.estado = estado  # type: ignore[method-assign]
    uow = _UoWFake(repo, _RepoTenantFake(tenants))
    auditoria = _AuditoriaFake()
    varredura = SincronizarConexoesWhatsApp(lambda: uow, provedor, auditoria)

    quedas = varredura.executar()

    assert len(quedas) == 1
    assert quedas[0].tenant_id == ids[0]
    assert conexoes[ids[0]].queda_detectada_em is not None
    assert conexoes[ids[0]].numero_pareado is None
    assert conexoes[ids[1]].queda_detectada_em is None
    assert conexoes[ids[1]].numero_pareado == numero_ok
