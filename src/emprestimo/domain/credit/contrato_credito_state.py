"""Estados do Contrato de Credito (EPIC-004)."""

from enum import StrEnum


class ContratoCreditoState(StrEnum):
    """Ciclo documental do contrato antes do Motor Financeiro."""

    RASCUNHO = "rascunho"
    FORMALIZADO = "formalizado"
    ASSINADO = "assinado"
    LIBERADO_PARA_MOTOR = "liberado_para_motor"
    CANCELADO = "cancelado"
    ENCERRADO = "encerrado"
