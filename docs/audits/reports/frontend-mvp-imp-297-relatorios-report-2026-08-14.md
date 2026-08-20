# Relatorio IMP-297 - Relatorios operacionais

**Plano relacionado:** PLAN-025

**Data:** 2026-08-14

**Status:** Concluido; IMP-298 permanece Planejado e depende de novo `fable:fable-judge`

---

## 1. Resultado

O IMP-297 materializou `/app/relatorios` como superficie server-first de leitura
dos Relatorios oficiais do backend certificado. A entrega consome somente os 4
GETs publicados no OpenAPI atual, sempre com Carteira propria do contexto,
periodo explicito e RBAC exato `relatorios.operacionais.ler`.

Nao foram criados Route Handlers publicos, Server Actions, exportacao,
paginacao, filtros nao publicados, calculo financeiro local, dependencias,
lockfiles, backend Python, Product, Registry ou snapshot OpenAPI.

---

## 2. Evidencia RED -> GREEN

- RED documental inicial: `node scripts/tests/test-plan-025-contracts.js` =
  157/158, falha unica esperada por `frontend/src/lib/bff/relatorios.server.ts`
  ausente.
- GREEN focal observado:
  - unit Relatorios + navegacao: 12/12;
  - component Relatorios: 4/4;
  - BFF Relatorios: 6/6;
  - contract Relatorios: 3/3, incluindo `api:check` e `typecheck`;
  - Playwright Relatorios: 8/8;
  - contrato documental PLAN-025: 160/160.

O judge adversarial focal identificou uma derivacao local de contagens por
`.length` nos arrays oficiais de pagamentos/fluxo. A correcao final removeu
essas contagens derivadas, passou a exibir os IDs retornados e adicionou mutacao
documental que rejeita a regressao.

O judge tambem identificou um falso verde documental em que uma mutacao que
adicionava `Idempotency-Key` diretamente ao loader de Relatorios era aceita pelo
contrato. O gate final rejeita explicitamente esse header inventado e preserva a
fronteira dos 4 GETs oficiais sem `Idempotency-Key`.

O RED e evidencia temporal da sessao; apos o GREEN, o estado reproduzivel e o
contrato documental final.

---

## 3. Contratos implementados

- `GET /credit/carteiras/{carteira_id}/relatorios/resumo`
- `GET /credit/carteiras/{carteira_id}/relatorios/vencimentos`
- `GET /credit/carteiras/{carteira_id}/relatorios/pagamentos`
- `GET /credit/carteiras/{carteira_id}/relatorios/fluxo`

Todos sao GETs protegidos por BearerAuth, com `X-Correlation-ID` opcional e sem
`Idempotency-Key` publicado no OpenAPI atual. O frontend nao inventa esse
header.

Estados observados: 400, 401, 403, 404, 500, timeout e resposta 200 malformada.
O 404 e neutro; mensagens estruturadas vindas do backend sao sanitizadas antes
de chegar ao browser.

---

## 4. Evidencia visual

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `frontend-mvp-imp-297-relatorios-list-desktop.png` | 1440x900 | `604b66c963aad9ab34f2ea6ec574c467ac3daf2437014617893c093eec517df5` |
| `frontend-mvp-imp-297-relatorios-list-mobile.png` | 390x844 | `018d8cbe0080dfc24d3f36c49298418982e8ae18d5ab7d5c429fbf4a1cba3e03` |
| `frontend-mvp-imp-297-fluxo-desktop.png` | 1440x900 | `68d927c1f4e3c56952376c8833e56dd7219e81f04812c8ba3f641b82d4fa19d3` |
| `frontend-mvp-imp-297-relatorios-states-mobile.png` | 390x844 | `fdf75dcfb3fa927db11dccc87f02f8e163ebfac063c0754ba48f5c4bc27609d8` |

## 5. Arquivos alterados/criados

Baseline IMP-297: 304 caminhos; mutaveis: 10; protegidos: 294; novos: 20;
inventario final esperado: 324.

Arquivos existentes alterados:

- `.github/workflows/quality.yml`
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`
- `docs/governance/frontend-mvp-traceability-matrix.md`
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`
- `frontend/package.json`
- `frontend/src/lib/shell/navigation-policy.ts`
- `frontend/tests/unit/navigation-policy.test.ts`
- `scripts/tests/test-plan-025-contracts.js`

Arquivos novos:

- `docs/audits/evidence/frontend-mvp-imp-297-fluxo-desktop.png`
- `docs/audits/evidence/frontend-mvp-imp-297-protected-baseline.json`
- `docs/audits/evidence/frontend-mvp-imp-297-relatorios-list-desktop.png`
- `docs/audits/evidence/frontend-mvp-imp-297-relatorios-list-mobile.png`
- `docs/audits/evidence/frontend-mvp-imp-297-relatorios-states-mobile.png`
- `docs/audits/reports/frontend-mvp-imp-297-relatorios-report-2026-08-14.md`
- `frontend/playwright.relatorios.config.ts`
- `frontend/src/app/app/relatorios/loading.tsx`
- `frontend/src/app/app/relatorios/page.tsx`
- `frontend/src/components/relatorios/relatorios.tsx`
- `frontend/src/lib/bff/relatorios.server.ts`
- `frontend/src/lib/relatorios/relatorios-policy.ts`
- `frontend/tests/bff/relatorios.test.ts`
- `frontend/tests/component/relatorios.test.tsx`
- `frontend/tests/contract/relatorios.test.ts`
- `frontend/tests/relatorios-e2e/backend-fixture.mjs`
- `frontend/tests/relatorios-e2e/relatorios-a11y.spec.ts`
- `frontend/tests/relatorios-e2e/relatorios.spec.ts`
- `frontend/tests/unit/relatorios-policy.test.ts`
- `scripts/tests/test-imp-297-scope.js`

---

## 6. Caveats preservados

- CI remota Linux/Windows esta configurada, mas nao foi observada sem
  commit/push.
- O RED inicial e temporal e nao e reproduzivel sem voltar o worktree.
- Exportacao, paginacao e filtros alem de `data_referencia`, `inicio` e `fim`
  dependem de contrato futuro.
- Pagamentos, vencimentos e fluxo sao apresentados como retornados; o frontend
  nao assume autoridade financeira.

---

## 7. Proxima decisao

O IMP-298 permanece Planejado. Recomenda-se executar `fable:fable-judge` focal
do IMP-297 antes de autorizar Configuracoes Financeiras.

---

## 8. Repino de evidencia visual (IMP-327, DR-004)

As quatro capturas foram regravadas em 2026-08-19. O plano de parcelas saiu do
contrato pela DR-004 e a tela de vencimentos passou a mostrar o acerto: data do
acerto, situacao, dia combinado, dias sem pagamento e o emprestado. O fluxo
diario trocou `previsto` — que so podia vir do plano — pela contagem de acertos
do dia.

Os SHA-256 publicados acima acompanham os bytes vigentes. Manter os hashes
antigos preservaria imagens de colunas que nao existem mais, e uma evidencia que
mostra tela removida engana mais do que um pino que precisou ser refeito.
