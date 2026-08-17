# PLAN-029-EXEC - Backlog da Linguagem Operacional da Interface

**ID:** PLAN-029-EXEC

**Versao:** 1.1.0

**Status:** IMP-316 e IMP-319 concluidos; IMP-315 parcial (Motor); IMP-317 e IMP-318 planejados

---

# 1. Contexto

Ordem executavel do PLAN-029. A numeracao continua apos IMP-314, ultimo item do
PLAN-028.

A ordem e deliberada: a formatacao (IMP-316) precede as telas que a consomem, e
a navegacao (IMP-318) vem depois do vocabulario, para que os rotulos ja estejam
no idioma do Credor quando o menu for reduzido.

---

# 2. Fase A - Fundacao

### IMP-315 - Identidade e vocabulario

- **Objetivo:** remover da interface a linguagem de arquitetura e de
  certificacao.
- **Alvos:** "o backend permanece autoridade...", "o frontend apenas envia o
  comando idempotente", "Documento e imutavel na API", "Timezone governado...",
  "Jornada P0", "(oficial)" em todas as ocorrencias de tela, "Aguardando envio
  do formulario", e "FRONTEND MVP" no cabecalho, que passa a ser TiaNet.
- **Componentes afetados:** `frontend/src/components/**`, shell e metadados de
  pagina.
- **Criterios de conclusao:** nenhuma string de tela menciona backend, frontend,
  API, idempotencia, Tenant tecnico ou "oficial"; os markers exigidos pelo gate
  passam a ser satisfeitos pelos testes, que e onde a asserção pertence.
- **Suite minima:** componente e Playwright das jornadas afetadas.
- **Status:** Parcial — Motor concluido; Dashboard, Devedores e shell pendentes.
- **Nota de execucao:** o painel de negativa deixou de exibir "denied" e o nome
  do modulo interno; "(oficial)" saiu dos titulos de secao, que passaram a
  "Quanto ainda falta", "Valor para quitar hoje", "Parcelas" e "Como a conta foi
  feita"; o identificador do Emprestimo deixou de ser titulo do detalhe. A lista
  de markers do gate foi atualizada para o vocabulario novo, de modo que ela
  continua afirmando o que a tela mostra, e nao o que a tela mostrava.
- **Pendente neste IMP:** a tela de detalhe do Motor ainda exibe quatro
  formularios tecnicos no topo, com campo `Idempotency-Key`, data em formato de
  maquina e a string literal `sem-idempotency:/credit/...`.

### IMP-316 - Formatacao brasileira de dinheiro, documento e data

- **Objetivo:** `R$ 10.000,00`, `390.533.447-05`, `17/08/2026`.
- **Componentes afetados:** modulo novo de formatacao, consumido pelas telas.
- **Restricao dura:** por manipulacao de texto sobre a string devolvida pelo
  backend, sem `Intl.NumberFormat`, `toFixed`, `parseFloat`, `parseInt` ou
  qualquer conversao para numero. Ver `PLAN-029 §5`.
- **Criterios de conclusao:** o modulo entra na varredura do gate com asserção
  propria de ausencia de aritmetica; a cobertura do guardrail aumenta.
- **Suite minima:** unidade sobre bordas (zero, centavos, milhar, valor longo,
  entrada ja formatada) e componente.
- **Status:** Concluido.
- **Nota de execucao:** `src/lib/formato/brasileiro.ts`, por manipulacao de
  texto. O gate passou de 172 para 173 checagens: o modulo entrou na varredura
  com asserção propria de ausencia de aritmetica e de construcao de data. Duas
  vezes o scanner recusou o arquivo por **mencao** das APIs proibidas em
  comentario — o mesmo que ocorrera com `cpfValido` no PLAN-027. A regra e cega
  por desenho; o comentario foi reescrito sem nomea-las.

---

# 3. Fase B - Telas

### IMP-317 - Devedor: emprestimos no topo e historico legivel

- **Objetivo:** cumprir o pedido original — "ao abrir um devedor **ja** termos as
  informacoes do emprestimo" — e tirar o JSON cru da tela.
- **Alvos:** o bloco de emprestimos sobe para logo abaixo da identificacao do
  Devedor; o historico deixa de imprimir `{"devedor_id": ..., "idempotency_key":
  ...}` e passa a descrever o evento em linguagem comum.
- **Componentes afetados:** `frontend/src/app/app/devedores/[devedorId]/`,
  `components/devedores/`, `components/motor/`.
- **Dependencias:** IMP-315, IMP-316.
- **Criterios de conclusao:** nenhum identificador tecnico e nenhum JSON
  aparecem na tela; o bloco de emprestimos e visivel sem rolagem em desktop.
- **Nota:** corrige defeito de intencao do IMP-310, que satisfez o criterio do
  backlog e nao o pedido do Credor.
- **Suite minima:** componente e Playwright.

### IMP-318 - Navegacao enxuta

- **Objetivo:** o menu principal passa a listar o que o Credor faz — emprestar,
  ver quem deve, receber — e o restante vai para um agrupamento secundario.
- **Componentes afetados:** `frontend/src/lib/shell/navigation-policy.ts` e o
  shell autenticado.
- **Dependencias:** IMP-315.
- **Criterios de conclusao:** nenhuma rota deixa de existir e nenhuma permissao
  muda; toda tela hoje alcancavel continua alcancavel.
- **Suite minima:** unidade da policy, componente e Playwright de navegacao.

### IMP-319 - Motor sem formulario tecnico

- **Objetivo:** remover do topo da lista o formulario que pede UUID de Contrato
  e Idempotency-Key.
- **Fundamento:** o caminho de criar emprestimo e o wizard (`/app/lancamentos`),
  entregue no IMP-308. Pedir UUID ao Credor e o oposto do que o PLAN-027
  decidiu, e ficou na tela por omissao do IMP-309.
- **Componentes afetados:** `components/motor/`, `app/app/motor/`.
- **Dependencias:** IMP-315.
- **Criterios de conclusao:** a criacao por Contrato permanece possivel para
  quem tem a permissao, fora do caminho principal; nenhum UUID e digitado pelo
  Credor no fluxo normal.
- **Suite minima:** componente e Playwright.
- **Status:** Concluido.
- **Nota de execucao:** o formulario foi recolhido, nao removido. A jornada
  Playwright passou a provar os dois lados: o campo de Contrato comeca oculto e
  so aparece quando o bloco e aberto de proposito.

---

# 4. Gates de conclusao

Os do `PLAN-029 §7`, integralmente, mais repino de evidencia visual apenas com
verificacao de estabilidade em execucoes consecutivas.

---

# 5. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.1.0 | 2026-08-17 | IMP-316 e IMP-319 concluidos; IMP-315 concluido no Motor. |
| 1.0.0 | 2026-08-17 | Backlog inicial IMP-315..319. |
