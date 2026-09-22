"""ComprovantePagamento (IMP-390, PLAN-045 §3.2-b e §4.11).

**O comprovante nao autentica nada.** E uma imagem, e forja-la e trivial: ele
entra no fluxo como o que o devedor DIZ ter pago, e quem verifica e a Credora
conferindo a propria conta. Por isso o objeto guarda e correlaciona, mas nunca
decide — nem escolhe entre o valor que leu e o que o devedor digitou.

**Quitou, limpou.** Na quitacao do emprestimo o binario e os valores somem; o
vinculo com o `Pagamento` fica. A prova contabil e o Pagamento, a memoria de
calculo e a trilha de auditoria, e nenhum deles depende da imagem — guardar
documento de terceiro depois que a divida acabou e risco sem contrapartida.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from emprestimo.domain.common.errors import ViolacaoInvarianteError

__all__ = [
    "ComprovantePagamento",
    "ComprovanteState",
    "TipoMidiaComprovante",
]


class ComprovanteState(StrEnum):
    """`recebido` espera a Credora; os outros dois sao decisao dela."""

    RECEBIDO = "recebido"
    LANCADO = "lancado"
    RECUSADO = "recusado"


class TipoMidiaComprovante(StrEnum):
    """Tipos que o ingress aceita. Fora desta lista, descarte."""

    IMAGEM_JPEG = "image/jpeg"
    IMAGEM_PNG = "image/png"
    PDF = "application/pdf"


_TERMINAIS = frozenset({ComprovanteState.LANCADO, ComprovanteState.RECUSADO})


@dataclass
class ComprovantePagamento:
    """Comprovante enviado pelo devedor, aguardando a conferencia da Credora."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    emprestimo_id: uuid.UUID
    devedor_id: uuid.UUID
    sha256: str
    tipo_midia: TipoMidiaComprovante
    tamanho: int
    recebido_em: datetime
    atualizado_em: datetime
    conteudo: bytes | None = field(default=None, repr=False)
    valor_extraido: Decimal | None = None
    valor_informado: Decimal | None = None
    estado: ComprovanteState = ComprovanteState.RECEBIDO
    pagamento_id: uuid.UUID | None = None
    motivo_recusa: str | None = None
    expurgado_em: datetime | None = None

    @property
    def divergente(self) -> bool:
        """Valor lido diferente do informado. O agente relata; nao resolve."""
        if self.valor_extraido is None or self.valor_informado is None:
            return False
        return self.valor_extraido != self.valor_informado

    @classmethod
    def receber(
        cls,
        *,
        tenant_id: uuid.UUID,
        emprestimo_id: uuid.UUID,
        devedor_id: uuid.UUID,
        conteudo: bytes,
        sha256: str,
        tipo_midia: TipoMidiaComprovante,
        valor_extraido: Decimal | None,
        valor_informado: Decimal | None,
        agora: datetime | None = None,
    ) -> ComprovantePagamento:
        if not conteudo:
            raise ViolacaoInvarianteError("INV-001", "comprovante sem conteudo nao e comprovante")
        instante = agora or datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            emprestimo_id=emprestimo_id,
            devedor_id=devedor_id,
            sha256=sha256,
            tipo_midia=tipo_midia,
            tamanho=len(conteudo),
            recebido_em=instante,
            atualizado_em=instante,
            conteudo=conteudo,
            valor_extraido=valor_extraido,
            valor_informado=valor_informado,
        )

    def lancar(self, *, pagamento_id: uuid.UUID, agora: datetime | None = None) -> None:
        """A Credora conferiu na conta dela e autorizou o lancamento."""
        self._exigir_pendente()
        self.estado = ComprovanteState.LANCADO
        self.pagamento_id = pagamento_id
        self.atualizado_em = agora or datetime.now(UTC)

    def recusar(self, *, motivo: str, agora: datetime | None = None) -> None:
        self._exigir_pendente()
        self.estado = ComprovanteState.RECUSADO
        self.motivo_recusa = motivo
        self.atualizado_em = agora or datetime.now(UTC)

    def expurgar(self, *, agora: datetime | None = None) -> None:
        """Apaga imagem e valores na quitacao. Idempotente por construcao."""
        if self.expurgado_em is not None:
            return
        self.conteudo = None
        self.valor_extraido = None
        self.valor_informado = None
        self.expurgado_em = agora or datetime.now(UTC)
        self.atualizado_em = self.expurgado_em

    def _exigir_pendente(self) -> None:
        if self.estado in _TERMINAIS:
            raise ViolacaoInvarianteError(
                "INV-002",
                f"comprovante ja {self.estado.value}: decisao da Credora nao se refaz",
            )
