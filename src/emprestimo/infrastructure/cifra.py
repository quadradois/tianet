"""Cifra simétrica para segredos que a plataforma guarda (IMP-364, PLAN-034).

Existe porque o token da instância do WhatsApp passa a viver no banco. Esse
token não vaza *informação* — vaza **capacidade de agir**: quem o tiver envia,
lê e desconecta em nome do Credor. A DR-006 decidiu guardá-lo cifrado em
repouso, e este módulo é o único lugar que sabe como.

Fernet, da `cryptography`: AES de 128 bits em modo CBC com HMAC, chave e IV
tratados pela própria biblioteca. A escolha é deliberadamente sem graça — a API
não oferece o pé em que se atirar (nonce reutilizado, modo sem autenticação,
padding manual).

**A chave nunca vem do banco.** Chave guardada junto do dado cifrado não protege
nada; ela vem de `WHATSAPP_TOKEN_ENCRYPTION_KEY`, no ambiente.
"""

from __future__ import annotations

from collections.abc import Mapping

from cryptography.fernet import Fernet, InvalidToken

ENV_CHAVE = "WHATSAPP_TOKEN_ENCRYPTION_KEY"


class CifraIndisponivelError(RuntimeError):
    """A cifra não pôde ser montada — falta a chave, ou ela é inválida."""


class SegredoCorrompidoError(RuntimeError):
    """O texto cifrado não abre com esta chave.

    Distinta de `CifraIndisponivelError` de propósito: aquela é configuração
    ausente, esta é dado que não confere. Confundir as duas faria uma chave
    trocada parecer um banco corrompido.
    """


class CifraToken:
    """Cifra e decifra segredos curtos guardados pela plataforma."""

    def __init__(self, chave: str) -> None:
        try:
            self._fernet = Fernet(chave.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise CifraIndisponivelError(
                f"{ENV_CHAVE} invalida: esperada chave Fernet em base64 urlsafe de 32 bytes"
            ) from exc

    def cifrar(self, valor: str) -> bytes:
        return self._fernet.encrypt(valor.encode("utf-8"))

    def decifrar(self, cifrado: bytes) -> str:
        try:
            return self._fernet.decrypt(cifrado).decode("utf-8")
        except InvalidToken as exc:
            raise SegredoCorrompidoError(
                "segredo nao abre com a chave atual: chave trocada ou dado adulterado"
            ) from exc

    @staticmethod
    def gerar_chave() -> str:
        """Gera uma chave nova, para provisionar um ambiente."""
        return Fernet.generate_key().decode("utf-8")


def resolver_cifra_token(ambiente: Mapping[str, str]) -> CifraToken:
    """Monta a cifra a partir do ambiente, ou recusa dizendo o que falta.

    **Não há modo degradado, em nenhum ambiente.** Para o canal de e-mail existe
    um fake legítimo em desenvolvimento; para uma cifra não existe equivalente —
    "cifra que não cifra" grava o segredo em texto claro, que é exatamente a
    falha que a DR-006 decidiu evitar. Guardar em claro porque alguém esqueceu
    uma variável seria o pior tipo de vazamento: o que não parece incidente.

    Isto é mais estrito que o PLAN-034 §4.2, que pedia recusa apenas em
    `APP_ENV=production`. A recusa vale em todo ambiente, e é barata: só alcança
    quem for de fato usar a conexão do WhatsApp.
    """
    chave = ambiente.get(ENV_CHAVE, "").strip()
    if not chave:
        raise CifraIndisponivelError(
            f"{ENV_CHAVE} ausente. Gere uma com "
            '`python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"` e coloque no ambiente.'
        )
    return CifraToken(chave)
