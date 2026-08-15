# Relatorio de execucao do IMP-284 - Scaffold governado do Frontend MVP

**Versao:** 1.0.0

**Data:** 2026-08-12

**Plano relacionado:** PLAN-025

**Status:** IMP-284 concluido; IMP-285 nao iniciado

---

# 1. Resultado

O IMP-284 materializou um workspace Next.js App Router isolado em `frontend/`,
sem converter o pacote documental da raiz em monorepo e sem alterar backend,
migrations, testes Python, Product ou snapshot OpenAPI.

Decisoes registradas antes da instalacao:

- npm com `package-lock.json` v3 proprio;
- Node.js 24.19.0 LTS e npm 11.17.0;
- Next.js 16.3.0, React/React DOM 19.2.8 e TypeScript 5.9.3;
- Server Components por padrao e nenhuma fronteira cliente no placeholder;
- BFF no IMP-288, shadcn/ui no IMP-286 e cliente OpenAPI no IMP-287;
- nenhuma variavel de ambiente ou segredo no scaffold.

---

# 2. Evidencia RED -> GREEN

Antes do scaffold, `node scripts/tests/test-plan-025-contracts.js` passou 16 de
17 casos e falhou somente com `frontend/package.json ausente`.

Depois da materializacao, a suite passou 26 de 26 casos. As mutacoes negativas
comprovam que o contrato rejeita TypeScript sem `strict`, range no pin do
Next.js e CI sem build.

---

# 3. Dependencias diretas

Runtime: somente `next`, `react` e `react-dom`.

Desenvolvimento: somente TypeScript, ESLint/config Next e tipos de Node/React.
Vitest, Testing Library, MSW, Playwright, Tailwind, shadcn, Radix,
`openapi-typescript` e `openapi-fetch` nao foram instalados.

O lockfile contem um `postinstall` transitivo de `unrs-resolver`. A instalacao
governada usa `npm ci --ignore-scripts`, portanto nenhum script transitivo e
executado; o build permanece verde sem esse script. `engines.npm` e
`engine-strict=true` ainda fazem a instalacao falhar com npm diferente do
fixado.

---

# 4. Gates observados

| Gate | Resultado |
|---|---|
| instalacao limpa com Node 24.19.0/npm 11.17.0 | `npm ci --ignore-scripts` verde |
| toolchain divergente | Node 24.15.0/npm 11.15.0 rejeitados com `EBADENGINE` |
| lint | verde, zero warning |
| typecheck | `next typegen && tsc --noEmit` verde |
| build | Next.js 16.3.0 verde, rota `/` estatica, zero warning apos fixar `turbopack.root` |
| contrato PLAN-025 | 26/26 verde |
| docs:validate | 315 verificacoes OK, 29 avisos historicos, 0 erro e nenhum aviso novo |
| docs:test | verde; inclui contrato PLAN-025 26/26, gate de escopo e mutacoes negativas |
| git diff --check | verde |
| OpenAPI | preservado em 107 operacoes, 133 schemas e SHA-256 `8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1` |
| escopo preexistente protegido | 37 arquivos comparados ao manifesto inicial; 0 divergencia |

`HEAD`, `master` e `origin/master` permaneceram em
`e48cb72ee4f62428491e8b8c19a569611d83fca8`. Testes unitarios, de componente,
MSW e Playwright sao N/A porque pertencem ao IMP-285.

O job de CI foi configurado, mas nao executado remotamente: commit e push eram
proibidos nesta sessao. Seus comandos equivalentes foram observados localmente
com Node 24.19.0 e npm 11.17.0 via toolchain efemera exata.

A prova de escopo e reproduzivel por
`node scripts/tests/test-imp-284-scope.js` contra o manifesto SHA-256 versionado
em `docs/audits/evidence/frontend-mvp-imp-284-protected-baseline.json`.

---

# 5. Fronteiras observadas

O placeholder nao usa `use client`, `fetch`, Route Handler, Server Action,
endpoint backend, estado global ou modelo de API. Nao contem formula, agregacao
ou reinterpretacao financeira. A revisao `vercel-react-best-practices`
confirmou Server Component puro, ausencia de serializacao cliente e ausencia de
estado mutavel compartilhado.

---

# 6. Decisao do IMP-285

O IMP-285 permanece **planejado e nao iniciado**. Tecnicamente, seus
pre-requisitos de scaffold estao presentes; sua autorizacao depende de
`fable:fable-judge` focal sobre o IMP-284.

---

# 7. Arquivos do IMP-284

Alterados:

- `.gitignore`;
- `.github/workflows/quality.yml`;
- `docs/architecture/adrs/ADR-001-stack-tecnologica-oficial-mvp.md`;
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`;
- `docs/governance/frontend-mvp-traceability-matrix.md`;
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`;
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`;
- `scripts/tests/test-plan-025-contracts.js`.

Criados como entregaveis:

- este relatorio;
- `docs/audits/evidence/frontend-mvp-imp-284-protected-baseline.json`;
- `scripts/tests/test-imp-284-scope.js`;
- `frontend/.gitignore`, `.npmrc`, `README.md`, `eslint.config.mjs`, `next.config.ts`,
  `package.json`, `package-lock.json`, `tsconfig.json`;
- `frontend/src/app/globals.css`, `layout.tsx` e `page.tsx`.

`frontend/node_modules/`, `frontend/.next/`, `frontend/next-env.d.ts` e
`frontend/tsconfig.tsbuildinfo` foram gerados localmente pelos gates e estao
ignorados. Nenhum arquivo preexistente fora da lista declarada divergiu do
manifesto inicial.

---

# 8. Historico de versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-12 | Execucao focal do IMP-284 sem emissao de novo ID PLAN. |
