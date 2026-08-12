"""Testes de contrato HTTP dos endpoints de Devedor (IMP-057, IMP-058, IMP-059).

Os casos de uso são substituídos por dublês via ``dependency_overrides``: o que
se verifica aqui é exclusivamente a camada Presentation — códigos de status,
serialização do DTO único (RA-012), validação de fronteira e a tradução de
exceções de domínio/aplicação feita pelos handlers do ``main.py``.

Não há banco de dados envolvido; a persistência é coberta pelos testes de
integração (IMP-061/062).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from starlette.testclient import TestClient

from emprestimo.application.autorizacao import Principal
from emprestimo.application.cadastro_devedor import DevedorCriado
from emprestimo.application.errors import (
    DevedorNaoEncontradoError,
    IdempotenciaConflitoError,
)
from emprestimo.application.ports import EventoAuditoria
from emprestimo.domain.common.errors import DevedorJaExisteError, ViolacaoInvarianteError
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.ports import DevedorResultadoPaginado
from emprestimo.presentation.api import dependencies
from emprestimo.presentation.api.main import create_app

CARTEIRA_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DEVEDOR_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DOCUMENTO = "52998224725"
CHAVE = "chave-devedor-1"
PRINCIPAL_TESTE = Principal(
    usuario_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
    tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
    perfil_acesso="Teste",
    access_token_expira_em=datetime.now(UTC) + timedelta(minutes=15),
)

CAMPOS_RESPONSE = {
    "id",
    "carteira_id",
    "documento",
    "nome",
    "contatos",
    "estado",
    "criado_em",
    "atualizado_em",
}

PAYLOAD_CRIACAO = {
    "documento": DOCUMENTO,
    "nome": "João da Silva",
    "contatos": [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}],
}


def _devedor(estado: DevedorState = DevedorState.ATIVO) -> Devedor:
    """Aggregate real (não mock) — garante que a conversão para DTO é exercitada."""
    contatos = (
        Contato(
            devedor_id=DEVEDOR_ID,
            tipo=TipoContato.TELEFONE,
            valor="(11) 1234-5678",
            preferencial=True,
        ),
    )
    devedor = Devedor.criar(
        carteira_id=CARTEIRA_ID,
        documento=Documento.from_str(DOCUMENTO),
        nome="João da Silva",
        contatos=contatos,
    )
    devedor.id = DEVEDOR_ID
    if estado is DevedorState.INATIVO:
        devedor.inativar()
    return devedor


def _devedor_criado() -> DevedorCriado:
    return DevedorCriado(
        devedor_id=DEVEDOR_ID,
        carteira_id=CARTEIRA_ID,
        documento=DOCUMENTO,
        nome="João da Silva",
        contatos=({"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True},),
        estado=DevedorState.ATIVO,
        criado_em=datetime.now(UTC),
    )


@pytest.fixture
def servicos() -> dict[str, Mock]:
    """Dublês dos casos de uso consumidos pelo router.

    ``consulta`` recebe um Devedor da CARTEIRA_ID por padrão: a dependência de
    pertinência (ADR-018) o consome em toda rota aninhada por ID. Testes que
    exercitam ausência ou pertinência divergente sobrescrevem o retorno.
    """
    consulta = Mock()
    consulta.consultar_por_id.return_value = _devedor()
    return {
        "cadastro": Mock(),
        "consulta": consulta,
        "documento": Mock(),
        "listagem": Mock(),
        "atualizacao": Mock(),
        "estado": Mock(),
        "historico": Mock(),
    }


def _provedor(dublê: Mock) -> Callable[[], Mock]:
    """Provider sem parâmetros para ``dependency_overrides``."""

    def _obter() -> Mock:
        return dublê

    return _obter


@pytest.fixture
def client(servicos: dict[str, Mock]) -> Iterator[TestClient]:
    app = create_app()
    overrides = {
        dependencies.get_devedor_cadastro_service: servicos["cadastro"],
        dependencies.get_devedor_consulta_service: servicos["consulta"],
        dependencies.get_devedor_consulta_por_documento_service: servicos["documento"],
        dependencies.get_devedor_listagem_service: servicos["listagem"],
        dependencies.get_devedor_atualizacao_service: servicos["atualizacao"],
        dependencies.get_devedor_estado_service: servicos["estado"],
        dependencies.get_devedor_historico_service: servicos["historico"],
    }
    for dependencia, dublê in overrides.items():
        # Closure sem parâmetros: um default (lambda d=dublê) faria o FastAPI
        # tratar `d` como parâmetro de query e copiar o dublê.
        app.dependency_overrides[dependencia] = _provedor(dublê)
    app.dependency_overrides[dependencies.get_principal_atual] = lambda: PRINCIPAL_TESTE
    autorizacao = Mock()
    autorizacao.exigir_permissao.return_value = None
    app.dependency_overrides[dependencies.get_autorizacao_service] = lambda: autorizacao

    def _carteira_autorizada(carteira_id: uuid.UUID) -> Carteira:
        return Carteira(id=carteira_id, tenant_id=PRINCIPAL_TESTE.tenant_id, nome="Carteira")

    app.dependency_overrides[dependencies.get_carteira_do_principal] = _carteira_autorizada
    with TestClient(app) as c:
        yield c


# --- IMP-057: POST /credit/carteiras/{carteira_id}/devedores ---


def test_post_cria_devedor_201(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["cadastro"].criar.return_value = _devedor_criado()

    resp = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores",
        json=PAYLOAD_CRIACAO,
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 201
    corpo = resp.json()
    assert set(corpo) == CAMPOS_RESPONSE  # DTO único, sem internals (RA-012)
    assert corpo["documento"] == DOCUMENTO
    assert corpo["estado"] == "ativo"
    assert corpo["contatos"] == [
        {"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}
    ]


def test_post_sem_idempotency_key_400(client: TestClient) -> None:
    resp = client.post(f"/credit/carteiras/{CARTEIRA_ID}/devedores", json=PAYLOAD_CRIACAO)

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "idempotency_key_ausente"


def test_post_documento_duplicado_409(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["cadastro"].criar.side_effect = DevedorJaExisteError(DOCUMENTO, CARTEIRA_ID)

    resp = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores",
        json=PAYLOAD_CRIACAO,
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 409
    assert resp.json()["codigo"] == "devedor_ja_existe"


def test_post_conflito_idempotencia_409(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["cadastro"].criar.side_effect = IdempotenciaConflitoError(
        CHAVE, "resultado divergente"
    )

    resp = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores",
        json=PAYLOAD_CRIACAO,
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 409
    assert resp.json()["codigo"] == "conflito_idempotencia"


def test_post_regra_violada_422(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["cadastro"].criar.side_effect = ViolacaoInvarianteError(
        "RN-003", "Devedor deve ter pelo menos um contato"
    )

    resp = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores",
        json=PAYLOAD_CRIACAO,
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 422
    assert resp.json()["codigo"] == "regra_violada"


def test_post_sem_contatos_400(client: TestClient) -> None:
    """Lista de contatos vazia é barrada na fronteira, antes do caso de uso."""
    resp = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores",
        json={**PAYLOAD_CRIACAO, "contatos": []},
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "payload_invalido"


def test_post_campo_desconhecido_400(client: TestClient) -> None:
    """``extra=forbid`` impede que campos não previstos entrem no caso de uso."""
    resp = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores",
        json={**PAYLOAD_CRIACAO, "estado": "inativo"},
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 400


# --- IMP-058: consultas ---


def test_get_por_id_200(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["consulta"].consultar_por_id.return_value = _devedor()

    resp = client.get(f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}")

    assert resp.status_code == 200
    corpo = resp.json()
    assert set(corpo) == CAMPOS_RESPONSE
    assert corpo["id"] == str(DEVEDOR_ID)
    assert corpo["documento"] == DOCUMENTO


def test_get_por_id_inexistente_404(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["consulta"].consultar_por_id.return_value = None

    resp = client.get(f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}")

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "devedor_nao_encontrado"


def test_get_por_documento_200(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["documento"].consultar_por_documento.return_value = _devedor()

    resp = client.get(f"/credit/carteiras/{CARTEIRA_ID}/devedores", params={"documento": DOCUMENTO})

    assert resp.status_code == 200
    assert resp.json()["documento"] == DOCUMENTO
    servicos["documento"].consultar_por_documento.assert_called_once_with(CARTEIRA_ID, DOCUMENTO)


def test_get_por_documento_inexistente_404(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["documento"].consultar_por_documento.return_value = None

    resp = client.get(f"/credit/carteiras/{CARTEIRA_ID}/devedores", params={"documento": DOCUMENTO})

    assert resp.status_code == 404


def test_listagem_paginada_200(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["listagem"].listar.return_value = DevedorResultadoPaginado(
        items=[_devedor()], total=1, pagina=1, tamanho=20
    )

    resp = client.get(f"/credit/carteiras/{CARTEIRA_ID}/devedores")

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 1
    assert corpo["page"] == 1
    assert corpo["size"] == 20
    assert corpo["pages"] == 1
    assert len(corpo["items"]) == 1
    assert set(corpo["items"][0]) == CAMPOS_RESPONSE


def test_listagem_repassa_filtros(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["listagem"].listar.return_value = DevedorResultadoPaginado(
        items=[], total=0, pagina=2, tamanho=5
    )

    resp = client.get(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores",
        params={"page": 2, "size": 5, "nome": "João", "estado": "inativo"},
    )

    assert resp.status_code == 200
    _, kwargs = servicos["listagem"].listar.call_args
    assert kwargs["pagina"] == 2
    assert kwargs["tamanho"] == 5
    assert kwargs["filtros"].nome == "João"
    assert kwargs["filtros"].estado == "inativo"


def test_listagem_size_acima_do_maximo_400(client: TestClient) -> None:
    resp = client.get(f"/credit/carteiras/{CARTEIRA_ID}/devedores", params={"size": 101})

    assert resp.status_code == 400


# --- IMP-059: PATCH e transições de estado ---


def test_patch_atualiza_200(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["consulta"].consultar_por_id.return_value = _devedor()

    resp = client.patch(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}",
        json={"nome": "João Santos"},
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 200
    assert set(resp.json()) == CAMPOS_RESPONSE
    _, kwargs = servicos["atualizacao"].atualizar.call_args
    assert kwargs["nome"] == "João Santos"
    assert kwargs["contatos"] is None


def test_patch_sem_idempotency_key_400(client: TestClient) -> None:
    resp = client.patch(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}", json={"nome": "João Santos"}
    )

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "idempotency_key_ausente"


def test_patch_devedor_inexistente_404(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["atualizacao"].atualizar.side_effect = DevedorNaoEncontradoError(DEVEDOR_ID)

    resp = client.patch(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}",
        json={"nome": "João Santos"},
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "devedor_nao_encontrado"


def test_patch_documento_nao_aceito_400(client: TestClient) -> None:
    """O documento é imutável (INV-003) — o payload nem chega ao caso de uso."""
    resp = client.patch(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}",
        json={"documento": "11144477735"},
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 400


def test_inativar_200(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["consulta"].consultar_por_id.return_value = _devedor(DevedorState.INATIVO)

    resp = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}/inativar",
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 200
    assert resp.json()["estado"] == "inativo"
    servicos["estado"].inativar.assert_called_once_with(DEVEDOR_ID, CHAVE)


def test_reativar_200(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["consulta"].consultar_por_id.return_value = _devedor()

    resp = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}/reativar",
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 200
    assert resp.json()["estado"] == "ativo"
    servicos["estado"].reativar.assert_called_once_with(DEVEDOR_ID, CHAVE)


def test_inativar_transicao_invalida_422(client: TestClient, servicos: dict[str, Mock]) -> None:
    """INV-005 é decidida no Aggregate e responde 422, não 409."""
    servicos["estado"].inativar.side_effect = ViolacaoInvarianteError(
        "INV-005", "Devedor já está inativo"
    )

    resp = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}/inativar",
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 422
    assert resp.json()["codigo"] == "regra_violada"


def test_inativar_sem_idempotency_key_400(client: TestClient) -> None:
    resp = client.post(f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}/inativar")

    assert resp.status_code == 400
    assert resp.json()["codigo"] == "idempotency_key_ausente"


def test_inativar_devedor_inexistente_404(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["estado"].inativar.side_effect = DevedorNaoEncontradoError(DEVEDOR_ID)

    resp = client.post(
        f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}/inativar",
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 404


# --- ADR-018: pertinência Carteira ↔ Devedor ---

OUTRA_CARTEIRA_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


@pytest.mark.parametrize(
    ("metodo", "sufixo", "corpo"),
    [
        ("get", "", None),
        ("get", "/historico", None),
        ("patch", "", {"nome": "João Santos"}),
        ("post", "/inativar", None),
        ("post", "/reativar", None),
    ],
)
def test_devedor_de_outra_carteira_404(
    client: TestClient,
    servicos: dict[str, Mock],
    metodo: str,
    sufixo: str,
    corpo: dict[str, object] | None,
) -> None:
    """Devedor real, mas de outra Carteira: 404 em toda rota aninhada (ADR-018).

    O dublê devolve um Devedor cujo ``carteira_id`` é CARTEIRA_ID, e a requisição
    usa OUTRA_CARTEIRA_ID — o par é inconsistente e a dependência o barra.
    """
    url = f"/credit/carteiras/{OUTRA_CARTEIRA_ID}/devedores/{DEVEDOR_ID}{sufixo}"
    kwargs: dict[str, object] = {"headers": {"Idempotency-Key": CHAVE}}
    if corpo is not None:
        kwargs["json"] = corpo

    resp = getattr(client, metodo)(url, **kwargs)

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "devedor_nao_encontrado"


def test_pertinencia_barra_antes_do_caso_de_uso(
    client: TestClient, servicos: dict[str, Mock]
) -> None:
    """A escrita não chega a ser executada quando a pertinência falha."""
    resp = client.post(
        f"/credit/carteiras/{OUTRA_CARTEIRA_ID}/devedores/{DEVEDOR_ID}/inativar",
        headers={"Idempotency-Key": CHAVE},
    )

    assert resp.status_code == 404
    servicos["estado"].inativar.assert_not_called()


def test_pertinencia_e_inexistencia_sao_indistinguiveis(
    client: TestClient, servicos: dict[str, Mock]
) -> None:
    """ADR-018: mesma resposta para ID inexistente e ID de outra Carteira.

    Um código distinto confirmaria a existência do identificador em outra
    Carteira, vazando informação através da fronteira de isolamento.
    """
    de_outra_carteira = client.get(f"/credit/carteiras/{OUTRA_CARTEIRA_ID}/devedores/{DEVEDOR_ID}")

    servicos["consulta"].consultar_por_id.return_value = None
    inexistente = client.get(f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}")

    assert de_outra_carteira.status_code == inexistente.status_code == 404
    assert de_outra_carteira.json() == inexistente.json()


# --- US-027: histórico cadastral ---


def _evento(acao: str, status: str = "ok") -> EventoAuditoria:
    return EventoAuditoria(
        id=uuid.uuid4(),
        entidade="devedor",
        entidade_id=DEVEDOR_ID,
        acao=acao,
        status=status,
        detalhes=None,
        criado_em=datetime.now(UTC),
    )


def test_historico_200_em_ordem(client: TestClient, servicos: dict[str, Mock]) -> None:
    servicos["historico"].consultar.return_value = [
        _evento("criar.sucesso"),
        _evento("inativar.sucesso"),
    ]

    resp = client.get(f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}/historico")

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["devedor_id"] == str(DEVEDOR_ID)
    assert [e["acao"] for e in corpo["eventos"]] == [
        "criar.sucesso",
        "inativar.sucesso",
    ]
    assert set(corpo["eventos"][0]) == {"acao", "status", "detalhes", "criado_em"}


def test_historico_devedor_inexistente_404(client: TestClient, servicos: dict[str, Mock]) -> None:
    """O serviço devolve None para Devedor inexistente — a rota traduz em 404."""
    servicos["historico"].consultar.return_value = None

    resp = client.get(f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}/historico")

    assert resp.status_code == 404
    assert resp.json()["codigo"] == "devedor_nao_encontrado"


def test_historico_vazio_200(client: TestClient, servicos: dict[str, Mock]) -> None:
    """Devedor sem eventos responde 200 com lista vazia, não 404."""
    servicos["historico"].consultar.return_value = []

    resp = client.get(f"/credit/carteiras/{CARTEIRA_ID}/devedores/{DEVEDOR_ID}/historico")

    assert resp.status_code == 200
    assert resp.json()["eventos"] == []
