# Relatorio de execucao — IMP-292 Comercial

**Data:** 2026-08-14

**Status:** IMP-292 concluido; IMP-293 nao iniciado e sob gate adversarial

## Resultado

O IMP-292 materializou a jornada Comercial governada a partir de Devedor ativo,
sem criar Contratos, Motor, pagamentos ou regra financeira no frontend. A
superficie usa somente as 12 operacoes oficiais do OpenAPI Comercial, com
Carteira propria do contexto operacional, RBAC por igualdade exata e parametros
tratados como JSON opaco retornado pelo backend.

## Evidencia RED -> GREEN

- RED documental inicial: `node scripts/tests/test-plan-025-contracts.js` passou
  127/128; a unica falha esperada foi
  `frontend/src/components/comercial/comercial.tsx ausente`.
- GREEN focal observado:
  - `npm --prefix frontend run test:unit -- --run tests/unit/comercial-policy.test.ts`: 4/4.
  - `npm --prefix frontend run test:component -- --run tests/component/comercial.test.tsx tests/component/devedores.test.tsx`: 9/9.
  - `npm --prefix frontend run test:bff -- --run tests/bff/comercial.test.ts`: 7/7.
  - `npm --prefix frontend run test:contract -- --run tests/contract/comercial.test.ts`: 3/3, incluindo `api:check` e `typecheck`.
  - `npm --prefix frontend run test:comercial`: 10/10.

## Evidencia visual

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `frontend-mvp-imp-292-comercial-list-desktop.png` | 1440x900 | `fa22e72628c663260bdd03864c9ae37a6cf04dc71c8e9fbe4ecfb52b7c886238` |
| `frontend-mvp-imp-292-comercial-list-mobile.png` | 390x844 | `289998fff89e40dd30e382e706e0c71343551b72032268894344a0efb8724aad` |
| `frontend-mvp-imp-292-proposta-detail-desktop.png` | 1440x900 | `739e12af2ce5d6c7e7d2783602dfdb3860c02cf17b63050cd738b714a1537d87` |
| `frontend-mvp-imp-292-proposta-flow-mobile.png` | 390x844 | `ea4511035299f0c9a882b7271d70597fcfbda9439f21f804de12d716ac348509` |

## Arquivos alterados ou criados no IMP-292

Alterados:

- `.github/workflows/quality.yml`
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`
- `docs/governance/frontend-mvp-traceability-matrix.md`
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`
- `frontend/README.md`
- `frontend/package.json`
- `frontend/src/components/devedores/devedores.tsx`
- `frontend/src/lib/shell/navigation-policy.ts`
- `frontend/tests/component/devedores.test.tsx`
- `scripts/tests/test-plan-025-contracts.js`

Criados:

- `docs/audits/evidence/frontend-mvp-imp-292-comercial-list-desktop.png`
- `docs/audits/evidence/frontend-mvp-imp-292-comercial-list-mobile.png`
- `docs/audits/evidence/frontend-mvp-imp-292-proposta-detail-desktop.png`
- `docs/audits/evidence/frontend-mvp-imp-292-proposta-flow-mobile.png`
- `docs/audits/evidence/frontend-mvp-imp-292-protected-baseline.json`
- `docs/audits/reports/frontend-mvp-imp-292-comercial-report-2026-08-14.md`
- `frontend/playwright.comercial.config.ts`
- `frontend/src/app/app/comercial/actions.ts`
- `frontend/src/app/app/comercial/propostas/[propostaId]/page.tsx`
- `frontend/src/app/app/devedores/[devedorId]/comercial/page.tsx`
- `frontend/src/components/comercial/comercial-json-form.client.tsx`
- `frontend/src/components/comercial/comercial.tsx`
- `frontend/src/components/comercial/proposta-decision-dialog.client.tsx`
- `frontend/src/lib/bff/comercial.server.ts`
- `frontend/src/lib/comercial/comercial-policy.ts`
- `frontend/tests/bff/comercial.test.ts`
- `frontend/tests/comercial-e2e/backend-fixture.mjs`
- `frontend/tests/comercial-e2e/comercial-a11y.spec.ts`
- `frontend/tests/comercial-e2e/comercial.spec.ts`
- `frontend/tests/component/comercial.test.tsx`
- `frontend/tests/contract/comercial.test.ts`
- `frontend/tests/unit/comercial-policy.test.ts`
- `scripts/tests/test-imp-292-scope.js`

## Fronteiras e caveats

- trilha de decisoes detalhada nao possui endpoint no OpenAPI Comercial; o
  frontend mostra apenas `total_decisoes` e estados retornados.
- filtro por periodo nao possui contrato no OpenAPI Comercial; a lista usa
  apenas `page`, `size` e `estado`.
- Idempotency-Key nao e publicada no OpenAPI Comercial; o frontend nao inventa
  esse header.
- CI Linux/Windows esta configurada, mas a execucao remota nao foi observada
  porque nao houve commit/push.
- O RED e evidencia temporal da sessao; nao e reproduzivel sem reverter o
  estado GREEN.

## Decisao

IMP-292 esta tecnicamente concluido e pronto para `$fable:fable-judge` focal.
O IMP-293 permanece bloqueado ate esse judge declarar VERIFIED ou VERIFIED WITH
CAVEATS nao bloqueantes.
