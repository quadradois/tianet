# Relatorio IMP-300 - Automacao

**Plano relacionado:** PLAN-025  
**Backlog relacionado:** PLAN-025-EXEC / IMP-300  
**Data:** 2026-08-14  
**Status:** Concluido localmente; IMP-301 permanece bloqueado ate novo `fable:fable-judge`

---

## Resultado

O IMP-300 materializou `/app/automacao` como superficie server-first para jobs,
templates e notificacoes. O recorte consome somente as 11 operacoes oficiais da
matriz de rastreabilidade: consultas de jobs/notificacoes/templates, cancel/retry
de job, criacao/aprovacao/ativacao de template e conciliacao de notificacao.

Nenhum worker, scheduler, provider externo, auditoria, observabilidade,
backend Python, migration, teste Python, Product, Registry, snapshot OpenAPI,
dependencia ou lockfile foi alterado por este IMP.

---

## Evidencia RED -> GREEN

- RED inicial: `node scripts/tests/test-plan-025-contracts.js` = 169/170.
- Falha unica inicial: `frontend/src/lib/bff/automacao.server.ts ausente`.
- GREEN focal observado:
  - unit Automacao + navegacao: 14/14;
  - component Automacao: 3/3;
  - BFF Automacao: 7/7;
  - contract Automacao: 3/3, incluindo `api:check` e `typecheck`;
  - Playwright Automacao: 8/8 desktop/mobile;
  - lint e typecheck verdes;
  - scope IMP-300: 368 baseline, 9 mutaveis, 359 protegidos, 22 novos,
    inventario final 390 e 0 divergencia.

---

## Fronteiras implementadas

- Rota autenticada: `/app/automacao`.
- Nenhum Route Handler publico novo.
- Operacoes oficiais do IMP-300: 11 GET/POST de jobs, notificacoes e templates.
- Permissoes exatas:
  - `automacao.job.consultar`;
  - `automacao.job.cancelar`;
  - `automacao.job.retry`;
  - `notificacao.consultar`;
  - `notificacao.template.gerir`;
  - `notificacao.conciliar`.
- Somente `POST /credit/notificacoes/{notification_id}/conciliar` envia
  `Idempotency-Key`, conforme OpenAPI. Cancel/retry de job e comandos de
  template nao inventam o header.
- A Carteira vem exclusivamente do contexto operacional corrente.
- 400/401/403/404/409/422/500 usam mensagens seguras e correlation ID.
- 404 usa texto neutro: "Recurso de Automacao nao encontrado ou indisponivel."
- A rota de agenda `POST /credit/agenda/lembretes/{lembrete_id}/enviar`
  permanece fora deste recorte de Automacao.

---

## Evidencia visual

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `frontend-mvp-imp-300-automacao-desktop.png` | 1440x900 | `70322a8acad72666c922e594da04b24003bb50837c6cf12b8cb0c9ad30a0c760` |
| `frontend-mvp-imp-300-automacao-mobile.png` | 390x844 | `6dd0293ac0f3be96c0d3f7dc0ed8d2c91091a83e593c886f5735615ab3b3aa39` |
| `frontend-mvp-imp-300-automacao-states-desktop.png` | 1440x900 | `bedbe9e1a181ed03214259a018f3b34924218bb1ba3e0a075ea9e7e9a2d52f7c` |
| `frontend-mvp-imp-300-automacao-states-mobile.png` | 390x844 | `6dd0293ac0f3be96c0d3f7dc0ed8d2c91091a83e593c886f5735615ab3b3aa39` |

As capturas foram geradas por `npm --prefix frontend run test:automacao`.
Correlation IDs dinamicos sao normalizados para `corr-evidence-300` antes do
screenshot.

---

## Arquivos criados

- `docs/audits/evidence/frontend-mvp-imp-300-automacao-desktop.png`
- `docs/audits/evidence/frontend-mvp-imp-300-automacao-mobile.png`
- `docs/audits/evidence/frontend-mvp-imp-300-automacao-states-desktop.png`
- `docs/audits/evidence/frontend-mvp-imp-300-automacao-states-mobile.png`
- `docs/audits/evidence/frontend-mvp-imp-300-protected-baseline.json`
- `docs/audits/reports/frontend-mvp-imp-300-automacao-report-2026-08-14.md`
- `frontend/playwright.automacao.config.ts`
- `frontend/src/app/app/automacao/actions.ts`
- `frontend/src/app/app/automacao/loading.tsx`
- `frontend/src/app/app/automacao/page.tsx`
- `frontend/src/components/automacao/automacao-actions.client.tsx`
- `frontend/src/components/automacao/automacao.tsx`
- `frontend/src/lib/automacao/automacao-policy.ts`
- `frontend/src/lib/bff/automacao.server.ts`
- `frontend/tests/automacao-e2e/automacao-a11y.spec.ts`
- `frontend/tests/automacao-e2e/automacao.spec.ts`
- `frontend/tests/automacao-e2e/backend-fixture.mjs`
- `frontend/tests/bff/automacao.test.ts`
- `frontend/tests/component/automacao.test.tsx`
- `frontend/tests/contract/automacao.test.ts`
- `frontend/tests/unit/automacao-policy.test.ts`
- `scripts/tests/test-imp-300-scope.js`

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
- IMP-301 permanece bloqueado ate novo `fable:fable-judge`.
