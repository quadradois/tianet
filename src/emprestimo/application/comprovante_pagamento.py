"""Caso de uso do comprovante de pagamento do Devedor (IMP-390, PLAN-045 §3.2-b).

**Nao confundir com `application/comprovante.py`**, que e o comprovante do
LANCAMENTO — o documento que a Credora envia ao devedor quando empresta. Este
aqui e o oposto: e o que o devedor manda para ela depois de pagar.

O comprovante entra como **alegacao do devedor**: o servico guarda, calcula o
hash e correlaciona, mas nao decide nada. Quem verifica e a Credora, conferindo
a propria conta — o lancamento vem depois, por ato dela (IMP-391).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from emprestimo.application.errors import EmprestimoNaoEncontradoError
from emprestimo.application.ports import AuditoriaRegistro, UnitOfWork
from emprestimo.domain.credit.comprovante import (
    ComprovantePagamento,
    ComprovanteState,
    TipoMidiaComprovante,
)

__all__ = [
    "ComprovantePagamentoResultado",
    "ComprovantePagamentoService",
    "MidiaComprovanteRecusadaError",
    "TAMANHO_MAXIMO_BYTES",
]

# 5 MiB: o Evolution ja foi observado entregando `HistorySync` de 5,6 MB
# (contexto externo §2.1), e comprovante de banco cabe folgado em muito menos.
TAMANHO_MAXIMO_BYTES = 5 * 1024 * 1024
RECURSO_AUDITORIA = "comprovante_pagamento"


class MidiaComprovanteRecusadaError(Exception):
    """Tipo nao aceito ou tamanho acima do limite — descarte nomeado."""

    def __init__(self, motivo: str) -> None:
        super().__init__(f"comprovante recusado: {motivo}")
        self.motivo = motivo


@dataclass(frozen=True)
class ComprovantePagamentoResultado:
    """Estado do comprovante. **Nunca carrega o binario.**"""

    id: uuid.UUID
    emprestimo_id: uuid.UUID
    devedor_id: uuid.UUID
    sha256: str
    tipo_midia: str
    tamanho: int
    estado: ComprovanteState
    valor_extraido: Decimal | None
    valor_informado: Decimal | None
    divergente: bool
    recebido_em: datetime
    duplicado: bool


def _resultado(
    comprovante: ComprovantePagamento, *, duplicado: bool
) -> ComprovantePagamentoResultado:
    return ComprovantePagamentoResultado(
        id=comprovante.id,
        emprestimo_id=comprovante.emprestimo_id,
        devedor_id=comprovante.devedor_id,
        sha256=comprovante.sha256,
        tipo_midia=comprovante.tipo_midia.value,
        tamanho=comprovante.tamanho,
        estado=comprovante.estado,
        valor_extraido=comprovante.valor_extraido,
        valor_informado=comprovante.valor_informado,
        divergente=comprovante.divergente,
        recebido_em=comprovante.recebido_em,
        duplicado=duplicado,
    )


class ComprovantePagamentoService:
    """Recebe, deduplica por conteudo e lista comprovantes."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        auditoria: AuditoriaRegistro,
        agora: Callable[[], datetime] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._auditoria = auditoria
        self._agora = agora or (lambda: datetime.now(UTC))

    def registrar(
        self,
        *,
        tenant_id: uuid.UUID,
        emprestimo_id: uuid.UUID,
        conteudo: bytes,
        tipo_midia: str,
        valor_extraido: Decimal | None = None,
        valor_informado: Decimal | None = None,
    ) -> ComprovantePagamentoResultado:
        """Guarda o comprovante; o mesmo arquivo reenviado converge.

        A deduplicacao e pelo **conteudo** (sha256), nao por `Idempotency-Key`:
        o devedor pode mandar a mesma imagem duas vezes sem nenhuma chave, e
        duas linhas para o mesmo arquivo confundiriam a Credora na conferencia.
        """
        if len(conteudo) == 0:
            raise MidiaComprovanteRecusadaError("conteudo_vazio")
        if len(conteudo) > TAMANHO_MAXIMO_BYTES:
            raise MidiaComprovanteRecusadaError("tamanho_excedido")
        try:
            tipo = TipoMidiaComprovante(tipo_midia)
        except ValueError as exc:
            raise MidiaComprovanteRecusadaError("tipo_nao_aceito") from exc

        sha256 = hashlib.sha256(conteudo).hexdigest()
        agora = self._agora()
        with self._uow_factory() as uow:
            emprestimo = uow.emprestimo.find_by_id(emprestimo_id)
            if emprestimo is None or emprestimo.tenant_id != tenant_id:
                raise EmprestimoNaoEncontradoError(emprestimo_id)
            existente = uow.comprovante_pagamento.find_by_sha256(emprestimo_id, sha256)
            if existente is not None:
                return _resultado(existente, duplicado=True)
            comprovante = ComprovantePagamento.receber(
                tenant_id=tenant_id,
                emprestimo_id=emprestimo_id,
                devedor_id=emprestimo.devedor_id,
                conteudo=conteudo,
                sha256=sha256,
                tipo_midia=tipo,
                valor_extraido=valor_extraido,
                valor_informado=valor_informado,
                agora=agora,
            )
            uow.comprovante_pagamento.save(comprovante)
            uow.commit()
        self._auditoria.registrar(
            RECURSO_AUDITORIA,
            comprovante.id,
            "registrar.sucesso",
            "ok",
            detalhes=json.dumps(
                {
                    "emprestimo_id": str(emprestimo_id),
                    "sha256": sha256,
                    "tamanho": comprovante.tamanho,
                    "divergente": comprovante.divergente,
                },
                sort_keys=True,
            ),
        )
        return _resultado(comprovante, duplicado=False)

    def listar(
        self, *, tenant_id: uuid.UUID, emprestimo_id: uuid.UUID
    ) -> list[ComprovantePagamentoResultado]:
        with self._uow_factory() as uow:
            emprestimo = uow.emprestimo.find_by_id(emprestimo_id)
            if emprestimo is None or emprestimo.tenant_id != tenant_id:
                raise EmprestimoNaoEncontradoError(emprestimo_id)
            itens = uow.comprovante_pagamento.listar_por_emprestimo(emprestimo_id)
        return [_resultado(item, duplicado=False) for item in itens]
