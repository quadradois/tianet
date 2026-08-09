"""CLI segura para o bootstrap do Administrador da Plataforma."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence

from emprestimo.application.bootstrap_plataforma import (
    AdministradorPlataformaBootstrapService,
)
from emprestimo.infrastructure.auditoria import SqlAlchemyAuditoriaRegistro
from emprestimo.infrastructure.db.session import get_session_factory
from emprestimo.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

ENV_HABILITADO = "PLATFORM_ADMIN_BOOTSTRAP_ENABLED"
ENV_HASH_AUTORIZACAO = "PLATFORM_ADMIN_BOOTSTRAP_SECRET_HASH"
_HASH_SHA256 = re.compile(r"[0-9a-fA-F]{64}")


class BootstrapRecusadoError(RuntimeError):
    """O gate operacional do bootstrap recusou a execucao."""


def validar_autorizacao(segredo: str, ambiente: Mapping[str, str]) -> None:
    if ambiente.get(ENV_HABILITADO, "").strip().lower() != "true":
        raise BootstrapRecusadoError("bootstrap operacional desabilitado")
    hash_esperado = ambiente.get(ENV_HASH_AUTORIZACAO, "").strip().lower()
    if _HASH_SHA256.fullmatch(hash_esperado) is None:
        raise BootstrapRecusadoError("configuracao de autorizacao invalida")
    if len(segredo) < 32:
        raise BootstrapRecusadoError("autorizacao recusada")
    hash_recebido = hashlib.sha256(segredo.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(hash_recebido, hash_esperado):
        raise BootstrapRecusadoError("autorizacao recusada")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inicializa o primeiro Administrador da Plataforma fora da API.",
    )
    parser.add_argument("--tenant-identificador", required=True)
    parser.add_argument("--tenant-nome", required=True)
    parser.add_argument("--admin-nome", required=True)
    parser.add_argument("--admin-email", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    argumentos = _parser().parse_args(argv)
    segredo = getpass.getpass("Segredo de autorizacao do bootstrap: ")
    try:
        validar_autorizacao(segredo, os.environ)
        segredo_inicial = getpass.getpass("Credencial inicial do administrador: ")
        confirmacao = getpass.getpass("Confirme a credencial inicial: ")
        if not hmac.compare_digest(segredo_inicial, confirmacao):
            raise BootstrapRecusadoError("confirmacao da credencial inicial diverge")
        session_factory = get_session_factory()
        service = AdministradorPlataformaBootstrapService(
            uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
            auditoria=SqlAlchemyAuditoriaRegistro(session_factory),
        )
        resultado = service.executar(
            identificador_institucional=argumentos.tenant_identificador,
            nome_tenant=argumentos.tenant_nome,
            nome_administrador=argumentos.admin_nome,
            email_administrador=argumentos.admin_email,
            segredo_inicial=segredo_inicial,
        )
    except Exception as exc:
        print(f"Bootstrap recusado: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "tenant_id": str(resultado.tenant_id),
                "usuario_id": str(resultado.usuario_id),
                "perfil_id": str(resultado.perfil_id),
                "estado": resultado.estado.value,
                "criado_agora": resultado.criado_agora,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
