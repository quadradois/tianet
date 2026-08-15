# Frontend MVP - Relatorio IMP-301 Jornadas Compostas

**Plano relacionado:** PLAN-025

**Status:** IMP-301 concluido localmente; IMP-302 permanece Planejado e bloqueado ate novo `fable:fable-judge`

**Data:** 2026-08-14

---

## 1. Resultado

O IMP-301 certificou jornadas compostas P0/P1 em stack real
Next.js/FastAPI/PostgreSQL, com seed integrado e sem mocks Playwright. A suite
executa login, refresh e logout, RBAC, 404 neutro cross-scope, fluxos
Devedor -> Proposta, Proposta -> Contrato -> Emprestimo, pagamento
idempotente, consulta do Motor sem calculo local, Cobranca -> promessa ->
Agenda -> Comunicacao, Relatorios, Configuracoes, IAM permitido, Automacao
operacional e 5xx correlacionado.

Nenhum Product, Registry, backend Python, migrations, testes Python, snapshot
OpenAPI, cliente OpenAPI gerado, lockfile ou dependencia foi alterado por este
IMP.

---

## 2. Evidencia RED -> GREEN

RED documental inicial:

- `node scripts/tests/test-plan-025-contracts.js` = 170/171.
- Falha unica esperada: `frontend/playwright.jornadas.config.ts ausente`.

GREEN observado:

- `npm --prefix frontend run test:jornadas` = 6/6.
- `node scripts/tests/test-plan-025-contracts.js` deve validar 171/171 apos a
  documentacao final.
- `node scripts/tests/test-imp-301-scope.js` deve validar 383 arquivos
  protegidos, inventario final 397 e 0 divergencia.

O RED e evidencia temporal da sessao: apos o GREEN, ele nao e reproduzivel sem
reverter os arquivos do IMP-301.

---

## 3. Stack real observada

A suite `frontend/tests/jornadas-e2e/real-stack.mjs`:

- sobe `postgres:16` descartavel em porta local livre;
- executa `frontend/tests/jornadas-e2e/seed_integrated.py`;
- usa `Base.metadata.create_all` e `SqlAlchemyUnitOfWork` para preparar dados;
- inicia FastAPI real via `uvicorn emprestimo.presentation.api.main:app`;
- executa `npm run build` e `npm run start` do Next.js;
- grava estado em `frontend/test-results/jornadas/state.json`;
- encerra Next.js, FastAPI e remove o container em cleanup.

O teste de 5xx derruba a arvore do FastAPI e exige erro tecnico seguro com
`Correlation ID:` na UI.

---

## 4. Jornadas certificadas

Marcadores observados pela suite:

- login, refresh e logout;
- acesso negado por RBAC;
- 404 neutro cross-scope;
- Devedor -> Proposta;
- Proposta -> Contrato -> Emprestimo;
- pagamento repetido com a mesma chave;
- consulta do Motor sem calculo local;
- cobranca -> promessa -> agenda -> comunicacao;
- automacao operacional;
- 5xx correlacionado.

A suite rejeita mocks Playwright (`page.route`, `route.fulfill`,
`backend-fixture` e `mock-only`) e evita chamada direta do browser ao backend.

---

## 5. Escopo e inventario

Baseline IMP-301:

- baseline: 390 caminhos;
- mutaveis: 7 caminhos;
- protegidos: 383 caminhos;
- novos: 7 caminhos;
- inventario final esperado: 397 caminhos;
- predecessor:
  `docs/audits/evidence/frontend-mvp-imp-300-protected-baseline.json`;
- SHA-256 do predecessor:
  `a1969fd23c87270f3157d3db1271851fc3b2405424088f3ede1a6f060906e1a6`;
- HEAD/base: `e48cb72ee4f62428491e8b8c19a569611d83fca8`.

Arquivos alterados pelo IMP-301:

- `.github/workflows/quality.yml`;
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`;
- `docs/governance/frontend-mvp-traceability-matrix.md`;
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`;
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`;
- `frontend/package.json`;
- `scripts/tests/test-plan-025-contracts.js`.

Arquivos criados pelo IMP-301:

- `docs/audits/evidence/frontend-mvp-imp-301-protected-baseline.json`;
- `docs/audits/reports/frontend-mvp-imp-301-jornadas-compostas-report-2026-08-14.md`;
- `frontend/playwright.jornadas.config.ts`;
- `frontend/tests/jornadas-e2e/jornadas-compostas.spec.ts`;
- `frontend/tests/jornadas-e2e/real-stack.mjs`;
- `frontend/tests/jornadas-e2e/seed_integrated.py`;
- `scripts/tests/test-imp-301-scope.js`.

---

## 6. Caveats nao bloqueantes

- A CI remota Linux/Windows nao foi observada porque nao houve commit, push ou
  PR.
- O RED inicial e temporal e nao reexecutavel no estado GREEN sem reversao.
- A worktree contem acumulado local de IMPs anteriores ainda nao commitado.
- `git diff --check` pode emitir avisos EOL historicos no Windows; erro real
  continua bloqueante.

---

## 7. Decisao

IMP-301 esta concluido localmente quando `test:jornadas`, contrato documental,
scope, docs e diff-check estiverem verdes. O IMP-302 nao foi iniciado e deve
permanecer bloqueado ate novo `fable:fable-judge` focal.
