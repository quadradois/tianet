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
    SqlAlchemyCarteiraRepository,
    SqlAlchemyConfiguracaoRepository,
    SqlAlchemyContatoRepository,
    SqlAlchemyContratoCreditoRepository,
    SqlAlchemyCredencialRepository,
    SqlAlchemyDevedorRepository,
    SqlAlchemyEmprestimoRepository,
    SqlAlchemyEventoFinanceiroRepository,
    SqlAlchemyMemoriaCalculoRepository,
    SqlAlchemyPagamentoRepository,
    SqlAlchemyParcelaRepository,
    SqlAlchemyPerfilAcessoRepository,
    SqlAlchemyPermissaoRepository,
    SqlAlchemyPropostaComercialRepository,
    SqlAlchemySessaoRepository,
    SqlAlchemySimulacaoComercialRepository,
    SqlAlchemyTenantRepository,
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
        self.simulacao_comercial = SqlAlchemySimulacaoComercialRepository(self._session)
        self.proposta_comercial = SqlAlchemyPropostaComercialRepository(self._session)
        self.contrato_credito = SqlAlchemyContratoCreditoRepository(self._session)
        self.emprestimo = SqlAlchemyEmprestimoRepository(self._session)
        self.parcela = SqlAlchemyParcelaRepository(self._session)
        self.pagamento = SqlAlchemyPagamentoRepository(self._session)
        self.memoria_calculo = SqlAlchemyMemoriaCalculoRepository(self._session)
        self.evento_financeiro = SqlAlchemyEventoFinanceiroRepository(self._session)
        self.idempotencia = SqlAlchemyIdempotenciaRegistro(self._session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()
