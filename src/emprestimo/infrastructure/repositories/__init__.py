"""Implementações dos repositórios (Repository Pattern — ADR-001).

Os repositórios apenas adicionam/flusham na sessão; o commit e o controle
transacional pertencem ao Unit of Work da fase de Aplicação (IMP-014).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from math import ceil

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from emprestimo.domain.common.errors import (
    DevedorJaExisteError,
    PerfilJaExisteError,
    TenantJaExisteError,
    ViolacaoInvarianteError,
)
from emprestimo.domain.credit.carteira import Carteira
from emprestimo.domain.credit.contato import Contato, TipoContato
from emprestimo.domain.credit.contrato_credito import ContratoCredito
from emprestimo.domain.credit.contrato_credito_state import ContratoCreditoState
from emprestimo.domain.credit.decisao_comercial import DecisaoComercial
from emprestimo.domain.credit.decisao_contrato import DecisaoContrato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento
from emprestimo.domain.credit.emprestimo import Emprestimo, EmprestimoState
from emprestimo.domain.credit.eventos_financeiros import (
    EmprestimoQuitado,
    EmprestimoRenegociado,
    EventoFinanceiro,
    PagamentoRegistrado,
)
from emprestimo.domain.credit.financeiro import PeriodoFinanceiro
from emprestimo.domain.credit.memoria_calculo import MemoriaCalculo, PassoCalculo
from emprestimo.domain.credit.pagamento import Pagamento, PagamentoState
from emprestimo.domain.credit.parcela import Parcela, ParcelaState
from emprestimo.domain.credit.ports import (
    CarteiraRepository,
    ContatoRepository,
    ContratoCreditoFiltros,
    ContratoCreditoRepository,
    ContratoCreditoResultadoPaginado,
    DevedorFiltros,
    DevedorRepository,
    DevedorResultadoPaginado,
    DevedorUniquenessChecker,
    EmprestimoFiltros,
    EmprestimoRepository,
    EmprestimoResultadoPaginado,
    EventoFinanceiroRepository,
    MemoriaCalculoRepository,
    PagamentoRepository,
    Paginacao,
    ParcelaRepository,
    PropostaComercialFiltros,
    PropostaComercialRepository,
    PropostaComercialResultadoPaginado,
    SimulacaoComercialRepository,
)
from emprestimo.domain.credit.proposta_comercial import PropostaComercial
from emprestimo.domain.credit.proposta_comercial_state import PropostaComercialState
from emprestimo.domain.credit.simulacao_comercial import SimulacaoComercial
from emprestimo.domain.platform.configuracao import Configuracao
from emprestimo.domain.platform.credencial import Credencial
from emprestimo.domain.platform.perfil import PerfilAcesso, PerfilState
from emprestimo.domain.platform.permissao import Permissao, normalizar_codigo_permissao
from emprestimo.domain.platform.ports import (
    ConfiguracaoRepository,
    CredencialRepository,
    PerfilAcessoRepository,
    PermissaoRepository,
    SessaoRepository,
    TenantFiltro,
    TenantOrdenacao,
    TenantPaginado,
    TenantRepository,
    TokenAtivacaoRepository,
    UsuarioRepository,
)
from emprestimo.domain.platform.sessao import Sessao
from emprestimo.domain.platform.tenant import Tenant, TenantState
from emprestimo.domain.platform.token_ativacao import TokenAtivacao
from emprestimo.domain.platform.usuario import Usuario, UsuarioState
from emprestimo.infrastructure.db.orm import (
    CarteiraORM,
    ConfiguracaoORM,
    ContatoORM,
    ContratoCreditoORM,
    CredencialORM,
    DecisaoComercialORM,
    DevedorORM,
    EmprestimoORM,
    EventoContratoORM,
    EventoFinanceiroORM,
    MemoriaCalculoORM,
    PagamentoORM,
    ParcelaORM,
    PerfilAcessoORM,
    PerfilPermissaoORM,
    PermissaoORM,
    PropostaComercialORM,
    SessaoORM,
    SimulacaoComercialORM,
    TenantORM,
    TokenAtivacaoORM,
    UsuarioORM,
    UsuarioPerfilORM,
)
from emprestimo.infrastructure.repositories.configuracoes_financeiras import (
    SqlAlchemyCalendarioFinanceiroRepository as SqlAlchemyCalendarioFinanceiroRepository,
)
from emprestimo.infrastructure.repositories.configuracoes_financeiras import (
    SqlAlchemyConfiguracaoFinanceiraRepository as SqlAlchemyConfiguracaoFinanceiraRepository,
)
from emprestimo.infrastructure.repositories.configuracoes_financeiras import (
    SqlAlchemyModalidadeFinanceiraRepository as SqlAlchemyModalidadeFinanceiraRepository,
)
from emprestimo.infrastructure.repositories.operacao_diaria import (
    SqlAlchemyAcaoCobrancaRepository as SqlAlchemyAcaoCobrancaRepository,
)
from emprestimo.infrastructure.repositories.operacao_diaria import (
    SqlAlchemyAgendaItemRepository as SqlAlchemyAgendaItemRepository,
)
from emprestimo.infrastructure.repositories.operacao_diaria import (
    SqlAlchemyApropriacaoPagamentoRepository as SqlAlchemyApropriacaoPagamentoRepository,
)
from emprestimo.infrastructure.repositories.operacao_diaria import (
    SqlAlchemyCobrancaCasoRepository as SqlAlchemyCobrancaCasoRepository,
)
from emprestimo.infrastructure.repositories.operacao_diaria import (
    SqlAlchemyLembreteRepository as SqlAlchemyLembreteRepository,
)
from emprestimo.infrastructure.repositories.operacao_diaria import (
    SqlAlchemyPromessaPagamentoRepository as SqlAlchemyPromessaPagamentoRepository,
)
from emprestimo.infrastructure.repositories.operacao_diaria import (
    SqlAlchemyRegistroComunicacaoRepository as SqlAlchemyRegistroComunicacaoRepository,
)
from emprestimo.infrastructure.repositories.operacao_diaria import (
    SqlAlchemyRelatorioOperacionalCacheRepository as SqlAlchemyRelatorioOperacionalCacheRepository,
)


class SqlAlchemyTenantRepository(TenantRepository):
    """Implementação SQLAlchemy do TenantRepository (IMP-004)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, tenant: Tenant) -> None:
        try:
            self._session.merge(
                TenantORM(
                    id=tenant.id,
                    identificador_institucional=tenant.identificador_institucional,
                    nome=tenant.nome,
                    estado=tenant.estado.value,
                    criado_em=tenant.criado_em,
                )
            )
            self._session.flush()
        except IntegrityError as exc:
            if "uq_tenant_identificador_institucional" in str(exc.orig):
                raise TenantJaExisteError(tenant.identificador_institucional) from exc
            raise

    def find_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        row = self._session.get(TenantORM, tenant_id)
        return _to_tenant(row) if row is not None else None

    def find_by_identificador_institucional(self, identificador: str) -> Tenant | None:
        row = self._session.scalar(
            select(TenantORM).where(TenantORM.identificador_institucional == identificador)
        )
        return _to_tenant(row) if row is not None else None

    def find_all_paginated(
        self,
        page: int = 1,
        size: int = 20,
        ordenacao: TenantOrdenacao | None = None,
        filtro: TenantFiltro | None = None,
    ) -> TenantPaginado:
        # Validar e limitar parâmetros
        page = max(1, page)
        size = min(max(1, size), 100)

        # Base query
        query = select(TenantORM)
        count_query = select(func.count(TenantORM.id))

        # Aplicar filtro de estado
        if filtro and filtro.estado is not None:
            query = query.where(TenantORM.estado == filtro.estado.value)
            count_query = count_query.where(TenantORM.estado == filtro.estado.value)

        # Total count
        total = self._session.scalar(count_query) or 0

        # Aplicar ordenação
        if ordenacao is None:
            ordenacao = TenantOrdenacao()

        order_column = getattr(TenantORM, ordenacao.campo, TenantORM.criado_em)
        order_column = order_column.desc() if ordenacao.direcao == "desc" else order_column.asc()
        # Adicionar id como tie-breaker para ordenação determinística
        query = query.order_by(order_column, TenantORM.id.asc())

        # Paginação
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        rows = self._session.scalars(query).all()
        items = [_to_tenant(row) for row in rows]

        pages = ceil(total / size) if size > 0 else 0

        return TenantPaginado(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    def find_all(self) -> list[Tenant]:
        rows = self._session.scalars(select(TenantORM).order_by(TenantORM.criado_em)).all()
        return [_to_tenant(row) for row in rows]


class SqlAlchemyUsuarioRepository(UsuarioRepository):
    """Implementação SQLAlchemy do UsuarioRepository (IMP-005)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, usuario: Usuario) -> None:
        self._session.merge(
            UsuarioORM(
                id=usuario.id,
                tenant_id=usuario.tenant_id,
                nome=usuario.nome,
                email=usuario.email,
                perfil_acesso=usuario.perfil_acesso,
                estado=usuario.estado.value,
                criado_em=usuario.criado_em,
            )
        )

    def find_by_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        row = self._session.get(UsuarioORM, usuario_id)
        return _to_usuario(row) if row is not None else None

    def find_by_email(self, email: str) -> Usuario | None:
        row = self._session.scalar(select(UsuarioORM).where(UsuarioORM.email == email.strip()))
        return _to_usuario(row) if row is not None else None

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Usuario]:
        rows = self._session.scalars(
            select(UsuarioORM).where(UsuarioORM.tenant_id == tenant_id)
        ).all()
        return [_to_usuario(row) for row in rows]


class SqlAlchemyConfiguracaoRepository(ConfiguracaoRepository):
    """Implementação SQLAlchemy do ConfiguracaoRepository (IMP-006)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, configuracao: Configuracao) -> None:
        self._session.merge(
            ConfiguracaoORM(
                id=configuracao.id,
                tenant_id=configuracao.tenant_id,
                chave=configuracao.chave,
                valor=configuracao.valor,
                criado_em=configuracao.criado_em,
            )
        )

    def find_by_id(self, configuracao_id: uuid.UUID) -> Configuracao | None:
        row = self._session.get(ConfiguracaoORM, configuracao_id)
        return _to_configuracao(row) if row is not None else None

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Configuracao]:
        rows = self._session.scalars(
            select(ConfiguracaoORM).where(ConfiguracaoORM.tenant_id == tenant_id)
        ).all()
        return [_to_configuracao(row) for row in rows]


class SqlAlchemyCredencialRepository(CredencialRepository):
    """Implementacao SQLAlchemy do CredencialRepository (IMP-086)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, credencial: Credencial) -> None:
        self._session.merge(
            CredencialORM(
                id=credencial.id,
                usuario_id=credencial.usuario_id,
                hash_credencial=credencial.hash_credencial,
                algoritmo=credencial.algoritmo,
                criado_em=credencial.criado_em,
                atualizado_em=credencial.atualizado_em,
            )
        )
        self._session.flush()

    def find_by_id(self, credencial_id: uuid.UUID) -> Credencial | None:
        row = self._session.get(CredencialORM, credencial_id)
        return _to_credencial(row) if row is not None else None

    def find_by_usuario_id(self, usuario_id: uuid.UUID) -> Credencial | None:
        row = self._session.scalar(
            select(CredencialORM).where(CredencialORM.usuario_id == usuario_id)
        )
        return _to_credencial(row) if row is not None else None


class SqlAlchemyTokenAtivacaoRepository(TokenAtivacaoRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, token: TokenAtivacao) -> None:
        self._session.merge(
            TokenAtivacaoORM(
                id=token.id,
                usuario_id=token.usuario_id,
                tenant_id=token.tenant_id,
                token_hash=token.token_hash,
                expira_em=token.expira_em,
                criado_em=token.criado_em,
                utilizado_em=token.utilizado_em,
            )
        )
        self._session.flush()

    def find_by_id(self, token_id: uuid.UUID) -> TokenAtivacao | None:
        row = self._session.scalar(
            select(TokenAtivacaoORM).where(TokenAtivacaoORM.id == token_id).with_for_update()
        )
        if row is None:
            return None
        return TokenAtivacao(
            id=row.id,
            usuario_id=row.usuario_id,
            tenant_id=row.tenant_id,
            token_hash=row.token_hash,
            expira_em=row.expira_em,
            criado_em=row.criado_em,
            utilizado_em=row.utilizado_em,
        )


class SqlAlchemySessaoRepository(SessaoRepository):
    """Implementacao SQLAlchemy do SessaoRepository (IMP-086)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, sessao: Sessao) -> None:
        self._session.merge(
            SessaoORM(
                id=sessao.id,
                usuario_id=sessao.usuario_id,
                tenant_id=sessao.tenant_id,
                refresh_token_hash=sessao.refresh_token_hash,
                expira_em=sessao.expira_em,
                criado_em=sessao.criado_em,
                revogado_em=sessao.revogado_em,
            )
        )
        self._session.flush()

    def find_by_id(self, sessao_id: uuid.UUID) -> Sessao | None:
        row = self._session.get(SessaoORM, sessao_id)
        return _to_sessao(row) if row is not None else None

    def find_by_usuario_id(self, usuario_id: uuid.UUID) -> list[Sessao]:
        rows = self._session.scalars(
            select(SessaoORM)
            .where(SessaoORM.usuario_id == usuario_id)
            .order_by(SessaoORM.criado_em, SessaoORM.id)
        ).all()
        return [_to_sessao(row) for row in rows]

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Sessao]:
        rows = self._session.scalars(
            select(SessaoORM)
            .where(SessaoORM.tenant_id == tenant_id)
            .order_by(SessaoORM.criado_em, SessaoORM.id)
        ).all()
        return [_to_sessao(row) for row in rows]


class SqlAlchemyPermissaoRepository(PermissaoRepository):
    """Implementacao SQLAlchemy do catalogo de Permissoes (IMP-086)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, permissao: Permissao) -> None:
        self._session.merge(
            PermissaoORM(
                codigo=permissao.codigo,
                descricao=permissao.descricao,
            )
        )
        self._session.flush()

    def find_by_codigo(self, codigo: str) -> Permissao | None:
        row = self._session.get(PermissaoORM, normalizar_codigo_permissao(codigo))
        return _to_permissao(row) if row is not None else None

    def find_all(self) -> list[Permissao]:
        rows = self._session.scalars(select(PermissaoORM).order_by(PermissaoORM.codigo)).all()
        return [_to_permissao(row) for row in rows]


class SqlAlchemyPerfilAcessoRepository(PerfilAcessoRepository):
    """Implementacao SQLAlchemy do PerfilAcessoRepository (IMP-086)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, perfil: PerfilAcesso) -> None:
        try:
            self._save(perfil)
        except IntegrityError as exc:
            if "uq_perfil_tenant_nome" in str(exc):
                raise PerfilJaExisteError() from exc
            raise

    def _save(self, perfil: PerfilAcesso) -> None:
        self._session.merge(
            PerfilAcessoORM(
                id=perfil.id,
                tenant_id=perfil.tenant_id,
                nome=perfil.nome,
                estado=perfil.estado.value,
                criado_em=perfil.criado_em,
                atualizado_em=perfil.atualizado_em,
            )
        )
        self._session.execute(
            delete(PerfilPermissaoORM).where(PerfilPermissaoORM.perfil_id == perfil.id)
        )
        for permissao in perfil.permissoes:
            self._session.merge(
                PermissaoORM(
                    codigo=permissao.codigo,
                    descricao=permissao.descricao,
                )
            )
            self._session.merge(
                PerfilPermissaoORM(
                    perfil_id=perfil.id,
                    permissao_codigo=permissao.codigo,
                )
            )
        self._session.flush()

    def find_by_id(self, perfil_id: uuid.UUID) -> PerfilAcesso | None:
        row = self._session.get(PerfilAcessoORM, perfil_id)
        if row is None:
            return None
        return _to_perfil_acesso(row, self._permissoes_de([row.id]).get(row.id, []))

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[PerfilAcesso]:
        rows = self._session.scalars(
            select(PerfilAcessoORM)
            .where(PerfilAcessoORM.tenant_id == tenant_id)
            .order_by(PerfilAcessoORM.nome, PerfilAcessoORM.id)
        ).all()
        permissoes = self._permissoes_de([row.id for row in rows])
        return [_to_perfil_acesso(row, permissoes.get(row.id, [])) for row in rows]

    def find_by_tenant_nome(self, tenant_id: uuid.UUID, nome: str) -> PerfilAcesso | None:
        row = self._session.scalar(
            select(PerfilAcessoORM).where(
                PerfilAcessoORM.tenant_id == tenant_id,
                PerfilAcessoORM.nome == nome.strip(),
            )
        )
        if row is None:
            return None
        return _to_perfil_acesso(row, self._permissoes_de([row.id]).get(row.id, []))

    def atribuir_usuario(self, usuario_id: uuid.UUID, perfil_id: uuid.UUID) -> None:
        usuario_tenant_id = self._session.scalar(
            select(UsuarioORM.tenant_id).where(UsuarioORM.id == usuario_id)
        )
        perfil_tenant_id = self._session.scalar(
            select(PerfilAcessoORM.tenant_id).where(PerfilAcessoORM.id == perfil_id)
        )
        if (
            usuario_tenant_id is not None
            and perfil_tenant_id is not None
            and usuario_tenant_id != perfil_tenant_id
        ):
            raise ViolacaoInvarianteError(
                "IAM-001",
                "Usuario e Perfil de Acesso devem pertencer ao mesmo Tenant",
            )
        self._session.execute(
            delete(UsuarioPerfilORM).where(UsuarioPerfilORM.usuario_id == usuario_id)
        )
        self._session.add(UsuarioPerfilORM(usuario_id=usuario_id, perfil_id=perfil_id))
        self._session.flush()

    def remover_usuario(self, usuario_id: uuid.UUID) -> None:
        self._session.execute(
            delete(UsuarioPerfilORM).where(UsuarioPerfilORM.usuario_id == usuario_id)
        )

    def find_by_usuario_id(self, usuario_id: uuid.UUID) -> PerfilAcesso | None:
        row = self._session.scalar(
            select(PerfilAcessoORM)
            .join(UsuarioPerfilORM, UsuarioPerfilORM.perfil_id == PerfilAcessoORM.id)
            .where(UsuarioPerfilORM.usuario_id == usuario_id)
        )
        if row is None:
            return None
        return _to_perfil_acesso(row, self._permissoes_de([row.id]).get(row.id, []))

    def exists_with_permission(self, codigo: str) -> bool:
        return (
            self._session.scalar(
                select(PerfilPermissaoORM.perfil_id)
                .where(PerfilPermissaoORM.permissao_codigo == codigo.strip().lower())
                .limit(1)
            )
            is not None
        )

    def tenant_has_permission(self, tenant_id: uuid.UUID, codigo: str) -> bool:
        return (
            self._session.scalar(
                select(PerfilPermissaoORM.perfil_id)
                .join(
                    PerfilAcessoORM,
                    PerfilAcessoORM.id == PerfilPermissaoORM.perfil_id,
                )
                .where(
                    PerfilAcessoORM.tenant_id == tenant_id,
                    PerfilPermissaoORM.permissao_codigo == codigo.strip().lower(),
                )
                .limit(1)
            )
            is not None
        )

    def count_usuarios(self, perfil_id: uuid.UUID) -> int:
        return (
            self._session.scalar(
                select(func.count())
                .select_from(UsuarioPerfilORM)
                .where(UsuarioPerfilORM.perfil_id == perfil_id)
            )
            or 0
        )

    def _permissoes_de(self, perfil_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Permissao]]:
        if not perfil_ids:
            return {}
        rows = self._session.execute(
            select(PerfilPermissaoORM.perfil_id, PermissaoORM)
            .join(
                PermissaoORM,
                PermissaoORM.codigo == PerfilPermissaoORM.permissao_codigo,
            )
            .where(PerfilPermissaoORM.perfil_id.in_(perfil_ids))
            .order_by(PerfilPermissaoORM.perfil_id, PermissaoORM.codigo)
        ).all()
        permissoes: dict[uuid.UUID, list[Permissao]] = {}
        for perfil_id, permissao_row in rows:
            permissoes.setdefault(perfil_id, []).append(_to_permissao(permissao_row))
        return permissoes


class SqlAlchemyCarteiraRepository(CarteiraRepository):
    """Implementação SQLAlchemy do CarteiraRepository (IMP-007)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, carteira: Carteira) -> None:
        self._session.merge(
            CarteiraORM(
                id=carteira.id,
                tenant_id=carteira.tenant_id,
                nome=carteira.nome,
                criado_em=carteira.criado_em,
            )
        )

    def find_by_id(self, carteira_id: uuid.UUID) -> Carteira | None:
        row = self._session.get(CarteiraORM, carteira_id)
        return _to_carteira(row) if row is not None else None

    def find_by_tenant_id(self, tenant_id: uuid.UUID) -> list[Carteira]:
        rows = self._session.scalars(
            select(CarteiraORM).where(CarteiraORM.tenant_id == tenant_id)
        ).all()
        return [_to_carteira(row) for row in rows]


class SqlAlchemySimulacaoComercialRepository(SimulacaoComercialRepository):
    """Implementacao SQLAlchemy do SimulacaoComercialRepository (IMP-111)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, simulacao: SimulacaoComercial) -> None:
        self._session.merge(
            SimulacaoComercialORM(
                id=simulacao.id,
                tenant_id=simulacao.tenant_id,
                carteira_id=simulacao.carteira_id,
                devedor_id=simulacao.devedor_id,
                criada_por_usuario_id=simulacao.criada_por_usuario_id,
                parametros=simulacao.parametros,
                criado_em=simulacao.criado_em,
            )
        )
        self._session.flush()

    def find_by_id(self, simulacao_id: uuid.UUID) -> SimulacaoComercial | None:
        row = self._session.get(SimulacaoComercialORM, simulacao_id)
        return _to_simulacao_comercial(row) if row is not None else None

    def find_by_devedor(self, devedor_id: uuid.UUID) -> list[SimulacaoComercial]:
        rows = self._session.scalars(
            select(SimulacaoComercialORM)
            .where(SimulacaoComercialORM.devedor_id == devedor_id)
            .order_by(SimulacaoComercialORM.criado_em, SimulacaoComercialORM.id)
        ).all()
        return [_to_simulacao_comercial(row) for row in rows]


class SqlAlchemyPropostaComercialRepository(PropostaComercialRepository):
    """Implementacao SQLAlchemy do PropostaComercialRepository (IMP-111)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, proposta: PropostaComercial) -> None:
        self._session.merge(
            PropostaComercialORM(
                id=proposta.id,
                tenant_id=proposta.tenant_id,
                carteira_id=proposta.carteira_id,
                devedor_id=proposta.devedor_id,
                criada_por_usuario_id=proposta.criada_por_usuario_id,
                simulacao_id=proposta.simulacao_id,
                estado=proposta.estado.value,
                parametros=proposta.parametros,
                criado_em=proposta.criado_em,
                atualizado_em=proposta.atualizado_em,
                aprovada_por_usuario_id=proposta.aprovada_por_usuario_id,
                aprovada_em=proposta.aprovada_em,
            )
        )
        for ordem, decisao in enumerate(proposta.decisoes, start=1):
            self._session.merge(
                DecisaoComercialORM(
                    id=decisao.id,
                    proposta_id=decisao.proposta_id,
                    usuario_id=decisao.usuario_id,
                    estado_anterior=decisao.estado_anterior.value,
                    estado_posterior=decisao.estado_posterior.value,
                    ordem=ordem,
                    motivo=decisao.motivo,
                    criado_em=decisao.criado_em,
                )
            )
        self._session.flush()

    def find_by_id(self, proposta_id: uuid.UUID) -> PropostaComercial | None:
        row = self._session.get(PropostaComercialORM, proposta_id)
        if row is None:
            return None
        return _to_proposta_comercial(row, self._decisoes_de([row.id]).get(row.id, []))

    def listar_paginado(
        self,
        filtros: PropostaComercialFiltros,
        paginacao: Paginacao,
    ) -> PropostaComercialResultadoPaginado:
        query = select(PropostaComercialORM).where(
            PropostaComercialORM.tenant_id == filtros.tenant_id
        )
        count_query = select(func.count(PropostaComercialORM.id)).where(
            PropostaComercialORM.tenant_id == filtros.tenant_id
        )

        if filtros.carteira_id is not None:
            query = query.where(PropostaComercialORM.carteira_id == filtros.carteira_id)
            count_query = count_query.where(PropostaComercialORM.carteira_id == filtros.carteira_id)
        if filtros.devedor_id is not None:
            query = query.where(PropostaComercialORM.devedor_id == filtros.devedor_id)
            count_query = count_query.where(PropostaComercialORM.devedor_id == filtros.devedor_id)
        if filtros.estado is not None:
            query = query.where(PropostaComercialORM.estado == filtros.estado.value)
            count_query = count_query.where(PropostaComercialORM.estado == filtros.estado.value)

        total = self._session.scalar(count_query) or 0
        rows = self._session.scalars(
            query.order_by(PropostaComercialORM.criado_em, PropostaComercialORM.id)
            .offset(paginacao.offset)
            .limit(paginacao.limit)
        ).all()
        decisoes = self._decisoes_de([row.id for row in rows])
        items = [_to_proposta_comercial(row, decisoes.get(row.id, [])) for row in rows]
        return PropostaComercialResultadoPaginado(
            items=items,
            total=total,
            pagina=paginacao.pagina,
            tamanho=paginacao.tamanho,
        )

    def _decisoes_de(
        self, proposta_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[DecisaoComercial]]:
        if not proposta_ids:
            return {}
        rows = self._session.scalars(
            select(DecisaoComercialORM)
            .where(DecisaoComercialORM.proposta_id.in_(proposta_ids))
            .order_by(DecisaoComercialORM.proposta_id, DecisaoComercialORM.ordem)
        ).all()
        por_proposta: dict[uuid.UUID, list[DecisaoComercial]] = {}
        for row in rows:
            por_proposta.setdefault(row.proposta_id, []).append(_to_decisao_comercial(row))
        return por_proposta


class SqlAlchemyContratoCreditoRepository(ContratoCreditoRepository):
    """Implementacao SQLAlchemy do ContratoCreditoRepository (IMP-131)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, contrato: ContratoCredito) -> None:
        self._session.merge(
            ContratoCreditoORM(
                id=contrato.id,
                tenant_id=contrato.tenant_id,
                carteira_id=contrato.carteira_id,
                devedor_id=contrato.devedor_id,
                proposta_comercial_id=contrato.proposta_comercial_id,
                criado_por_usuario_id=contrato.criado_por_usuario_id,
                estado=contrato.estado.value,
                parametros=contrato.parametros,
                criado_em=contrato.criado_em,
                atualizado_em=contrato.atualizado_em,
                formalizado_por_usuario_id=contrato.formalizado_por_usuario_id,
                formalizado_em=contrato.formalizado_em,
                assinado_por_usuario_id=contrato.assinado_por_usuario_id,
                assinado_em=contrato.assinado_em,
                liberado_por_usuario_id=contrato.liberado_por_usuario_id,
                liberado_em=contrato.liberado_em,
                motivo_encerramento=contrato.motivo_encerramento,
            )
        )
        for ordem, decisao in enumerate(contrato.decisoes, start=1):
            self._session.merge(
                EventoContratoORM(
                    id=decisao.id,
                    contrato_id=decisao.contrato_id,
                    usuario_id=decisao.usuario_id,
                    tipo=decisao.tipo,
                    estado_anterior=decisao.estado_anterior.value,
                    estado_posterior=decisao.estado_posterior.value,
                    ordem=ordem,
                    motivo=decisao.motivo,
                    criado_em=decisao.criado_em,
                )
            )
        self._session.flush()

    def find_by_id(self, contrato_id: uuid.UUID) -> ContratoCredito | None:
        row = self._session.get(ContratoCreditoORM, contrato_id)
        if row is None:
            return None
        return _to_contrato_credito(row, self._eventos_contrato_de([row.id]).get(row.id, []))

    def find_by_proposta_id(self, proposta_id: uuid.UUID) -> ContratoCredito | None:
        row = self._session.scalar(
            select(ContratoCreditoORM).where(
                ContratoCreditoORM.proposta_comercial_id == proposta_id
            )
        )
        if row is None:
            return None
        return _to_contrato_credito(row, self._eventos_contrato_de([row.id]).get(row.id, []))

    def listar_paginado(
        self,
        filtros: ContratoCreditoFiltros,
        paginacao: Paginacao,
    ) -> ContratoCreditoResultadoPaginado:
        query = select(ContratoCreditoORM).where(ContratoCreditoORM.tenant_id == filtros.tenant_id)
        count_query = select(func.count(ContratoCreditoORM.id)).where(
            ContratoCreditoORM.tenant_id == filtros.tenant_id
        )

        if filtros.carteira_id is not None:
            query = query.where(ContratoCreditoORM.carteira_id == filtros.carteira_id)
            count_query = count_query.where(ContratoCreditoORM.carteira_id == filtros.carteira_id)
        if filtros.devedor_id is not None:
            query = query.where(ContratoCreditoORM.devedor_id == filtros.devedor_id)
            count_query = count_query.where(ContratoCreditoORM.devedor_id == filtros.devedor_id)
        if filtros.estado is not None:
            query = query.where(ContratoCreditoORM.estado == filtros.estado.value)
            count_query = count_query.where(ContratoCreditoORM.estado == filtros.estado.value)

        total = self._session.scalar(count_query) or 0
        rows = self._session.scalars(
            query.order_by(ContratoCreditoORM.criado_em, ContratoCreditoORM.id)
            .offset(paginacao.offset)
            .limit(paginacao.limit)
        ).all()
        eventos = self._eventos_contrato_de([row.id for row in rows])
        items = [_to_contrato_credito(row, eventos.get(row.id, [])) for row in rows]
        return ContratoCreditoResultadoPaginado(
            items=items,
            total=total,
            pagina=paginacao.pagina,
            tamanho=paginacao.tamanho,
        )

    def _eventos_contrato_de(
        self, contrato_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[DecisaoContrato]]:
        if not contrato_ids:
            return {}
        rows = self._session.scalars(
            select(EventoContratoORM)
            .where(EventoContratoORM.contrato_id.in_(contrato_ids))
            .order_by(EventoContratoORM.contrato_id, EventoContratoORM.ordem)
        ).all()
        por_contrato: dict[uuid.UUID, list[DecisaoContrato]] = {}
        for row in rows:
            por_contrato.setdefault(row.contrato_id, []).append(_to_decisao_contrato(row))
        return por_contrato


class SqlAlchemyEmprestimoRepository(EmprestimoRepository):
    """Implementacao SQLAlchemy do EmprestimoRepository (IMP-156)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, emprestimo: Emprestimo) -> None:
        self._session.merge(
            EmprestimoORM(
                id=emprestimo.id,
                tenant_id=emprestimo.tenant_id,
                carteira_id=emprestimo.carteira_id,
                devedor_id=emprestimo.devedor_id,
                contrato_id=emprestimo.contrato_id,
                estado=emprestimo.estado.value,
                principal_original=emprestimo.principal_original,
                moeda=emprestimo.moeda,
                parametros_financeiros=emprestimo.parametros_financeiros,
                criado_em=emprestimo.criado_em,
                atualizado_em=emprestimo.atualizado_em,
                ultimo_processamento_em=emprestimo.ultimo_processamento_em,
                ultimo_pagamento_em=emprestimo.ultimo_pagamento_em,
                proximo_vencimento_em=emprestimo.proximo_vencimento_em,
                quitado_em=emprestimo.quitado_em,
            )
        )
        self._session.flush()

    def find_by_id(self, emprestimo_id: uuid.UUID) -> Emprestimo | None:
        row = self._session.get(EmprestimoORM, emprestimo_id)
        if row is None:
            return None
        return _to_emprestimo(row, self._eventos_de([row.id]).get(row.id, []))

    def find_by_contrato_id(self, contrato_id: uuid.UUID) -> Emprestimo | None:
        row = self._session.scalar(
            select(EmprestimoORM).where(EmprestimoORM.contrato_id == contrato_id)
        )
        if row is None:
            return None
        return _to_emprestimo(row, self._eventos_de([row.id]).get(row.id, []))

    def listar_paginado(
        self,
        filtros: EmprestimoFiltros,
        paginacao: Paginacao,
    ) -> EmprestimoResultadoPaginado:
        query = select(EmprestimoORM).where(EmprestimoORM.tenant_id == filtros.tenant_id)
        count_query = select(func.count(EmprestimoORM.id)).where(
            EmprestimoORM.tenant_id == filtros.tenant_id
        )
        if filtros.carteira_id is not None:
            query = query.where(EmprestimoORM.carteira_id == filtros.carteira_id)
            count_query = count_query.where(EmprestimoORM.carteira_id == filtros.carteira_id)
        if filtros.devedor_id is not None:
            query = query.where(EmprestimoORM.devedor_id == filtros.devedor_id)
            count_query = count_query.where(EmprestimoORM.devedor_id == filtros.devedor_id)
        if filtros.estado is not None:
            query = query.where(EmprestimoORM.estado == filtros.estado.value)
            count_query = count_query.where(EmprestimoORM.estado == filtros.estado.value)

        total = self._session.scalar(count_query) or 0
        rows = self._session.scalars(
            query.order_by(EmprestimoORM.criado_em, EmprestimoORM.id)
            .offset(paginacao.offset)
            .limit(paginacao.limit)
        ).all()
        eventos = self._eventos_de([row.id for row in rows])
        return EmprestimoResultadoPaginado(
            items=[_to_emprestimo(row, eventos.get(row.id, [])) for row in rows],
            total=total,
            pagina=paginacao.pagina,
            tamanho=paginacao.tamanho,
        )

    def _eventos_de(
        self,
        emprestimo_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, list[EventoFinanceiro]]:
        if not emprestimo_ids:
            return {}
        rows = self._session.scalars(
            select(EventoFinanceiroORM)
            .where(EventoFinanceiroORM.emprestimo_id.in_(emprestimo_ids))
            .order_by(EventoFinanceiroORM.ocorrido_em, EventoFinanceiroORM.id)
        ).all()
        por_emprestimo: dict[uuid.UUID, list[EventoFinanceiro]] = {}
        for row in rows:
            por_emprestimo.setdefault(row.emprestimo_id, []).append(_to_evento_financeiro(row))
        return por_emprestimo


class SqlAlchemyParcelaRepository(ParcelaRepository):
    """Implementacao SQLAlchemy do ParcelaRepository (IMP-156)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_many(self, parcelas: Sequence[Parcela]) -> None:
        for parcela in parcelas:
            self._session.merge(_to_parcela_orm(parcela))
        self._session.flush()

    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[Parcela]:
        rows = self._session.scalars(
            select(ParcelaORM)
            .where(ParcelaORM.emprestimo_id == emprestimo_id)
            .order_by(ParcelaORM.numero, ParcelaORM.id)
        ).all()
        return [_to_parcela(row) for row in rows]


class SqlAlchemyPagamentoRepository(PagamentoRepository):
    """Implementacao SQLAlchemy do PagamentoRepository (IMP-156)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, pagamento: Pagamento) -> None:
        self._session.merge(_to_pagamento_orm(pagamento))
        self._session.flush()

    def find_by_id(self, pagamento_id: uuid.UUID) -> Pagamento | None:
        row = self._session.get(PagamentoORM, pagamento_id)
        return _to_pagamento(row) if row is not None else None

    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[Pagamento]:
        rows = self._session.scalars(
            select(PagamentoORM)
            .where(PagamentoORM.emprestimo_id == emprestimo_id)
            .order_by(PagamentoORM.recebido_em, PagamentoORM.id)
        ).all()
        return [_to_pagamento(row) for row in rows]

    def find_by_idempotency_key(
        self,
        emprestimo_id: uuid.UUID,
        chave_idempotencia: str,
    ) -> Pagamento | None:
        row = self._session.scalar(
            select(PagamentoORM).where(
                PagamentoORM.emprestimo_id == emprestimo_id,
                PagamentoORM.chave_idempotencia == chave_idempotencia,
            )
        )
        return _to_pagamento(row) if row is not None else None


class SqlAlchemyMemoriaCalculoRepository(MemoriaCalculoRepository):
    """Implementacao SQLAlchemy do MemoriaCalculoRepository (IMP-156)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(
        self,
        memoria: MemoriaCalculo,
        emprestimo_id: uuid.UUID,
        pagamento_id: uuid.UUID | None = None,
    ) -> None:
        self._session.merge(
            MemoriaCalculoORM(
                id=memoria.id,
                emprestimo_id=emprestimo_id,
                pagamento_id=pagamento_id,
                tipo=memoria.tipo,
                data_referencia=_data_referencia_from_memoria(memoria),
                entradas=dict(memoria.entradas),
                regra=dict(memoria.regra),
                periodos=[dict(periodo) for periodo in memoria.periodos],
                passos=[_passo_to_json(passo) for passo in memoria.passos],
                arredondamentos=list(memoria.arredondamentos),
                resultados=dict(memoria.resultados),
                criado_em=memoria.criado_em,
            )
        )
        self._session.flush()

    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[MemoriaCalculo]:
        rows = self._session.scalars(
            select(MemoriaCalculoORM)
            .where(MemoriaCalculoORM.emprestimo_id == emprestimo_id)
            .order_by(MemoriaCalculoORM.criado_em, MemoriaCalculoORM.id)
        ).all()
        return [_to_memoria_calculo(row) for row in rows]


class SqlAlchemyEventoFinanceiroRepository(EventoFinanceiroRepository):
    """Implementacao SQLAlchemy do EventoFinanceiroRepository (IMP-156)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, evento: EventoFinanceiro) -> None:
        self._session.merge(_to_evento_financeiro_orm(evento))
        self._session.flush()

    def find_by_emprestimo_id(self, emprestimo_id: uuid.UUID) -> list[EventoFinanceiro]:
        rows = self._session.scalars(
            select(EventoFinanceiroORM)
            .where(EventoFinanceiroORM.emprestimo_id == emprestimo_id)
            .order_by(EventoFinanceiroORM.ocorrido_em, EventoFinanceiroORM.id)
        ).all()
        return [_to_evento_financeiro(row) for row in rows]


def _to_tenant(row: TenantORM) -> Tenant:
    return Tenant(
        id=row.id,
        identificador_institucional=row.identificador_institucional,
        nome=row.nome,
        estado=TenantState(row.estado),
        criado_em=row.criado_em,
    )


def _to_usuario(row: UsuarioORM) -> Usuario:
    return Usuario(
        id=row.id,
        tenant_id=row.tenant_id,
        nome=row.nome,
        email=row.email,
        perfil_acesso=row.perfil_acesso,
        estado=UsuarioState(row.estado),
        criado_em=row.criado_em,
    )


def _to_configuracao(row: ConfiguracaoORM) -> Configuracao:
    return Configuracao(
        id=row.id,
        tenant_id=row.tenant_id,
        chave=row.chave,
        valor=row.valor,
        criado_em=row.criado_em,
    )


def _to_credencial(row: CredencialORM) -> Credencial:
    return Credencial(
        id=row.id,
        usuario_id=row.usuario_id,
        hash_credencial=row.hash_credencial,
        algoritmo=row.algoritmo,
        criado_em=row.criado_em,
        atualizado_em=row.atualizado_em,
    )


def _to_sessao(row: SessaoORM) -> Sessao:
    return Sessao(
        id=row.id,
        usuario_id=row.usuario_id,
        tenant_id=row.tenant_id,
        refresh_token_hash=row.refresh_token_hash,
        expira_em=row.expira_em,
        criado_em=row.criado_em,
        revogado_em=row.revogado_em,
    )


def _to_permissao(row: PermissaoORM) -> Permissao:
    return Permissao(codigo=row.codigo, descricao=row.descricao)


def _to_perfil_acesso(
    row: PerfilAcessoORM, permissoes: list[Permissao] | None = None
) -> PerfilAcesso:
    perfil = PerfilAcesso(
        id=row.id,
        tenant_id=row.tenant_id,
        nome=row.nome,
        estado=PerfilState(row.estado),
        criado_em=row.criado_em,
        atualizado_em=row.atualizado_em,
    )
    perfil._permissoes = permissoes if permissoes is not None else []
    return perfil


def _to_carteira(row: CarteiraORM) -> Carteira:
    return Carteira(
        id=row.id,
        tenant_id=row.tenant_id,
        nome=row.nome,
        criado_em=row.criado_em,
    )


def _to_simulacao_comercial(row: SimulacaoComercialORM) -> SimulacaoComercial:
    return SimulacaoComercial.restaurar(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        devedor_id=row.devedor_id,
        criada_por_usuario_id=row.criada_por_usuario_id,
        parametros=row.parametros,
        criado_em=row.criado_em,
    )


def _to_decisao_comercial(row: DecisaoComercialORM) -> DecisaoComercial:
    return DecisaoComercial(
        id=row.id,
        proposta_id=row.proposta_id,
        usuario_id=row.usuario_id,
        estado_anterior=PropostaComercialState(row.estado_anterior),
        estado_posterior=PropostaComercialState(row.estado_posterior),
        motivo=row.motivo,
        criado_em=row.criado_em,
    )


def _to_proposta_comercial(
    row: PropostaComercialORM,
    decisoes: list[DecisaoComercial] | None = None,
) -> PropostaComercial:
    return PropostaComercial.restaurar(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        devedor_id=row.devedor_id,
        criada_por_usuario_id=row.criada_por_usuario_id,
        parametros=row.parametros,
        simulacao_id=row.simulacao_id,
        estado=PropostaComercialState(row.estado),
        criado_em=row.criado_em,
        atualizado_em=row.atualizado_em,
        aprovada_por_usuario_id=row.aprovada_por_usuario_id,
        aprovada_em=row.aprovada_em,
        decisoes=decisoes,
    )


def _to_decisao_contrato(row: EventoContratoORM) -> DecisaoContrato:
    return DecisaoContrato(
        id=row.id,
        contrato_id=row.contrato_id,
        usuario_id=row.usuario_id,
        tipo=row.tipo,
        estado_anterior=ContratoCreditoState(row.estado_anterior),
        estado_posterior=ContratoCreditoState(row.estado_posterior),
        motivo=row.motivo,
        criado_em=row.criado_em,
    )


def _to_contrato_credito(
    row: ContratoCreditoORM,
    decisoes: list[DecisaoContrato] | None = None,
) -> ContratoCredito:
    return ContratoCredito.restaurar(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        devedor_id=row.devedor_id,
        proposta_comercial_id=row.proposta_comercial_id,
        criado_por_usuario_id=row.criado_por_usuario_id,
        parametros=row.parametros,
        estado=ContratoCreditoState(row.estado),
        criado_em=row.criado_em,
        atualizado_em=row.atualizado_em,
        formalizado_por_usuario_id=row.formalizado_por_usuario_id,
        formalizado_em=row.formalizado_em,
        assinado_por_usuario_id=row.assinado_por_usuario_id,
        assinado_em=row.assinado_em,
        liberado_por_usuario_id=row.liberado_por_usuario_id,
        liberado_em=row.liberado_em,
        motivo_encerramento=row.motivo_encerramento,
        decisoes=decisoes,
    )


def _to_emprestimo(
    row: EmprestimoORM,
    eventos: list[EventoFinanceiro] | None = None,
) -> Emprestimo:
    emprestimo = Emprestimo.restaurar(
        id=row.id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        devedor_id=row.devedor_id,
        contrato_id=row.contrato_id,
        principal_original=row.principal_original,
        moeda=row.moeda,
        parametros_financeiros=row.parametros_financeiros,
        estado=EmprestimoState(row.estado),
        criado_em=row.criado_em,
        atualizado_em=row.atualizado_em,
        ultimo_processamento_em=row.ultimo_processamento_em,
        ultimo_pagamento_em=row.ultimo_pagamento_em,
        proximo_vencimento_em=row.proximo_vencimento_em,
        quitado_em=row.quitado_em,
    )
    emprestimo._eventos = eventos if eventos is not None else []  # type: ignore[assignment]
    return emprestimo


def _to_parcela_orm(parcela: Parcela) -> ParcelaORM:
    return ParcelaORM(
        id=parcela.id,
        emprestimo_id=parcela.emprestimo_id,
        numero=parcela.numero,
        vencimento=parcela.vencimento,
        valor_previsto=parcela.valor_previsto,
        principal=parcela.principal,
        juros=parcela.juros,
        encargos=parcela.encargos,
        valor_liquidado=parcela.valor_liquidado,
        periodo=_periodo_to_json(parcela.periodo),
        estado=parcela.estado.value,
        criada_em=parcela.criada_em,
        atualizada_em=parcela.atualizada_em,
    )


def _to_parcela(row: ParcelaORM) -> Parcela:
    return Parcela(
        id=row.id,
        emprestimo_id=row.emprestimo_id,
        numero=row.numero,
        vencimento=row.vencimento,
        valor_previsto=row.valor_previsto,
        principal=row.principal,
        juros=row.juros,
        encargos=row.encargos,
        valor_liquidado=row.valor_liquidado,
        periodo=_periodo_from_json(row.periodo),
        estado=ParcelaState(row.estado),
        criada_em=row.criada_em,
        atualizada_em=row.atualizada_em,
    )


def _to_pagamento_orm(pagamento: Pagamento) -> PagamentoORM:
    return PagamentoORM(
        id=pagamento.id,
        emprestimo_id=pagamento.emprestimo_id,
        valor_recebido=pagamento.valor_recebido,
        recebido_em=pagamento.recebido_em,
        valor_juros=pagamento.valor_juros,
        valor_amortizacao=pagamento.valor_amortizacao,
        valor_encargos=pagamento.valor_encargos,
        chave_idempotencia=pagamento.chave_idempotencia or "",
        parcelas_liquidadas=[str(parcela_id) for parcela_id in pagamento.parcelas_liquidadas],
        distribuicao=pagamento.distribuicao,
        usuario_id=pagamento.usuario_id,
        estado=pagamento.estado.value,
        criado_em=pagamento.criado_em,
    )


def _to_pagamento(row: PagamentoORM) -> Pagamento:
    return Pagamento(
        id=row.id,
        emprestimo_id=row.emprestimo_id,
        valor_recebido=row.valor_recebido,
        recebido_em=row.recebido_em,
        valor_juros=row.valor_juros,
        valor_amortizacao=row.valor_amortizacao,
        valor_encargos=row.valor_encargos,
        chave_idempotencia=row.chave_idempotencia,
        parcelas_liquidadas=tuple(uuid.UUID(valor) for valor in row.parcelas_liquidadas),
        distribuicao=row.distribuicao,
        usuario_id=row.usuario_id,
        estado=PagamentoState(row.estado),
        criado_em=row.criado_em,
    )


def _to_memoria_calculo(row: MemoriaCalculoORM) -> MemoriaCalculo:
    return MemoriaCalculo(
        id=row.id,
        tipo=row.tipo,
        entradas=row.entradas,
        regra=row.regra,
        periodos=tuple(row.periodos),
        passos=tuple(_passo_from_json(passo) for passo in row.passos),
        arredondamentos=tuple(row.arredondamentos),
        resultados=row.resultados,
        criado_em=row.criado_em,
    )


def _to_evento_financeiro_orm(evento: EventoFinanceiro) -> EventoFinanceiroORM:
    return EventoFinanceiroORM(
        id=evento.id,
        emprestimo_id=evento.emprestimo_id,
        tenant_id=evento.tenant_id,
        carteira_id=evento.carteira_id,
        devedor_id=evento.devedor_id,
        usuario_id=evento.usuario_id,
        memoria_calculo_id=evento.memoria_calculo_id,
        pagamento_id=evento.pagamento_id,
        tipo=evento.tipo,
        estado_anterior=evento.estado_anterior.value if evento.estado_anterior else None,
        estado_posterior=evento.estado_posterior.value if evento.estado_posterior else None,
        valor=evento.valor,
        detalhes=dict(evento.detalhes) if evento.detalhes is not None else None,
        ocorrido_em=evento.ocorrido_em,
    )


def _to_evento_financeiro(row: EventoFinanceiroORM) -> EventoFinanceiro:
    evento_cls = {
        "pagamento_registrado": PagamentoRegistrado,
        "emprestimo_quitado": EmprestimoQuitado,
        "emprestimo_renegociado": EmprestimoRenegociado,
    }.get(row.tipo, EventoFinanceiro)
    return evento_cls(
        id=row.id,
        emprestimo_id=row.emprestimo_id,
        tenant_id=row.tenant_id,
        carteira_id=row.carteira_id,
        devedor_id=row.devedor_id,
        usuario_id=row.usuario_id,
        memoria_calculo_id=row.memoria_calculo_id,
        pagamento_id=row.pagamento_id,
        tipo=row.tipo,
        estado_anterior=EmprestimoState(row.estado_anterior) if row.estado_anterior else None,
        estado_posterior=EmprestimoState(row.estado_posterior) if row.estado_posterior else None,
        valor=row.valor,
        detalhes=row.detalhes,
        ocorrido_em=row.ocorrido_em,
    )


def _periodo_to_json(periodo: PeriodoFinanceiro | None) -> dict[str, object] | None:
    if periodo is None:
        return None
    return {
        "data_inicio": periodo.data_inicio.isoformat(),
        "data_fim": periodo.data_fim.isoformat(),
        "dias": periodo.dias,
    }


def _periodo_from_json(valor: dict[str, object] | None) -> PeriodoFinanceiro | None:
    if valor is None:
        return None
    return PeriodoFinanceiro(
        data_inicio=date.fromisoformat(str(valor["data_inicio"])),
        data_fim=date.fromisoformat(str(valor["data_fim"])),
    )


def _passo_to_json(passo: PassoCalculo) -> dict[str, object]:
    return {
        "nome": passo.nome,
        "entradas": dict(passo.entradas),
        "saidas": dict(passo.saidas),
        "arredondamento": passo.arredondamento,
    }


def _passo_from_json(valor: dict[str, object]) -> PassoCalculo:
    entradas = valor.get("entradas", {})
    saidas = valor.get("saidas", {})
    arredondamento = valor.get("arredondamento")
    return PassoCalculo(
        nome=str(valor["nome"]),
        entradas=entradas if isinstance(entradas, dict) else {},
        saidas=saidas if isinstance(saidas, dict) else {},
        arredondamento=str(arredondamento) if arredondamento is not None else None,
    )


def _data_referencia_from_memoria(memoria: MemoriaCalculo) -> date | None:
    valor = memoria.entradas.get("data_referencia")
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        return date.fromisoformat(valor)
    return None


class SqlAlchemyDevedorRepository(DevedorRepository, DevedorUniquenessChecker):
    """Implementação SQLAlchemy do DevedorRepository (IMP-049).

    Segue o padrão do EPIC-001: merge/flush no repositório, commit no UoW.
    Também satisfaz ``DevedorUniquenessChecker`` (IMP-046), consumido pelo
    UnicidadeDevedorService na criação e na atualização.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, devedor: Devedor) -> None:
        try:
            self._session.merge(
                DevedorORM(
                    id=devedor.id,
                    carteira_id=devedor.carteira_id,
                    documento=devedor.documento.valor,
                    nome=devedor.nome,
                    estado=devedor.estado.value,
                    criado_em=devedor.criado_em,
                    atualizado_em=devedor.atualizado_em,
                )
            )
            self._session.flush()
        except IntegrityError as exc:
            if "uq_devedor_carteira_documento" in str(exc.orig):
                raise DevedorJaExisteError(devedor.documento.valor, devedor.carteira_id) from exc
            raise

    def _contatos_de(self, devedor_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Contato]]:
        """Carrega os contatos de vários Devedores em uma única query (evita N+1).

        Não há ``relationship`` entre DevedorORM e ContatoORM (IMP-042), então a
        coleção do Aggregate é remontada explicitamente na leitura.
        """
        if not devedor_ids:
            return {}
        rows = self._session.scalars(
            select(ContatoORM)
            .where(ContatoORM.devedor_id.in_(devedor_ids))
            .order_by(ContatoORM.criado_em, ContatoORM.id)
        ).all()
        por_devedor: dict[uuid.UUID, list[Contato]] = {}
        for row in rows:
            por_devedor.setdefault(row.devedor_id, []).append(_to_contato(row))
        return por_devedor

    def find_by_id(self, devedor_id: uuid.UUID) -> Devedor | None:
        row = self._session.get(DevedorORM, devedor_id)
        if row is None:
            return None
        return _to_devedor(row, self._contatos_de([row.id]).get(row.id, []))

    def find_by_documento_carteira(
        self, documento: Documento, carteira_id: uuid.UUID
    ) -> Devedor | None:
        row = self._session.scalar(
            select(DevedorORM).where(
                DevedorORM.carteira_id == carteira_id,
                DevedorORM.documento == documento.valor,
            )
        )
        if row is None:
            return None
        return _to_devedor(row, self._contatos_de([row.id]).get(row.id, []))

    def exists_by_documento_carteira(self, documento: Documento, carteira_id: uuid.UUID) -> bool:
        """Verificação de unicidade do documento na Carteira (IMP-046, INV-002)."""
        return (
            self._session.scalar(
                select(func.count(DevedorORM.id)).where(
                    DevedorORM.carteira_id == carteira_id,
                    DevedorORM.documento == documento.valor,
                )
            )
            or 0
        ) > 0

    def listar_paginado(
        self,
        carteira_id: uuid.UUID,
        filtros: DevedorFiltros,
        paginacao: Paginacao,
    ) -> DevedorResultadoPaginado:
        query = select(DevedorORM).where(DevedorORM.carteira_id == carteira_id)
        count_query = select(func.count(DevedorORM.id)).where(DevedorORM.carteira_id == carteira_id)

        if filtros.nome:
            query = query.where(DevedorORM.nome.ilike(f"%{filtros.nome}%"))
            count_query = count_query.where(DevedorORM.nome.ilike(f"%{filtros.nome}%"))

        if filtros.estado:
            query = query.where(DevedorORM.estado == filtros.estado)
            count_query = count_query.where(DevedorORM.estado == filtros.estado)

        if filtros.documento:
            query = query.where(DevedorORM.documento == filtros.documento)
            count_query = count_query.where(DevedorORM.documento == filtros.documento)

        total = self._session.scalar(count_query) or 0

        query = query.order_by(DevedorORM.criado_em, DevedorORM.id)
        query = query.offset(paginacao.offset).limit(paginacao.limit)

        rows = self._session.scalars(query).all()
        contatos = self._contatos_de([row.id for row in rows])
        items = [_to_devedor(row, contatos.get(row.id, [])) for row in rows]

        return DevedorResultadoPaginado(
            items=items,
            total=total,
            pagina=paginacao.pagina,
            tamanho=paginacao.tamanho,
        )


class SqlAlchemyContatoRepository(ContatoRepository):
    """Implementação SQLAlchemy do ContatoRepository (IMP-049).

    Segue o mesmo padrão: merge/flush no repositório, commit no UoW.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, contato: Contato) -> None:
        self._session.merge(
            ContatoORM(
                id=contato.id,
                devedor_id=contato.devedor_id,
                tipo=contato.tipo.value,
                valor=contato.valor,
                preferencial=contato.preferencial,
                criado_em=contato.criado_em,
                atualizado_em=contato.atualizado_em,
                removido_em=contato.removido_em,
            )
        )

    def find_by_id(self, contato_id: uuid.UUID) -> Contato | None:
        row = self._session.get(ContatoORM, contato_id)
        return _to_contato(row) if row is not None else None

    def find_by_devedor(self, devedor_id: uuid.UUID) -> list[Contato]:
        rows = self._session.scalars(
            select(ContatoORM)
            .where(ContatoORM.devedor_id == devedor_id)
            .order_by(ContatoORM.criado_em, ContatoORM.id)
        ).all()
        return [_to_contato(r) for r in rows]

    # remove() foi retirado: a remoção de Contato é agora soft-delete
    # (DOMAIN-021 §141), feita pelo Aggregate via Contato.remover() e persistida
    # por save(). O DELETE físico violava a regra de preservação de auditoria.


def _to_devedor(row: DevedorORM, contatos: list[Contato] | None = None) -> Devedor:
    devedor = Devedor.__new__(Devedor)
    devedor.id = row.id
    devedor.carteira_id = row.carteira_id
    devedor._documento = Documento.from_str(row.documento)
    devedor.nome = row.nome
    devedor.estado = DevedorState(row.estado)
    devedor.criado_em = row.criado_em
    devedor.atualizado_em = row.atualizado_em
    devedor._contatos = contatos if contatos is not None else []
    return devedor


def _to_contato(row: ContatoORM) -> Contato:
    return Contato(
        id=row.id,
        devedor_id=row.devedor_id,
        tipo=TipoContato(row.tipo),
        valor=row.valor,
        preferencial=row.preferencial,
        criado_em=row.criado_em,
        atualizado_em=row.atualizado_em,
        removido_em=row.removido_em,
    )
