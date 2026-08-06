"""Aggregate Devedor — Aggregate Root do contexto Cadastro (DOMAIN-020).

O Devedor representa a Pessoa cadastrada pelo Credor como responsável por
obrigações financeiras dentro da Carteira. Concentra as informações
cadastrais — documento, contatos e histórico — e garante a identificação
única do Devedor dentro da Carteira (INV-002, garantida externamente pelo
UnicidadeDevedorService — IMP-046).

Invariantes protegidas nesta entity (IMP-045):
    - INV-001: todo Devedor pertence exatamente a uma Carteira;
    - INV-003: o documento é imutável após a criação (sem setter);
    - INV-005: transições apenas entre Ativo ↔ Inativo;
    - RN-003: ao menos um Contato válido é obrigatório na criação;
    - DOMAIN-021 §2/RN-005: contatos únicos por tipo+valor e apenas um
      preferencial por tipo.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from emprestimo.domain.common.errors import ViolacaoInvarianteError
from emprestimo.domain.credit.documento import Documento

if TYPE_CHECKING:
    from collections.abc import Sequence

    from emprestimo.domain.credit.contato import Contato

NOME_MAXIMO = 200
"""Comprimento máximo do nome do Devedor (DOMAIN-020)."""


class DevedorState(StrEnum):
    """Estado operacional do Devedor (DOMAIN-020 INV-005)."""

    ATIVO = "ativo"
    INATIVO = "inativo"


@dataclass
class Devedor:
    """Aggregate Root do contexto Cadastro (DOMAIN-020).

    Attributes:
        carteira_id: vínculo obrigatório à Carteira (INV-001).
        nome: nome do Devedor (atualizável).
        estado: estado operacional (Ativo/Inativo — INV-005).
        id: identidade única do Devedor.
        criado_em/atualizado_em: rastreabilidade cadastral.
    """

    carteira_id: uuid.UUID
    nome: str
    estado: DevedorState = DevedorState.ATIVO
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))
    atualizado_em: datetime | None = None
    _contatos: list[Contato] = field(default_factory=list, init=False, repr=False)
    _documento: Documento = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # INV-001: vínculo obrigatório e válido à Carteira
        if not isinstance(self.carteira_id, uuid.UUID):
            raise ViolacaoInvarianteError(
                "INV-001",
                f"carteira_id deve ser uuid.UUID, recebido {self.carteira_id!r}",
            )
        nome = self.nome.strip()
        if not nome:
            raise ViolacaoInvarianteError(
                "DOMAIN-020",
                "nome do Devedor não pode ser vazio",
            )
        if len(nome) > NOME_MAXIMO:
            raise ViolacaoInvarianteError(
                "DOMAIN-020",
                f"nome do Devedor deve ter no máximo {NOME_MAXIMO} caracteres",
            )
        self.nome = nome

        # INV-005: estado deve ser um DevedorState valido
        if not isinstance(self.estado, DevedorState):
            raise ViolacaoInvarianteError(
                "INV-005",
                f"estado deve ser DevedorState, recebido {self.estado!r}",
            )

    # ------------------------------------------------------------------ #
    # Estado interno (somente leitura fora do aggregate)
    # ------------------------------------------------------------------ #

    @property
    def documento(self) -> Documento:
        """Documento do Devedor — imutável (INV-003, sem setter)."""
        return self._documento

    @property
    def contatos(self) -> tuple[Contato, ...]:
        """Contatos vinculados ao Devedor (DOMAIN-021).

        Retorna copias defensivas das entidades para impedir que mutacoes
        externas quebrem as invariantes do Aggregate (RN-005 e unicidade
        tipo+valor).
        """
        return tuple(replace(c) for c in self._contatos)

    # ------------------------------------------------------------------ #
    # Criacao (RN-003)
    # ------------------------------------------------------------------ #

    @classmethod
    def criar(
        cls,
        *,
        carteira_id: uuid.UUID,
        documento: Documento,
        nome: str,
        contatos: Sequence[Contato],
    ) -> Devedor:
        """Cria um Devedor exigindo ao menos um Contato valido (RN-003).

        O Aggregate nao armazena as instancias externas de Contato: cria
        copias validadas com o vinculo correto ao Devedor recém-criado
        (RN-001). A validacao de unicidade do documento dentro da Carteira
        (INV-002) eh responsabilidade do UnicidadeDevedorService (IMP-046).
        """
        devedor = cls(carteira_id=carteira_id, nome=nome)
        if not isinstance(documento, Documento):
            raise ViolacaoInvarianteError(
                "INV-003",
                f"documento deve ser um Documento valido, recebido {documento!r}",
            )
        devedor._documento = documento
        for contato in contatos:
            devedor.adicionar_contato(replace(contato, devedor_id=devedor.id))
        if not devedor._contatos:
            raise ViolacaoInvarianteError(
                "RN-003",
                "ao menos um Contato eh obrigatório na criacao do Devedor",
            )
        return devedor

    # ------------------------------------------------------------------ #
    # Gestão de contatos (DOMAIN-021)
    # ------------------------------------------------------------------ #

    def adicionar_contato(self, contato: Contato) -> None:
        """Adiciona um Contato ao Devedor, protegendo RN-001 e RN-005.

        Rejeita Contatos de outro Devedor (RN-001), combinações tipo+valor
        duplicadas (DOMAIN-021 §2) e um segundo preferencial do mesmo tipo
        (DOMAIN-021 RN-005).
        """
        if contato.devedor_id != self.id:
            raise ViolacaoInvarianteError(
                "RN-001",
                f"Contato {contato.id} pertence ao Devedor {contato.devedor_id}, "
                f"não ao Devedor {self.id}",
            )
        if any(
            existente.tipo == contato.tipo and existente.valor == contato.valor
            for existente in self._contatos
        ):
            raise ViolacaoInvarianteError(
                "DOMAIN-021",
                f"Contato {contato.tipo.value!r} com valor {contato.valor!r} "
                "já existente neste Devedor",
            )
        if contato.preferencial and any(
            existente.preferencial and existente.tipo == contato.tipo
            for existente in self._contatos
        ):
            raise ViolacaoInvarianteError(
                "RN-005",
                f"Ja existe um Contato preferencial do tipo {contato.tipo.value!r} "
                "neste Devedor",
            )
        # Armazena copia defensiva para impedir mutacao externa do objeto
        # recebido (TASK-092-B).
        self._contatos.append(replace(contato, devedor_id=self.id))
        self._marcar_atualizado()

    def atualizar_contato(
        self,
        contato_id: uuid.UUID,
        *,
        valor: str | None = None,
        preferencial: bool | None = None,
    ) -> None:
        """Atualiza valor e/ou preferencial de um Contato existente.

        O novo valor é validado pelo próprio Contato (RN-004) ao ser
        reconstruído. A troca de ``preferencial`` respeita RN-005 (apenas
        um preferencial por tipo).
        """
        contato = self._buscar_contato(contato_id)

        if valor is not None:
            valor_normalizado = valor.strip()
            if valor_normalizado != contato.valor:
                for existente in self._contatos:
                    if (
                        existente.id != contato_id
                        and existente.tipo == contato.tipo
                        and existente.valor == valor_normalizado
                    ):
                        raise ViolacaoInvarianteError(
                            "DOMAIN-021",
                            f"Contato {contato.tipo.value!r} com valor {valor_normalizado!r} "
                            "ja existente neste Devedor",
                        )
                # Reconstroi o Contato com o novo valor; o __post_init__ da
                # entity revalida RN-004 (formato conforme o tipo).
                contato_reconstruido = replace(contato, valor=valor_normalizado)
                self._contatos[self._contatos.index(contato)] = contato_reconstruido
                contato = contato_reconstruido

        if preferencial is True and not contato.preferencial:
            if any(
                existente.preferencial and existente.tipo == contato.tipo
                for existente in self._contatos
            ):
                raise ViolacaoInvarianteError(
                    "RN-005",
                    f"Já existe um Contato preferencial do tipo "
                    f"{contato.tipo.value!r} neste Devedor",
                )
            contato.preferencial = True
        elif preferencial is False and contato.preferencial:
            contato.preferencial = False

        self._marcar_atualizado()

    def remover_contato(self, contato_id: uuid.UUID) -> None:
        """Remove um Contato do cadastro (DOMAIN-021 §4).

        A remoção é conceitual: o histórico de auditoria permanece
        registrado pela camada de infraestrutura (RN-006/INV-003 — sem
        exclusão física de histórico, DOMAIN-025).
        """
        contato = self._buscar_contato(contato_id)
        self._contatos.remove(contato)
        self._marcar_atualizado()

    def _buscar_contato(self, contato_id: uuid.UUID) -> Contato:
        for contato in self._contatos:
            if contato.id == contato_id:
                return contato
        raise ViolacaoInvarianteError(
            "DOMAIN-021",
            f"Contato {contato_id} não encontrado neste Devedor",
        )

    # ------------------------------------------------------------------ #
    # Atualização cadastral (US-024)
    # ------------------------------------------------------------------ #

    def atualizar_nome(self, novo_nome: str) -> None:
        """Atualiza o nome do Devedor, preservando os demais campos."""
        nome = novo_nome.strip()
        if not nome:
            raise ViolacaoInvarianteError(
                "DOMAIN-020",
                "nome do Devedor não pode ser vazio",
            )
        if len(nome) > NOME_MAXIMO:
            raise ViolacaoInvarianteError(
                "DOMAIN-020",
                f"nome do Devedor deve ter no máximo {NOME_MAXIMO} caracteres",
            )
        self.nome = nome
        self._marcar_atualizado()

    # ------------------------------------------------------------------ #
    # Transições de estado (INV-005)
    # ------------------------------------------------------------------ #

    def inativar(self) -> None:
        """Transição Ativo → Inativo (FEATURE-008, US-025).

        A inativação não altera documento, contatos nem histórico
        (RN-006). Devedor inativo não pode originar novas operações
        (RN-005 — verificação de negócio downstream).
        """
        if self.estado is not DevedorState.ATIVO:
            raise ViolacaoInvarianteError(
                "INV-005",
                f"apenas Devedores Ativos podem ser inativados "
                f"(estado atual: {self.estado.value})",
            )
        self.estado = DevedorState.INATIVO
        self._marcar_atualizado()

    def reativar(self) -> None:
        """Transição Inativo → Ativo (FEATURE-008, US-026).

        A unicidade do documento dentro da Carteira (INV-002) é
        reverificada pelo UnicidadeDevedorService (IMP-046) antes da
        reativação — este Aggregate não detém o estado da Carteira.
        """
        if self.estado is not DevedorState.INATIVO:
            raise ViolacaoInvarianteError(
                "INV-005",
                f"apenas Devedores Inativos podem ser reativados "
                f"(estado atual: {self.estado.value})",
            )
        self.estado = DevedorState.ATIVO
        self._marcar_atualizado()

    # ------------------------------------------------------------------ #
    # Rastreabilidade
    # ------------------------------------------------------------------ #

    def _marcar_atualizado(self) -> None:
        """Atualiza o timestamp de modificação do cadastro."""
        self.atualizado_em = datetime.now(UTC)
