# Relatorio focal — IMP-295 Cobranca

**Plano relacionado:** PLAN-025 — Frontend MVP Transversal  
**Data:** 2026-08-14  
**Status:** IMP-295 concluido; IMP-296 nao iniciado e permanece sob novo `fable:fable-judge`.

---

## 1. Resultado

O IMP-295 materializou a jornada Cobranca em `/app/cobranca`, consumindo somente
as 4 operacoes oficiais do snapshot OpenAPI governado:

- consultar a fila de casos de cobranca da Carteira propria;
- registrar acao de cobranca;
- registrar promessa de pagamento;
- apropriar pagamento oficial a uma promessa.

O frontend apresenta caso, estado, total pendente e promessa como fatos
retornados pelo backend. Nao calcula saldo, cumprimento, inadimplencia,
apropriacao ou valor financeiro local.

---

## 2. RED -> GREEN

- **RED inicial observado:** `node scripts/tests/test-plan-025-contracts.js` =
  137/138.
- **Falha unica esperada:** `frontend/src/lib/bff/cobranca.server.ts ausente`.
- **GREEN observado:** suite Cobranca e contrato documental passam apos a
  implementacao minima.

O RED e evidencia temporal da sessao; depois do GREEN ele nao e reproduzivel sem
reverter arquivos.

---

## 3. Contrato tecnico entregue

- RBAC por igualdade exata:
  `cobranca.caso.ler`, `cobranca.acao.registrar`,
  `cobranca.promessa.registrar` e `cobranca.promessa.apropriar`.
- Carteira vem exclusivamente do contexto operacional corrente; o browser nao
  seleciona Tenant ou Carteira.
- `Idempotency-Key` e enviada somente onde o OpenAPI exige:
  - `POST /credit/cobrancas/casos/{cobranca_caso_id}/acoes`;
  - `POST /credit/cobrancas/casos/{cobranca_caso_id}/promessas`;
  - `POST /credit/cobrancas/promessas/{promessa_id}/apropriacoes`.
- `GET /credit/cobrancas/casos` permanece sem `Idempotency-Key`, porque o
  contrato publicado nao exige esse header.
- 400/401/403/404/409/5xx e resposta malformada sao estados seguros e
  correlacionados; 404 permanece neutro.
- O OpenAPI atual de Cobranca nao publica 422 nesses comandos; a UI registra a
  fronteira sem inventar status.
- Nenhum endpoint, componente ou fluxo de Agenda, Comunicacao, Relatorios,
  Configuracoes, Contratos, Motor ou pagamentos foi iniciado.

---

## 4. Evidencia visual

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `frontend-mvp-imp-295-cobranca-list-desktop.png` | 1440x900 | `d435ffc84ca096a44a117d57f75ffbbe54291d3c20f4be7bb8bd013d8f836b22` |
| `frontend-mvp-imp-295-cobranca-list-mobile.png` | 390x844 | `3b1767b2c1ba668bb02b2832917e74041e917663b075694c7a2f380156dc3065` |
| `frontend-mvp-imp-295-cobranca-action-desktop.png` | 1440x900 | `425480f1f36a51a487ff9f26dcdd6a722e4f062b05396d01fc44ee3b587050cd` |
| `frontend-mvp-imp-295-cobranca-promessa-mobile.png` | 390x844 | `1d25417b856c2f1a955352f333bda389b181b14722dd64337c94162fd1557ed7` |

---

## 5. Gates observados

- `npm --prefix frontend run lint` — verde.
- `npm --prefix frontend run typecheck` — verde.
- `npm --prefix frontend run build` — verde.
- `npm --prefix frontend run test:unit -- --run tests/unit/cobranca-policy.test.ts`
  — 3/3.
- `npm --prefix frontend run test:unit -- --run tests/unit/navigation-policy.test.ts`
  — 6/6.
- `npm --prefix frontend run test:component -- --run tests/component/cobranca.test.tsx`
  — 3/3.
- `npm --prefix frontend run test:bff -- --run tests/bff/cobranca.test.ts`
  — 5/5.
- `npm --prefix frontend run test:contract -- --run tests/contract/cobranca.test.ts`
  — 3/3, incluindo `api:check` e `typecheck`.
- `npm --prefix frontend run test:cobranca` — 8/8.

Gates documentais finais (`test-plan`, scope, docs validate/test e diff-check)
devem ser reobservados no judge focal.

---

## 6. Inventario e escopo

Baseline IMP-295: 259 caminhos.  
Mutaveis declarados: 12.  
Protegidos: 247.  
Novos declarados: 21.  
Inventario final esperado: 280 caminhos.

O predecessor encadeado e
`docs/audits/evidence/frontend-mvp-imp-294-protected-baseline.json` com SHA-256
`dbe12e07074d0743b503b12b2328a70842965891279d538b29d8f65f951dd745`.

Arquivos criados principais:

- `frontend/src/lib/bff/cobranca.server.ts`;
- `frontend/src/lib/cobranca/cobranca-policy.ts`;
- `frontend/src/components/cobranca/cobranca.tsx`;
- `frontend/src/components/cobranca/cobranca-command-dialog.client.tsx`;
- `frontend/src/app/app/cobranca/page.tsx`;
- `frontend/src/app/app/cobranca/actions.ts`;
- testes unit/component/BFF/contract/Playwright Cobranca;
- `scripts/tests/test-imp-295-scope.js`;
- este relatorio e as 4 evidencias visuais.

Arquivos protegidos nao alterados pelo IMP-295: backend Python, migrations,
testes Python, Product, Registry, snapshot OpenAPI, cliente OpenAPI gerado,
lockfiles, BFF de sessao e Motor/pagamentos.

---

## 7. Caveats nao bloqueantes

- CI remota Linux/Windows ainda nao foi observada sem commit/push.
- O RED inicial e temporal.
- Avisos EOL do Windows podem aparecer no `git diff --check`; nao sao alteracao
  de contrato.
- A toolchain exata permanece governada por `frontend/tests/toolchain-check.mjs`
  e CI, embora o shell local possa divergir.
- As Stories Product US-075..US-078 pedem historico, responsavel, periodo,
  paginacao e semanticas adicionais que nao existem no OpenAPI atual de
  Cobranca. O IMP-295 entrega apenas a fatia contratada pelos 4 endpoints
  certificados.

---

## 8. Decisao

O IMP-295 esta tecnicamente concluido no estado local observado. O IMP-296
continua bloqueado ate novo `$fable:fable-judge` focal.
