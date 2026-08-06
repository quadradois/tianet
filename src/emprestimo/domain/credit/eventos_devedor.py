"""Eventos de domínio do Aggregate Devedor (DOMAIN-026..DOMAIN-029).

São dataclasses imutáveis que representam fatos ocorridos no ciclo de vida
do Devedor. A publicação em bus interno é postergada (DA-307); por ora
os eventos são registrados na trilha de auditoria (ADR-002) pela camada
de Aplicação.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from emprestimo.domain.credit.contato import Contato
from emprestimo.domain.credit.devedor import Devedor, DevedorState
from emprestimo.domain.credit.documento import Documento


@dataclass(frozen=True)
class DevedorCadastrado:
    """Evento DOMAIN-026 — Devedor Cadastrado.

    Publicado quando o cadastro do Devedor é concluído com sucesso e o
    Devedor entra no estado Ativo.
    """

    devedor_id: uuid.UUID
    carteira_id: uuid.UUID
    tenant_id: uuid.UUID
    documento: Documento
    nome: str
    contatos: tuple[Contato, ...]
    criado_em: datetime = datetime.now(UTC)

    @classmethod
    def from_devedor(cls, devedor: Devedor, tenant_id: uuid.UUID) -> DevedorCadastrado:
        """Constrói o evento a partir do Aggregate Devedor."""
        return cls(
            devedor_id=devedor.id,
            carteira_id=devedor.carteira_id,
            tenant_id=tenant_id,
            documento=devedor.documento,
            nome=devedor.nome,
            contatos=devedor.contatos,
            criado_em=devedor.criado_em,
        )

    def to_audit_dict(self) -> dict[str, object]:
        """Serializa para registro na trilha de auditoria (ADR-002)."""
        return {
            "evento": "DevedorCadastrado",
            "devedor_id": str(self.devedor_id),
            "carteira_id": str(self.carteira_id),
            "tenant_id": str(self.tenant_id),
            "documento": self.documento.valor,
            "nome": self.nome,
            "contatos": [
                {
                    "tipo": c.tipo.value,
                    "valor": c.valor,
                    "preferencial": c.preferencial,
                }
                for c in self.contatos
            ],
            "criado_em": self.criado_em.isoformat(),
        }


@dataclass(frozen=True)
class DevedorAtualizado:
    """Evento DOMAIN-027 — Devedor Atualizado.

    Publicado quando nome ou contatos são alterados; o documento e o
    vínculo com a Carteira nunca são alterados.
    """

    devedor_id: uuid.UUID
    carteira_id: uuid.UUID
    tenant_id: uuid.UUID
    alteracoes: dict[str, tuple[str, str]]  # campo -> (antes, depois)
    atualizado_em: datetime = datetime.now(UTC)

    @classmethod
    def from_devedor(
        cls,
        devedor: Devedor,
        tenant_id: uuid.UUID,
        *,
        nome_anterior: str | None = None,
        contatos_anteriores: tuple[Contato, ...] | None = None,
    ) -> DevedorAtualizado:
        """Constrói o evento comparando estado anterior e atual."""
        alteracoes: dict[str, tuple[str, str]] = {}

        if nome_anterior is not None and nome_anterior != devedor.nome:
            alteracoes["nome"] = (nome_anterior, devedor.nome)

        if contatos_anteriores is not None:
            anterior_map = {(c.tipo, c.valor): c for c in contatos_anteriores}
            atual_map = {(c.tipo, c.valor): c for c in devedor.contatos}

            # Contatos removidos
            for key, contato in anterior_map.items():
                if key not in atual_map:
                    alteracoes[f"contato_removido_{key[0].value}_{key[1]}"] = (
                        f"{contato.tipo.value}:{contato.valor}",
                        "",
                    )

            # Contatos adicionados ou alterados
            for key, contato in atual_map.items():
                if key not in anterior_map:
                    alteracoes[f"contato_adicionado_{key[0].value}_{key[1]}"] = (
                        "",
                        f"{contato.tipo.value}:{contato.valor} "
                        f"(preferencial={contato.preferencial})",
                    )
                else:
                    anterior = anterior_map[key]
                    if anterior.preferencial != contato.preferencial:
                        alteracoes[f"contato_preferencial_{key[0].value}_{key[1]}"] = (
                            f"preferencial={anterior.preferencial}",
                            f"preferencial={contato.preferencial}",
                        )

        return cls(
            devedor_id=devedor.id,
            carteira_id=devedor.carteira_id,
            tenant_id=tenant_id,
            alteracoes=alteracoes,
            atualizado_em=devedor.atualizado_em or datetime.now(UTC),
        )

    def to_audit_dict(self) -> dict[str, object]:
        """Serializa para registro na trilha de auditoria (ADR-002)."""
        return {
            "evento": "DevedorAtualizado",
            "devedor_id": str(self.devedor_id),
            "carteira_id": str(self.carteira_id),
            "tenant_id": str(self.tenant_id),
            "alteracoes": {k: {"antes": v[0], "depois": v[1]} for k, v in self.alteracoes.items()},
            "atualizado_em": self.atualizado_em.isoformat(),
        }


@dataclass(frozen=True)
class DevedorInativado:
    """Evento DOMAIN-028 — Devedor Inativado.

    Publicado quando o Devedor Ativo é inativado. O cadastro deixa de
    originar novas operações, preservando integralmente seu histórico.
    """

    devedor_id: uuid.UUID
    carteira_id: uuid.UUID
    tenant_id: uuid.UUID
    estado_anterior: DevedorState = DevedorState.ATIVO
    estado_novo: DevedorState = DevedorState.INATIVO
    inativado_em: datetime = datetime.now(UTC)

    @classmethod
    def from_devedor(cls, devedor: Devedor, tenant_id: uuid.UUID) -> DevedorInativado:
        """Constrói o evento a partir do Aggregate Devedor."""
        return cls(
            devedor_id=devedor.id,
            carteira_id=devedor.carteira_id,
            tenant_id=tenant_id,
            estado_anterior=DevedorState.ATIVO,
            estado_novo=DevedorState.INATIVO,
            inativado_em=devedor.atualizado_em or datetime.now(UTC),
        )

    def to_audit_dict(self) -> dict[str, object]:
        """Serializa para registro na trilha de auditoria (ADR-002)."""
        return {
            "evento": "DevedorInativado",
            "devedor_id": str(self.devedor_id),
            "carteira_id": str(self.carteira_id),
            "tenant_id": str(self.tenant_id),
            "estado_anterior": self.estado_anterior.value,
            "estado_novo": self.estado_novo.value,
            "inativado_em": self.inativado_em.isoformat(),
        }


@dataclass(frozen=True)
class DevedorReativado:
    """Evento DOMAIN-029 — Devedor Reativado.

    Publicado quando o Devedor Inativo é reativado. O cadastro volta a
    originar novas operações, mantendo o mesmo documento e histórico.
    """

    devedor_id: uuid.UUID
    carteira_id: uuid.UUID
    tenant_id: uuid.UUID
    estado_anterior: DevedorState = DevedorState.INATIVO
    estado_novo: DevedorState = DevedorState.ATIVO
    reativado_em: datetime = datetime.now(UTC)

    @classmethod
    def from_devedor(cls, devedor: Devedor, tenant_id: uuid.UUID) -> DevedorReativado:
        """Constrói o evento a partir do Aggregate Devedor."""
        return cls(
            devedor_id=devedor.id,
            carteira_id=devedor.carteira_id,
            tenant_id=tenant_id,
            estado_anterior=DevedorState.INATIVO,
            estado_novo=DevedorState.ATIVO,
            reativado_em=devedor.atualizado_em or datetime.now(UTC),
        )

    def to_audit_dict(self) -> dict[str, object]:
        """Serializa para registro na trilha de auditoria (ADR-002)."""
        return {
            "evento": "DevedorReativado",
            "devedor_id": str(self.devedor_id),
            "carteira_id": str(self.carteira_id),
            "tenant_id": str(self.tenant_id),
            "estado_anterior": self.estado_anterior.value,
            "estado_novo": self.estado_novo.value,
            "reativado_em": self.reativado_em.isoformat(),
        }
