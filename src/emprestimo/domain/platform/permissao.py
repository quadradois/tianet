"""Value Object Permissao - operacao autorizavel por RBAC (IMP-084)."""

from __future__ import annotations

from dataclasses import dataclass

from emprestimo.domain.common.errors import ViolacaoInvarianteError


def normalizar_codigo_permissao(codigo: str) -> str:
    codigo_normalizado = codigo.strip().lower()
    if not codigo_normalizado:
        raise ViolacaoInvarianteError(
            "FEATURE-011",
            "codigo da permissao nao pode ser vazio",
        )
    return codigo_normalizado


@dataclass(frozen=True)
class Permissao:
    """Permissao de operacao consumida pelo Perfil de Acesso."""

    codigo: str
    descricao: str

    def __post_init__(self) -> None:
        codigo = normalizar_codigo_permissao(self.codigo)
        descricao = self.descricao.strip()
        if not descricao:
            raise ViolacaoInvarianteError(
                "FEATURE-011",
                "descricao da permissao nao pode ser vazia",
            )
        object.__setattr__(self, "codigo", codigo)
        object.__setattr__(self, "descricao", descricao)
