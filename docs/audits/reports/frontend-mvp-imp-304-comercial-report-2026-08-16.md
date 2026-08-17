# Frontend MVP - Relatorio IMP-304 Opacidade dos Parametros Comerciais

**Plano relacionado:** PLAN-025

**Decisao de origem:** DR-002, resolvida pela Opcao B

**Status:** IMP-304 concluido localmente

**Data:** 2026-08-16

---

## 1. Resultado

Nenhum operador conseguia lancar um Emprestimo ate o plano de parcelas usando
apenas a interface. O defeito foi encontrado em validacao manual da stack
completa em Docker, apos a certificacao do Frontend MVP.

`parseOpaqueParameters` rejeitava qualquer parametro cuja chave casasse com
`/juros|mora|multa|amortiza|saldo|quitacao|renegocia|parcela|pagamento|emprestimo|memoria/i`.
Duas chaves canonicas do Motor caiam por coincidencia de substring:
`quantidade_parcelas` e `taxa_juros_mensal`.

Os dois caminhos possiveis morriam:

| Caminho | Resultado observado |
|---|---|
| Com o vocabulario correto | guard descarta; BFF envia `parametros: {}`; backend responde `422`. O mesmo payload direto na API responde `201`. |
| Apenas com chaves que passam | Proposta, Contrato, assinatura, liberacao e Emprestimo respondem `201`/`200`; o plano falha com `409 - Invariante EPIC-005 violada: quantidade_parcelas deve ser inteiro`. |

---

## 2. Evidencia RED -> GREEN

Cenario de jornada real acrescentado em
`frontend/tests/jornadas-e2e/jornadas-compostas.spec.ts`, executado contra
Next.js + FastAPI + PostgreSQL reais, sem mock.

| Estado | Execucao |
|---|---|
| RED | com o guard reintroduzido temporariamente, o cenario falha |
| GREEN | com a correcao aplicada, `7 passed` na suite de stack real |

A verificacao nos dois sentidos e o que distingue um cenario de regressao de um
teste que passaria de qualquer forma.

Teste unitario correspondente em `frontend/tests/unit/comercial-policy.test.ts`
fixa o vocabulario canonico do Motor atravessando `parseOpaqueParameters`
intacto, e mantem a rejeicao de nao-objeto, objeto vazio e JSON invalido.

---

## 3. Por que os gates anteriores nao detectaram

| Suite | Submete o formulario Comercial | Backend |
|---|---|---|
| `comercial-e2e` | sim | `backend-fixture.mjs` (stub, aceita qualquer payload) |
| `jornadas-e2e` (IMP-301) | nao | FastAPI + PostgreSQL reais |

A unica suite contra backend real semeava dados por `seed_integrated.py`, no
nivel Python, e usava a interface apenas para leitura e navegacao. As duas
suites passavam; a composicao entre elas nao existia.

---

## 4. O que mudou

- `frontend/src/lib/comercial/comercial-policy.ts` - `parseOpaqueParameters`
  deixa de inspecionar nomes de chave; valida apenas objeto JSON nao vazio.
- `frontend/src/lib/bff/comercial.server.ts` - `createCommercialProposal`
  deixa de converter falha de validacao em `{}` e passa a responder `400` com
  mensagem acionavel, como as duas funcoes irmas ja faziam. As tres mensagens
  foram alinhadas apos a remocao da regra.
- `frontend/tests/unit/comercial-policy.test.ts` - cobertura do vocabulario do Motor.
- `frontend/tests/jornadas-e2e/jornadas-compostas.spec.ts` - cenario de stack real.
- `scripts/tests/test-plan-025-contracts.js` - faixa IMP-274..IMP-304 e pinos da
  matriz em 3.3.0.
- Matriz de rastreabilidade em 3.3.0, com a superficie Comercial corrigida.

A garantia contra motor financeiro paralelo permanece integral: quem a entrega
e o scanner estatico `certifyNoFinancialEngineParallel`, que veta `.reduce(`,
`parseFloat(`, `parseInt(`, `toFixed(` e soma sobre identificadores
financeiros. Filtrar nomes de chave nunca impediu calculo, que pode usar
qualquer identificador.

---

## 5. Escopo e inventario

Manifesto `docs/audits/evidence/frontend-mvp-imp-304-protected-baseline.json`,
encadeado ao manifesto verificado do IMP-303.

| Metrica | Valor |
|---|---|
| baseline | 414 paths |
| allowlist mutavel | 66 paths |
| protegidos | 348 paths |
| allowlist nova | 3 paths |
| inventario final | 417 paths |

## 5.1 Separacao das duas metades do gate

O gate de escopo fazia duas verificacoes com durabilidade diferente, e a segunda
o tornava impossivel de manter:

| Verificacao | Durabilidade | Tratamento |
|---|---|---|
| SHA de arquivo protegido | permanente | falha dura, inalterada |
| Caminho declarado nao pode sumir | permanente | falha dura, inalterada |
| Contagem exata de caminhos | instante da certificacao | passou a `>=`; nao pode encolher |
| Caminho novo apos a certificacao | instante da certificacao | reportado, nao bloqueia |

A comparacao e feita contra `HEAD`, que se move. Exigir contagem exata
significava que **qualquer commit posterior quebrava o gate**, tivesse ou nao
relacao com o IMP. Ocorreu duas vezes no mesmo dia, a segunda com uma correcao
de documentacao sem nenhuma ligacao com o Frontend MVP.

A saida aparentemente obvia — emitir um IMP novo a cada mudanca so para atualizar
o manifesto — foi recusada: sob o PLAN-025 seria erro de categoria, e feita apenas
para acender a luz verde equivale a enfraquecer o gate por outro caminho.

Verificado nos dois sentidos apos a mudanca: alterar um arquivo protegido
(`frontend/next.config.ts`) produz falha dura com o diff de SHA; restaurado,
o gate volta a passar. Caminhos novos aparecem listados na saida, entao a
visibilidade nao foi perdida — apenas deixou de bloquear.

## 5.2 Aposentadoria do gate na CI

A separacao da secao 5.1 resolveu caminhos novos, mas nao arquivos protegidos
alterados. O PLAN-027 altera arquivos protegidos por definicao: publicar uma
operacao regera o snapshot OpenAPI, o cliente tipado e os pinos de contagem.
Na primeira execucao o gate acusou 23 divergencias, todas legitimas.

A causa e o `head` do manifesto: `e48cb72`, o `master` **anterior** ao PR #10.
Com o PR mergeado, esse delta passou a incluir trabalho que ja esta no `master`
e cresce a cada commit seguinte. O manifesto mede uma janela que nao existe
mais.

O gate cumpriu o que existia para provar — que o IMP-304 alterou exatamente o
que declarou — e esse trabalho esta no `master`. Ele sai da CI e permanece no
repositorio como evidencia historica, junto com seu manifesto. O PLAN-027 emite
o proprio no IMP-311, quando tiver o que certificar.

E a cadeia funcionando como projetada: cada manifesto serve ao seu momento de
certificacao, nao para sempre. As asseracoes de contrato que exigiam a presenca
do passo na CI foram removidas, e nao reescritas para parecerem verdadeiras —
a propriedade que afirmavam deixou de existir.

Os 10 paths acrescidos em relacao ao IMP-303 sao a infraestrutura Docker local
(`Dockerfile`, `docker-compose.yml`, dois `.dockerignore`, `frontend/Dockerfile`),
o runbook `docs/operations/ambiente-local-docker.md`, o seed local
`scripts/seed_operador_local.py`, a DR-002, a normalizacao do H1 da DR-001 e a
correcao de relogio em `tests/unit/domain/test_sessao.py`.

---

## 6. Caveats nao bloqueantes

- **Correcao adjacente de teste.** `test_sessao.py` criava sessao em 2026-08-08
  e verificava o refresh token sem fixar `agora`. Como o token expira em sete
  dias, o teste passou a falhar em 2026-08-15 e falharia para sempre. Nao tem
  relacao com a DR-002; foi corrigido porque bloqueava o gate de backend.
- **H1 da DR-001.** `identifier-check.js` so registra emissao quando o H1 comeca
  pelo ID; o da DR-001 comecava por "DECISION REQUEST". A lacuna so apareceu
  quando o contador do namespace avancou para 2. Conteudo e decisao intactos.
- **Lacuna 7 permanece.** Nao ha administracao integral de Usuarios pela
  interface; o primeiro operador com permissao operacional ainda precisa vir de
  fora da UI. Registrado no PLAN-025 e reobservado em teste manual.
- **Ergonomia do formulario.** Os parametros continuam sendo digitados como JSON
  cru, o que exige do operador conhecer o vocabulario interno do Motor. A
  Opcao D da DR-002 registra isso como trabalho de produto subsequente, com
  Discovery proprio.

---

## 7. Decisao

IMP-304 concluido. A jornada `Contrato ate pagamento` fecha pela interface e
passa a ter cenario de regressao contra backend real.

---

## 8. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.2.0 | 2026-08-17 | Gate de escopo aposentado da CI (secao 5.2): cumpriu sua certificacao e o manifesto media uma janela inexistente. Script e manifesto permanecem como evidencia. |
| 1.1.0 | 2026-08-16 | Separacao das duas metades do gate de escopo (secao 5.1): integridade permanece falha dura, inventario congelado vira relato. |
| 1.0.0 | 2026-08-16 | Relatorio do IMP-304: execucao da DR-002, correcao da falha silenciosa e cenario de jornada real para o formulario Comercial. |
