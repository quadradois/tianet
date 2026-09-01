"""Invariantes da Entity ConexaoWhatsApp (IMP-365, PLAN-034)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.platform.conexao_whatsapp import ConexaoWhatsApp

TENANT = uuid.UUID("11111111-1111-4111-8111-111111111111")


def _conexao() -> ConexaoWhatsApp:
    return ConexaoWhatsApp.criar(
        tenant_id=TENANT,
        instancia_id="8a8c901f-16f9-4431-b19d-ed69cccc46c0",
        instancia_nome="adm_tianet",
    )


class TestCriacao:
    def test_nasce_nao_pareada(self) -> None:
        conexao = _conexao()
        assert conexao.pareada is False
        assert conexao.numero_pareado is None

    def test_normaliza_espacos(self) -> None:
        conexao = ConexaoWhatsApp.criar(
            tenant_id=TENANT, instancia_id="  abc  ", instancia_nome="  adm  "
        )
        assert conexao.instancia_id == "abc"
        assert conexao.instancia_nome == "adm"

    @pytest.mark.parametrize("vazio", ["", "   "])
    def test_recusa_instancia_id_vazio(self, vazio: str) -> None:
        with pytest.raises(ViolacaoInvarianteError, match="instancia_id"):
            ConexaoWhatsApp.criar(tenant_id=TENANT, instancia_id=vazio, instancia_nome="adm")

    def test_recusa_nome_vazio(self) -> None:
        with pytest.raises(ViolacaoInvarianteError, match="instancia_nome"):
            ConexaoWhatsApp.criar(tenant_id=TENANT, instancia_id="abc", instancia_nome="  ")


class TestPareamento:
    def test_parear_registra_o_numero(self) -> None:
        pareada = _conexao().parear("556284290661")
        assert pareada.pareada is True
        assert pareada.numero_pareado == "556284290661"

    def test_parear_recusa_numero_vazio(self) -> None:
        """Numero vazio significa que o provedor nao confirmou vinculo."""
        with pytest.raises(ViolacaoInvarianteError, match="nao confirmou"):
            _conexao().parear("   ")

    def test_desparear_mantem_a_instancia(self) -> None:
        """Reconectar deve custar um QR, nao um provisionamento inteiro."""
        conexao = _conexao().parear("556284290661")
        solta = conexao.desparear()
        assert solta.pareada is False
        assert solta.instancia_id == conexao.instancia_id
        assert solta.id == conexao.id

    def test_transicoes_atualizam_o_carimbo(self) -> None:
        antes = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
        depois = datetime(2026, 9, 1, 12, 5, tzinfo=UTC)
        conexao = _conexao()
        assert conexao.parear("556284290661", agora=antes).atualizado_em == antes
        assert conexao.desparear(agora=depois).atualizado_em == depois

    def test_a_entidade_e_imutavel(self) -> None:
        """`parear` devolve instancia nova; a original nao muda."""
        original = _conexao()
        original.parear("556284290661")
        assert original.pareada is False


def test_numero_vazio_no_construtor_e_recusado() -> None:
    """`None` e "nao pareado"; string vazia e um estado que nao existe."""
    with pytest.raises(ViolacaoInvarianteError, match="numero_pareado"):
        ConexaoWhatsApp(
            id=uuid.uuid4(),
            tenant_id=TENANT,
            instancia_id="abc",
            instancia_nome="adm",
            numero_pareado="  ",
            criado_em=datetime.now(UTC),
            atualizado_em=datetime.now(UTC),
        )
