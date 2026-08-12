"""Erros de domínio — falhas expressas na linguagem do negócio (IMP-008).

A camada Domain comunica violações de regras através de exceções próprias,
nunca de exceções de infraestrutura (ADR-001): a aplicação traduz
DomainError em respostas HTTP sem conhecer detalhes de persistência.
"""

from __future__ import annotations

import uuid


class DomainError(Exception):
    """Falha de regra de negócio do domínio."""


class ViolacaoInvarianteError(DomainError):
    """Estado inválido bloqueado por uma invariante do Aggregate (IMP-009).

    Args:
        codigo: identificador da invariante violada (ex.: ``INV-005``).
        mensagem: descrição legível da violação.
    """

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(f"Invariante {codigo} violada: {mensagem}")
        self.codigo = codigo
        self.mensagem = mensagem


class TenantJaExisteError(DomainError):
    """A organização já está provisionada na plataforma (IMP-008, UC-002).

    Levantada tanto pela consulta de unicidade quanto pela tradução da
    violação de constraint em corrida (AD-002) — conflito explícito, sem
    exceção genérica de persistência.
    """

    def __init__(self, identificador_institucional: str) -> None:
        super().__init__(f"Organização já existente: {identificador_institucional!r}")
        self.identificador_institucional = identificador_institucional


class DocumentoInvalidoError(DomainError):
    """CPF informado não é válido (IMP-043, DOMAIN-022 VO-022-VAL-001/002).

    Levantada pelo Value Object ``Documento`` quando o valor informado não
    contém 11 dígitos ou falha no algoritmo dos dígitos verificadores.
    """

    def __init__(self, documento: str, motivo: str) -> None:
        super().__init__(f"Documento inválido: {documento!r} — {motivo}")
        self.documento = documento
        self.motivo = motivo


class DevedorJaExisteError(DomainError):
    """Documento do Devedor já cadastrado na Carteira (IMP-046, DOMAIN-024).

    Levantada pelo UnicidadeDevedorService quando já existe Devedor com o
    mesmo documento na mesma Carteira, independentemente do estado (Ativo
    ou Inativo).
    """

    def __init__(self, documento: str, carteira_id: uuid.UUID) -> None:
        super().__init__(
            f"Devedor com documento {documento!r} já existente na " f"Carteira {carteira_id}"
        )
        self.documento = documento
        self.carteira_id = carteira_id


class PerfilJaExisteError(DomainError):
    """Nome de Perfil de Acesso ja utilizado no mesmo Tenant."""

    def __init__(self) -> None:
        super().__init__("Perfil de Acesso ja existente no Tenant")


class TemplateNotificacaoJaExisteError(DomainError):
    """Codigo e versao de template ja emitidos no mesmo Tenant."""

    def __init__(self, codigo: str, versao: int) -> None:
        super().__init__(f"Template {codigo!r} versao {versao} ja existe no Tenant")
        self.codigo = codigo
        self.versao = versao
