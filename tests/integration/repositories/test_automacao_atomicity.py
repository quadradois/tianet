from typing import cast

import pytest
from sqlalchemy import Table, UniqueConstraint
from sqlalchemy.orm import Session
from tests.factories import TenantFactory, UsuarioFactory

from emprestimo.domain.common.errors import TemplateNotificacaoJaExisteError
from emprestimo.domain.credit.notifications import TemplateNotificacao
from emprestimo.infrastructure.db.orm import RegistroComunicacaoORM
from emprestimo.infrastructure.repositories import (
    SqlAlchemyTenantRepository,
    SqlAlchemyUsuarioRepository,
)
from emprestimo.infrastructure.repositories.automacao import (
    SqlAlchemyTemplateNotificacaoRepository,
)


def test_comunicacao_automatica_e_unica_por_notificacao() -> None:
    table = cast(Table, RegistroComunicacaoORM.__table__)
    constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert constraints["uq_comunicacao_notification"] == ("notification_id",)
    assert table.c.template_id.foreign_keys
    assert table.c.provider_message_id.nullable


def test_constraint_de_template_duplicado_e_traduzida_para_conflito(
    session: Session,
) -> None:
    tenant = TenantFactory.build()
    usuario = UsuarioFactory.build(tenant_id=tenant.id)
    SqlAlchemyTenantRepository(session).save(tenant)
    SqlAlchemyUsuarioRepository(session).save(usuario)
    repo = SqlAlchemyTemplateNotificacaoRepository(session)

    def template() -> TemplateNotificacao:
        return TemplateNotificacao(
            tenant_id=tenant.id,
            codigo="lembrete_operacional_v1",
            versao=1,
            assunto="Lembrete {data_hora}",
            corpo="Atendimento por {canal_atendimento}",
            parametros_permitidos=("data_hora", "canal_atendimento"),
            criado_por_usuario_id=usuario.id,
        )

    repo.save(template())
    session.commit()

    with pytest.raises(TemplateNotificacaoJaExisteError):
        repo.save(template())
