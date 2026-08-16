# Relatorio de execucao — IMP-290 Dashboard operacional

**Data:** 2026-08-13/14  
**Plano relacionado:** PLAN-025  
**Status:** Concluido tecnicamente; IMP-291 bloqueado ate novo fable-judge

## 1. Resultado

O IMP-290 materializou exclusivamente `/app` como Dashboard operacional
server-first e read-only. Resumo, vencimentos, agenda e fila de cobranca usam
os quatro GETs certificados, a Carteira padrao do contexto US-125 e igualdade
exata de Permissao. O frontend nao soma, reclassifica ou calcula valor
financeiro.

O IMP-290 nao cria `/dashboard`, Route Handler, dependencia, tipo de dominio
manual, comando, link futuro ou cliente browser-backend. IMP-291 permanece
planejado.

## 2. Evidencia temporal RED → GREEN

- RED documental observado: **106/107**; a unica falha foi
  `frontend/src/components/dashboard/dashboard.tsx ausente`.
- INTENT observado antes do codigo: substituir o placeholder autenticado de
  `/app` pelo Dashboard P0 read-only, preservando backend, Product, Registry,
  OpenAPI, lockfile e IMP-291.
- GREEN focal final: **126/126** contratos documentais, incluindo mutacoes
  negativas do IMP-290.
- A evidencia RED e temporal e nao pode ser reexecutada no estado GREEN sem
  reverter deliberadamente o pacote.
- RED adversarial posterior: unit **7/8** e BFF **63/65**, expondo offset
  historico fixo, 403 sem correlation, sucesso 2xx amplo e schema 200
  incompleto. O GREEN posterior fechou esses quatro motivos.
- Um segundo ataque provou que `Date.parse` normalizava 30 de fevereiro. O
  validator agora verifica calendario e componentes RFC3339 sem normalizacao,
  com negativos independentes para os quatro campos date-time consumidos.

## 3. Decisoes observadas

1. `/app` e a unica rota do Dashboard.
2. Relatorios exigem `relatorios.operacionais.ler`; agenda, `agenda.ler`; fila,
   `cobranca.caso.ler`. Sem permissao, a secao nao chama o backend.
3. `tenant_id` e `carteira_id` do browser nao selecionam escopo; a Carteira vem
   somente do contexto corrente, e identidades divergentes falham como 502.
4. A URL canonica usa `data_referencia=YYYY-MM-DD`. Sem parametro, o servidor
   escolhe a data civil de `America/Sao_Paulo`; a agenda usa os limites civis
   inclusivos e o offset IANA vigente na data selecionada. Esta e uma politica
   MVP de apresentacao, nao regra financeira.
5. As quatro leituras iniciam concorrentemente e falham de forma independente.
   400/401/403/404/500, timeout e resposta malformada sao seguros e
   correlacionados; 409/422 nao sao inventados para estes GETs.
6. O Dashboard e preview contratual; nao declara US-079/084/085 completas nem
   substitui os IMP-295/296/297.
7. A composicao visual `/app` pertence ao PLAN-025 e nao altera o escopo
   Product de FEATURE-031. A matriz separa os relatorios da Feature da
   composicao tecnica P0 sobre resultados read-only de FEATURE-028/029/031;
   nenhum novo agregado, Feature ou Story foi materializado.

## 4. Suites e gates observados

- Node 24.19.0 / npm 11.17.0: observados.
- unit: **8/8**.
- component: **15/15**.
- BFF: **65/65**.
- contract: **7/7**, incluindo `api:check` e typecheck.
- Dashboard Playwright: **12/12** em Chromium, desktop e mobile.
- foundation Playwright: **12/12**; sessao/shell Playwright: **16/16**.
- infraestrutura real: PostgreSQL 16 descartavel e FastAPI `/health` prontos,
  isolados e encerrados ao final.
- lint: verde.
- build: verde; nenhuma rota futura foi criada.
- backend: **951 testes** coletados e verdes; Ruff, Black e mypy verdes.
- migrations: ciclo destrutivo `upgrade head -> downgrade base -> upgrade head`
  verde em PostgreSQL 16 descartavel, removido ao final.
- docs:validate: **321 verificacoes OK, 29 avisos historicos e 0 erros**;
  docs:test verde; `git diff --check` verde.
- escopo: **135 arquivos protegidos**, inventario exato de **169 paths** e
  **0 divergencia**.
- OpenAPI preservado em **107 operacoes / 133 schemas**, SHA-256
  `8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1`.
- CI Linux/Windows: configurada, mas a execucao remota nao foi observada sem
  commit/push.

## 5. Auditoria visual e de experiencia

Capturas reais do build de producao, sem indicador de dev:

| Evidencia | Dimensoes | SHA-256 |
|---|---:|---|
| Dashboard loaded desktop | 1440x900 | `2f39876d383747981c0cf7ed4161b90f9512682992e0a15e1ef9a7bcaef63080` |
| Dashboard loaded mobile | 390x844 | `9da95ae2e7c8b1631223fd0318f4075faaca106cec90286129e778af0a279f26` |
| Estados desktop (dark) | 1440x900 | `dbbd1fed2fd76e41259b513b56428772d54483599cf25a4f10fc08d658a2e52d` |
| Estados mobile (dark) | 390x844 | `86d061ba1ef863bbc6293009ded0debfd37124dd01216a28ddd4577af7026f59` |

O fluxo suporta o objetivo do operador: contexto Tenant/Carteira visivel,
seletor temporal canonico, hierarquia das quatro secoes e falha parcial sem
derrubar o restante. Axe, teclado, foco, responsive, dark mode, empty, error,
denied e overflow foram observados. A densidade de metricas e tabela foi
ajustada apos inspecao visual; datas usam `Intl` e valores oficiais preservam a
representacao retornada.

A auditoria de produto nao encontrou bloqueio visual para esta fatia. A
hierarquia e a composicao parcial ficaram legiveis nos dois viewports; no
mobile, as secoes refluem sem overflow global e a tabela permanece contida em
regiao nomeada. Permanecem como riscos deliberados, e nao como falso verde:
rolagem vertical longa em payloads extensos, ausencia de paginacao contratual e
timezone fixo enquanto o contexto nao publicar timezone por Tenant.

## 6. Fronteiras e dividas conhecidas

- nenhuma regra financeira foi implementada no frontend;
- agenda, vencimentos e fila nao sao paginados no contrato corrente; overflow
  visual nao resolve o risco de payload/escala;
- US-084 fala em periodo, mas resumo usa `data_referencia`; US-085 e US-079
  possuem filtros/campos/paginacao ainda ausentes no contrato;
- o timezone por Tenant ainda nao existe no contexto; `America/Sao_Paulo` e a
  politica explicita e revisavel desta fase, com transicoes historicas
  derivadas da base IANA;
- a selecao temporal desta fase aceita `1970-01-01` ate `9998-12-31`; valores
  fora da faixa viram periodo invalido, sem excecao server-side;
- caveats herdados de sessao permanecem: single-flight/logout-wins por
  processo/isolate e 401 atrasado nao bloqueante;
- um 401 isolado em uma secao, se o contexto continuar 200, faz uma unica
  tentativa de bootstrap e retorna ao login; o frontend falha fechado e nao
  promete recuperacao transparente para essa divergencia backend;
- Actions `@v4` permanecem tags mutaveis e a CI remota nao foi observada.

## 7. Escopo temporal

- baseline: 150 paths;
- mutaveis exatos: 15;
- protegidos: 135;
- novos exatos: 19;
- inventario final esperado/observado: 169;
- predecessor IMP-289:
  `25e40b40d8ffe4a697df77a5912c0b67f45cd71b8af10dfb84d5f51fb02950fa`.

### Arquivos existentes alterados

1. `.github/workflows/quality.yml`
2. `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`
3. `docs/governance/frontend-mvp-traceability-matrix.md`
4. `docs/implementation/backlogs/PLAN-025-execution-backlog.md`
5. `docs/implementation/plans/PLAN-025-frontend-mvp.md`
6. `frontend/README.md`
7. `frontend/package.json`
8. `frontend/src/app/app/layout.tsx`
9. `frontend/src/app/app/page.tsx`
10. `frontend/src/lib/shell/navigation-policy.ts`
11. `frontend/tests/component/session-shell.test.tsx`
12. `frontend/tests/session-e2e/session-shell.spec.ts`
13. `frontend/tests/session-e2e/session-shell-a11y.spec.ts`
14. `frontend/tests/unit/navigation-policy.test.ts`
15. `scripts/tests/test-plan-025-contracts.js`

### Arquivos criados

1. `docs/audits/evidence/frontend-mvp-imp-290-dashboard-desktop.png`
2. `docs/audits/evidence/frontend-mvp-imp-290-dashboard-mobile.png`
3. `docs/audits/evidence/frontend-mvp-imp-290-dashboard-states-desktop.png`
4. `docs/audits/evidence/frontend-mvp-imp-290-dashboard-states-mobile.png`
5. `docs/audits/evidence/frontend-mvp-imp-290-protected-baseline.json`
6. `docs/audits/reports/frontend-mvp-imp-290-dashboard-report-2026-08-13.md`
7. `frontend/playwright.dashboard.config.ts`
8. `frontend/src/components/dashboard/dashboard.tsx`
9. `frontend/src/lib/bff/current-context.server.ts`
10. `frontend/src/lib/bff/dashboard.server.ts`
11. `frontend/src/lib/dashboard/dashboard-policy.ts`
12. `frontend/tests/unit/dashboard-policy.test.ts`
13. `frontend/tests/component/dashboard.test.tsx`
14. `frontend/tests/bff/dashboard.test.ts`
15. `frontend/tests/contract/dashboard.test.ts`
16. `frontend/tests/dashboard-e2e/backend-fixture.mjs`
17. `frontend/tests/dashboard-e2e/dashboard-a11y.spec.ts`
18. `frontend/tests/dashboard-e2e/dashboard.spec.ts`
19. `scripts/tests/test-imp-290-scope.js`

Nenhum Product, Registry, backend Python, migration, teste Python, snapshot,
cliente gerado, dependencia ou lockfile foi alterado pelo IMP-290.

## 8. Decisao de continuidade

O IMP-290 esta tecnicamente concluido, mas **o IMP-291 continua bloqueado**.
Executar `$fable:fable-judge` focal sobre este pacote antes de autorizar
Devedores.
