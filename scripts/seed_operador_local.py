"""Concede o catalogo completo de permissoes a um usuario do ambiente LOCAL.

O bootstrap da plataforma cria um administrador com apenas `tenant.*`, o que
deixa quase toda a interface em "Sem permissao". Este script cria um Perfil com
o catalogo inteiro e o atribui ao usuario, para que seja possivel percorrer as
jornadas operacionais em teste manual.

Uso (a partir da raiz do repositorio, com a stack no ar):

    docker compose run --rm -T -v ./scripts:/app/scripts api \\
        python scripts/seed_operador_local.py --institution tianet-local \\
                                              --email admin@local.test

NAO use isto em producao: em producao os Perfis sao criados pela tela de IAM,
com permissoes minimas por funcao.
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from emprestimo.application.iam_catalogo import CATALOGO_PERMISSOES
from emprestimo.domain.platform.perfil import PerfilAcesso
from emprestimo.infrastructure.db.orm import TenantORM, UsuarioORM
from emprestimo.infrastructure.repositories import SqlAlchemyPerfilAcessoRepository

NOME_PERFIL = "Operador Local (teste)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--institution", required=True)
    parser.add_argument("--email", required=True)
    argumentos = parser.parse_args()

    if os.environ.get("APP_ENV", "development") == "production":
        print("recusado: este seed e apenas para ambiente local", file=sys.stderr)
        return 1

    engine = create_engine(os.environ["DATABASE_URL"])
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        tenant = session.scalar(
            select(TenantORM).where(TenantORM.identificador_institucional == argumentos.institution)
        )
        if tenant is None:
            print(f"Tenant '{argumentos.institution}' nao encontrado", file=sys.stderr)
            return 1

        usuario = session.scalar(
            select(UsuarioORM).where(
                UsuarioORM.tenant_id == tenant.id, UsuarioORM.email == argumentos.email
            )
        )
        if usuario is None:
            print(f"Usuario '{argumentos.email}' nao encontrado no Tenant", file=sys.stderr)
            return 1

        perfil = PerfilAcesso(tenant_id=tenant.id, nome=NOME_PERFIL)
        for permissao in CATALOGO_PERMISSOES:
            perfil.adicionar_permissao(permissao)

        repositorio = SqlAlchemyPerfilAcessoRepository(session)
        repositorio.save(perfil)
        repositorio.atribuir_usuario(usuario.id, perfil.id)
        session.commit()

        print(f"Perfil '{NOME_PERFIL}' com {len(CATALOGO_PERMISSOES)} permissoes")
        print(f"atribuido a {argumentos.email} no Tenant {argumentos.institution}.")
        print("Faca logout e login novamente para a sessao recarregar as permissoes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
