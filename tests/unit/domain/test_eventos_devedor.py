"""Testes unitários dos eventos de domínio do Devedor (IMP-047, DOMAIN-026..DOMAIN-029)."""

from __future__ import annotations

import uuid

from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.eventos_devedor import (
    DevedorAtualizado,
    DevedorCadastrado,
    DevedorInativado,
    DevedorReativado,
)

CARTEIRA_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
DEVEDOR_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
DOCUMENTO = Documento.from_str("52998224725")
OUTRO_DOCUMENTO = Documento.from_str("11144477735")


def _contato_telefone(devedor_id: uuid.UUID = DEVEDOR_ID, preferencial: bool = False) -> Contato:
    return Contato(
        devedor_id=devedor_id,
        tipo=TipoContato.TELEFONE,
        valor="(11) 1234-5678",
        preferencial=preferencial,
    )


def _contato_email(devedor_id: uuid.UUID, preferencial: bool = False) -> Contato:
    return Contato(
        devedor_id=devedor_id,
        tipo=TipoContato.EMAIL,
        valor="joao@exemplo.com",
        preferencial=preferencial,
    )


def _devedor(contatos: list[Contato] | None = None, devedor_id: uuid.UUID = DEVEDOR_ID) -> Devedor:
    return Devedor.criar(
        carteira_id=CARTEIRA_ID,
        documento=DOCUMENTO,
        nome="João da Silva",
        contatos=contatos or [_contato_telefone(devedor_id=devedor_id)],
    )


class TestDevedorCadastrado:
    def test_cria_evento_com_dados_do_devedor(self) -> None:
        devedor = _devedor()
        telefone = _contato_telefone(devedor.id, preferencial=True)
        email = _contato_email(devedor.id)
        devedor = _devedor([telefone, email])

        evento = DevedorCadastrado.from_devedor(devedor, TENANT_ID)

        assert evento.devedor_id == devedor.id
        assert evento.carteira_id == CARTEIRA_ID
        assert evento.tenant_id == TENANT_ID
        assert evento.documento == DOCUMENTO
        assert evento.nome == "João da Silva"
        assert len(evento.contatos) == 2
        assert evento.criado_em == devedor.criado_em

    def test_to_audit_dict_serializa_corretamente(self) -> None:
        devedor = _devedor([_contato_telefone(preferencial=True)])
        evento = DevedorCadastrado.from_devedor(devedor, TENANT_ID)

        audit = evento.to_audit_dict()

        assert audit["evento"] == "DevedorCadastrado"
        assert audit["devedor_id"] == str(devedor.id)
        assert audit["carteira_id"] == str(CARTEIRA_ID)
        assert audit["tenant_id"] == str(TENANT_ID)
        assert audit["documento"] == "52998224725"
        assert audit["nome"] == "João da Silva"
        assert len(audit["contatos"]) == 1
        assert audit["contatos"][0]["tipo"] == "telefone"
        assert audit["contatos"][0]["valor"] == "(11) 1234-5678"
        assert audit["contatos"][0]["preferencial"] is True


class TestDevedorAtualizado:
    def test_cria_evento_apenas_nome_alterado(self) -> None:
        devedor = _devedor()
        nome_anterior = "João da Silva"

        devedor.atualizar_nome("Maria Souza")
        evento = DevedorAtualizado.from_devedor(devedor, TENANT_ID, nome_anterior=nome_anterior)

        assert evento.devedor_id == devedor.id
        assert evento.carteira_id == CARTEIRA_ID
        assert evento.tenant_id == TENANT_ID
        assert evento.alteracoes == {"nome": ("João da Silva", "Maria Souza")}

    def test_cria_evento_contato_adicionado(self) -> None:
        devedor = _devedor([_contato_telefone(devedor_id=DEVEDOR_ID)])
        contatos_anteriores = devedor.contatos

        devedor.adicionar_contato(_contato_email(devedor.id, preferencial=True))
        evento = DevedorAtualizado.from_devedor(
            devedor, TENANT_ID, contatos_anteriores=contatos_anteriores
        )

        assert "contato_adicionado_email_joao@exemplo.com" in evento.alteracoes
        antes, depois = evento.alteracoes["contato_adicionado_email_joao@exemplo.com"]
        assert antes == ""
        assert "email:joao@exemplo.com" in depois
        assert "preferencial=True" in depois

    def test_cria_evento_contato_removido(self) -> None:
        telefone = _contato_telefone()
        email = _contato_email(devedor_id=telefone.devedor_id, preferencial=True)
        devedor = _devedor([telefone, email])
        contatos_anteriores = devedor.contatos

        devedor.remover_contato(email.id)
        evento = DevedorAtualizado.from_devedor(
            devedor, TENANT_ID, contatos_anteriores=contatos_anteriores
        )

        assert "contato_removido_email_joao@exemplo.com" in evento.alteracoes
        antes, depois = evento.alteracoes["contato_removido_email_joao@exemplo.com"]
        assert "email:joao@exemplo.com" in antes
        assert depois == ""

    def test_cria_evento_preferencial_alterado(self) -> None:
        # Inicia sem telefone preferencial
        telefone1 = _contato_telefone(preferencial=False)
        telefone2 = _contato_telefone()
        telefone2 = Contato(
            devedor_id=DEVEDOR_ID,
            tipo=TipoContato.TELEFONE,
            valor="(21) 98765-4321",
            preferencial=False,
        )
        devedor = _devedor([telefone1, telefone2])
        contatos_anteriores = devedor.contatos

        telefone2_id = devedor.contatos[1].id
        devedor.atualizar_contato(telefone2_id, preferencial=True)
        evento = DevedorAtualizado.from_devedor(
            devedor, TENANT_ID, contatos_anteriores=contatos_anteriores
        )

        assert "contato_preferencial_telefone_(21) 98765-4321" in evento.alteracoes
        antes, depois = evento.alteracoes["contato_preferencial_telefone_(21) 98765-4321"]
        assert antes == "preferencial=False"
        assert depois == "preferencial=True"

    def test_to_audit_dict_serializa_corretamente(self) -> None:
        devedor = _devedor()
        nome_anterior = "João da Silva"
        devedor.atualizar_nome("Maria Souza")
        evento = DevedorAtualizado.from_devedor(devedor, TENANT_ID, nome_anterior=nome_anterior)

        audit = evento.to_audit_dict()

        assert audit["evento"] == "DevedorAtualizado"
        assert audit["devedor_id"] == str(devedor.id)
        assert audit["alteracoes"]["nome"]["antes"] == "João da Silva"
        assert audit["alteracoes"]["nome"]["depois"] == "Maria Souza"


class TestDevedorInativado:
    def test_cria_evento_com_estados_corretos(self) -> None:
        devedor = _devedor()
        devedor.inativar()
        evento = DevedorInativado.from_devedor(devedor, TENANT_ID)

        assert evento.devedor_id == devedor.id
        assert evento.carteira_id == CARTEIRA_ID
        assert evento.tenant_id == TENANT_ID
        assert evento.estado_anterior == DevedorState.ATIVO
        assert evento.estado_novo == DevedorState.INATIVO
        assert evento.inativado_em == devedor.atualizado_em

    def test_to_audit_dict_serializa_corretamente(self) -> None:
        devedor = _devedor()
        devedor.inativar()
        evento = DevedorInativado.from_devedor(devedor, TENANT_ID)

        audit = evento.to_audit_dict()

        assert audit["evento"] == "DevedorInativado"
        assert audit["estado_anterior"] == "ativo"
        assert audit["estado_novo"] == "inativo"


class TestDevedorReativado:
    def test_cria_evento_com_estados_corretos(self) -> None:
        devedor = _devedor()
        devedor.inativar()
        devedor.reativar()
        evento = DevedorReativado.from_devedor(devedor, TENANT_ID)

        assert evento.devedor_id == devedor.id
        assert evento.carteira_id == CARTEIRA_ID
        assert evento.tenant_id == TENANT_ID
        assert evento.estado_anterior == DevedorState.INATIVO
        assert evento.estado_novo == DevedorState.ATIVO
        assert evento.reativado_em == devedor.atualizado_em

    def test_to_audit_dict_serializa_corretamente(self) -> None:
        devedor = _devedor()
        devedor.inativar()
        devedor.reativar()
        evento = DevedorReativado.from_devedor(devedor, TENANT_ID)

        audit = evento.to_audit_dict()

        assert audit["evento"] == "DevedorReativado"
        assert audit["estado_anterior"] == "inativo"
        assert audit["estado_novo"] == "ativo"
