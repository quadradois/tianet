# IMP-289 - Shell autenticado e contexto operacional do Frontend MVP

**Data:** 2026-08-13

**Plano relacionado:** PLAN-025

**Status:** Concluido localmente; IMP-290 permanece bloqueado ate fable:fable-judge

---

# 1. Resultado

O IMP-289 materializou a primeira superficie autenticada do Frontend MVP sem
iniciar Dashboard ou outra jornada de negocio:

- `/login` envia somente e-mail e senha ao BFF same-origin; o BFF deriva o
  `identificador_institucional` server-only antes de chamar o backend com
  `AuthLoginRequest`;
- `/app` e um shell Server Component com Usuario, Tenant, Carteira e Perfil do
  proprio Principal;
- a fonte unica e `GET /iam/contexto-atual`, sem IDs arbitrarios e sem consulta
  ao catalogo administrativo;
- um 401 passa uma unica vez por `/session/recover` e pelo POST protegido
  `/api/auth/bootstrap`, fora do render que nao pode persistir cookies;
- 409 nao escolhe Carteira alternativa; 404 e neutro; falhas tecnicas mostram
  correlation ID seguro;
- a navegacao usa igualdade exata de Permissao e publica somente `/app`;
- tokens nao foram observados em HTML, storage, resposta publica ou chamadas
  diretas do browser ao backend;
- nenhum calculo financeiro foi criado.

O endpoint certificado de contexto publica apenas 200/401/409/500. Estados
403/404 permanecem apresentacoes genericas do shell e nao foram falsamente
atribuidos ao contrato de `GET /iam/contexto-atual`.

---

# 2. Evidencia RED -> GREEN

O contrato documental foi ampliado antes do comportamento. O RED observado foi
**90/91**: a unica falha foi
`frontend/src/lib/bff/context.server.ts ausente`. O gate historico do IMP-288
foi substituido por prova de encadeamento ao novo baseline, sem enfraquecer o
manifesto anterior.

Depois da implementacao, os resultados focais observados foram:

- unit: 3/3;
- component: 10/10;
- BFF: 59/59;
- contract: 4/4, com `api:check` e typecheck encadeados;
- Playwright sessao/contexto: 16/16 em desktop e mobile;
- contrato documental PLAN-025: 106/106, incluindo mutacoes negativas;
- scope IMP-289: 103 protegidos, inventario 150 e 0 divergencia;
- lint, typecheck e build Next 16.3.0 verdes;
- build com `/api/auth/bootstrap`, `/app`, `/login` e `/session/recover`.

O RED e evidencia temporal da sessao e nao e reproduzivel depois do GREEN sem
reverter deliberadamente a implementacao.

O primeiro ataque adversarial posterior ao GREEN encontrou REDs adicionais:
contexto com identidade divergente do JWE era aceito, status 4xx nao certificado
podia atravessar o BFF, recovery podia remontar sem teto e logout remoto 5xx
mantinha PII na tela apesar do cookie local limpo. Testes executaveis foram
adicionados antes das correcoes; o fechamento fail-closed vincula Usuario e
Tenant a sessao, aceita somente 401/409 e 500 sanitizado, limita recovery a uma
tentativa efemera e sempre remove o shell apos resposta do logout local.

---

# 3. Evidencias visuais

As capturas sao evidencia diagnostica, nao o baseline de regressao visual final
reservado ao IMP-302:

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| login desktop | 1440x900 | `ba82633897b26f1cbfd1abfa9f4341a5dfbceb5a10279ab59a20d61c1a1985b7` |
| login mobile | 1024x2216, surface em viewport 390x844 | `28e5f59d9f747fec3c4d3e662eaa3d4023df83124ea647577d3b6ba6e3911ece` |
| shell desktop | 1440x900 | `68a14423cb3a487dbdb86f1ba131d2f717080060dbf0e37fac974d82909c3013` |
| shell mobile | 1024x2216, surface em viewport 390x844 | `004de0e54e932e87a93bf8c32f76bc0f7be4ee0b8d0cc54ebeaaefe07fa50592` |

O runner usa device scale factor no projeto mobile, por isso o PNG fisico tem
1024x2216 embora a viewport CSS observada seja 390x844.

---

# 4. Escopo e cadeia de evidencia

- HEAD/base: `e48cb72ee4f62428491e8b8c19a569611d83fca8`;
- baseline anterior: 116 caminhos;
- predecessor IMP-288 SHA-256:
  `1280db56e1b029932712aab19c64dd2fb9d5a224be65f22ba542b6225052f85a`;
- 13 paths mutaveis exatos;
- 103 arquivos protegidos por hash;
- 34 paths novos exatos;
- inventario final esperado: 150 caminhos.

Durante `next dev`, o Next.js 16.3.0 gerou `frontend/AGENTS.md` e
`frontend/CLAUDE.md` e declarou que os reemitiria em cada execucao. Os dois
paths foram aceitos nominalmente no manifesto; nao houve allowlist de
diretorio.

Arquivos existentes alterados pelo IMP-289:

- `.github/workflows/quality.yml`;
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`;
- `docs/governance/frontend-mvp-traceability-matrix.md`;
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`;
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`;
- `frontend/README.md`;
- `frontend/package.json`;
- `frontend/src/app/layout.tsx`;
- `scripts/tests/test-plan-025-contracts.js`.

Arquivos novos:

- `docs/audits/evidence/frontend-mvp-imp-289-protected-baseline.json`;
- quatro PNGs `frontend-mvp-imp-289-{login,shell}-{desktop,mobile}.png`;
- este relatorio;
- `frontend/AGENTS.md` e `frontend/CLAUDE.md`, gerados pelo Next 16;
- `frontend/playwright.session.config.ts`;
- `frontend/src/app/api/auth/bootstrap/route.ts`;
- `frontend/src/app/app/{error,layout,loading,page}.tsx`;
- `frontend/src/app/foundation/page.tsx`;
- `frontend/src/app/login/page.tsx`;
- `frontend/src/app/not-found.tsx`;
- `frontend/src/app/session/recover/page.tsx`;
- `frontend/src/components/auth/{login-form.client,logout-button.client,session-recovery.client}.tsx`;
- `frontend/src/components/shell/{app-shell,context-summary,navigation}.tsx`;
- `frontend/src/lib/bff/context.server.ts`;
- `frontend/src/lib/shell/navigation-policy.ts`;
- `frontend/tests/bff/context.test.ts`;
- `frontend/tests/component/session-shell.test.tsx`;
- `frontend/tests/contract/session-shell.test.ts`;
- `frontend/tests/session-e2e/{backend-fixture.mjs,session-shell-a11y.spec.ts,session-shell.spec.ts}`;
- `frontend/tests/unit/navigation-policy.test.ts`;
- `scripts/tests/test-imp-289-scope.js`.

Nao foram alterados backend Python, migrations, testes Python, Product,
Registry, snapshot/gerado OpenAPI, BFF/session certificados do IMP-288,
dependencias ou lockfiles.

---

# 5. Recertificacao observada

- Node.js 24.19.0 e npm 11.17.0 governados;
- `api:check`, lint, typecheck e build verdes;
- unit 3/3, component 10/10, BFF 59/59 e contract 4/4;
- Playwright foundation 12/12 e sessao/contexto 16/16;
- smoke real FastAPI/PostgreSQL e cleanup verdes;
- backend: 951 testes coletados, `pytest -q`, Ruff, Black e mypy verdes;
- migrations: ciclo destrutivo verde em PostgreSQL 16 descartavel dedicado,
  seguido de remocao do container;
- docs:validate: 320 verificacoes OK, 29 avisos historicos e 0 erros;
- docs:test e `git diff --check` verdes;
- OpenAPI preservado em 107 operacoes, 133 schemas e SHA-256
  `8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1`.

---

# 6. Caveats e proxima decisao

- CI remota Linux/Windows nao foi observada porque nao houve commit/push;
- single-flight e logout-wins continuam limitados a processo/isolate Next;
- 401 atrasado permanece caveat nao bloqueante herdado do IMP-288;
- o marcador HttpOnly de recovery expira em 60 segundos e nao e limpo por
  login/logout; nesse intervalo uma nova sessao pode falhar fechada direto no
  login em vez de tentar novo recovery, sem vazamento ou elevacao de acesso;
- identidade visual final e regressao visual cross-platform continuam nos
  gates posteriores;
- a fixture E2E e um backend HTTP real e deterministico para os contratos auth
  e contexto; a recertificacao completa FastAPI/PostgreSQL continua nos gates
  finais do PLAN.

**Decisao:** IMP-290 permanece bloqueado. Executar `fable:fable-judge` focal
sobre este pacote antes de autorizar Dashboard ou qualquer jornada de negocio.
