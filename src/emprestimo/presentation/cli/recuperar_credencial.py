"""CLI operacional para recuperar a credencial de um Usuario pelo e-mail.

Existe para o caso em que o unico administrador esqueceu a senha: a rota
`POST /iam/usuarios/{id}/credencial/redefinir` exige alguem logado com
`credencial.redefinir`, e o bootstrap so cria Tenant novo. Roda na VPS
(`docker compose exec api emprestimo-recuperar-credencial --email ...`)
atras do MESMO gate do bootstrap: `PLATFORM_ADMIN_BOOTSTRAP_ENABLED=true` e o
segredo cujo SHA-256 esta em `PLATFORM_ADMIN_BOOTSTRAP_SECRET_HASH`.
"""

from __future__ import annotations

import argparse
import getpass
import hmac
import json
import os
import sys
from collections.abc import Sequence

from emprestimo.application.credenciais import CredenciaisService
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.session import get_session_factory
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from emprestimo.presentation.cli.bootstrap_plataforma import (
    BootstrapRecusadoError,
    validar_autorizacao,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="emprestimo-recuperar-credencial",
        description="Redefine a credencial de um Usuario ativo pelo e-mail (gate do bootstrap).",
    )
    parser.add_argument("--email", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    argumentos = _parser().parse_args(argv)
    segredo = getpass.getpass("Segredo de autorizacao do bootstrap: ")
    try:
        validar_autorizacao(segredo, os.environ)
        novo = getpass.getpass("Nova credencial: ")
        confirmacao = getpass.getpass("Confirme a nova credencial: ")
        if not hmac.compare_digest(novo, confirmacao):
            raise BootstrapRecusadoError("confirmacao da nova credencial diverge")
        session_factory = get_session_factory()
        service = CredenciaisService(
            uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
            auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
        )
        resultado = service.recuperar_operacional(email=argumentos.email, novo_segredo=novo)
    except Exception as exc:
        print(f"Recuperacao recusada: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "usuario_id": str(resultado.usuario_id),
                "tenant_id": str(resultado.tenant_id),
                "estado": resultado.estado.value,
                "sessoes_revogadas": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
