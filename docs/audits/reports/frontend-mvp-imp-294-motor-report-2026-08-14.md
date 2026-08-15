# Relatorio focal — IMP-294 Motor e pagamentos

**Plano relacionado:** PLAN-025 — Frontend MVP Transversal  
**Data:** 2026-08-14  
**Status:** IMP-294 concluido; IMP-295 nao iniciado e permanece sob novo `fable:fable-judge`.

---

## 1. Resultado

O IMP-294 materializou a jornada Motor/pagamentos em `/app/motor`, consumindo
somente as 11 operacoes oficiais do snapshot OpenAPI governado:

- criar Emprestimo a partir de Contrato liberado;
- listar e consultar Emprestimos da Carteira propria;
- gerar/consultar parcelas;
- registrar pagamento;
- consultar saldo, memoria de calculo e quitacao;
- executar quitacao;
- registrar renegociacao opaca.

O frontend apresenta valores, parametros e memoria retornados pelo backend sem
formula local, soma, arredondamento, reclassificacao ou formatacao financeira
autoritativa.

---

## 2. RED -> GREEN

- **RED inicial observado:** `node scripts/tests/test-plan-025-contracts.js` =
  136/137.
- **Falha unica esperada:** `frontend/src/lib/bff/motor.server.ts ausente`.
- **GREEN observado:** suite Motor e contrato documental passam apos a
  implementacao minima.

O RED e evidencia temporal da sessao; depois do GREEN ele nao e reproduzivel sem
reverter arquivos.

---

## 3. Contrato tecnico entregue

- RBAC por igualdade exata:
  `motor.emprestimo.criar`, `motor.emprestimo.ler`, `motor.parcela.gerar`,
  `motor.parcela.ler`, `motor.pagamento.registrar`, `motor.saldo.ler`,
  `motor.memoria.ler`, `motor.quitacao.executar` e
  `motor.renegociacao.criar`.
- Carteira vem exclusivamente do contexto operacional corrente; o browser nao
  seleciona Tenant ou Carteira.
- `Idempotency-Key` e enviada somente onde o OpenAPI exige:
  - `POST /credit/contratos/{contrato_id}/emprestimos`;
  - `POST /credit/emprestimos/{emprestimo_id}/pagamentos`;
  - `POST /credit/emprestimos/{emprestimo_id}/quitacao`;
  - `POST /credit/emprestimos/{emprestimo_id}/renegociacoes`.
- `POST /credit/emprestimos/{emprestimo_id}/parcelas` permanece sem
  `Idempotency-Key`, porque o contrato publicado nao exige esse header.
- 400/401/403/404/409/422/5xx e resposta malformada sao estados seguros e
  correlacionados; 404 permanece neutro.
- Nenhum endpoint, componente ou fluxo de Cobranca/Agenda/Relatorios/Configuracoes
  foi iniciado.

---

## 4. Evidencia visual

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `frontend-mvp-imp-294-motor-list-desktop.png` | 1440x900 | `b172f7f17a3160830412e8d7f7971aefcbf6c8ecc42234144561af6476e0bcf8` |
| `frontend-mvp-imp-294-motor-list-mobile.png` | 390x844 | `0d053a899cfbeeb8ae51049d6d292ef7c21d1fd5dadfb43792ab52846be326bf` |
| `frontend-mvp-imp-294-emprestimo-detail-desktop.png` | 1440x900 | `bac442ac94fa6f6dcb70dde988c1eef7178d97397d256b75dcf52dcab788c6cf` |
| `frontend-mvp-imp-294-pagamento-flow-mobile.png` | 390x844 | `52a3f492c8191b43a48c05088c8929371becc3d4bdf28dea88c5a2fbcaa3db25` |

---

## 5. Gates observados

- `npm --prefix frontend run lint` — verde.
- `npm --prefix frontend run typecheck` — verde.
- `npm --prefix frontend run build` — verde.
- `npm --prefix frontend run test:unit -- --run tests/unit/motor-policy.test.ts`
  — 5/5.
- `npm --prefix frontend run test:component -- --run tests/component/motor.test.tsx`
  — 4/4.
- `npm --prefix frontend run test:bff -- --run tests/bff/motor.test.ts` — 6/6.
- `npm --prefix frontend run test:contract -- --run tests/contract/motor.test.ts`
  — 3/3, incluindo `api:check` e `typecheck`.
- `npm --prefix frontend run test:motor` — 8/8.

Gates documentais finais (`test-plan`, scope, docs validate/test e diff-check)
devem ser reobservados no judge focal.

---

## 6. Inventario e escopo

Baseline IMP-294: 237 caminhos.  
Mutaveis declarados: 11.  
Protegidos: 226.  
Novos declarados: 22.  
Inventario final esperado: 259 caminhos.

O predecessor encadeado e
`docs/audits/evidence/frontend-mvp-imp-293-protected-baseline.json` com SHA-256
`702c0decb21c8339216b053da9588a701e375fd766ec73428e8ef37044634202`.

Arquivos criados principais:

- `frontend/src/lib/bff/motor.server.ts`;
- `frontend/src/lib/motor/motor-policy.ts`;
- `frontend/src/components/motor/motor.tsx`;
- `frontend/src/components/motor/motor-command-dialog.client.tsx`;
- `frontend/src/app/app/motor/page.tsx`;
- `frontend/src/app/app/motor/[emprestimoId]/page.tsx`;
- `frontend/src/app/app/motor/actions.ts`;
- testes unit/component/BFF/contract/Playwright Motor;
- `scripts/tests/test-imp-294-scope.js`;
- este relatorio e as 4 evidencias visuais.

Arquivos protegidos nao alterados pelo IMP-294: backend Python, migrations,
testes Python, Product, Registry, snapshot OpenAPI, cliente OpenAPI gerado,
lockfiles e BFF de sessao.

---

## 7. Caveats nao bloqueantes

- CI remota Linux/Windows ainda nao foi observada sem commit/push.
- O RED inicial e temporal.
- Avisos EOL do Windows podem aparecer no `git diff --check`; nao sao alteracao
  de contrato.
- A toolchain exata permanece governada por `frontend/tests/toolchain-check.mjs`
  e CI, embora o shell local possa divergir.

---

## 8. Decisao

O IMP-294 esta tecnicamente concluido no estado local observado. O IMP-295
continua bloqueado ate novo `$fable:fable-judge` focal.
