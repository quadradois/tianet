# Relatorio IMP-299 - IAM permitido

**Plano relacionado:** PLAN-025  
**Backlog relacionado:** PLAN-025-EXEC / IMP-299  
**Data:** 2026-08-14  
**Status:** Concluido localmente; IMP-300 permanece bloqueado ate novo `fable:fable-judge`

---

## Resultado

O IMP-299 materializou `/app/iam` como superficie server-first de IAM permitido.
O recorte usa exclusivamente os contratos existentes de Perfis, catalogo
canonico e permissoes efetivas de Usuario conhecido. A Lacuna 7 permanece
explicita: nao existe lista de Usuarios, gestao integral de Usuarios,
credenciais, redefinicao de senha ou automacao neste IMP.

Nenhum backend Python, migration, teste Python, Product, Registry, snapshot
OpenAPI, dependencia ou lockfile foi alterado por este IMP.

---

## Evidencia RED -> GREEN

- RED inicial: `node scripts/tests/test-plan-025-contracts.js` = 168/169.
- Falha unica inicial: `frontend/src/lib/bff/iam.server.ts ausente`.
- GREEN focal observado:
  - unit IAM: 3/3;
  - navigation + IAM policy unit: 13/13;
  - component IAM: 4/4;
  - BFF IAM: 6/6;
  - contract IAM: 4/4, incluindo `api:check` e `typecheck`;
  - Playwright IAM: 8/8 desktop/mobile;
  - lint, typecheck e build verdes;
  - `node scripts/tests/test-plan-025-contracts.js`: 169/169;
  - scope IMP-299: 346 baseline, 9 mutaveis, 337 protegidos, 22 novos,
    inventario final 368 e 0 divergencia.

---

## Fronteiras implementadas

- Rota autenticada: `/app/iam`.
- Nenhum Route Handler publico novo.
- Operacoes oficiais do IMP-299: 11 GET/POST/PATCH/PUT/DELETE de Perfis,
  catalogo e Usuario conhecido.
- Sete comandos enviam `Idempotency-Key` conforme OpenAPI.
- `perfil.ler` governa leitura de Perfis, catalogo e permissoes efetivas.
- `perfil.gerir` governa criar/renomear/inativar Perfil, associar/remover
  permissao e atribuir/remover Perfil de Usuario conhecido.
- `GET /iam/permissoes` e a fonte canonica do catalogo; nao ha lista paralela
  de permission codes.
- Lacuna 7: `usuario_id` e aceito apenas como Usuario conhecido informado por UUID; nao
  ha busca ou listagem de Usuarios.
- 400/401/403/404/409/422/500 usam mensagens seguras e correlation ID.
- 404 usa texto neutro: "Recurso IAM nao encontrado ou indisponivel."

---

## Evidencia visual

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `frontend-mvp-imp-299-iam-desktop.png` | 1440x900 | `2466ab2e9808ce543675f4d7bef71873d7c7579107c413e5d2e6ef9060afb42b` |
| `frontend-mvp-imp-299-iam-mobile.png` | 390x844 | `47363255b77510598161ce866b015a5d6e79fe6521fe4239fed97fd5cd1d1031` |
| `frontend-mvp-imp-299-iam-states-desktop.png` | 1440x900 | `a0716780ebfa28cc7fb012ddd0628784fdc66ff3b11d87fa6158e7404d97aead` |
| `frontend-mvp-imp-299-iam-states-mobile.png` | 390x844 | `d440e86e733877a4d5d2288cb0a3b3a1c1a7d973bec5cb74ea5b96cc9179c7e9` |

As capturas foram geradas por `npm --prefix frontend run test:iam`. Correlation
IDs dinamicos sao normalizados para `corr-evidence-299` antes do screenshot.

---

## Arquivos criados

- `docs/audits/evidence/frontend-mvp-imp-299-iam-desktop.png`
- `docs/audits/evidence/frontend-mvp-imp-299-iam-mobile.png`
- `docs/audits/evidence/frontend-mvp-imp-299-iam-states-desktop.png`
- `docs/audits/evidence/frontend-mvp-imp-299-iam-states-mobile.png`
- `docs/audits/evidence/frontend-mvp-imp-299-protected-baseline.json`
- `docs/audits/reports/frontend-mvp-imp-299-iam-report-2026-08-14.md`
- `frontend/playwright.iam.config.ts`
- `frontend/src/app/app/iam/actions.ts`
- `frontend/src/app/app/iam/loading.tsx`
- `frontend/src/app/app/iam/page.tsx`
- `frontend/src/components/iam/iam-actions.client.tsx`
- `frontend/src/components/iam/iam-admin.tsx`
- `frontend/src/lib/bff/iam.server.ts`
- `frontend/src/lib/iam/iam-policy.ts`
- `frontend/tests/bff/iam.test.ts`
- `frontend/tests/component/iam.test.tsx`
- `frontend/tests/contract/iam.test.ts`
- `frontend/tests/iam-e2e/backend-fixture.mjs`
- `frontend/tests/iam-e2e/iam-a11y.spec.ts`
- `frontend/tests/iam-e2e/iam.spec.ts`
- `frontend/tests/unit/iam-policy.test.ts`
- `scripts/tests/test-imp-299-scope.js`

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
- O axe do E2E IAM desabilita `color-contrast` por falso positivo
  `elmPartiallyObscured`; contraste visual final permanece coberto pela
  foundation e deve ser recertificado no judge focal.
- IMP-300 permanece bloqueado ate novo `fable:fable-judge`.
