# PLAN-043 - Suite operacional 356-F e qualificação de custo (2026-09-16)

Evidência do slice 5: executor verificado contra stack real (auth JWT,
RBAC, slots, sessão, API via ASGI, PostgreSQL) com LLM roteirizado, e
qualificação de custo backend por ferramenta em carteira sintética
(1.000 operações, 10.000 pagamentos, 2 clientes concorrentes).

## Suite operacional (`test_executor_operacao.py`, 8 casos, verdes)

Turno localizar completo com trilha e audit restrito ao IAM; ref de
outro tenant recusada; revogação mid-turn encerra; escritas inexistentes
recusadas pré-rede; crash antes/depois sem duplicar e com slot liberado;
provedor indisponível fecha; injeção com stack real não vaza (máscara
provada nas mensagens persistidas).

## Qualificação de custo (`scripts/benchmark_356f.py`, 100 consultas por
## ferramenta, 2 concorrentes)

| Ferramenta | p50 | p95 | max | Veredito |
|---|---|---|---|---|
| localizar_devedor | 0,020s | 0,026s | 0,186s | OK |
| consultar_saldo_devedor | 0,057s | 0,101s | 0,432s | OK |
| consultar_resumo_carteira | 1,638s | 1,833s | 1,904s | OK |
| consultar_acertos | 0,184s | 0,312s | 0,780s | OK |
| consultar_pagamentos_periodo | 1,542s | 1,742s | 2,060s | OK |
| consultar_fluxo_realizado | 1,425s | 1,565s | 1,805s | OK |

Critério (p95 ≤ 2s, nenhuma > 5s): **6/6 aprovadas, nenhuma
desabilitada**. Achado e correção no caminho: resumo media p95 8,9s —
projeção 12m filtrava 10k pagamentos por empréstimo (O(L×P)) sobre
N+1 consultas. Corrigido sem mudar contrato: `find_by_emprestimo_ids`
em lote + agrupamento único (ports + SQL + serviço). Segunda medição
estável acima. O `ferramentas_habilitadas` do executor permanece como
freio permanente.

## Pendências (fora deste slice, sem código novo)

- Habilitação produtiva: IMP-359/GATE-E1b (fail-closed até prova de
  origem), certificação de modelo + política de dados (DR-005 §7),
  GATE-E3. Flag não substitui.
- Restore com egress incerto: 356-E (sem egress, nada a bloquear).
- Provisionamento do usuário copiloto e `LLM_*`/`COPILOT_*` na VPS: SSH
  do proprietário.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-09-16 | Suite operacional + qualificação de custo do 356-F. |
