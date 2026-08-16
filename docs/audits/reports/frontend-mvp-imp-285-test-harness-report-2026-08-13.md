# Relatorio de execucao do IMP-285 - Test harness do Frontend MVP

**Versao:** 1.0.0

**Data:** 2026-08-13

**Plano relacionado:** PLAN-025

**Status:** IMP-285 concluido; IMP-286 nao iniciado

---

# 1. Resultado

O IMP-285 materializou exclusivamente o harness tecnico de testes no workspace
`frontend/`. Nenhum arquivo de backend, migration, teste Python, Product,
Registry, snapshot OpenAPI ou `src/app` foi alterado.

As categorias sao independentes:

- Vitest/Node para unidade tecnica;
- Testing Library, user-event, jest-dom, jsdom e MSW Node para componente;
- Vitest/Node para leitura do snapshot OpenAPI certificado;
- Playwright Chromium contra o build de producao Next iniciado pelo runner.

---

# 2. Evidencia RED -> GREEN

Antes da instalacao, `node scripts/tests/test-plan-025-contracts.js` passou 26
de 27 casos e falhou exclusivamente com
`frontend/vitest.unit.config.ts ausente`.

O primeiro agregado encontrou dois erros reais do harness sob TypeScript
estrito: uma propriedade opcional `workers: undefined` incompatível com
`exactOptionalPropertyTypes` e um acumulador OpenAPI inferido como `unknown`.
Ambos foram corrigidos nos testes/configs, sem relaxar o `tsconfig`.

Depois da correcao:

- unit: 1 arquivo, 1 teste;
- component/MSW: 1 arquivo, 4 testes;
- contract: 1 arquivo, 1 teste;
- Playwright: 1 arquivo, 1 teste Chromium;
- agregado `test:harness`: todas as quatro categorias verdes.

---

# 3. Dependencias diretas e fronteiras

Pins exatos adicionados ao unico lockfile permitido, `frontend/package-lock.json`:

- `vitest` 4.1.10;
- `jsdom` 30.0.1;
- `@testing-library/react` 16.3.2;
- `@testing-library/dom` 10.4.1;
- `@testing-library/jest-dom` 7.0.1;
- `@testing-library/user-event` 14.6.4;
- `msw` 2.15.0;
- `@playwright/test` 1.62.1.

Nao foram instalados shadcn/ui, Tailwind, Radix, axe, cliente OpenAPI, estado
global, formularios, auth ou BFF. O MSW nao registra service worker e intercepta
somente o recurso interno `msw.harness.invalid/lifecycle`, sem simular endpoint
backend. O teste de contrato le o JSON oficial e nao gera tipos ou consumidor.

---

# 4. Gates observados

| Gate | Resultado |
|---|---|
| toolchain controlada | Node 24.19.0/npm 11.17.0 via execucao efemera exata |
| instalacao | dependencias instaladas com `--ignore-scripts`; audit 0 vulnerabilidades |
| unit | 1/1 verde |
| component/MSW | 4/4 verdes, placeholder, interacao, recurso tecnico isolado e request inesperada fail-closed |
| contract | 1/1 verde; 107 operacoes, 133 schemas, `/health` e endpoints IAM observados |
| infrastructure | PostgreSQL 16 descartavel + FastAPI `/health` verdes, com cleanup observado |
| Playwright Windows | Chromium 151 versionado instalado; 1/1 verde |
| agregado | `npm run test:harness` verde |
| lint | verde, zero warning |
| typecheck | `next typegen && tsc --noEmit` verde |
| build | Next.js 16.3.0 verde; rota `/` estatica |
| contrato documental final | 37/37 verde, incluindo 9 mutacoes negativas do IMP-285 |
| escopo | predecessor IMP-284 verificado; 49 arquivos protegidos; 0 divergencia |
| docs:validate | 316 verificacoes OK, 29 avisos historicos, 0 erro |
| docs:test | verde, incluindo contrato PLAN-025 e gate encadeado |
| backend adjacente | pytest completo, Ruff, Black e mypy verdes |
| migrations | ciclo upgrade/downgrade/upgrade verde em PostgreSQL 16 descartavel na porta 55433 |
| git diff --check | verde |

A CI foi configurada como matriz `ubuntu-latest`/`windows-latest`, instala npm
11.17.0 e Chromium explicitamente, executa as quatro categorias e publica
`playwright-report`/`test-results` com `if: always()`. A execucao remota nao foi
observada porque commit e push sao proibidos nesta sessao; ela permanece gate do
primeiro commit/PR.

---

# 5. Servidores, banco e artifacts

O Playwright inicia deterministicamente `next build` + `next start` em
`127.0.0.1:3100`, espera readiness e usa `reuseExistingServer: false`.
Artifacts ficam em `test-results/` e `playwright-report/`, ignorados pelo Git e
publicados pela CI.

O smoke de infraestrutura sobe PostgreSQL 16 descartavel em porta local livre,
espera `pg_isready`, inicia a aplicacao FastAPI real em outra porta livre,
observa `/health` healthy e encerra processo/container em `finally`. Isso prova
servidor e banco deterministas sem criar consumidor frontend. A integracao do
frontend permanece bloqueada ate cliente OpenAPI (IMP-287) e BFF (IMP-288).
O cleanup aguarda a saida do FastAPI, escala para `SIGKILL` se necessario,
remove o container com `docker rm --force` e falha se `docker inspect` ainda o
encontrar; a execucao final deixou zero recurso residual.

O `playwright-cli` abriu o build local e confirmou titulo e heading. Observou um
unico 404 de `favicon.ico`; e caveat visual nao bloqueante reservado ao IMP-286,
sem justificativa para alterar `src/app` neste pacote.

---

# 6. Evidencia de escopo

O baseline `frontend-mvp-imp-285-protected-baseline.json` registra o HEAD
`e48cb72ee4f62428491e8b8c19a569611d83fca8`, os 59 caminhos existentes antes do
IMP-285 e o SHA-256 do manifesto imutavel do IMP-284. O gate atual:

- valida o predecessor;
- recalcula 49 hashes nao mutaveis;
- proibe allowlist em backend, migrations, testes Python, Product, Registry e
  snapshot OpenAPI;
- compara o inventario completo de `git status` com a allowlist exata.

---

# 7. Arquivos do IMP-285

Alterados:

- `.github/workflows/quality.yml`;
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`;
- `docs/governance/frontend-mvp-traceability-matrix.md`;
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`;
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`;
- `frontend/.gitignore`, `README.md`, `package.json`, `package-lock.json`;
- `scripts/tests/test-plan-025-contracts.js`.

Criados:

- este relatorio;
- `docs/audits/evidence/frontend-mvp-imp-285-protected-baseline.json`;
- `scripts/tests/test-imp-285-scope.js`;
- `frontend/vitest.unit.config.ts`, `vitest.component.config.ts`,
  `vitest.contract.config.ts`, `playwright.config.ts`;
- `frontend/tests/toolchain-check.mjs`;
- `frontend/tests/unit/harness.test.ts`;
- `frontend/tests/component/setup.ts`, `harness.test.tsx`;
- `frontend/tests/mocks/server.ts`;
- `frontend/tests/contract/openapi-snapshot.test.ts`;
- `frontend/tests/e2e/scaffold.spec.ts`.
- `frontend/tests/infrastructure/real-stack-smoke.mjs`.

---

# 8. Decisao do IMP-286

O IMP-285 esta tecnicamente concluido. O IMP-286 permanece **planejado e nao
iniciado** ate `fable:fable-judge` focal deste pacote. A execucao remota da CI
continua obrigatoria no primeiro commit/PR.

---

# 9. Historico de versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-13 | Execucao focal do IMP-285 sem emissao de novo ID PLAN. |
