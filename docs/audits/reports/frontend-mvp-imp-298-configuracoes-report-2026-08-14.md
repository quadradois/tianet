# Relatorio IMP-298 - Configuracoes Financeiras

**Plano relacionado:** PLAN-025  
**Backlog relacionado:** PLAN-025-EXEC / IMP-298  
**Data:** 2026-08-14  
**Status:** Concluido localmente; IMP-299 permanece bloqueado ate novo `fable:fable-judge`

---

## Resultado

O IMP-298 materializou a superficie server-first de Configuracoes Financeiras em
`/app/configuracoes-financeiras`, usando exclusivamente as 13 operacoes oficiais
do OpenAPI para configuracoes, vigente, modalidades, calendarios, transicoes e
snapshots. A Carteira vem do contexto operacional corrente, o RBAC usa
permissoes exatas, parametros financeiros sao tratados como payload opaco e o
frontend nao inventa `Idempotency-Key`.

Nenhum backend Python, migration, teste Python, Product, Registry, snapshot
OpenAPI, dependencia ou lockfile foi alterado por este IMP.

---

## Evidencia RED -> GREEN

- RED inicial: `node scripts/tests/test-plan-025-contracts.js` = 160/161.
- Falha unica inicial: `frontend/src/lib/bff/configuracoes-financeiras.server.ts ausente`.
- GREEN focal observado:
  - unit frontend completo: 44/44;
  - component frontend completo: 47/47;
  - BFF frontend completo: 115/115;
  - contract frontend completo: 33/33, incluindo `api:check` e `typecheck`;
  - Playwright Configuracoes: 8/8 desktop/mobile;
  - contrato documental: 168/168;
  - `docs:validate`: 330 OK, 29 avisos historicos, 0 erros;
  - scope IMP-298: 324 baseline, 9 mutaveis, 315 protegidos, 22 novos e inventario final esperado 346.

---

## Fronteiras implementadas

- Rota autenticada: `/app/configuracoes-financeiras`.
- Nenhum Route Handler publico novo.
- Nenhuma rota de IAM, Automacao, Templates ou jornada futura.
- Nenhuma dependencia nova e nenhum lockfile alterado.
- BFF `server-only` com `cache: "no-store"`, Bearer e `X-Correlation-ID`.
- Respostas 2xx inesperadas e payloads malformados fecham como problema seguro.
- 400/401/403/404/409/422/500 e timeout possuem mensagem segura e correlation ID.
- 404 usa texto neutro: "Configuracao Financeira nao encontrada ou indisponivel."
- `tenant_id` e `carteira_id` vindos do browser nao sao aceitos.
- Parametros, taxas e politica de arredondamento permanecem opacos; sem soma,
  arredondamento, taxa derivada, parcela, saldo ou elegibilidade no frontend.

---

## Evidencia visual

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `frontend-mvp-imp-298-configuracoes-desktop.png` | 1440x900 | `be4c9a0582ddd9939fc0aaa35f9f17c24aac3580928a6baa7bbe8a61b4fae296` |
| `frontend-mvp-imp-298-configuracoes-mobile.png` | 390x844 | `b83295fb862c6f306d333a09f622bb4f49ee5eb34ca7f6b12c994bdad170581d` |
| `frontend-mvp-imp-298-configuracoes-states-desktop.png` | 1440x900 | `c29d03d6c55f07244bad23f3e419b6d19c15fe5db09d83a881a65e536f834b4d` |
| `frontend-mvp-imp-298-configuracoes-states-mobile.png` | 390x844 | `eb38be1598f6c88b3ba16e4ff8bec272225e84317f20ddbe7da7aba1f72a45db` |

As capturas foram geradas por `npm --prefix frontend run test:configuracoes`.
Correlation IDs dinamicos sao normalizados para `corr-evidence-298` antes do
screenshot.

---

## Arquivos criados

- `docs/audits/evidence/frontend-mvp-imp-298-configuracoes-desktop.png`
- `docs/audits/evidence/frontend-mvp-imp-298-configuracoes-mobile.png`
- `docs/audits/evidence/frontend-mvp-imp-298-configuracoes-states-desktop.png`
- `docs/audits/evidence/frontend-mvp-imp-298-configuracoes-states-mobile.png`
- `docs/audits/evidence/frontend-mvp-imp-298-protected-baseline.json`
- `docs/audits/reports/frontend-mvp-imp-298-configuracoes-report-2026-08-14.md`
- `frontend/playwright.configuracoes.config.ts`
- `frontend/src/app/app/configuracoes-financeiras/actions.ts`
- `frontend/src/app/app/configuracoes-financeiras/loading.tsx`
- `frontend/src/app/app/configuracoes-financeiras/page.tsx`
- `frontend/src/components/configuracoes-financeiras/configuracoes-actions.client.tsx`
- `frontend/src/components/configuracoes-financeiras/configuracoes-financeiras.tsx`
- `frontend/src/lib/bff/configuracoes-financeiras.server.ts`
- `frontend/src/lib/configuracoes-financeiras/configuracoes-policy.ts`
- `frontend/tests/bff/configuracoes-financeiras.test.ts`
- `frontend/tests/component/configuracoes-financeiras.test.tsx`
- `frontend/tests/configuracoes-e2e/backend-fixture.mjs`
- `frontend/tests/configuracoes-e2e/configuracoes-a11y.spec.ts`
- `frontend/tests/configuracoes-e2e/configuracoes.spec.ts`
- `frontend/tests/contract/configuracoes-financeiras.test.ts`
- `frontend/tests/unit/configuracoes-policy.test.ts`
- `scripts/tests/test-imp-298-scope.js`

## Arquivos existentes alterados

- `.github/workflows/quality.yml`
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`
- `docs/governance/frontend-mvp-traceability-matrix.md`
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`
- `frontend/package.json`
- `frontend/src/lib/shell/navigation-policy.ts`
- `frontend/tests/unit/navigation-policy.test.ts`
- `scripts/tests/test-plan-025-contracts.js`

---

## Caveats preservados

- O RED e temporal e nao e reproduzivel sem reverter o estado GREEN.
- A CI remota Linux/Windows ainda nao foi observada porque nao houve commit/push.
- O shell local pode usar Node/npm diferente dos pinos governados; a CI continua
  configurada para Node 24.19.0 e npm 11.17.0.
- Avisos EOL do Windows podem aparecer em `git diff --check`.
- IMP-299 permanece bloqueado ate novo `fable:fable-judge`.
