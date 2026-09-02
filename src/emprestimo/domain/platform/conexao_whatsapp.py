"""Entity ConexaoWhatsApp — a instância do Credor no provedor (IMP-365, PLAN-034).

Guarda a identidade da instância no Evolution e o estado do pareamento. **Não
guarda o token**: ele é segredo, vive cifrado, e a fronteira entre "o que o
domínio sabe" e "o que o repositório protege" está exatamente aí.

Por que uma Entity de plataforma e não de crédito: conectar um número é
configuração de quem opera, não fato de uma operação de crédito. Nenhum
agregado de crédito depende disto.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from emprestimo.domain.common.errors import ViolacaoInvarianteError


@dataclass(frozen=True)
class EstadoPareamento:
    """O que o provedor reporta sobre a instância, traduzido para o domínio.

    Existe para que a Application não precise importar o cliente HTTP só para
    nomear um estado. `conectado` é o socket de pé; `pareado` é o número
    vinculado — e apenas o segundo significa WhatsApp funcionando.

    `nome_exibicao` é o push name da conta pareada, **não o telefone**: o
    `/instance/status` do Evolution devolve `Name` (`"Barbosa"`, na resposta
    real de 2026-08-31) e nenhum campo com o número. Quem precisar do número
    tem de achar outra fonte antes de prometê-lo na interface.
    """

    conectado: bool
    pareado: bool
    nome_exibicao: str | None


@dataclass(frozen=True)
class ConexaoWhatsApp:
    """Uma instância de WhatsApp pertencente a um Tenant.

    Imutável: transições devolvem instância nova. Estado de pareamento é fato
    observado no provedor, nunca decidido aqui — por isso `parear` e `desparear`
    recebem o que o Evolution respondeu, em vez de inferir.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    instancia_id: str
    instancia_nome: str
    numero_pareado: str | None
    criado_em: datetime
    atualizado_em: datetime

    def __post_init__(self) -> None:
        if not self.instancia_id.strip():
            raise ViolacaoInvarianteError(
                "PLAN-034", "instancia_id e obrigatorio: sem ele a conexao nao e enderecavel"
            )
        if not self.instancia_nome.strip():
            raise ViolacaoInvarianteError("PLAN-034", "instancia_nome e obrigatorio")
        if self.numero_pareado is not None and not self.numero_pareado.strip():
            raise ViolacaoInvarianteError(
                "PLAN-034",
                "numero_pareado vazio nao e o mesmo que ausente: use None para nao pareado",
            )

    @property
    def pareada(self) -> bool:
        """Pareada significa `LoggedIn` no provedor, não `Connected`.

        O Evolution reporta os dois separadamente: `Connected` é o socket de pé,
        `LoggedIn` é o número vinculado. Tratar o primeiro como conexão faria a
        interface anunciar sucesso com nenhum WhatsApp do outro lado.
        """
        return self.numero_pareado is not None

    @classmethod
    def criar(
        cls,
        *,
        tenant_id: uuid.UUID,
        instancia_id: str,
        instancia_nome: str,
        agora: datetime | None = None,
    ) -> ConexaoWhatsApp:
        instante = agora or datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            instancia_id=instancia_id.strip(),
            instancia_nome=instancia_nome.strip(),
            numero_pareado=None,
            criado_em=instante,
            atualizado_em=instante,
        )

    def parear(self, numero: str, *, agora: datetime | None = None) -> ConexaoWhatsApp:
        """Registra o número que o provedor reportou como vinculado."""
        limpo = numero.strip()
        if not limpo:
            raise ViolacaoInvarianteError(
                "PLAN-034", "numero pareado vazio: o provedor nao confirmou vinculo"
            )
        return replace(self, numero_pareado=limpo, atualizado_em=agora or datetime.now(UTC))

    def desparear(self, *, agora: datetime | None = None) -> ConexaoWhatsApp:
        """A instância permanece; só o número é desvinculado.

        Apagar a instância no logout obrigaria a recriá-la — e com ela um token
        novo — a cada desconexão. Reconectar deve custar um QR, não um ciclo
        inteiro de provisionamento.
        """
        return replace(self, numero_pareado=None, atualizado_em=agora or datetime.now(UTC))
