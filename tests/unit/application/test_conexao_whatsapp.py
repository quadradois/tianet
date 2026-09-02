"""Casos de uso da conexão de WhatsApp (IMP-367, PLAN-034).

O que estes testes protegem, em ordem de importância:

1. **`Connected` sem `LoggedIn` não é conexão.** O Evolution reporta os dois
   separadamente, e uma instância recém-criada responde `Connected: true` com
   `LoggedIn: false` — verificado contra o servidor real em 2026-08-31. Tratar o
   primeiro como sucesso faria a tela anunciar WhatsApp ligado sem nenhum
   celular do outro lado;
2. **inexistente ≠ pendente.** As duas ausências pedem ações diferentes;
3. **o QR não entra na trilha.** Append-only: o que entra lá não sai.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

import pytest

from emprestimo.application.conexao_whatsapp import (
    ConectarWhatsApp,
    ConsultarConexaoWhatsApp,
    DesconectarWhatsApp,
)
from emprestimo.application.errors import ConexaoWhatsAppNaoEncontradaError
from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp, EstadoPareamento
from emprestimo.domain.platform.ports import QrCodeIndisponivelError

QRCODE = "data:image/png;base64,iVBORw0KGgo="
NOME = "Barbosa"
"""`Name` do provedor e o push name da conta, nao o telefone (resposta real de 2026-08-31)."""


class _ProvedorFake:
    """Provedor controlado pelo teste, contando o que foi chamado."""

    def __init__(
        self,
        estado: EstadoPareamento | None = None,
        *,
        falhar_em_qrcode: Exception | None = None,
    ) -> None:
        self._estado = estado or EstadoPareamento(
            conectado=False, pareado=False, nome_exibicao=None
        )
        self._falhar_em_qrcode = falhar_em_qrcode
        self.criadas: list[str] = []
        self.qrcodes_pedidos = 0
        self.conectadas: list[str] = []
        self.desconectadas: list[str] = []

    def criar_instancia(self, nome: str) -> tuple[str, str]:
        self.criadas.append(nome)
        return "instancia-nova", "token-novo"

    def conectar(self, token: str) -> None:
        self.conectadas.append(token)

    def qrcode(self, token: str) -> str:
        self.qrcodes_pedidos += 1
        if self._falhar_em_qrcode is not None:
            raise self._falhar_em_qrcode
        return QRCODE

    def estado(self, token: str) -> EstadoPareamento:
        return self._estado

    def desconectar(self, token: str) -> None:
        self.desconectadas.append(token)


class _RepoFake:
    def __init__(
        self,
        conexao: ConexaoWhatsApp | None = None,
        token: str | None = None,
        *,
        cifra_indisponivel: bool = False,
    ) -> None:
        self.conexao = conexao
        self.token = token
        self.gravacoes: list[tuple[ConexaoWhatsApp, str | None]] = []
        self.bloqueios: list[uuid.UUID] = []
        self._cifra_indisponivel = cifra_indisponivel

    def exigir_disponibilidade(self) -> None:
        if self._cifra_indisponivel:
            raise RuntimeError("WHATSAPP_TOKEN_ENCRYPTION_KEY ausente")

    def bloquear_tenant(self, tenant_id: uuid.UUID) -> None:
        self.bloqueios.append(tenant_id)

    def save(self, conexao: ConexaoWhatsApp, *, token: str | None = None) -> None:
        self.conexao = conexao
        if token is not None:
            self.token = token
        self.gravacoes.append((conexao, token))

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> ConexaoWhatsApp | None:
        return self.conexao

    def find_token(self, tenant_id: uuid.UUID) -> str | None:
        return self.token


@dataclass
class _UoWFake:
    conexao_whatsapp: _RepoFake
    commits: int = 0

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


@dataclass
class _AuditoriaFake:
    eventos: list[tuple[str, str, str, str | None]] = field(default_factory=list)

    def registrar(
        self,
        entidade: str,
        entidade_id: uuid.UUID | None,
        acao: str,
        status: str,
        detalhes: str | None = None,
    ) -> None:
        self.eventos.append((entidade, acao, status, detalhes))


def _conexao(identificacao: str | None = None) -> ConexaoWhatsApp:
    base = ConexaoWhatsApp.criar(
        tenant_id=uuid.uuid4(),
        instancia_id="instancia-1",
        instancia_nome="tianet",
    )
    return base.parear(identificacao) if identificacao else base


def _montar(
    repo: _RepoFake,
    provedor: _ProvedorFake,
) -> tuple[_UoWFake, _AuditoriaFake]:
    return _UoWFake(repo), _AuditoriaFake()


def test_consulta_sem_instancia_nao_e_o_mesmo_que_nao_pareada() -> None:
    """Inexistente pede criar; pendente pede escanear. A tela decide por isto."""

    repo = _RepoFake()
    uow, _ = _montar(repo, _ProvedorFake())

    estado = ConsultarConexaoWhatsApp(lambda: uow, _ProvedorFake()).executar(uuid.uuid4())

    assert estado.existe is False
    assert estado.pareada is False
    assert estado.instancia_nome is None


def test_consulta_connected_sem_loggedin_nao_conta_como_pareada() -> None:
    """O defeito que este teste existe para impedir foi observado em producao.

    Instancia recem-criada responde `Connected: true` com `LoggedIn: false`.
    """

    repo = _RepoFake(_conexao(), token="token-1")
    provedor = _ProvedorFake(EstadoPareamento(conectado=True, pareado=False, nome_exibicao=None))
    uow, _ = _montar(repo, provedor)

    estado = ConsultarConexaoWhatsApp(lambda: uow, provedor).executar(uuid.uuid4())

    assert estado.conectado is True
    assert estado.pareada is False
    assert estado.nome_exibicao is None


def test_consulta_pareada_traz_a_identificacao_do_provedor() -> None:
    repo = _RepoFake(_conexao(), token="token-1")
    provedor = _ProvedorFake(EstadoPareamento(conectado=True, pareado=True, nome_exibicao=NOME))
    uow, _ = _montar(repo, provedor)

    estado = ConsultarConexaoWhatsApp(lambda: uow, provedor).executar(uuid.uuid4())

    assert estado.pareada is True
    assert estado.nome_exibicao == NOME
    assert repo.conexao is not None and repo.conexao.numero_pareado == NOME


def test_consulta_desfaz_pareamento_quando_provedor_reporta_logout() -> None:
    """O logout pode acontecer no celular, sem passar por nos."""

    repo = _RepoFake(_conexao(NOME), token="token-1")
    provedor = _ProvedorFake(EstadoPareamento(conectado=False, pareado=False, nome_exibicao=None))
    uow, _ = _montar(repo, provedor)

    estado = ConsultarConexaoWhatsApp(lambda: uow, provedor).executar(uuid.uuid4())

    assert estado.pareada is False
    assert repo.conexao is not None and repo.conexao.numero_pareado is None


def test_consulta_pareada_sem_identificacao_preserva_o_que_ja_se_sabia() -> None:
    """Resposta incompleta nao vale apagar informacao boa."""

    repo = _RepoFake(_conexao(NOME), token="token-1")
    provedor = _ProvedorFake(EstadoPareamento(conectado=True, pareado=True, nome_exibicao=None))
    uow, _ = _montar(repo, provedor)

    estado = ConsultarConexaoWhatsApp(lambda: uow, provedor).executar(uuid.uuid4())

    assert estado.nome_exibicao == NOME
    assert repo.gravacoes == []


def test_consulta_com_conexao_sem_token_e_erro_nomeado() -> None:
    """Registro orfao: existe e nao pode falar com o provedor."""

    repo = _RepoFake(_conexao(), token=None)
    provedor = _ProvedorFake()
    uow, _ = _montar(repo, provedor)

    with pytest.raises(ConexaoWhatsAppNaoEncontradaError):
        ConsultarConexaoWhatsApp(lambda: uow, provedor).executar(uuid.uuid4())


def test_consulta_pendente_traz_o_qr_de_agora() -> None:
    """O QR vive ~20s e o provedor rotaciona sozinho.

    Devolver o da chamada anterior seria devolver um QR morto — por isso a
    consulta busca a cada vez enquanto o pareamento esta pendente.
    """

    repo = _RepoFake(_conexao(), token="token-1")
    provedor = _ProvedorFake(EstadoPareamento(conectado=True, pareado=False, nome_exibicao=None))
    uow, _ = _montar(repo, provedor)

    estado = ConsultarConexaoWhatsApp(lambda: uow, provedor).executar(uuid.uuid4())

    assert estado.qrcode_base64 == QRCODE
    assert provedor.qrcodes_pedidos == 1


def test_consulta_pareada_nao_pede_qr() -> None:
    """Ja pareado nao tem o que escanear, e pedir gastaria chamada a toa."""

    repo = _RepoFake(_conexao(NOME), token="token-1")
    provedor = _ProvedorFake(EstadoPareamento(conectado=True, pareado=True, nome_exibicao=NOME))
    uow, _ = _montar(repo, provedor)

    estado = ConsultarConexaoWhatsApp(lambda: uow, provedor).executar(uuid.uuid4())

    assert estado.qrcode_base64 is None
    assert provedor.qrcodes_pedidos == 0


def test_consulta_com_qr_ainda_gerando_devolve_none_em_vez_de_falhar() -> None:
    """E o estado normal logo apos conectar, e a tela ja faz polling."""

    repo = _RepoFake(_conexao(), token="token-1")
    provedor = _ProvedorFake(
        EstadoPareamento(conectado=True, pareado=False, nome_exibicao=None),
        falhar_em_qrcode=QrCodeIndisponivelError("no QR code available"),
    )
    uow, _ = _montar(repo, provedor)

    estado = ConsultarConexaoWhatsApp(lambda: uow, provedor).executar(uuid.uuid4())

    assert estado.qrcode_base64 is None
    assert estado.existe is True


def test_conectar_recusa_antes_de_criar_no_provedor_se_a_cifra_faltar() -> None:
    """Descobrir isso no `save` deixaria a instancia criada e o token perdido."""

    repo = _RepoFake(cifra_indisponivel=True)
    provedor = _ProvedorFake()
    uow, auditoria = _montar(repo, provedor)

    with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
        ConectarWhatsApp(lambda: uow, provedor, auditoria).executar(uuid.uuid4(), "tianet")

    assert provedor.criadas == [], "nao pode existir instancia orfa no provedor"


def test_conectar_serializa_a_criacao_pelo_tenant() -> None:
    """`UNIQUE (tenant_id)` so rejeita no commit, quando o efeito externo ja foi."""

    repo = _RepoFake()
    provedor = _ProvedorFake()
    uow, auditoria = _montar(repo, provedor)
    tenant_id = uuid.uuid4()

    ConectarWhatsApp(lambda: uow, provedor, auditoria).executar(tenant_id, "tianet")

    assert repo.bloqueios == [tenant_id]


def test_conectar_cria_instancia_quando_nao_existe_e_guarda_o_token() -> None:
    repo = _RepoFake()
    provedor = _ProvedorFake()
    uow, auditoria = _montar(repo, provedor)

    resultado = ConectarWhatsApp(lambda: uow, provedor, auditoria).executar(uuid.uuid4(), "tianet")

    assert resultado.qrcode_base64 == QRCODE
    assert provedor.criadas == ["tianet"]
    assert repo.token == "token-novo"
    assert uow.commits == 1


def test_conectar_reaproveita_instancia_existente() -> None:
    """Reconectar deve custar um QR, nao um ciclo de provisionamento."""

    repo = _RepoFake(_conexao(), token="token-1")
    provedor = _ProvedorFake()
    uow, auditoria = _montar(repo, provedor)

    ConectarWhatsApp(lambda: uow, provedor, auditoria).executar(uuid.uuid4(), "tianet")

    assert provedor.criadas == []
    assert provedor.conectadas == ["token-1"]


def test_conectar_nao_registra_o_qr_na_trilha() -> None:
    """Guardrail, nao convencao: a trilha e append-only."""

    repo = _RepoFake()
    provedor = _ProvedorFake()
    uow, auditoria = _montar(repo, provedor)

    ConectarWhatsApp(lambda: uow, provedor, auditoria).executar(uuid.uuid4(), "tianet")

    assert auditoria.eventos, "nenhum evento registrado"
    for _, _, _, detalhes in auditoria.eventos:
        assert QRCODE not in (detalhes or "")
        assert "token-novo" not in (detalhes or "")


def test_conectar_registra_autoria_em_todo_evento() -> None:
    """IMP-361: inicio, sucesso e falha carregam o mesmo Principal."""

    usuario_id = uuid.uuid4()
    repo = _RepoFake()
    provedor = _ProvedorFake()
    uow, auditoria = _montar(repo, provedor)

    ConectarWhatsApp(lambda: uow, provedor, auditoria).executar(
        uuid.uuid4(), "tianet", usuario_id=usuario_id
    )

    assert len(auditoria.eventos) == 2
    for _, _, _, detalhes in auditoria.eventos:
        assert json.loads(detalhes or "{}")["usuario_id"] == str(usuario_id)


def test_conectar_falha_registra_so_o_tipo_do_erro() -> None:
    """A mensagem do provedor pode carregar token ou QR."""

    repo = _RepoFake()
    provedor = _ProvedorFake(falhar_em_qrcode=RuntimeError(f"falhou com {QRCODE}"))
    uow, auditoria = _montar(repo, provedor)

    with pytest.raises(RuntimeError):
        ConectarWhatsApp(lambda: uow, provedor, auditoria).executar(uuid.uuid4(), "tianet")

    assert [e[1] for e in auditoria.eventos] == [
        "conectar.inicio",
        "conectar.falha",
        "conectar.rollback",
    ]
    falha = [e for e in auditoria.eventos if e[1] == "conectar.falha"]
    assert len(falha) == 1
    detalhes = json.loads(falha[0][3] or "{}")
    assert detalhes["erro_tipo"] == "RuntimeError"
    assert QRCODE not in (falha[0][3] or "")


def test_conectar_com_qr_ainda_gerando_devolve_pendente_em_vez_de_falhar() -> None:
    """O caminho mais provavel logo apos conectar nao pode parecer erro.

    O contrato descreve a corrida: o provedor responde "no QR code available"
    e manda esperar 3s e repetir, ate 5 vezes. A tela ja faz polling.
    """

    repo = _RepoFake()
    provedor = _ProvedorFake(falhar_em_qrcode=QrCodeIndisponivelError("no QR code available"))
    uow, auditoria = _montar(repo, provedor)

    resultado = ConectarWhatsApp(lambda: uow, provedor, auditoria).executar(uuid.uuid4(), "tianet")

    assert resultado.qrcode_base64 is None
    assert repo.conexao is not None, "a instancia tem de ficar gravada"
    assert [e[1] for e in auditoria.eventos] == ["conectar.inicio", "conectar.sucesso"]


def test_qr_indisponivel_nao_apaga_a_instancia_ja_criada() -> None:
    """O caso mais provavel de todos, e o que mais custava caro.

    `qrcode()` levantar "ainda gerando" e estado NORMAL logo apos o `connect` —
    o contrato manda esperar 3s e repetir, ate 5 vezes. Se essa excecao
    desfizesse a transacao, a conexao local sumiria enquanto a instancia
    continuaria existindo no provedor, com um token que so nos tinhamos. A cada
    tentativa nasceria outra instancia orfa e inalcancavel.
    """

    repo = _RepoFake()
    provedor = _ProvedorFake(falhar_em_qrcode=RuntimeError("no QR code available"))
    uow, auditoria = _montar(repo, provedor)
    caso = ConectarWhatsApp(lambda: uow, provedor, auditoria)

    with pytest.raises(RuntimeError):
        caso.executar(uuid.uuid4(), "tianet")

    assert repo.conexao is not None, "a instancia criada no provedor tem de sobreviver"
    assert repo.token == "token-novo"

    # A segunda tentativa reaproveita — nao cria uma instancia nova.
    with pytest.raises(RuntimeError):
        caso.executar(uuid.uuid4(), "tianet")

    assert provedor.criadas == ["tianet"]


def test_desconectar_mantem_a_instancia_e_so_desvincula_a_conta() -> None:
    conexao = _conexao(NOME)
    repo = _RepoFake(conexao, token="token-1")
    provedor = _ProvedorFake()
    uow, auditoria = _montar(repo, provedor)

    estado = DesconectarWhatsApp(lambda: uow, provedor, auditoria).executar(uuid.uuid4())

    assert estado.existe is True
    assert estado.pareada is False
    assert estado.nome_exibicao is None
    assert provedor.desconectadas == ["token-1"]
    assert repo.conexao is not None
    assert repo.conexao.instancia_id == conexao.instancia_id
    assert repo.token == "token-1", "o token nao pode ser apagado no logout"


def test_desconectar_sem_conexao_e_erro_nomeado() -> None:
    repo = _RepoFake()
    provedor = _ProvedorFake()
    uow, auditoria = _montar(repo, provedor)

    with pytest.raises(ConexaoWhatsAppNaoEncontradaError):
        DesconectarWhatsApp(lambda: uow, provedor, auditoria).executar(uuid.uuid4())

    assert provedor.desconectadas == []
    # ADR-002: falha diz que deu errado, rollback diz que nada ficou meio
    # gravado. Quem le a trilha precisa dos dois para saber se sobrou estado.
    assert [e[1] for e in auditoria.eventos] == [
        "desconectar.inicio",
        "desconectar.falha",
        "desconectar.rollback",
    ]
