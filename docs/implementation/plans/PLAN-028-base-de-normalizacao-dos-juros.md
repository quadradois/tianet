# PLAN-028 — Base de Normalizacao dos Juros por Periodo

**ID:** PLAN-028

**Versao:** 1.0.0

**Status:** Aprovado para execucao

**Decisao de origem:** `docs/governance/decision-requests/DR-003-base-de-normalizacao-dos-juros-por-periodo.md` (Opcao A)

---

# 1. Objetivo

Executar a Opcao A da DR-003: normalizar os juros de um periodo pelos dias do
mes a que o periodo pertence, e nao pelos dias do mes em que a parcela vence.

O plano corrige o numero **e** as duas ausencias que permitiram o numero passar
despercebido — a regra nao tinha especificacao e nao tinha teste de valor.

---

# 2. Decisoes formais

| # | Decisao | Fundamento |
|---|---|---|
| 1 | **Plano proprio, e nao IMP dentro do PLAN-027** | A correcao e no Motor (EPIC-005), nao no wizard. Precedente: PLAN-024 e PLAN-026 tambem foram planos de correcao. |
| 2 | **A especificacao e obrigatoria, nao opcional** | A DR-003 §5 registra que o achado mais grave nao e o valor, e sim a regra sem convencao documentada. |
| 3 | **O teste de valor entra antes da mudanca da formula** | Ele deve falhar sobre o comportamento antigo; um teste escrito depois so fixa o que ja passa. |
| 4 | **Os 9 emprestimos locais sao descartados, nao recalculados** | Sao dados de teste. O sistema nao esta implantado e o alcance em producao e zero (DR-003 §6 e Resolucao). |
| 5 | **Sem novo EPIC, FEATURE ou US** | Nenhuma capacidade nova: a regra existente passa a produzir o valor pretendido. |
| 6 | **Versao da regra `juros_simples_periodo_real` mantida** | Ver §6. |

---

# 3. Escopo

| Camada | Alteracao |
|---|---|
| Domain | `motor_financeiro.py`: divisor passa de `periodo.data_fim` para `periodo.data_inicio` |
| Domain (doc) | `DOMAIN-030` — especificacao da convencao, com exemplo numerico das 10 parcelas |
| Testes | `tests/unit/domain/test_motor_juros_base.py` — teste de valor sobre plano conhecido |
| Dados | descarte dos emprestimos do ambiente local |

---

# 4. API

**Nenhuma alteracao.** O inventario permanece em 108 operacoes e 137 schemas,
com o mesmo hash de contrato. Nenhuma operacao muda de forma, de codigo de erro
ou de permissao.

A correcao muda o **valor** que o Motor calcula, nunca o formato em que ele o
publica: `ParcelaResponse.juros` continua sendo o mesmo campo, do mesmo tipo, na
mesma operacao. Por isso este plano nao mexe em `openapi.json` nem nos pins de
contrato do frontend.

---

# 5. Fora de escopo

- **Recalculo de emprestimos** — nao ha producao a recalcular (DR-003 §6).
- **Exposicao da memoria de calculo em linguagem comum** (DR-003 §9 item 5) —
  e trabalho de interface, cabe no PLAN-027 junto com o IMP-309.
- **`RegraCalculo.parametros["base"]`** — a DR-003 §5 registra que o campo e
  aceito e nunca lido. Segue como divida conhecida: implementa-lo agora seria
  criar configuracao para um valor que nao varia.

---

# 6. Versionamento da regra de calculo

A regra declarada na memoria de calculo permanece `juros_simples_periodo_real`
versao `1.0.0`.

Fundamento: versionar serve para distinguir planos gerados sob convencoes
diferentes. Nenhum plano sob a convencao antiga sobrevive a este plano — os 9
emprestimos locais sao descartados no IMP-314 e a producao nao existe. Nao ha
populacao a distinguir, e subir a versao registraria uma coexistencia que nunca
ocorreu.

**Este fundamento expira na primeira implantacao.** Depois que houver emprestimo
real gerado, qualquer alteracao da formula exige nova versao da regra, porque ai
sim existirao planos sob convencoes diferentes convivendo.

---

# 7. Gates

- `uv run pytest -q` (967 testes), `ruff`, `black --check`, `mypy src tests`;
- `npm run docs:validate` com 0 erros;
- `git diff --check`.

Frontend e contratos nao sao tocados; seus gates permanecem na baseline do
PLAN-027.

---

# 8. Riscos

| Risco | Tratamento |
|---|---|
| Outro teste depender do valor antigo | suite completa executada; 967 passam — nenhum dependia (o que confirma o achado da DR-003 §5) |
| A correcao remover a proporcionalidade por dias | teste dedicado fixa periodo parcial em 250,00 para meio mes |
| Alteracao futura repetir o problema | `DOMAIN-030` + teste de valor fazem qualquer mudanca falhar visivelmente |
| Emprestimo local sobreviver ao descarte e exibir valor antigo | descarte verificado por contagem apos a operacao |

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-17 | Execucao da Opcao A da DR-003: base de normalizacao, especificacao DOMAIN-030 e teste de valor. |
