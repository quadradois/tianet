"""Testes da cifra de segredos da plataforma (IMP-364, PLAN-034)."""

from __future__ import annotations

import pytest

from emprestimo.infrastructure.cifra import (
    ENV_CHAVE,
    CifraIndisponivelError,
    CifraToken,
    SegredoCorrompidoError,
    resolver_cifra_token,
)

TOKEN = "5f29f723-7f3c-4ffa-9cbc-1df51d5eb9e5"


def _chave() -> str:
    return CifraToken.gerar_chave()


class TestCifraToken:
    def test_ida_e_volta_preserva_o_segredo(self) -> None:
        cifra = CifraToken(_chave())
        assert cifra.decifrar(cifra.cifrar(TOKEN)) == TOKEN

    def test_o_cifrado_nao_contem_o_segredo(self) -> None:
        """Guardrail contra a cifra virar identidade numa refatoracao.

        Sem esta assercao, trocar `cifrar` por `valor.encode()` passaria em
        todos os outros testes — a ida e volta continuaria funcionando.
        """
        cifrado = CifraToken(_chave()).cifrar(TOKEN)
        assert TOKEN.encode("utf-8") not in cifrado
        assert TOKEN not in cifrado.decode("utf-8", errors="ignore")

    def test_duas_cifragens_do_mesmo_valor_diferem(self) -> None:
        """Fernet usa IV aleatorio: igualdade denunciaria modo determinista."""
        cifra = CifraToken(_chave())
        assert cifra.cifrar(TOKEN) != cifra.cifrar(TOKEN)

    def test_chave_errada_nao_abre_e_nao_devolve_lixo(self) -> None:
        cifrado = CifraToken(_chave()).cifrar(TOKEN)
        with pytest.raises(SegredoCorrompidoError):
            CifraToken(_chave()).decifrar(cifrado)

    def test_dado_adulterado_e_recusado(self) -> None:
        """HMAC do Fernet: alterar um byte invalida, nao decifra torto."""
        cifra = CifraToken(_chave())
        cifrado = bytearray(cifra.cifrar(TOKEN))
        cifrado[-1] ^= 0x01
        with pytest.raises(SegredoCorrompidoError):
            cifra.decifrar(bytes(cifrado))

    def test_chave_malformada_recusa_na_construcao(self) -> None:
        with pytest.raises(CifraIndisponivelError, match="invalida"):
            CifraToken("nao-e-uma-chave-fernet")


class TestResolverCifraToken:
    def test_monta_a_cifra_quando_a_chave_existe(self) -> None:
        cifra = resolver_cifra_token({ENV_CHAVE: _chave()})
        assert cifra.decifrar(cifra.cifrar(TOKEN)) == TOKEN

    @pytest.mark.parametrize("ambiente", [{}, {ENV_CHAVE: ""}, {ENV_CHAVE: "   "}])
    def test_recusa_sem_chave_em_qualquer_ambiente(self, ambiente: dict[str, str]) -> None:
        """Nao ha modo degradado — nem em desenvolvimento.

        Uma "cifra que nao cifra" gravaria o token em texto claro, que e
        exatamente a falha que a DR-006 decidiu evitar.
        """
        with pytest.raises(CifraIndisponivelError, match=ENV_CHAVE):
            resolver_cifra_token(ambiente)

    def test_a_recusa_diz_como_resolver(self) -> None:
        """Erro que nao ensina o proximo passo custa uma ida a documentacao."""
        with pytest.raises(CifraIndisponivelError, match="generate_key"):
            resolver_cifra_token({})
