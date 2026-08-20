"""Comprovante do lancamento, gerado no backend e enviado de forma assincrona.

O texto recebe um snapshot financeiro pronto do Motor. Este modulo apenas
apresenta esses valores e cria o job duravel; nao consulta nem recalcula dados
financeiros.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from emprestimo.application.ports import UnitOfWork
from emprestimo.domain.credit.operacao_diaria import CanalComunicacao
from emprestimo.domain.credit.scheduler import JobAgendado

TIPO_JOB_COMPROVANTE = "enviar_comprovante_whatsapp"
ORIGEM_COMPROVANTE = "comprovante_lancamento"


@dataclass(frozen=True)
class ComprovanteLancamento:
    """Snapshot imutavel necessario para montar e entregar o comprovante."""

    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    nome_devedor: str
    destinatario_whatsapp: str
    emprestimo_id: uuid.UUID
    valor_contratado: Decimal
    moeda: str
    taxa_juros_mensal_percentual: Decimal
    dia_de_acerto: int
    primeiro_acerto_em: date


def montar_texto_comprovante(dados: ComprovanteLancamento) -> str:
    """Apresenta, sem derivar valores, o snapshot devolvido pelo Motor."""

    valor = _formatar_decimal(dados.valor_contratado, casas=2)
    taxa = _formatar_decimal(dados.taxa_juros_mensal_percentual, casas=2)
    return "\n".join(
        (
            "Comprovante do lancamento",
            f"Devedor: {dados.nome_devedor}",
            f"Emprestimo: {dados.emprestimo_id}",
            f"Valor contratado: {dados.moeda} {valor}",
            f"Taxa de juros mensal: {taxa}%",
            f"Dia de acerto: {dados.dia_de_acerto}",
            f"Primeiro acerto: {dados.primeiro_acerto_em:%d/%m/%Y}",
        )
    )


class ComprovanteService:
    """Enfileira uma unica entrega por lancamento em UnitOfWork proprio."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        *,
        agora: Callable[[], datetime] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._agora = agora or (lambda: datetime.now(UTC))

    def enfileirar(self, comprovante: ComprovanteLancamento) -> JobAgendado:
        with self._uow_factory() as uow:
            existente = uow.job_agendado.find_by_origem(
                tenant_id=comprovante.tenant_id,
                origem_tipo=ORIGEM_COMPROVANTE,
                origem_id=comprovante.emprestimo_id,
            )
            if existente is not None:
                return existente

            instante = self._agora()
            job = JobAgendado(
                tenant_id=comprovante.tenant_id,
                carteira_id=comprovante.carteira_id,
                tipo=TIPO_JOB_COMPROVANTE,
                executar_em=instante,
                correlation_id=f"lancamento:{comprovante.emprestimo_id}",
                payload={
                    "canal": CanalComunicacao.WHATSAPP.value,
                    "destinatario": comprovante.destinatario_whatsapp,
                    "texto": montar_texto_comprovante(comprovante),
                },
                origem_tipo=ORIGEM_COMPROVANTE,
                origem_id=comprovante.emprestimo_id,
            )
            uow.job_agendado.save(job)
            uow.commit()
            return job


def _formatar_decimal(valor: Decimal, *, casas: int) -> str:
    bruto = f"{valor:,.{casas}f}"
    return bruto.replace(",", "_").replace(".", ",").replace("_", ".")
