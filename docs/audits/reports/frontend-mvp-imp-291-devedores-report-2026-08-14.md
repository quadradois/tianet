# Relatorio IMP-291 - Devedores Frontend MVP

**Data:** 2026-08-14

**Plano relacionado:** PLAN-025

**Status:** Concluido; IMP-292 permanece bloqueado ate novo `fable:fable-judge`

---

## 1. Resultado

O IMP-291 materializou a jornada Devedores em `/app/devedores` e
`/app/devedores/[devedorId]`, consumindo somente os contratos oficiais do
Backend MVP certificado.

Entregue:

- listagem paginada e consulta exata por documento na rota oficial de listagem;
- detalhe cadastral e historico do Devedor;
- cadastro, atualizacao, inativacao e reativacao por comandos idempotentes;
- RBAC por permissao exata `devedor.*`;
- Carteira sempre derivada do contexto operacional corrente;
- 404 neutro, 400/403/409/422/5xx correlacionados e estados loading/empty/error/
  denied/overflow;
- evidencias desktop/mobile, axe e teclado.

Nao foi iniciado: Comercial, Propostas, Contratos, Motor, cobranca, agenda,
comunicacao, regras financeiras, dependencias novas ou alteracoes backend.

---

## 2. Evidencia RED -> GREEN

RED documental inicial observado:

- `node scripts/tests/test-plan-025-contracts.js`: 126/127;
- falha unica: `frontend/src/components/devedores/devedores.tsx ausente`.

GREEN final observado:

- `npm --prefix frontend run test:unit`: 12/12;
- `npm --prefix frontend run test:component`: 19/19;
- `npm --prefix frontend run test:bff`: 71/71;
- `npm --prefix frontend run test:contract`: 11/11, incluindo `api:check` e
  `typecheck`;
- `npm --prefix frontend run test:dashboard`: 12/12;
- `npm --prefix frontend run test:session`: 16/16;
- `npm --prefix frontend run test:devedores`: 10/10;
- `npm --prefix frontend run lint`: verde;
- `npm --prefix frontend run build`: verde.

---

## 3. Contratos e fronteiras observadas

OpenAPI preservado:

- 107 operacoes;
- 133 schemas;
- SHA-256:
  `8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1`.

Endpoints Devedores consumidos:

- `GET /credit/carteiras/{carteira_id}/devedores`;
- `POST /credit/carteiras/{carteira_id}/devedores`;
- `GET /credit/carteiras/{carteira_id}/devedores/{devedor_id}`;
- `PATCH /credit/carteiras/{carteira_id}/devedores/{devedor_id}`;
- `GET /credit/carteiras/{carteira_id}/devedores/{devedor_id}/historico`;
- `POST /credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar`;
- `POST /credit/carteiras/{carteira_id}/devedores/{devedor_id}/reativar`.

Fronteiras preservadas:

- nenhum `tenant_id` ou `carteira_id` aceito de URL, query, form ou payload;
- nenhum token exposto em Client Component, HTML, storage ou resposta publica;
- nenhuma chamada browser -> backend externo;
- nenhum calculo financeiro ou regra comercial local;
- nenhum link, rota ou componente de IMP-292+.

---

## 4. Evidencias visuais

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `frontend-mvp-imp-291-devedores-list-desktop.png` | 1440x900 | `3a3e1e0610ad4c0c65f5005249c6702fc133d52ca770df68f849c2fdd863a129` |
| `frontend-mvp-imp-291-devedores-list-mobile.png` | 390x844 | `cc1d272854a42683ea64f3ebb330a2ea72d5623c91365485c874db4a2253bde1` |
| `frontend-mvp-imp-291-devedor-detail-desktop.png` | 1440x900 | `b08d689966e77fde47fac82161ab4372a1212b07bba5ff3508fee0e7b9ee913d` |
| `frontend-mvp-imp-291-devedor-form-mobile.png` | 390x844 | `df1db5992e7a3649a851c663305332721bb89a10e5bec262b3000cc422912ca4` |

---

> **Pinos avancados no IMP-310** (PLAN-027). Duas causas distintas, ambas reais:
>
> 1. **A tela mudou.** O detalhe do Devedor passou a embutir os emprestimos dele,
>    e o fixture passou a conceder `motor.emprestimo.ler` — o que faz o item
>    "Motor" aparecer na navegacao tambem nas capturas de lista.
> 2. **A evidencia era irreprodutivel.** As capturas de detalhe variavam entre
>    execucoes identicas: o Correlation ID e um UUID novo a cada requisicao e era
>    impresso na tela apos Inativar/Reativar. O pino de SHA registrava ruido, nao
>    prova. A jornada agora congela o Correlation ID antes da captura, preservando
>    os 36 caracteres para nao deslocar o layout. Verificado: 4/4 identicas em
>    execucoes consecutivas.

---

## 5. Escopo e inventario

Manifesto IMP-291:

- baseline: 169 caminhos;
- mutaveis: 15 caminhos;
- protegidos: 154 caminhos;
- novos permitidos: 23 caminhos;
- inventario final esperado: 192 caminhos;
- predecessor: `docs/audits/evidence/frontend-mvp-imp-290-protected-baseline.json`
  com SHA-256
  `e13f4b26b95a6c021941d6788dd187a3ea1a099e4904be697cbab555e6fc6589`.

Arquivos alterados existentes:

- `.github/workflows/quality.yml`;
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`;
- `docs/audits/evidence/frontend-mvp-imp-290-dashboard-states-desktop.png`;
- `docs/audits/reports/frontend-mvp-imp-290-dashboard-report-2026-08-13.md`;
- `docs/governance/frontend-mvp-traceability-matrix.md`;
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`;
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`;
- `frontend/package.json`;
- `frontend/src/lib/shell/navigation-policy.ts`;
- `frontend/tests/component/session-shell.test.tsx`;
- `frontend/tests/session-e2e/session-shell.spec.ts`;
- `scripts/tests/test-plan-025-contracts.js`.

Arquivos criados:

- `docs/audits/evidence/frontend-mvp-imp-291-devedores-list-desktop.png`;
- `docs/audits/evidence/frontend-mvp-imp-291-devedores-list-mobile.png`;
- `docs/audits/evidence/frontend-mvp-imp-291-devedor-detail-desktop.png`;
- `docs/audits/evidence/frontend-mvp-imp-291-devedor-form-mobile.png`;
- `docs/audits/evidence/frontend-mvp-imp-291-protected-baseline.json`;
- `docs/audits/reports/frontend-mvp-imp-291-devedores-report-2026-08-14.md`;
- `frontend/playwright.devedores.config.ts`;
- `frontend/src/app/app/devedores/page.tsx`;
- `frontend/src/app/app/devedores/[devedorId]/page.tsx`;
- `frontend/src/app/app/devedores/actions.ts`;
- `frontend/src/components/devedores/devedor-form.client.tsx`;
- `frontend/src/components/devedores/devedor-status-dialog.client.tsx`;
- `frontend/src/components/devedores/devedores.tsx`;
- `frontend/src/lib/bff/devedores.server.ts`;
- `frontend/src/lib/devedores/devedores-policy.ts`;
- `frontend/tests/unit/devedores-policy.test.ts`;
- `frontend/tests/component/devedores.test.tsx`;
- `frontend/tests/bff/devedores.test.ts`;
- `frontend/tests/contract/devedores.test.ts`;
- `frontend/tests/devedores-e2e/backend-fixture.mjs`;
- `frontend/tests/devedores-e2e/devedores-a11y.spec.ts`;
- `frontend/tests/devedores-e2e/devedores.spec.ts`;
- `scripts/tests/test-imp-291-scope.js`.

---

## 6. Caveats nao bloqueantes

- O RED inicial e temporal e nao e reprodutivel sem reverter o worktree.
- A CI remota Linux/Windows nao foi observada porque nao houve commit/push.
- Caveats herdados permanecem: single-flight/logout-wins process-local, 401
  atrasado, ausencia de paginacao em alguns contratos posteriores, timezone por
  Tenant ausente para contratos que ainda nao o expõem.

---

## 7. Decisao

IMP-291 esta tecnicamente concluido no estado local observado.

IMP-292 permanece bloqueado ate execucao de novo `$fable:fable-judge` focal.
