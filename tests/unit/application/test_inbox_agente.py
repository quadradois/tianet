"""Consulta operacional da inbox do agente (S3, somente leitura).

O que estes testes protegem:

1. **leitura não escreve**: o caso de uso abre o UoW e nunca chama `commit`;
2. **o teto de `limite` é aplicado antes do repositório** — a rota valida de
   novo, mas a regra mora no caso de uso;
3. **inbox vazia devolve zeros**, não ausência: a tela distingue "sem
   mensagens" de "sem permissão" pelo 403, não pelo corpo.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

from emprestimo.agent.conversa import (
    ClasseContexto,
    EntradaConversa,
    InboxConversaRepository,
)
from emprestimo.application.inbox_agente import (
    LIMITE_MAXIMO_RECENTES,
    ConsultarInboxAgente,
)

TENANT = uuid.uuid4()


def _entrada(provider_input_id: str, classe: ClasseContexto) -> EntradaConversa:
    return EntradaConversa(
        id=uuid.uuid4(),
        tenant_id=TENANT,
        instancia_ref="tianet",
        envelope_instance_id="instancia-stub",
        provider_input_id=provider_input_id,
        remetente_normalizado="556299999999",
        classe=classe,
        texto="ola",
        estado="recebida",
        recebido_em=datetime.now(UTC),
    )


class _InboxFake(InboxConversaRepository):
    def __init__(self, entradas: list[EntradaConversa]) -> None:
        self._entradas = entradas
        self.limites_pedidos: list[int] = []

    def salvar(self, entrada: EntradaConversa) -> bool:
        raise NotImplementedError

    def buscar_por_chave(
        self, tenant_id: uuid.UUID, instancia_ref: str, provider_input_id: str
    ) -> EntradaConversa | None:
        raise NotImplementedError

    def contar(self, tenant_id: uuid.UUID) -> int:
        return len(self._entradas)

    def contar_por_classe(self, tenant_id: uuid.UUID) -> dict[ClasseContexto, int]:
        totais: dict[ClasseContexto, int] = {}
        for entrada in self._entradas:
            totais[entrada.classe] = totais.get(entrada.classe, 0) + 1
        return totais

    def listar_recentes(self, tenant_id: uuid.UUID, limite: int) -> list[EntradaConversa]:
        self.limites_pedidos.append(limite)
        return self._entradas[:limite]


def _montar(entradas: list[EntradaConversa]) -> tuple[Any, _InboxFake]:
    repo = _InboxFake(entradas)
    uow = MagicMock()
    uow.inbox_conversa = repo
    uow.__enter__.return_value = uow
    return uow, repo


def test_resumo_agrega_total_classe_e_recentes() -> None:
    uow, _ = _montar(
        [_entrada("a", ClasseContexto.OPERADORA), _entrada("b", ClasseContexto.PRE_CADASTRO)]
    )
    resumo = ConsultarInboxAgente(lambda: uow).executar(TENANT)
    assert resumo.total == 2
    assert resumo.por_classe == {ClasseContexto.OPERADORA: 1, ClasseContexto.PRE_CADASTRO: 1}
    assert [e.provider_input_id for e in resumo.recentes] == ["a", "b"]
    uow.commit.assert_not_called()


def test_limite_e_cortado_no_teto_antes_do_repositorio() -> None:
    uow, repo = _montar([_entrada("a", ClasseContexto.OPERADORA)])
    ConsultarInboxAgente(lambda: uow).executar(TENANT, limite=5000)
    assert repo.limites_pedidos == [LIMITE_MAXIMO_RECENTES]


def test_inbox_vazia_devolve_zeros() -> None:
    uow, _ = _montar([])
    resumo = ConsultarInboxAgente(lambda: uow).executar(TENANT)
    assert resumo.total == 0
    assert resumo.por_classe == {}
    assert resumo.recentes == ()
