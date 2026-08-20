"""DTOs da API REST da Operacao Diaria (EPIC-007/P4)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from emprestimo.domain.credit.operacao_diaria import (
    CanalComunicacao,
    EstadoCobranca,
    EstadoCompromisso,
    EstadoLembrete,
    TipoAcaoCobranca,
)
from emprestimo.domain.credit.pagamento import PagamentoState
from emprestimo.domain.credit.promessa import PromessaPagamentoState


class AcaoCobrancaCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: TipoAcaoCobranca
    resultado: str = Field(min_length=1)


class PromessaPagamentoCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valor_declarado: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)
    data_promessa: date
    observacao: str | None = None
    pagamento_informado: bool = False


class ApropriacaoPagamentoCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pagamento_id: uuid.UUID
    data_referencia: date | None = None


class CompromissoAgendaCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(min_length=1)
    previsto_para: datetime
    emprestimo_id: uuid.UUID | None = None


class LembreteAgendaCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    horario: datetime
    mensagem: str = Field(min_length=1)


class ReagendarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    novo_horario: datetime


class ComunicacaoManualCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canal: CanalComunicacao
    ocorrido_em: datetime
    resumo: str = Field(min_length=1)
    resultado: str = Field(min_length=1)
    emprestimo_id: uuid.UUID | None = None
    cobranca_acao_id: uuid.UUID | None = None
    agenda_item_id: uuid.UUID | None = None


class CobrancaCasoResponse(BaseModel):
    caso_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    emprestimo_id: uuid.UUID | None
    titulo: str
    origem: str
    estado: EstadoCobranca
    total_pendente: Decimal
    criado_em: datetime


class FilaCobrancaResponse(BaseModel):
    items: list[CobrancaCasoResponse]
    total: int


class AcaoCobrancaResponse(BaseModel):
    acao_id: uuid.UUID
    caso_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID | None
    emprestimo_id: uuid.UUID
    usuario_id: uuid.UUID
    tipo: TipoAcaoCobranca
    resultado: str
    registrada_em: datetime


class PromessaPagamentoResponse(BaseModel):
    promessa_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    emprestimo_id: uuid.UUID
    valor_declarado: Decimal
    data_promessa: date
    estado: PromessaPagamentoState


class ApropriacaoPagamentoResponse(BaseModel):
    apropriacao_id: uuid.UUID
    promessa_id: uuid.UUID
    pagamento_id: uuid.UUID
    valor: Decimal
    realizado_em: datetime
    estado_promessa: PromessaPagamentoState


class AgendaItemResponse(BaseModel):
    agenda_item_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    devedor_id: uuid.UUID
    usuario_solicitante_id: uuid.UUID
    titulo: str
    previsto_para: datetime
    emprestimo_id: uuid.UUID | None
    estado: EstadoCompromisso
    atualizado_em: datetime | None


class LembreteResponse(BaseModel):
    lembrete_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    agenda_item_id: uuid.UUID
    horario: datetime
    enviado_por_usuario_id: uuid.UUID
    mensagem: str
    estado: EstadoLembrete


class AgendaOperacionalResponse(BaseModel):
    compromissos: list[AgendaItemResponse]
    lembretes: list[LembreteResponse]
    total: int


class RegistroComunicacaoResponse(BaseModel):
    registro_id: uuid.UUID
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    responsavel_id: uuid.UUID | None
    canal: CanalComunicacao
    ocorrido_em: datetime
    resumo: str
    resultado: str
    devedor_id: uuid.UUID | None
    emprestimo_id: uuid.UUID | None
    cobranca_acao_id: uuid.UUID | None
    agenda_item_id: uuid.UUID | None


class HistoricoComunicacaoResponse(BaseModel):
    registros: list[RegistroComunicacaoResponse]
    total: int


class ResumoCarteiraResponse(BaseModel):
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    data_referencia: date
    total_operacoes: int
    operacoes_ativas: int
    operacoes_quitadas: int
    acertos_pendentes: int
    principal_a_receber: Decimal
    total_realizado: Decimal


class VencimentoOperacionalResponse(BaseModel):
    emprestimo_id: uuid.UUID
    devedor_id: uuid.UUID
    dia_de_acerto: int
    acerto_em: date
    dias_sem_pagamento: int
    principal_original: Decimal
    situacao: str


class VencimentosInadimplenciaResponse(BaseModel):
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    data_referencia: date
    itens: list[VencimentoOperacionalResponse]
    total: int


class PagamentoOperacionalResponse(BaseModel):
    pagamento_id: uuid.UUID
    emprestimo_id: uuid.UUID
    recebido_em: date
    valor_recebido: Decimal
    estado: PagamentoState


class PagamentosEncerramentosResponse(BaseModel):
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    inicio: date
    fim: date
    pagamentos: list[PagamentoOperacionalResponse]
    operacoes_quitadas: list[uuid.UUID]
    total_realizado: Decimal


class FluxoDiaResponse(BaseModel):
    data: date
    realizado: Decimal
    acertos: int
    pagamento_ids: list[uuid.UUID]


class FluxoPrevistoRealizadoResponse(BaseModel):
    tenant_id: uuid.UUID
    carteira_id: uuid.UUID
    inicio: date
    fim: date
    itens: list[FluxoDiaResponse]
