# Frontend MVP - IMP-296 Agenda/Comunicacao

**Data:** 2026-08-14

**Status:** IMP-296 concluido; IMP-297 nao iniciado e sob gate adversarial

**Plano relacionado:** PLAN-025 Frontend MVP

---

## 1. Resultado

O IMP-296 materializa `/app/agenda` como superficie autenticada server-first
para Agenda e Comunicacao, consumindo somente contratos OpenAPI oficiais,
Carteira propria do contexto operacional e permissoes RBAC por igualdade exata.

Foram cobertas as 12 operacoes oficiais de Agenda/Comunicacao:

- `GET /credit/agenda`;
- `GET /credit/comunicacoes`;
- 10 comandos `POST` certificados com `Idempotency-Key` obrigatorio.

O frontend nao cria Relatorios, Configuracoes, IAM, Automacao, template de
notificacao, regra financeira, rota backend nova, calculo local ou permissao por
prefixo.

---

## 2. Evidencia RED -> GREEN

| Momento | Comando | Resultado |
|---|---|---|
| RED temporal | `node scripts/tests/test-plan-025-contracts.js` | 144/145; falha unica esperada: `frontend/src/lib/bff/agenda-comunicacao.server.ts ausente` |
| GREEN funcional | `npm --prefix frontend run test:unit -- --run tests/unit/agenda-policy.test.ts tests/unit/navigation-policy.test.ts` | 10/10 |
| GREEN componente | `npm --prefix frontend run test:component -- --run tests/component/agenda-comunicacao.test.tsx` | 3/3 |
| GREEN BFF | `npm --prefix frontend run test:bff -- --run tests/bff/agenda-comunicacao.test.ts` | 8/8 |
| GREEN contrato | `npm --prefix frontend run test:contract -- --run tests/contract/agenda-comunicacao.test.ts` | 3/3, com `api:check` e `typecheck` |
| GREEN browser | `npm --prefix frontend run test:agenda` | 8/8 |
| GREEN documental esperado | `node scripts/tests/test-plan-025-contracts.js` | 152/152 apos mutacoes negativas do IMP-296 |

As mutacoes negativas do IMP-296 rejeitam remover `Idempotency-Key` de comando,
inventar `Idempotency-Key` nas consultas, usar permissao por prefixo, calcular
valor financeiro local, antecipar Relatorios, ampliar allowlist para diretorio e
concluir o IMP-297.

---

## 3. Evidencia visual

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `docs/audits/evidence/frontend-mvp-imp-296-agenda-list-desktop.png` | 1440x900 | `3166a3febfea1bf4a911420f3201ccd1a220298ea910401ee7f9b8dafc28eb43` |
| `docs/audits/evidence/frontend-mvp-imp-296-agenda-list-mobile.png` | 390x844 | `7f9b047b25cda04ca482099e61a3dc6f49ea8c563efecac407dfbb3d1058a37c` |
| `docs/audits/evidence/frontend-mvp-imp-296-agenda-command-desktop.png` | 1440x900 | `b93062bd10a3f9e5e86f7785efc167b6f8994b12a4d75568a58ebdc3cfe961da` |
| `docs/audits/evidence/frontend-mvp-imp-296-comunicacao-flow-mobile.png` | 390x844 | `3318465b6ccc52d069e213e638c10c3b46468cffe0a1ed77c0753b319a8d404c` |

---

## 4. Escopo e inventario

Manifesto encadeado:

- baseline anterior: 280 caminhos;
- caminhos mutaveis autorizados: 10;
- caminhos protegidos: 270;
- caminhos novos do IMP-296: 21;
- inventario final esperado: 301 caminhos;
- predecessor: `docs/audits/evidence/frontend-mvp-imp-295-protected-baseline.json`;
- SHA-256 do predecessor: `e8540e9f3a072e5d6c0f4dcb4d1f2700087b3475c331edacdf5f4f1a7016a7d1`.

Arquivos principais criados:

- `frontend/src/app/app/agenda/page.tsx`;
- `frontend/src/app/app/agenda/actions.ts`;
- `frontend/src/lib/bff/agenda-comunicacao.server.ts`;
- `frontend/src/lib/agenda/agenda-policy.ts`;
- `frontend/src/components/agenda/agenda-comunicacao.tsx`;
- `frontend/src/components/agenda/agenda-command-dialog.client.tsx`;
- `frontend/tests/unit/agenda-policy.test.ts`;
- `frontend/tests/component/agenda-comunicacao.test.tsx`;
- `frontend/tests/bff/agenda-comunicacao.test.ts`;
- `frontend/tests/contract/agenda-comunicacao.test.ts`;
- `frontend/tests/agenda-e2e/agenda-comunicacao.spec.ts`;
- `frontend/tests/agenda-e2e/agenda-comunicacao-a11y.spec.ts`;
- `frontend/tests/agenda-e2e/backend-fixture.mjs`;
- `frontend/playwright.agenda.config.ts`;
- `scripts/tests/test-imp-296-scope.js`;
- `docs/audits/evidence/frontend-mvp-imp-296-protected-baseline.json`.

Arquivos existentes alterados no escopo do IMP-296:

- `.github/workflows/quality.yml`;
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`;
- `docs/governance/frontend-mvp-traceability-matrix.md`;
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`;
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`;
- `frontend/README.md`;
- `frontend/package.json`;
- `frontend/src/lib/shell/navigation-policy.ts`;
- `frontend/tests/unit/navigation-policy.test.ts`;
- `scripts/tests/test-plan-025-contracts.js`.

---

## 5. Caveats nao bloqueantes

- O RED 144/145 e evidencia temporal da sessao e nao e reproduzivel sem
  reverter os arquivos criados.
- A CI remota Linux/Windows ainda nao foi observada porque nao houve commit,
  push ou PR.
- O OpenAPI atual nao publica paginacao de comunicacoes, prioridade,
  responsavel nem `data_referencia` de Agenda. A interface declara a fronteira
  e nao inventa esses campos.
- O alias `POST /credit/agenda/lembretes/{lembrete_id}/enviar` permanece como
  conciliacao legada governada pela permissao `notificacao.conciliar`; nao foi
  criado disparo arbitrario de notificacao.

---

## 6. Decisao sobre IMP-297

O IMP-297 permanece **Planejado** e nao foi iniciado. A autorizacao para
Relatorios deve depender de novo `$fable:fable-judge` focal sobre este pacote
IMP-296.
