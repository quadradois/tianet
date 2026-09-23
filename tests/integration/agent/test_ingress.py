"""Ingress duravel do agente — aceite das Entregas 356-A e 356-B (IMP-356).

Tudo contra PostgreSQL real: unicidade, replay, isolamento de classe,
recuperacao sem estado em memoria, limites de payload, descarte de midia e
metricas sem conteudo. Nenhum LLM, ferramenta ou envio existe nestes slices.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient
from tests.factories import CarteiraFactory, TenantFactory

from emprestimo.agent.admissao import (
    ConfiguracaoAdmissao,
    ControleAdmissao,
    DimensaoCota,
)
from emprestimo.agent.conversa import (
    LIMITE_PADRAO_BYTES,
    ClasseContexto,
    ConfiguracaoIngress,
)
from emprestimo.agent.ingress import create_ingress_app
from emprestimo.agent.metricas import METRICAS
from emprestimo.application.notifications import CHAVE_WHATSAPP_CREDOR
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.tenant import TenantState
from emprestimo.infrastructure.cifra import CifraToken
from emprestimo.infrastructure.db.session import get_session_factory
from emprestimo.infrastructure.repositories import SqlAlchemyTenantRepository
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

INSTANCIA_ID = "035eaa43-0000-4000-8000-aaaaaaaaaaaa"
INSTANCIA_REF = "tianet_teste"
OPERADORA_NUMERO = "5511999999999"
# IMP-381: o envelope so vale com o token da instancia guardado na TiaNet.
TOKEN_INSTANCIA = "token-da-instancia-de-teste"
CIFRA = CifraToken(CifraToken.gerar_chave())


def _uow(session_factory: sessionmaker[Session]) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory, cifra_factory=lambda: CIFRA)


def _config(tenant_id: uuid.UUID) -> ConfiguracaoIngress:
    return ConfiguracaoIngress(tenant_id=tenant_id, instancia_ref=INSTANCIA_REF)


@pytest.fixture
def tenant_id(session: Session) -> uuid.UUID:
    """Tenant com instancia conectada e Credora identificada pelo numero de avisos."""
    tenant = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(tenant)
    session.commit()
    with _uow(get_session_factory()) as uow:
        uow.conexao_whatsapp.save(
            ConexaoWhatsApp.criar(
                tenant_id=tenant.id, instancia_id=INSTANCIA_ID, instancia_nome=INSTANCIA_REF
            ),
            token=TOKEN_INSTANCIA,
        )
        uow.configuracao.save(
            Configuracao(tenant_id=tenant.id, chave=CHAVE_WHATSAPP_CREDOR, valor=OPERADORA_NUMERO)
        )
        uow.commit()
    return tenant.id


@pytest.fixture
def app(tenant_id: uuid.UUID) -> Iterator[TestClient]:
    session_factory = get_session_factory()
    application = create_ingress_app(
        _config(tenant_id),
        lambda: _uow(session_factory),
        INSTANCIA_ID,
    )
    with TestClient(application) as client:
        yield client


def _envelope(
    *,
    event: str = "Message",
    instance_id: str = INSTANCIA_ID,
    info_id: str | None = "3EB0TESTE0001",
    sender: str = f"{OPERADORA_NUMERO}@s.whatsapp.net",
    is_from_me: bool = False,
    is_group: bool = False,
    texto: str | None = "qual e o saldo?",
    instance_token: str | None = TOKEN_INSTANCIA,
) -> dict[str, Any]:
    info: dict[str, Any] = {"Sender": sender, "IsFromMe": is_from_me, "IsGroup": is_group}
    if info_id is not None:
        info["ID"] = info_id
    mensagem: dict[str, Any] = {}
    if texto is not None:
        mensagem = {"conversation": texto}
    return {
        "event": event,
        "instanceId": instance_id,
        "instanceToken": instance_token,
        "instanceName": "nome-nao-confiavel",
        "data": {"Info": info, "Message": mensagem},
    }


def _contar(tenant_id: uuid.UUID) -> int:
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        total = uow.inbox_conversa.contar(tenant_id)
        uow.commit()
        return total


def test_aceita_e_persiste_operadora(app: TestClient, tenant_id: uuid.UUID) -> None:
    resposta = app.post("/whatsapp/webhook", json=_envelope())
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo == {"message": "accepted", "duplicada": False, "classe": "operadora"}
    assert _contar(tenant_id) == 1
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        linha = uow.inbox_conversa.buscar_por_chave(tenant_id, INSTANCIA_REF, "3EB0TESTE0001")
        assert linha is not None
        assert linha.estado == "recebida"
        assert linha.texto == "qual e o saldo?"
        assert linha.classe is ClasseContexto.OPERADORA
        assert linha.envelope_instance_id == INSTANCIA_ID
        sessao = uow.sessao_conversa.buscar(
            tenant_id, INSTANCIA_REF, ClasseContexto.OPERADORA, OPERADORA_NUMERO
        )
        assert sessao is not None
        uow.commit()


def test_replay_nao_duplica_nem_reprocessa(app: TestClient, tenant_id: uuid.UUID) -> None:
    primeira = app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0REPLAY01"))
    assert primeira.json()["duplicada"] is False
    segunda = app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0REPLAY01"))
    assert segunda.status_code == 200
    assert segunda.json() == {"message": "accepted", "duplicada": True, "classe": "operadora"}
    assert _contar(tenant_id) == 1


def test_mesmo_id_em_outra_instancia_nao_colide(
    app: TestClient, tenant_id: uuid.UUID, session_factory: sessionmaker[Session]
) -> None:
    assert app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0MESMOID")).status_code == 200
    outra = create_ingress_app(
        ConfiguracaoIngress(
            tenant_id=tenant_id,
            instancia_ref="tianet_outra",
        ),
        lambda: _uow(session_factory),
        "ffffffff-0000-4000-8000-bbbbbbbbbbbb",
    )
    with TestClient(outra) as outra_client:
        resposta = outra_client.post(
            "/whatsapp/webhook",
            json=_envelope(
                info_id="3EB0MESMOID",
                instance_id="ffffffff-0000-4000-8000-bbbbbbbbbbbb",
            ),
        )
    assert resposta.status_code == 200
    assert resposta.json()["duplicada"] is False
    assert _contar(tenant_id) == 2


@pytest.mark.parametrize(
    ("ajuste", "motivo"),
    [
        ({"is_from_me": True}, "propria"),
        ({"is_group": True}, "grupo"),
        ({"sender": "5511999999999-123456@g.us"}, "grupo"),
        ({"info_id": None}, "sem-id"),
        ({"event": "HistorySync"}, "evento-nao-suportado"),
        ({"event": "Receipt"}, "evento-nao-suportado"),
        ({"instance_id": "desconhecida"}, "instancia-desconhecida"),
    ],
)
def test_descartes_respondem_2xx_sem_persistir(
    app: TestClient, tenant_id: uuid.UUID, ajuste: dict[str, Any], motivo: str
) -> None:
    resposta = app.post("/whatsapp/webhook", json=_envelope(**ajuste))
    assert resposta.status_code == 200
    assert resposta.json() == {"message": "discarded", "motivo": motivo}
    assert _contar(tenant_id) == 0


def test_desconhecido_vira_pre_cadastro_sem_leitura_de_carteira(
    app: TestClient, tenant_id: uuid.UUID
) -> None:
    resposta = app.post(
        "/whatsapp/webhook",
        json=_envelope(info_id="3EB0DESCONHECIDO", sender="5511888888888@s.whatsapp.net"),
    )
    assert resposta.json() == {"message": "accepted", "duplicada": False, "classe": "pre_cadastro"}
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        linha = uow.inbox_conversa.buscar_por_chave(tenant_id, INSTANCIA_REF, "3EB0DESCONHECIDO")
        assert linha is not None
        assert linha.classe is ClasseContexto.PRE_CADASTRO
        uow.commit()


def test_lid_nunca_e_operadora_mesmo_com_numero_de_avisos(
    app: TestClient, tenant_id: uuid.UUID
) -> None:
    resposta = app.post(
        "/whatsapp/webhook",
        json=_envelope(info_id="3EB0LID01", sender=f"{OPERADORA_NUMERO}@lid"),
    )
    assert resposta.json()["classe"] == "pre_cadastro"


def test_contextos_nunca_compartilham_sessao(app: TestClient, tenant_id: uuid.UUID) -> None:
    app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0S1"))
    app.post(
        "/whatsapp/webhook",
        json=_envelope(info_id="3EB0S2", sender="5511888888888@s.whatsapp.net"),
    )
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        operadora = uow.sessao_conversa.buscar(
            tenant_id, INSTANCIA_REF, ClasseContexto.OPERADORA, OPERADORA_NUMERO
        )
        pre = uow.sessao_conversa.buscar(
            tenant_id, INSTANCIA_REF, ClasseContexto.PRE_CADASTRO, "5511888888888"
        )
        assert operadora is not None
        assert pre is not None
        assert operadora.id != pre.id
        uow.commit()


def test_recuperacao_apos_crash_nao_duplica(app: TestClient, tenant_id: uuid.UUID) -> None:
    # O servidor nao guarda nada em memoria: a prova de recuperacao e
    # reenviar o mesmo ID e observar deduplicacao pelo banco.
    primeira = app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0CRASH01"))
    assert primeira.json()["duplicada"] is False
    del primeira
    segunda = app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0CRASH01"))
    assert segunda.json()["duplicada"] is True
    assert _contar(tenant_id) == 1


# ---------------------------------------------------------------------------
# Entrega 356-B: limites de payload, descarte de midia e metricas sem conteudo
# ---------------------------------------------------------------------------


@pytest.fixture
def metricas_limpas() -> Iterator[None]:
    METRICAS.bytes_recebidos = 0
    METRICAS.aceitas = 0
    METRICAS.duplicadas = 0
    METRICAS.descartes_por_motivo.clear()
    yield
    METRICAS.bytes_recebidos = 0
    METRICAS.aceitas = 0
    METRICAS.duplicadas = 0
    METRICAS.descartes_por_motivo.clear()


def _app_com_limite(
    tenant_id: uuid.UUID,
    session_factory: sessionmaker[Session],
    max_bytes: int,
) -> TestClient:
    application = create_ingress_app(
        ConfiguracaoIngress(
            tenant_id=tenant_id,
            instancia_ref=INSTANCIA_REF,
            max_bytes=max_bytes,
        ),
        lambda: _uow(session_factory),
        INSTANCIA_ID,
    )
    return TestClient(application)


def test_limite_padrao_cobre_amostra_e_respeita_teto() -> None:
    assert LIMITE_PADRAO_BYTES == 5_898_240
    assert LIMITE_PADRAO_BYTES < 8 * 1024 * 1024


def test_carga_acima_do_limite_descarta_sem_persistir_nem_llm(
    tenant_id: uuid.UUID, session_factory: sessionmaker[Session], metricas_limpas: None
) -> None:
    with _app_com_limite(tenant_id, session_factory, 1024) as pequeno:
        grande = _envelope(info_id="3EB0GRANDE01", texto="x" * 5000)
        assert len(json.dumps(grande).encode("utf-8")) > 1024
        for _ in range(3):
            resposta = pequeno.post("/whatsapp/webhook", json=grande)
            assert resposta.status_code == 200
            assert resposta.json() == {"message": "discarded", "motivo": "carga-excedida"}
    assert _contar(tenant_id) == 0
    retrato = METRICAS.retrato()
    assert retrato["descartes_por_motivo"] == {"carga-excedida": 3}
    assert "x" * 100 not in str(retrato)


def test_historysync_grande_nao_derruba_nem_persiste(
    tenant_id: uuid.UUID, session_factory: sessionmaker[Session]
) -> None:
    with _app_com_limite(tenant_id, session_factory, 1024) as pequeno:
        sincronia = {
            "event": "HistorySync",
            "instanceId": INSTANCIA_ID,
            "data": {"sincronizacao": "y" * 5000},
        }
        resposta = pequeno.post("/whatsapp/webhook", json=sincronia)
        assert resposta.status_code == 200
        assert resposta.json()["motivo"] == "carga-excedida"
    assert _contar(tenant_id) == 0


def test_historysync_dentro_do_limite_descarta_com_motivo_proprio(
    tenant_id: uuid.UUID, session_factory: sessionmaker[Session]
) -> None:
    with _app_com_limite(tenant_id, session_factory, 1024 * 1024) as app:
        resposta = app.post(
            "/whatsapp/webhook",
            json={"event": "HistorySync", "instanceId": INSTANCIA_ID, "data": {}},
        )
        assert resposta.status_code == 200
        assert resposta.json() == {"message": "discarded", "motivo": "evento-nao-suportado"}
    assert _contar(tenant_id) == 0


def test_midia_sem_texto_descarta_antes_de_persistir(
    tenant_id: uuid.UUID, session_factory: sessionmaker[Session]
) -> None:
    envelope = _envelope(info_id="3EB0MIDIA01", texto=None)
    assert isinstance(envelope["data"], dict)
    envelope["data"]["Message"] = {"imageMessage": {"mimetype": "image/jpeg", "blob": "a" * 500}}
    with _app_com_limite(tenant_id, session_factory, 1024 * 1024) as app:
        resposta = app.post("/whatsapp/webhook", json=envelope)
        assert resposta.status_code == 200
        assert resposta.json() == {"message": "discarded", "motivo": "midia-sem-texto"}
    assert _contar(tenant_id) == 0


def test_legenda_com_midia_aceita_so_o_texto(
    tenant_id: uuid.UUID, session_factory: sessionmaker[Session]
) -> None:
    legenda = "segue o comprovante"
    envelope = _envelope(info_id="3EB0LEGENDA01", texto=None)
    assert isinstance(envelope["data"], dict)
    envelope["data"]["Message"] = {
        "extendedTextMessage": {
            "text": legenda,
            "contextInfo": {"quotedMessage": {"imageMessage": {}}},
        }
    }
    with _app_com_limite(tenant_id, session_factory, 1024 * 1024) as app:
        resposta = app.post("/whatsapp/webhook", json=envelope)
        assert resposta.json() == {
            "message": "accepted",
            "duplicada": False,
            "classe": "operadora",
        }
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        linha = uow.inbox_conversa.buscar_por_chave(tenant_id, INSTANCIA_REF, "3EB0LEGENDA01")
        assert linha is not None
        assert linha.texto == legenda
        uow.commit()


def test_metricas_contam_sem_conteudo(
    app: TestClient, tenant_id: uuid.UUID, metricas_limpas: None
) -> None:
    app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0MET01", texto="saldo secreto 123"))
    app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0MET01", texto="saldo secreto 123"))
    app.post("/whatsapp/webhook", json={"event": "Receipt", "instanceId": INSTANCIA_ID, "data": {}})
    retrato = METRICAS.retrato()
    assert retrato["aceitas"] == 2
    assert retrato["duplicadas"] == 1
    assert retrato["descartes_por_motivo"] == {"evento-nao-suportado": 1}
    serializado = json.dumps(retrato, ensure_ascii=False)
    assert "saldo secreto" not in serializado
    assert retrato["bytes_recebidos"] > 0


# ---------------------------------------------------------------------------
# Entrega 356-C: quota no ingress — dedupe antes, recusa fixa depois
# ---------------------------------------------------------------------------


def _app_com_quota(
    tenant_id: uuid.UUID,
    session_factory: sessionmaker[Session],
    limite_operadora: int,
) -> TestClient:
    application = create_ingress_app(
        ConfiguracaoIngress(
            tenant_id=tenant_id,
            instancia_ref=INSTANCIA_REF,
        ),
        lambda: _uow(session_factory),
        INSTANCIA_ID,
        admissao=ControleAdmissao(
            ConfiguracaoAdmissao(
                dimensoes=(
                    DimensaoCota("instancia", 60, 100),
                    DimensaoCota("operadora-remetente", 60, limite_operadora),
                    DimensaoCota("desconhecido-remetente", 60, 100),
                    DimensaoCota("desconhecido-classe", 60, 100),
                )
            )
        ),
    )
    return TestClient(application)


def test_duplicada_nao_consome_quota(
    tenant_id: uuid.UUID, session_factory: sessionmaker[Session], metricas_limpas: None
) -> None:
    with _app_com_quota(tenant_id, session_factory, 1) as com_quota:
        primeira = com_quota.post("/whatsapp/webhook", json=_envelope(info_id="3EB0Q01"))
        assert primeira.json()["duplicada"] is False
        # Replay nao passa pela quota: aceita sem consumir a vaga.
        segunda = com_quota.post("/whatsapp/webhook", json=_envelope(info_id="3EB0Q01"))
        assert segunda.json() == {"message": "accepted", "duplicada": True, "classe": "operadora"}
        # ID novo com quota esgotada (limite 1, consumido pela primeira): recusa.
        terceira = com_quota.post("/whatsapp/webhook", json=_envelope(info_id="3EB0Q02"))
        assert terceira.json() == {
            "message": "recusada",
            "motivo": "janela-cheia:operadora-remetente",
        }
    assert _contar(tenant_id) == 1
    assert METRICAS.retrato()["recusas_por_motivo"] == {"janela-cheia:operadora-remetente": 1}


def test_recusada_resposta_fixa_sem_linha_nem_loop(
    tenant_id: uuid.UUID, session_factory: sessionmaker[Session]
) -> None:
    with _app_com_quota(tenant_id, session_factory, 1) as com_quota:
        assert (
            com_quota.post("/whatsapp/webhook", json=_envelope(info_id="3EB0R01")).status_code
            == 200
        )
        for i in range(2, 5):
            resposta = com_quota.post("/whatsapp/webhook", json=_envelope(info_id=f"3EB0R0{i}"))
            assert resposta.status_code == 200
            assert resposta.json()["message"] == "recusada"
    assert _contar(tenant_id) == 1


# --- IMP-381: prova de origem e identidade por telefone -----------------------


def _devedor_com_whatsapp(tenant_id: uuid.UUID, telefone: str, *, ativo: bool = True) -> uuid.UUID:
    """Devedor numa carteira do tenant, com o WhatsApp cadastrado COM mascara."""
    with _uow(get_session_factory()) as uow:
        carteira = CarteiraFactory.build(tenant_id=tenant_id)
        uow.carteira.save(carteira)
        devedor = Devedor.criar(
            carteira_id=carteira.id,
            documento=Documento.from_str(_cpf_valido()),
            nome=f"Devedor {uuid.uuid4().hex[:6]}",
            contatos=(
                Contato(
                    devedor_id=uuid.uuid4(),
                    tipo=TipoContato.WHATSAPP,
                    valor=telefone,
                    preferencial=True,
                ),
            ),
        )
        if not ativo:
            devedor.inativar()
        uow.devedor.save(devedor)
        # O repositorio do Devedor nao grava contatos: vao pelo proprio, como
        # no cadastro real (DevedorCadastroService).
        for contato in devedor.contatos:
            uow.contato.save(contato)
        uow.commit()
        return devedor.id


def _cpf_valido() -> str:
    base = [int(d) for d in f"{uuid.uuid4().int % 10**9:09d}"]
    for peso_inicial in (10, 11):
        soma = sum(d * p for d, p in zip(base, range(peso_inicial, 1, -1), strict=False))
        base.append(0 if soma % 11 < 2 else 11 - soma % 11)
    return "".join(map(str, base))


@pytest.mark.parametrize("token", ["token-forjado", "", None])
def test_token_errado_ou_ausente_e_descartado_sem_persistir(
    app: TestClient, tenant_id: uuid.UUID, token: str | None
) -> None:
    """Sem o token da instancia, `Sender` e texto que qualquer um escreve."""
    envelope = _envelope(info_id=f"3EB0FORJA{token}", instance_token=token)
    if token is None:
        envelope.pop("instanceToken")

    resposta = app.post("/whatsapp/webhook", json=envelope)

    assert resposta.status_code == 200
    assert resposta.json()["motivo"] == "token-invalido"
    assert _contar(tenant_id) == 0


def test_token_rotacionado_vale_na_hora_sem_restart(app: TestClient, tenant_id: uuid.UUID) -> None:
    with _uow(get_session_factory()) as uow:
        conexao = uow.conexao_whatsapp.find_by_tenant_id(tenant_id)
        assert conexao is not None
        uow.conexao_whatsapp.save(conexao, token="token-novo-apos-rotacao")
        uow.commit()

    antigo = app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0ROT01"))
    novo = app.post(
        "/whatsapp/webhook",
        json=_envelope(info_id="3EB0ROT02", instance_token="token-novo-apos-rotacao"),
    )

    assert antigo.json()["motivo"] == "token-invalido"
    assert novo.json()["message"] == "accepted"


@pytest.mark.parametrize(
    "sender",
    ["5511988887766@s.whatsapp.net", "551188887766@s.whatsapp.net"],
    ids=["com-nono-digito", "jid-antigo-sem-nono-digito"],
)
def test_devedor_cadastrado_com_mascara_e_reconhecido(
    app: TestClient, tenant_id: uuid.UUID, sender: str
) -> None:
    _devedor_com_whatsapp(tenant_id, "(11) 98888-7766")

    resposta = app.post(
        "/whatsapp/webhook", json=_envelope(info_id=f"3EB0{sender[:12]}", sender=sender)
    )

    assert resposta.json()["classe"] == "devedor"


def test_devedor_inativo_nao_e_reconhecido(app: TestClient, tenant_id: uuid.UUID) -> None:
    _devedor_com_whatsapp(tenant_id, "(11) 97777-6655", ativo=False)

    resposta = app.post(
        "/whatsapp/webhook",
        json=_envelope(info_id="3EB0INATIVO", sender="5511977776655@s.whatsapp.net"),
    )

    assert resposta.json()["classe"] == "pre_cadastro"


def test_devedor_de_outro_tenant_nao_vaza_identidade(
    app: TestClient, tenant_id: uuid.UUID, session: Session
) -> None:
    outro = TenantFactory.build(estado=TenantState.ATIVO)
    SqlAlchemyTenantRepository(session).save(outro)
    session.commit()
    _devedor_com_whatsapp(outro.id, "(11) 96666-5544")

    resposta = app.post(
        "/whatsapp/webhook",
        json=_envelope(info_id="3EB0CROSS", sender="5511966665544@s.whatsapp.net"),
    )

    assert resposta.json()["classe"] == "pre_cadastro"


def test_trocar_numero_de_avisos_vale_na_proxima_mensagem(
    app: TestClient, tenant_id: uuid.UUID
) -> None:
    """Sem cache e sem restart: o numero da tela e lido a cada mensagem."""
    novo_numero = "5562988887777"
    with _uow(get_session_factory()) as uow:
        atual = next(
            c
            for c in uow.configuracao.find_by_tenant_id(tenant_id)
            if c.chave == CHAVE_WHATSAPP_CREDOR
        )
        uow.configuracao.save(
            Configuracao(
                tenant_id=tenant_id, chave=CHAVE_WHATSAPP_CREDOR, valor=novo_numero, id=atual.id
            )
        )
        uow.commit()

    antigo = app.post("/whatsapp/webhook", json=_envelope(info_id="3EB0TROCA1"))
    novo = app.post(
        "/whatsapp/webhook",
        json=_envelope(info_id="3EB0TROCA2", sender=f"{novo_numero}@s.whatsapp.net"),
    )

    assert antigo.json()["classe"] == "pre_cadastro"
    assert novo.json()["classe"] == "operadora"


def test_allowlist_de_ambiente_nao_existe_mais() -> None:
    """A identidade da Credora vem da tela (`credor_whatsapp`), nao do servidor.

    Duas fontes para a mesma resposta divergem; a variavel escondida venceria
    em silencio quem a Credora cadastrou na tela.
    """
    raiz = Path(__file__).resolve().parents[3]
    alvos = [
        raiz / "src",
        raiz / "docker-compose.yml",
        raiz / "docker-compose.prod.yml",
        raiz / ".env.example",
    ]
    encontrados = [
        str(caminho.relative_to(raiz))
        for alvo in alvos
        for caminho in ([alvo] if alvo.is_file() else alvo.rglob("*.py"))
        if re.search(r"COPILOT_OPERATOR_ALLOWLIST\s*[=:\"']", caminho.read_text(encoding="utf-8"))
    ]
    assert encontrados == []
