"""Unit of Work SQLAlchemy — transação única (AD-001, IMP-014).

O UnitOfWork abre uma sessão própria, expõe os repositórios de domínio e o
registro de idempotência compartilhando a mesma transação, e só executa
commit no fim. Nenhum repositório executa commit; qualquer exceção dispara
rollback automático no ``__exit__``.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from emprestimo.application.ports import UnitOfWork
from emprestimo.infrastructure.idempotencia import SqlAlchemyIdempotenciaRegistro
from emprestimo.infrastructure.repositories import (
    SqlAlchemyAcaoCobrancaRepository,
    SqlAlchemyAgendaItemRepository,
    SqlAlchemyApropriacaoPagamentoRepository,
    SqlAlchemyCalendarioFinanceiroRepository,
    SqlAlchemyCarteiraRepository,
    SqlAlchemyCobrancaCasoRepository,
    SqlAlchemyConfiguracaoFinanceiraRepository,
    SqlAlchemyConfiguracaoRepository,
    SqlAlchemyContatoRepository,
    SqlAlchemyContratoCreditoRepository,
    SqlAlchemyCredencialRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyEmprestimoRepository,
    SqlAlchemyEventoFinanceiroRepository,
    SqlAlchemyJobAgendadoRepository,
    SqlAlchemyLembreteRepository,
    SqlAlchemyMemoriaCalculoRepository,
    SqlAlchemyModalidadeFinanceiraRepository,
    SqlAlchemyPagamentoRepository,
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyPermissaoRepository,
    SqlAlchemyPreferenciaNotificacaoRepository,
    SqlAlchemyPromessaPagamentoRepository,
    SqlAlchemyPropostaComercialRepository,
    SqlAlchemyRegistroComunicacaoRepository,
    SqlAlchemyRelatorioOperacionalCacheRepository,
    SqlAlchemySessaoRepository,
    SqlAlchemySimulacaoComercialRepository,
    SqlAlchemySolicitacaoNotificacaoRepository,
    SqlAlchemyTemplateNotificacaoRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyTentativaJobRepository,
    SqlAlchemyTokenAtivacaoRepository,
    SqlAlchemyUsuarioRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Implementação SQLAlchemy do Unit of Work (AD-001)."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session = session_factory()
        self.tenant = SqlAlchemyTenantRepository(self._session)
        self.usuario = SqlAlchemyUsuarioRepository(self._session)
        self.configuracao = SqlAlchemyConfiguracaoRepository(self._session)
        self.credencial = SqlAlchemyCredencialRepository(self._session)
        self.sessao = SqlAlchemySessaoRepository(self._session)
        self.token_ativacao = SqlAlchemyTokenAtivacaoRepository(self._session)
        self.permissao = SqlAlchemyPermissaoRepository(self._session)
        self.perfil_acesso = SqlAlchemyPerfilAcessoRepository(self._session)
        self.carteira = SqlAlchemyCarteiraRepository(self._session)
        self.devedor = SqlAlchemyDevedorRepository(self._session)
        self.contato = SqlAlchemyContatoRepository(self._session)
        self.cobranca_caso = SqlAlchemyCobrancaCasoRepository(self._session)
        self.acao_cobranca = SqlAlchemyAcaoCobrancaRepository(self._session)
        self.promessa_pagamento = SqlAlchemyPromessaPagamentoRepository(self._session)
        self.apropriacao_pagamento = SqlAlchemyApropriacaoPagamentoRepository(self._session)
        self.agenda_item = SqlAlchemyAgendaItemRepository(self._session)
        self.lembrete = SqlAlchemyLembreteRepository(self._session)
        self.registro_comunicacao = SqlAlchemyRegistroComunicacaoRepository(self._session)
        self.relatorio_operacional_cache = SqlAlchemyRelatorioOperacionalCacheRepository(
            self._session
        )
        self.modalidade_financeira = SqlAlchemyModalidadeFinanceiraRepository(self._session)
        self.calendario_financeiro = SqlAlchemyCalendarioFinanceiroRepository(self._session)
        self.configuracao_financeira = SqlAlchemyConfiguracaoFinanceiraRepository(self._session)
        self.simulacao_comercial = SqlAlchemySimulacaoComercialRepository(self._session)
        self.proposta_comercial = SqlAlchemyPropostaComercialRepository(self._session)
        self.contrato_credito = SqlAlchemyContratoCreditoRepository(self._session)
        self.emprestimo = SqlAlchemyEmprestimoRepository(self._session)
        self.pagamento = SqlAlchemyPagamentoRepository(self._session)
        self.memoria_calculo = SqlAlchemyMemoriaCalculoRepository(self._session)
        self.evento_financeiro = SqlAlchemyEventoFinanceiroRepository(self._session)
        self.job_agendado = SqlAlchemyJobAgendadoRepository(self._session)
        self.tentativa_job = SqlAlchemyTentativaJobRepository(self._session)
        self.preferencia_notificacao = SqlAlchemyPreferenciaNotificacaoRepository(self._session)
        self.template_notificacao = SqlAlchemyTemplateNotificacaoRepository(self._session)
        self.solicitacao_notificacao = SqlAlchemySolicitacaoNotificacaoRepository(self._session)
        self.idempotencia = SqlAlchemyIdempotenciaRegistro(self._session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()
