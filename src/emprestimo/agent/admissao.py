"""Controle de admissão do agente (IMP-356-C): janelas, reserva e fail-closed.

Toda dimensão é obrigatória e positiva — limite ausente ou zerado recusa
subir a capacidade em vez de operar sem teto. Contagens e reservas vivem no
PostgreSQL (sobrevivem a restart); o relógio é injetável para testes com
tempo controlado. Desconhecido nunca consome a reserva da Operadora.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class DimensaoCota:
    """Uma janela deslizante: no máximo `limite` admissões por `chave`."""

    escopo: str
    janela_segundos: int
    limite: int


@dataclass(frozen=True)
class ConfiguracaoAdmissao:
    """Fail-fast: qualquer dimensão inválida impede iniciar a capacidade."""

    dimensoes: tuple[DimensaoCota, ...]
    slots_totais: int = 2
    slots_reservados_operadora: int = 1

    def __post_init__(self) -> None:
        if not self.dimensoes:
            raise ValueError("admissao exige ao menos uma dimensao")
        for dimensao in self.dimensoes:
            if dimensao.janela_segundos <= 0 or dimensao.limite <= 0:
                raise ValueError(f"dimensao invalida: {dimensao!r}")
        if self.slots_totais <= 0 or not (0 < self.slots_reservados_operadora <= self.slots_totais):
            raise ValueError("slots de concorrencia invalidos")


PADRAO_DIMENSOES: tuple[DimensaoCota, ...] = (
    DimensaoCota("instancia", 60, 30),
    DimensaoCota("operadora-remetente", 60, 6),
    DimensaoCota("desconhecido-remetente", 60, 2),
    DimensaoCota("desconhecido-classe", 60, 6),
)
TTL_RESERVA_SEGUNDOS = 120

ESCOPOS_OBRIGATORIOS = frozenset(
    {
        "instancia",
        "operadora-remetente",
        "desconhecido-remetente",
        "desconhecido-classe",
    }
)


@dataclass(frozen=True)
class DecisaoAdmissao:
    admitida: bool
    motivo: str
    avisar: bool


class AdmissaoRepository(ABC):
    """Porta durável de contagens e reservas (mesma transação da inbox)."""

    @abstractmethod
    def contar_janela(self, escopo: str, chave: str, desde: datetime) -> int: ...

    @abstractmethod
    def registrar_evento(
        self,
        tenant_id: uuid.UUID,
        instancia_ref: str,
        escopo: str,
        chave: str,
        instante: datetime,
    ) -> None: ...

    @abstractmethod
    def expurgar_antes(self, corte: datetime) -> int: ...

    @abstractmethod
    def reservar_slot(self, sessao_ref: str, *, operadora: bool, agora: datetime) -> bool:
        """Reserva atômica; False quando sem vaga (inclusive reserva alheia)."""
        ...

    @abstractmethod
    def liberar_slot(self, sessao_ref: str) -> None: ...

    @abstractmethod
    def liberar_expiradas(self, agora: datetime) -> int: ...


def chaves_para(
    tenant_id: uuid.UUID, instancia_ref: str, classe: str, remetente: str
) -> dict[str, str]:
    base = f"{tenant_id}:{instancia_ref}"
    return {
        "instancia": base,
        "operadora-remetente": f"{base}:operadora:{remetente}",
        "desconhecido-remetente": f"{base}:pre_cadastro:{remetente}",
        "desconhecido-classe": f"{base}:pre_cadastro",
    }


@dataclass
class ControleAdmissao:
    """Orquestra janelas + reserva + aviso (processo-local, relógio injetável)."""

    config: ConfiguracaoAdmissao
    ultimo_aviso_por_remetente: dict[str, datetime] = field(default_factory=dict)

    def __post_init__(self) -> None:
        presentes = {d.escopo for d in self.config.dimensoes}
        faltando = ESCOPOS_OBRIGATORIOS - presentes
        if faltando:
            raise ValueError(f"dimensoes obrigatorias ausentes: {sorted(faltando)}")

    def avaliar(
        self,
        repo: AdmissaoRepository,
        *,
        tenant_id: uuid.UUID,
        instancia_ref: str,
        classe: str,
        remetente: str,
        agora: datetime | None = None,
    ) -> DecisaoAdmissao:
        momento = agora or datetime.now(UTC)
        chaves = chaves_para(tenant_id, instancia_ref, classe, remetente)
        dimensoes: tuple[tuple[str, str], ...] = (("instancia", "instancia"),)
        if classe == "operadora":
            dimensoes = (*dimensoes, ("operadora-remetente", "operadora-remetente"))
        else:
            dimensoes = (
                *dimensoes,
                ("desconhecido-remetente", "desconhecido-remetente"),
                ("desconhecido-classe", "desconhecido-classe"),
            )
        limites = {d.escopo: d for d in self.config.dimensoes}
        for dimensao_nome, chave_nome in dimensoes:
            dimensao = limites[dimensao_nome]
            desde = momento - timedelta(seconds=dimensao.janela_segundos)
            usados = repo.contar_janela(dimensao.escopo, chaves[chave_nome], desde)
            if usados >= dimensao.limite:
                return DecisaoAdmissao(
                    admitida=False,
                    motivo=f"janela-cheia:{dimensao.escopo}",
                    avisar=self._deve_avis_ar(remetente, momento),
                )
        for dimensao_nome, chave_nome in dimensoes:
            dimensao = limites[dimensao_nome]
            repo.registrar_evento(
                tenant_id, instancia_ref, dimensao.escopo, chaves[chave_nome], momento
            )
        repo.expurgar_antes(momento - timedelta(seconds=3600))
        return DecisaoAdmissao(admitida=True, motivo="ok", avisar=False)

    def _deve_avis_ar(self, remetente: str, agora: datetime) -> bool:
        """No máximo um aviso por remetente a cada 60 s (anti-tempestade)."""
        ultimo = self.ultimo_aviso_por_remetente.get(remetente)
        if ultimo is not None and (agora - ultimo) < timedelta(seconds=60):
            return False
        self.ultimo_aviso_por_remetente[remetente] = agora
        return True
