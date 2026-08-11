"""Ports da camada de Aplicação (TASK-043, IMP-014..IMP-016).

A camada de Aplicação depende de contratos (ABCs); a Infrastructure
implementa. Idempotência e Auditoria são preocupações técnicas de
aplicação, não regras de domínio — por isso seus contratos vivem aqui e
não em ``domain``.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from emprestimo.domain.credit.ports import (
    AcaoCobrancaRepository,
    AgendaItemRepository,
    ApropriacaoPagamentoRepository,
    CarteiraRepository,
    CobrancaCasoRepository,
    ContatoRepository,
    ContratoCreditoRepository,
    DevedorRepository,
    EmprestimoRepository,
    EventoFinanceiroRepository,
    LembreteRepository,
    MemoriaCalculoRepository,
    PagamentoRepository,
    ParcelaRepository,
    PromessaPagamentoRepository,
    PropostaComercialRepository,
    RegistroComunicacaoRepository,
    RelatorioOperacionalCacheRepository,
    SimulacaoComercialRepository,
)
from emprestimo.domain.platform.ports import (
    ConfiguracaoRepository,
    CredencialRepository,
    PerfilAcessoRepository,
    PermissaoRepository,
    SessaoRepository,
    TenantRepository,
    TokenAtivacaoRepository,
    UsuarioRepository,
)


class IdempotenciaRegistro(ABC):
    """Registro de Idempotency-Keys com constraint único (AD-002, IMP-015).

    O registro pertence à mesma transação do caso de uso (Unit of Work):
    a chave só fica visível como concluída junto com o resultado persistido.

    A identidade do registro é o par ``(chave, escopo)``, não a chave sozinha
    (TASK-100): a mesma chave em casos de uso distintos designa operações
    distintas. Por isso ``escopo`` é obrigatório nas três operações — antes ele
    era gravado por ``registrar`` e ignorado na busca, o que fazia um cadastro
    e uma inativação com a mesma chave colidirem indevidamente.
    """

    @abstractmethod
    def registrar(self, chave: str, escopo: str, solicitacao_hash: str) -> None: ...

    @abstractmethod
    def find_by_chave(self, chave: str, escopo: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def concluir(self, chave: str, escopo: str, resultado: str) -> None: ...


class AuditoriaRegistro(ABC):
    """Trilha append-only e imutável do provisionamento (IMP-016).

    Persiste em sessão independente: os registros de início/falha/rollback
    sobrevivem ao rollback da transação de negócio (AD-001).
    """

    @abstractmethod
    def registrar(
        self,
        entidade: str,
        entidade_id: uuid.UUID | None,
        acao: str,
        status: str,
        detalhes: str | None = None,
    ) -> None: ...


@dataclass(frozen=True)
class EventoAuditoria:
    """Um evento da trilha append-only, para leitura (US-027).

    Espelha uma linha de ``audit_log``. Imutável: a trilha é somente INSERT.
    """

    id: uuid.UUID
    entidade: str
    entidade_id: uuid.UUID | None
    acao: str
    status: str
    detalhes: str | None
    criado_em: datetime


class AuditoriaConsulta(ABC):
    """Leitura da trilha append-only (US-027, ADR-002).

    Contrato separado de ``AuditoriaRegistro``: escrever e ler a trilha são
    responsabilidades distintas, e a leitura não deve poder gravar.
    """

    @abstractmethod
    def listar_por_entidade(
        self, entidade: str, entidade_id: uuid.UUID
    ) -> list[EventoAuditoria]: ...


class UnitOfWork(ABC):
    """Fronteira transacional única do caso de uso (AD-001, IMP-014).

    Expõe os repositórios e o registro de idempotência compartilhando a
    mesma sessão/transação. Commit apenas ao final; qualquer exceção
    dispara rollback automático no ``__exit__``. Nenhum repositório
    executa commit.
    """

    tenant: TenantRepository
    usuario: UsuarioRepository
    configuracao: ConfiguracaoRepository
    credencial: CredencialRepository
    sessao: SessaoRepository
    token_ativacao: TokenAtivacaoRepository
    permissao: PermissaoRepository
    perfil_acesso: PerfilAcessoRepository
    carteira: CarteiraRepository
    devedor: DevedorRepository
    contato: ContatoRepository
    cobranca_caso: CobrancaCasoRepository
    acao_cobranca: AcaoCobrancaRepository
    promessa_pagamento: PromessaPagamentoRepository
    apropriacao_pagamento: ApropriacaoPagamentoRepository
    agenda_item: AgendaItemRepository
    lembrete: LembreteRepository
    registro_comunicacao: RegistroComunicacaoRepository
    relatorio_operacional_cache: RelatorioOperacionalCacheRepository
    simulacao_comercial: SimulacaoComercialRepository
    proposta_comercial: PropostaComercialRepository
    contrato_credito: ContratoCreditoRepository
    emprestimo: EmprestimoRepository
    parcela: ParcelaRepository
    pagamento: PagamentoRepository
    memoria_calculo: MemoriaCalculoRepository
    evento_financeiro: EventoFinanceiroRepository
    idempotencia: IdempotenciaRegistro

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is not None:
            self.rollback()
        self.close()
