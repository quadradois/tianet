"""Resumo diario ao Credor (IMP-353): texto em codigo, valores do Motor."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from emprestimo.application.resumo_diario import montar_texto_resumo_diario
from emprestimo.application.varredura_cobranca import (
    DevedorVarreduraCobranca,
    EmprestimoVarreduraCobranca,
)


def _devedor(
    nome: str,
    saldo: str,
    juros: str,
    *,
    em_atraso: bool = False,
    acerto_vigente_em: date = date(2026, 9, 20),
) -> DevedorVarreduraCobranca:
    tenant_id = uuid.uuid4()
    carteira_id = uuid.uuid4()
    devedor_id = uuid.uuid4()
    return DevedorVarreduraCobranca(
        tenant_id=tenant_id,
        carteira_id=carteira_id,
        devedor_id=devedor_id,
        devedor_nome=nome,
        emprestimos=(
            EmprestimoVarreduraCobranca(
                tenant_id=tenant_id,
                carteira_id=carteira_id,
                devedor_id=devedor_id,
                devedor_nome=nome,
                emprestimo_id=uuid.uuid4(),
                data_referencia=date(2026, 9, 20),
                acerto_vigente_em=acerto_vigente_em,
                proximo_acerto_em=date(2026, 10, 20),
                data_acerto_calculada=acerto_vigente_em,
                vence_hoje=not em_atraso,
                vence_amanha=False,
                saldo_devedor=Decimal(saldo),
                percentual_juros=Decimal("0.0300"),
                valor_juros_periodo=Decimal(juros),
                juros_pendente_acerto=Decimal(juros),
                em_atraso=em_atraso,
            ),
        ),
    )


def test_texto_lista_quem_vence_hoje_com_valores_do_motor() -> None:
    texto = montar_texto_resumo_diario(
        date(2026, 9, 20),
        (_devedor("Maria", "1500.00", "45.00"), _devedor("Joao", "12000.50", "360.02")),
    )

    linhas = texto.splitlines()
    assert linhas[0] == "Acertos de hoje (20/09/2026): 2"
    assert "Maria - juro R$ 45,00 - saldo R$ 1.500,00" in linhas
    assert "Joao - juro R$ 360,02 - saldo R$ 12.000,50" in linhas


def test_texto_ordena_por_nome_para_ser_determinista() -> None:
    texto = montar_texto_resumo_diario(
        date(2026, 9, 20),
        (_devedor("Zeca", "1.00", "1.00"), _devedor("Ana", "1.00", "1.00")),
    )

    assert texto.index("Ana") < texto.index("Zeca")


def test_texto_inclui_bloco_de_atraso_com_dias_e_juro_do_motor() -> None:
    texto = montar_texto_resumo_diario(
        date(2026, 9, 20),
        (
            _devedor("Maria", "1500.00", "45.00"),
            _devedor(
                "Carlos", "2000.00", "87.00", em_atraso=True, acerto_vigente_em=date(2026, 9, 10)
            ),
        ),
    )

    linhas = texto.splitlines()
    assert linhas[0] == "Acertos de hoje (20/09/2026): 1"
    assert "Maria - juro R$ 45,00 - saldo R$ 1.500,00" in linhas
    assert "Carlos" not in linhas[1]
    assert "Em atraso: 1" in linhas
    assert "Carlos - desde 10/09 (10 dias) - juro R$ 87,00 - saldo R$ 2.000,00" in linhas


def test_texto_so_com_atrasados_nao_menciona_acertos_de_hoje() -> None:
    texto = montar_texto_resumo_diario(
        date(2026, 9, 20),
        (
            _devedor(
                "Carlos", "2000.00", "87.00", em_atraso=True, acerto_vigente_em=date(2026, 9, 19)
            ),
        ),
    )

    assert texto.splitlines()[0] == "Em atraso: 1"
    assert "Carlos - desde 19/09 (1 dia) - juro R$ 87,00 - saldo R$ 2.000,00" in texto
    assert "Acertos de hoje" not in texto
