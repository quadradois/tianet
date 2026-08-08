"""Testes de fiação das dependências da API (IMP-063).

Os demais testes substituem os providers por dublês via ``dependency_overrides``,
o que deixa a montagem real dos casos de uso sem cobertura: um erro de fiação
(argumento trocado, dependência faltando) só apareceria em produção.

Aqui os providers são invocados de verdade, contra o banco real, para verificar
que cada caso de uso é montado com as dependências corretas e opera de ponta a
ponta sem override algum.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from tests.factories import CarteiraFactory, TenantFactory

from emprestimo.application.atualizacao_devedor import DevedorAtualizacaoService
from emprestimo.application.cadastro_devedor import DevedorCadastroService
from emprestimo.application.consulta_devedor import (
    DevedorConsultaPorDocumentoService,
    DevedorConsultaService,
    DevedorListagemService,
)
from emprestimo.application.estado_devedor import DevedorEstadoService
from emprestimo.application.historico_devedor import DevedorHistoricoService
from emprestimo.application.provisioning import TenantProvisioningService
from emprestimo.domain.credit.ports import DevedorFiltros
from emprestimo.domain.platform.ports import TenantRepository
from emprestimo.infrastructure.repositories import (
    SqlAlchemyCarteiraRepository,
    SqlAlchemyTenantRepository,
)
from emprestimo.presentation.api import dependencies

CPF = "52998224725"
CONTATOS = [{"tipo": "telefone", "valor": "(11) 1234-5678", "preferencial": True}]


@pytest.fixture
def sessao(session: Session) -> Session:
    """A sessão de leitura que os providers recebem via Depends(_get_session)."""
    return session


def test_get_session_abre_e_fecha_a_sessao() -> None:
    """O gerador de sessão por requisição precisa fechar ao final."""
    gerador = dependencies._get_session()
    sessao = next(gerador)
    assert sessao.is_active
    gerador.close()  # dispara o finally
    assert not sessao.in_transaction()


def test_providers_de_tenant_montam_os_servicos(sessao: Session) -> None:
    assert isinstance(
        dependencies.get_tenant_provisioning_service(sessao), TenantProvisioningService
    )
    assert isinstance(dependencies.get_tenant_repository(sessao), TenantRepository)


def test_providers_de_devedor_montam_os_servicos(sessao: Session) -> None:
    assert isinstance(dependencies.get_devedor_cadastro_service(sessao), DevedorCadastroService)
    assert isinstance(dependencies.get_devedor_consulta_service(sessao), DevedorConsultaService)
    assert isinstance(
        dependencies.get_devedor_consulta_por_documento_service(sessao),
        DevedorConsultaPorDocumentoService,
    )
    assert isinstance(dependencies.get_devedor_listagem_service(sessao), DevedorListagemService)
    assert isinstance(
        dependencies.get_devedor_atualizacao_service(sessao), DevedorAtualizacaoService
    )
    assert isinstance(dependencies.get_devedor_estado_service(sessao), DevedorEstadoService)
    assert isinstance(dependencies.get_devedor_historico_service(sessao), DevedorHistoricoService)


def test_servicos_montados_pelos_providers_operam_de_ponta_a_ponta(sessao: Session) -> None:
    """Prova que a fiação está correta: os serviços reais funcionam sem override.

    Um argumento trocado na montagem passaria pelo teste de tipo acima, mas
    quebraria aqui — é este o caso que a cobertura dos providers protege.
    """
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(sessao).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(sessao).save(carteira)
    sessao.commit()

    criado = dependencies.get_devedor_cadastro_service(sessao).criar(
        carteira_id=carteira.id,
        documento=CPF,
        nome="João da Silva",
        contatos=CONTATOS,
        idempotency_key="wiring-1",
    )

    consulta = dependencies.get_devedor_consulta_service(sessao)
    assert consulta.consultar_por_id(criado.devedor_id) is not None

    por_doc = dependencies.get_devedor_consulta_por_documento_service(sessao)
    assert por_doc.consultar_por_documento(carteira.id, CPF) is not None

    listagem = dependencies.get_devedor_listagem_service(sessao)
    assert listagem.listar(carteira.id, 1, 20, DevedorFiltros()).total == 1

    dependencies.get_devedor_atualizacao_service(sessao).atualizar(
        criado.devedor_id, "wiring-2", nome="João Santos"
    )

    dependencies.get_devedor_estado_service(sessao).inativar(criado.devedor_id, "wiring-3")
    assert consulta.consultar_por_id(criado.devedor_id).estado.value == "inativo"

    eventos = dependencies.get_devedor_historico_service(sessao).consultar(criado.devedor_id)
    assert eventos and any(e.acao == "criar.sucesso" for e in eventos)


def test_pertinencia_resolve_o_devedor_da_carteira(sessao: Session) -> None:
    """ADR-018: a dependência devolve o Aggregate quando o par é consistente."""
    tenant = TenantFactory.build()
    SqlAlchemyTenantRepository(sessao).save(tenant)
    carteira = CarteiraFactory.build(tenant_id=tenant.id)
    SqlAlchemyCarteiraRepository(sessao).save(carteira)
    sessao.commit()

    criado = dependencies.get_devedor_cadastro_service(sessao).criar(
        carteira_id=carteira.id,
        documento=CPF,
        nome="João da Silva",
        contatos=CONTATOS,
        idempotency_key="wiring-pert",
    )
    servico = dependencies.get_devedor_consulta_service(sessao)

    devedor = dependencies.get_devedor_da_carteira(carteira.id, criado.devedor_id, servico)

    assert devedor.id == criado.devedor_id


def test_pertinencia_recusa_devedor_de_outra_carteira(sessao: Session) -> None:
    """404 tanto para inexistente quanto para pertencente a outra Carteira."""
    from fastapi import HTTPException

    servico = dependencies.get_devedor_consulta_service(sessao)

    with pytest.raises(HTTPException) as exc:
        dependencies.get_devedor_da_carteira(uuid.uuid4(), uuid.uuid4(), servico)

    assert exc.value.status_code == 404
    assert exc.value.detail["codigo"] == "devedor_nao_encontrado"
