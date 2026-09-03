"""Contratos HTTP da conexao de WhatsApp (IMP-368, PLAN-034).

O que estes testes protegem:

1. **RBAC de verdade**: `whatsapp.conexao.ler` NAO autoriza conectar nem apagar.
   Duas permissoes existem justamente para separar consultar de mexer;
2. **desconectar != excluir**: sao rotas diferentes porque sao intencoes
   diferentes, e a de excluir chega ao provedor;
3. **o nome da instancia nao entra pelo contrato**: o `POST` nao tem corpo. Um
   campo digitavel transformaria erro de digitacao em segunda instancia — nao
   pareada — no provedor.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.application.autenticacao import HmacAccessTokenService
from emprestimo.application.conexao_whatsapp import (
    ConectarWhatsApp,
    ConsultarConexaoWhatsApp,
    DesconectarWhatsApp,
    ExcluirConexaoWhatsApp,
)
from emprestimo.application.ports import AuditoriaRegistro
from emprestimo.domain.platform.conexao_whatsapp import EstadoPareamento
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.domain.platform.permissao import Permissao
from emprestimo.domain.platform.ports import ProvedorWhatsApp
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.cifra import ENV_CHAVE, CifraToken
from emprestimo.infrastructure.db.session import get_session_factory
from emprestimo.infrastructure.repositories import (
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

JWT_SECRET = "segredo-api-whatsapp-conexao"
QRCODE = "data:image/png;base64,iVBORw0KGgo="
LER = "whatsapp.conexao.ler"
GERIR = "whatsapp.conexao.gerir"
ROTA = "/platform/whatsapp/conexao"
ROTA_INSTANCIA = "/platform/whatsapp/conexao/instancia"


class _ProvedorStub(ProvedorWhatsApp):
    """Dubles das quatro operacoes, registrando o que foi chamado."""

    def __init__(self, *, pareado: bool = False) -> None:
        self._pareado = pareado
        self.criadas: list[str] = []
        self.excluidas: list[str] = []
        self.desconectadas: list[str] = []
        # Conta os pedidos de QR: o guardrail do IMP-368 e a AUSENCIA de chamada
        # no caminho de leitura, e um campo nulo no corpo nao provaria isso.
        self.qrcodes_pedidos = 0

    def instancia_existente(self, nome: str) -> tuple[str, str] | None:
        return None

    def criar_instancia(self, nome: str) -> tuple[str, str]:
        self.criadas.append(nome)
        return "instancia-stub", "token-stub"

    def conectar(self, token: str) -> None: ...

    def qrcode(self, token: str) -> str:
        self.qrcodes_pedidos += 1
        return QRCODE

    def estado(self, token: str, instancia_id: str) -> EstadoPareamento:
        return EstadoPareamento(
            conectado=self._pareado,
            pareado=self._pareado,
            nome_exibicao="Barbosa" if self._pareado else None,
            numero="556299999999" if self._pareado else None,
        )

    def desconectar(self, token: str) -> None:
        self.desconectadas.append(token)

    def excluir_instancia(self, instancia_id: str) -> None:
        self.excluidas.append(instancia_id)


@dataclass(frozen=True)
class _Autenticado:
    usuario: Usuario
    tenant: Tenant
    token: str


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(dependencies.JWT_SECRET_ENV, JWT_SECRET)


@pytest.fixture(autouse=True)
def chave_de_cifra(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cifra vem do ambiente, e nao ha modo degradado (IMP-364).

    Definida aqui, e nao herdada do shell: um teste que so passa quando a
    variavel ja existe na maquina passa por sorte.
    """
    monkeypatch.setenv(ENV_CHAVE, CifraToken.gerar_chave())


@pytest.fixture
def provedor() -> _ProvedorStub:
    return _ProvedorStub()


@pytest.fixture
def client(provedor: _ProvedorStub) -> Iterator[TestClient]:
    """App com os casos de uso montados sobre o provedor dublado.

    Os providers reais chamam `get_provedor_whatsapp()` por dentro — e nao por
    `Depends` —, entao o override tem de ser no caso de uso, nao no provedor.
    """
    app = create_app()

    def _uow() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(get_session_factory())

    def _auditoria() -> AuditoriaRegistro:
        return SqlAlchemyAuditoriaRegistro(get_session_factory())

    app.dependency_overrides[dependencies.get_consultar_conexao_whatsapp] = (
        lambda: ConsultarConexaoWhatsApp(_uow, provedor, _auditoria())
    )
    app.dependency_overrides[dependencies.get_conectar_whatsapp] = lambda: ConectarWhatsApp(
        _uow, provedor, _auditoria()
    )
    app.dependency_overrides[dependencies.get_desconectar_whatsapp] = lambda: DesconectarWhatsApp(
        _uow, provedor, _auditoria()
    )
    app.dependency_overrides[dependencies.get_excluir_conexao_whatsapp] = (
        lambda: ExcluirConexaoWhatsApp(_uow, provedor, _auditoria())
    )
    with TestClient(app) as c:
        yield c


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _autenticar(
    session: Session,
    *permissoes: str,
    tenant: Tenant | None = None,
    perfil_nome: str = "OperadorWhatsApp",
) -> _Autenticado:
    """Principal novo. `tenant=` reusa um existente em vez de criar outro.

    Reusar importa quando o teste precisa de DOIS principais com permissoes
    diferentes olhando a MESMA conexao — sem isso cada um cai no seu Tenant e o
    segundo nao ve nada, o que faria um teste de permissao passar por engano.
    """
    if tenant is None:
        tenant = TenantFactory.build(estado=TenantState.ATIVO)
        SqlAlchemyTenantRepository(session).save(tenant)
    usuario = UsuarioFactory.build(
        tenant_id=tenant.id,
        estado=UsuarioState.ATIVO,
        perfil_acesso=perfil_nome,
    )
    SqlAlchemyUsuarioRepository(session).save(usuario)
    perfil = PerfilAcesso(tenant_id=tenant.id, nome=perfil_nome)
    for codigo in permissoes:
        perfil.adicionar_permissao(Permissao(codigo=codigo, descricao=codigo))
    repo = SqlAlchemyPerfilAcessoRepository(session)
    repo.save(perfil)
    repo.atribuir_usuario(usuario.id, perfil.id)
    session.commit()
    return _Autenticado(
        usuario=usuario,
        tenant=tenant,
        token=HmacAccessTokenService(JWT_SECRET).emitir(usuario).token,
    )


@pytest.mark.parametrize(
    ("metodo", "rota"),
    [
        ("get", ROTA),
        ("post", ROTA),
        ("delete", ROTA),
        ("delete", ROTA_INSTANCIA),
    ],
)
def test_sem_token_responde_401(
    client: TestClient,
    session: Session,
    metodo: str,
    rota: str,
) -> None:
    # `session` nao e usada aqui, e mesmo assim e obrigatoria: e ela que cria o
    # schema descartavel. Sem isso a recusa e auditada contra um banco vazio, o
    # INSERT em `audit_log` estoura, e o 401 vira 500 — a rota parece quebrada
    # quando o que faltou foi a tabela.
    del session

    resposta = client.request(metodo.upper(), rota)

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "autenticacao_recusada"


@pytest.mark.parametrize(
    ("metodo", "rota"),
    [
        ("get", ROTA),
        ("post", ROTA),
        ("delete", ROTA),
        ("delete", ROTA_INSTANCIA),
    ],
)
def test_sem_permissao_responde_403(
    client: TestClient,
    session: Session,
    metodo: str,
    rota: str,
) -> None:
    autenticado = _autenticar(session)

    resposta = client.request(metodo.upper(), rota, headers=_headers(autenticado.token))

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "acesso_negado"


@pytest.mark.parametrize(
    ("metodo", "rota"),
    [
        ("post", ROTA),
        ("delete", ROTA),
        ("delete", ROTA_INSTANCIA),
    ],
)
def test_permissao_de_leitura_nao_autoriza_mexer(
    client: TestClient,
    session: Session,
    provedor: _ProvedorStub,
    metodo: str,
    rota: str,
) -> None:
    """Duas permissoes existem para separar consultar de mexer.

    Se `ler` autorizasse conectar, o catalogo teria uma permissao a mais e
    nenhuma protecao a mais.
    """
    autenticado = _autenticar(session, LER)

    resposta = client.request(metodo.upper(), rota, headers=_headers(autenticado.token))

    assert resposta.status_code == 403
    assert provedor.criadas == []
    assert provedor.excluidas == []


def test_consultar_sem_instancia_nao_e_o_mesmo_que_nao_pareada(
    client: TestClient,
    session: Session,
) -> None:
    autenticado = _autenticar(session, LER)

    resposta = client.get(ROTA, headers=_headers(autenticado.token))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["existe"] is False
    assert corpo["pareada"] is False
    assert corpo["numero"] is None


def test_consulta_com_pareamento_pendente_nao_entrega_o_qr_a_quem_so_le(
    client: TestClient,
    session: Session,
    provedor: _ProvedorStub,
) -> None:
    """Escalada de privilegio pega em review: `ler` nao pode virar `gerir`.

    O QR nao e informacao, e **capacidade**: quem o escaneia vincula uma conta de
    WhatsApp ao Tenant. Enquanto ele viajava na consulta, um principal com apenas
    `whatsapp.conexao.ler` alterava a conexao so de olhar a tela — a permissao
    `gerir` existia e nao protegia nada neste caminho.

    O estado exercitado e o UNICO em que havia QR a vazar: instancia existente e
    pareamento PENDENTE. Um teste em conexao ausente passaria mesmo com o defeito
    de volta.
    """
    gerente = _autenticar(session, GERIR)
    assert client.post(ROTA, headers=_headers(gerente.token)).status_code == 200
    provedor.qrcodes_pedidos = 0

    # MESMO Tenant, outro perfil: e a permissao que muda, nao o escopo de dados.
    so_le = _autenticar(session, LER, tenant=gerente.tenant, perfil_nome="SomenteLeitura")
    resposta = client.get(ROTA, headers=_headers(so_le.token))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["existe"] is True
    assert corpo["pareada"] is False
    # Nao basta o campo estar nulo: ele nao existe no contrato, e o provedor
    # sequer foi consultado pelo QR.
    assert "qrcode_base64" not in corpo
    assert provedor.qrcodes_pedidos == 0


def test_conectar_cria_a_instancia_e_devolve_o_qr(
    client: TestClient,
    session: Session,
    provedor: _ProvedorStub,
) -> None:
    autenticado = _autenticar(session, GERIR)

    resposta = client.post(ROTA, headers=_headers(autenticado.token))

    assert resposta.status_code == 200
    assert resposta.json() == {"qrcode_base64": QRCODE}
    # Nome derivado do Tenant, e nao um valor que alguem escolheu na chamada.
    assert provedor.criadas == [f"tianet_{autenticado.tenant.id}"]


def test_desconectar_sem_conexao_responde_404(
    client: TestClient,
    session: Session,
) -> None:
    autenticado = _autenticar(session, GERIR)

    resposta = client.delete(ROTA, headers=_headers(autenticado.token))

    assert resposta.status_code == 404


def test_excluir_sem_conexao_responde_404(
    client: TestClient,
    session: Session,
    provedor: _ProvedorStub,
) -> None:
    autenticado = _autenticar(session, GERIR)

    resposta = client.delete(ROTA_INSTANCIA, headers=_headers(autenticado.token))

    assert resposta.status_code == 404
    assert provedor.excluidas == [], "nada existe: nada a apagar la fora"


def test_excluir_apaga_a_instancia_no_provedor(
    client: TestClient,
    session: Session,
    provedor: _ProvedorStub,
) -> None:
    """Sem isto o provedor acumula instancia morta e nada no sistema a remove."""
    # As duas permissoes: a consulta final do teste passa por `ler`.
    autenticado = _autenticar(session, LER, GERIR)
    client.post(ROTA, headers=_headers(autenticado.token))

    resposta = client.delete(ROTA_INSTANCIA, headers=_headers(autenticado.token))

    assert resposta.status_code == 200
    assert resposta.json()["existe"] is False
    assert provedor.excluidas == ["instancia-stub"]
    # E de verdade: a consulta seguinte volta ao ponto de partida.
    assert client.get(ROTA, headers=_headers(autenticado.token)).json()["existe"] is False


def test_desconectar_nao_apaga_a_instancia(
    client: TestClient,
    session: Session,
    provedor: _ProvedorStub,
) -> None:
    """Logout desvincula o numero; reconectar deve custar um QR, nao um ciclo
    de provisionamento. Colapsar as duas operacoes destruiria o token a cada
    troca de numero."""
    autenticado = _autenticar(session, GERIR)
    client.post(ROTA, headers=_headers(autenticado.token))

    resposta = client.delete(ROTA, headers=_headers(autenticado.token))

    assert resposta.status_code == 200
    assert provedor.desconectadas == ["token-stub"]
    assert provedor.excluidas == [], "desconectar nao pode apagar a instancia"


def test_contrato_nao_aceita_nome_de_instancia() -> None:
    """Guardrail no contrato publico, nao so na assinatura interna.

    Um corpo aqui seria um campo digitavel, e um caractere diferente faria a
    adocao nao achar nada, o `create` rodar, e nascer uma segunda instancia nao
    pareada — com o WhatsApp do operador ligado na primeira.
    """
    schema = create_app().openapi()
    operacao = schema["paths"][ROTA]["post"]

    assert "requestBody" not in operacao
    # `X-Correlation-ID` e o unico parametro aceito, e ele e de observabilidade.
    # Qualquer outro seria uma porta para o nome voltar a entrar por fora.
    assert [p["name"] for p in operacao.get("parameters", [])] == ["X-Correlation-ID"]


def test_as_quatro_operacoes_estao_no_contrato() -> None:
    schema = create_app().openapi()

    assert set(schema["paths"][ROTA]) >= {"get", "post", "delete"}
    assert "delete" in schema["paths"][ROTA_INSTANCIA]
