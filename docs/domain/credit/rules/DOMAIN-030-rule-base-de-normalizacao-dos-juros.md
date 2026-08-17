# DOMAIN-030 — Business Rule Base de normalização dos juros por período

**ID:** DOMAIN-030

**Versão:** 1.0.0

**Status:** Aprovado

**Origem:** DR-003, resolvida pela Opção A

---

# 1. Identificador

BR-030

---

# 2. Descrição

Os juros de um período são normalizados pelos dias do **mês a que o período
pertence** — o mês da data de início —, nunca pelos dias do mês em que a parcela
vence.

```
juros = principal × taxa_mensal × dias_do_periodo ÷ dias_do_mes_de_inicio
```

A regra correspondente no Motor é `juros_simples_periodo_real`.

---

# 3. Fundamento

A taxa é contratada **por mês**. Um período que cobre exatamente um mês
calendário deve custar exatamente a taxa contratada, independentemente de o mês
ter 28, 30 ou 31 dias. Períodos parciais permanecem proporcionais aos dias
reais decorridos.

Normalizar pelo mês de vencimento media um mês com a régua de outro: o período
de 01/01 a 01/02 tem 31 dias, todos de janeiro, e ao ser dividido pelos 28 dias
de fevereiro custava **1,107 mês**. O período seguinte, fevereiro inteiro
dividido por março, custava **0,903 mês**. Ver DR-003 §4.1.

---

# 4. Exemplo numérico

Empréstimo de R$ 10.000,00 em 10 parcelas, 5% ao mês, lançado em 17/08/2026,
primeiro vencimento em 01/09/2026. Principal de R$ 1.000,00 por parcela,
portanto R$ 50,00 por mês cheio.

| # | Período | Dias | Mês do período | Juros |
|---|---|---:|---|---:|
| 1 | 17/08 → 01/09 | 15 | ago (31) | **24,19** |
| 2 | 01/09 → 01/10 | 30 | set (30) | **50,00** |
| 3 | 01/10 → 01/11 | 31 | out (31) | **50,00** |
| 4 | 01/11 → 01/12 | 30 | nov (30) | **50,00** |
| 5 | 01/12 → 01/01 | 31 | dez (31) | **50,00** |
| 6 | 01/01 → 01/02 | 31 | jan (31) | **50,00** |
| 7 | 01/02 → 01/03 | 28 | fev (28) | **50,00** |
| 8 | 01/03 → 01/04 | 31 | mar (31) | **50,00** |
| 9 | 01/04 → 01/05 | 30 | abr (30) | **50,00** |
| 10 | 01/05 → 01/06 | 31 | mai (31) | **50,00** |

Apenas a primeira parcela é proporcional, por cobrir 15 dias de agosto em vez de
um mês inteiro.

---

# 5. Invariantes

- **BR-030-INV-001:** período que cobre um mês calendário integral custa
  exatamente a taxa mensal contratada;
- **BR-030-INV-002:** período parcial custa proporcionalmente aos dias reais
  decorridos, sobre a base do mês a que pertence;
- **BR-030-INV-003:** o cálculo é exclusivo do Motor Financeiro e usa `Decimal`
  com arredondamento `ROUND_HALF_UP` ao centavo.

---

# 6. Verificação

`tests/unit/domain/test_motor_juros_base.py` fixa os valores do exemplo da
seção 4. Este teste é obrigatório: a DR-003 encontrou a regra **sem
especificação e sem nenhum teste que fixasse resultado**, de modo que qualquer
alteração da fórmula passava despercebida. A suíte cobria tipos, periodicidade e
estrutura da regra — nunca o número.

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 17/08/2026 | Especificação criada pela DR-003, junto com a correção da base de normalização e o teste de valor. |
