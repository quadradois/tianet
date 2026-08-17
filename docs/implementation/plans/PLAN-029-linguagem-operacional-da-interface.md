# PLAN-029 — Linguagem Operacional da Interface

**ID:** PLAN-029

**Versao:** 1.0.0

**Status:** Aprovado para execucao

**Origem:** inspecao visual da stack local com o Credor (2026-08-17)

---

# 1. Objetivo

Fazer a interface falar com quem empresta o proprio dinheiro, e nao com quem
construiu o sistema.

O Credor abriu o produto e disse, textualmente, que estava "muito confuso, com
muita informacao que nao esta fazendo sentido". A inspecao confirmou a queixa e
identificou a causa: as telas foram escritas para **provar conformidade**, nao
para operar.

---

# 2. Evidencia

Colhida na stack local (Next.js + FastAPI + PostgreSQL reais), em 2026-08-17.

| # | O que a tela mostra | Por que quebra |
|---|---|---|
| 1 | `{"devedor_id": "e9e7c421-...", "idempotency_key": "427d916c-..."}` no historico do Devedor | JSON cru na cara do operador |
| 2 | "O backend permanece autoridade de todos os valores e estados" | explica arquitetura interna a quem quer saber quanto vai receber |
| 3 | "A transicao e autorizada e validada pelo backend; o frontend apenas envia o comando idempotente" | idem |
| 4 | "Timezone governado: America/Sao_Paulo... o offset vigente na data selecionada" | idem |
| 5 | "Total previsto **(oficial)**", "Total **oficial**: 8", "Detalhe cadastral **oficial**" | "(oficial)" e vocabulario de certificacao, nao de produto |
| 6 | "**Jornada P0** de Devedores da Carteira corrente" | nome interno de projeto |
| 7 | `BRL 10000.00` | deveria ser `R$ 10.000,00` |
| 8 | `39053344705` | deveria ser `390.533.447-05` |
| 9 | `2026-08-17T18:32:00.325592Z` e `2026-08-17` | deveria ser `17/08/2026` |
| 10 | Motor pede "**UUID** do Contrato liberado" e "**Idempotency-Key**" no topo | formulario de programador como primeira coisa da tela |
| 11 | Menu com 11 itens, incluindo Comercial, Contratos, Motor, IAM, Automacao | divisoes internas do sistema, nao tarefas do Credor |
| 12 | "FRONTEND MVP" no cabecalho | o produto e TiaNet |
| 13 | Emprestimos do Devedor no rodape da pagina | o pedido foi "ao abrir um devedor **ja** termos as informacoes do emprestimo" |

O item 13 e defeito do IMP-310: o criterio do backlog foi cumprido e a intencao
do Credor, nao.

---

# 3. Decisoes formais

| # | Decisao | Fundamento |
|---|---|---|
| 1 | **Nenhuma capacidade e removida** | As telas tecnicas continuam alcancaveis; apenas saem do caminho principal. Elas sao EPICs certificados, e esconder nao e apagar. |
| 2 | **Nenhuma regra financeira muda** | O Motor, as invariantes e os valores permanecem intocados. Este plano e de apresentacao. |
| 3 | **Formatacao de dinheiro por manipulacao de texto** | Ver §5. |
| 4 | **Sem novo EPIC, FEATURE ou US** | Nenhum resultado de negocio novo: o mesmo resultado passa a ser compreensivel. |
| 5 | **`(oficial)` sai da interface e permanece na documentacao** | Ali ele distingue valor do backend de valor local, o que importa a auditoria e nao ao Credor. |

---

# 4. API

**Nenhuma alteracao.** O inventario permanece em 108 operacoes e 137 schemas,
com o mesmo hash de contrato. Este plano nao toca backend, OpenAPI, permissoes
nem codigos de erro — apenas o que a interface escreve na tela.

---

# 5. Formatacao de valores e o guardrail anti-calculo

O scanner de contrato veta `Intl.NumberFormat`, `toFixed(`, `parseFloat(`,
`parseInt(` e `.reduce(` nos componentes de Motor, Dashboard e Devedores, sob o
titulo "nao calcula regra financeira". A regra esta certa e **nao sera
afrouxada** — e a terceira vez neste repositorio que ela colide com uma
necessidade legitima (DR-002, IMP-310), e as tres vezes a saida correta foi
respeita-la, nao abrir excecao.

Formatar nao e calcular. A formatacao sera feita em modulo dedicado, por
**manipulacao de texto sobre a string decimal que o backend devolveu** —
`"10000.00"` vira `"R$ 10.000,00"` agrupando digitos, sem jamais converter para
numero. Isso mantem o guardrail intacto e, de quebra, elimina qualquer risco de
artefato de ponto flutuante em valor financeiro, pelo mesmo motivo que levou
`percentualParaFracao` a ser escrita assim no PLAN-027.

O modulo entra na varredura do gate, com asserção propria de que nao contem
aritmetica. A cobertura do guardrail **aumenta**; nao diminui.

---

# 6. Fora de escopo

- **Redesenho visual** (cores, tipografia, espacamento) — a queixa e de
  linguagem e de excesso, nao de estetica.
- **Remocao de telas** — ver decisao 1.
- **Traducao de mensagens de erro do backend** — vem do dominio, com codigo
  estavel; mexer nelas e outro assunto.
- **Acentuacao do restante do repositorio** — a interface ja e sem acento por
  convencao vigente; mudar isso e decisao separada.

---

# 7. Gates

- frontend: typecheck, lint, unit, component, contract, BFF e build;
- `node scripts/tests/test-plan-025-contracts.js`;
- Playwright de todas as jornadas afetadas, contra stack real;
- `npm run docs:validate` com 0 erros;
- `git diff --check`.

Backend nao e tocado; seus gates permanecem na baseline do PLAN-028.

---

# 8. Riscos

| Risco | Tratamento |
|---|---|
| Gate exigir literalmente um texto que sai da tela | os markers vivem em `component + componentTest + e2eTest`; a asserção passa a recair sobre o teste, que e onde ela deveria estar |
| Esconder item de menu quebrar jornada Playwright | cada jornada navega por URL direta tambem; o destino continua existindo |
| Formatacao introduzir erro em valor | modulo puro, com teste de unidade sobre casos de borda (centavos, milhar, zero, valor longo) |
| Evidencia visual repinada em massa | os pinos so avancam com verificacao de estabilidade em execucoes consecutivas, como no IMP-310 |

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-17 | Plano da linguagem operacional: vocabulario, formatacao brasileira, historico legivel, navegacao enxuta e remocao do formulario tecnico do Motor. |
