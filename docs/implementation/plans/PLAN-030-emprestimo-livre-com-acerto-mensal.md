# PLAN-030 — Emprestimo Livre com Acerto Mensal

**ID:** PLAN-030

**Versao:** 1.0.0

**Status:** Em execucao

**Decisao de origem:** `docs/governance/decision-requests/DR-004-base-e-acumulacao-dos-juros-e-fim-do-plano-de-parcelas.md`

---

# 1. Objetivo

Trocar o modelo do produto: o emprestimo deixa de ser um plano de parcelas e
passa a ser livre, com acerto mensal no dia combinado.

O devedor toma o valor. Na data de acerto pede a atualizacao; o sistema calcula
os juros do periodo sobre o saldo devedor. O devedor paga o quanto puder — no
minimo os juros —, o sistema separa juros de amortizacao, e assim ate quitar.

---

# 2. Decisoes formais

| # | Decisao | Fundamento |
|---|---|---|
| 1 | **Juros sobre o saldo devedor, acumulados por trecho** | O plano cobrava 5% sobre a fatia de amortizacao: R$ 474,19 de juros em dez meses de um emprestimo de R$ 10.000 a 5% ao mes. |
| 2 | **Todo emprestimo tem dia de acerto** | Da ao Credor um dia para cobrar, e a fila de cobranca uma ancora quando ela existir. Ver a correcao da DR-004 secao 6: Cobranca e Agenda **nao** dependiam de parcela, ao contrario do que a abertura afirmou. |
| 3 | **A obrigacao no acerto e apenas o juro do periodo** | Amortizar e voluntario; o devedor quita quando e quanto puder. |
| 4 | **Atraso nao gera multa nem encargo** | Contam-se os dias e aplica-se a fracao da taxa. Atrasar e ter mais tempo de juros, nao uma penalidade. |
| 5 | **O plano de parcelas sai, sem deixar arquivo legado** | Decisao do Credor. |
| 6 | **O operacional primeiro, a remocao por ultimo** | A correcao do calculo nao depende de remover nada, e e ela que torna o modelo correto. |
| 7 | **`encargos` permanece no saldo, sempre zerado** | Um encargo negociado caso a caso caberia ali sem alteracao de contrato. |

---

# 3. Escopo mapeado

| Camada | Alcance |
|---|---|
| Backend | 24 arquivos, 528 ocorrencias de `parcela` |
| Testes backend | 95 arquivos |
| Frontend | 25 arquivos |
| Banco | 4 tabelas com FK para `parcela` |

---

# 4. API

O contrato **muda de forma nao aditiva**, o que e deliberado e consta da
resolucao da DR-004.

- `CondicoesLancamentoRequest` perde `quantidade_parcelas` e
  `primeiro_vencimento`, e ganha `dia_de_acerto`;
- `LancamentoResponse` troca `quantidade_parcelas` por `primeiro_acerto_em`;
- na ultima fase, `GET/POST /credit/emprestimos/{id}/parcelas` e os quatro
  schemas de parcela saem, e o inventario deixa de ser 108/137.

Ate la a contagem permanece em **108 operacoes e 137 schemas**: a alteracao
desta fase e de campo, nao de superficie.

---

# 5. Fases

A ordem existe para que o sistema fique verde entre elas, e para que a remocao
so ocorra quando ninguem mais depender do que sai.

1. **Motor e dominio** — acumulacao por trecho, regra de calendario do acerto e
   o agregado sabendo o proprio dia.
2. **Lancamento e wizard** — o emprestimo nasce livre, sem plano.
3. **Operacao diaria** — Inicio e Relatorios trocam "parcela vencida" por
   "acerto vencido". Cobranca e Agenda nao precisam de mudanca: nao dependiam de
   parcela (DR-004 secao 6, corrigida). Resta a apropriacao de promessa, que
   resolve a parcela pelo pagamento.
4. **Telas do emprestimo** — extrato no lugar da tabela de parcelas.
5. **Remocao** — plano, agregado, tabela, operacao do contrato e testes.

---

# 6. Fora de escopo

- **Recalculo de emprestimos existentes.** O sistema nao esta implantado e os
  dados locais sao de teste, como na DR-003.
- **Multa e mora.** Decisao 4.
- **Polimento visual com design system.** O Credor reservou esse trabalho para
  si.

---

# 7. Gates

- `uv run pytest -q`, `ruff`, `black --check`, `mypy src tests`;
- `npm run docs:validate` com 0 erros;
- frontend: typecheck, lint, unit, component, contract, BFF e build;
- `node scripts/tests/test-plan-025-contracts.js`;
- Playwright das jornadas afetadas contra stack real;
- `git diff --check`.

---

# 8. Riscos

| Risco | Tratamento |
|---|---|
| Operacao diaria ficar sem gatilho | risco superdimensionado na abertura; a verificacao no codigo mostrou que so os relatorios dependiam de parcela |
| Emprestimo antigo sem dia de acerto | ausencia e estado legitimo ate a fase 5; nada quebra |
| Contrato quebrar consumidor | o unico consumidor e o proprio frontend, versionado no mesmo repositorio |
| Repetir o erro da DR-003 | os testes desta vez conferem o **valor esperado pelo negocio**, e nao apenas a estabilidade do numero |

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-17 | Plano do emprestimo livre: juros sobre saldo por trecho, acerto mensal no dia combinado e fim do plano de parcelas. |
