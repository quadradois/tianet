# Relatorio de execucao - IMP-286 Design Foundation do Frontend MVP

**Data:** 2026-08-13

**Plano relacionado:** PLAN-025

**Status:** IMP-286 concluido; IMP-287 nao iniciado e sob gate adversarial

---

# 1. Resultado

O IMP-286 materializou exclusivamente uma foundation funcional neutra no
workspace `frontend/`: tokens semanticos claro/escuro, primitives locais
compatíveis com shadcn/ui, estados acessiveis, specimen tecnico server-first e
evidencias component/browser em desktop e mobile. Nenhuma tela ou jornada de
negocio, cliente OpenAPI, BFF, sessao, decisao RBAC ou calculo financeiro foi
criado.

A identidade de marca final continua pendente de aprovacao Product/Design. O
specimen `/` e temporario e nao representa uma jornada do MVP.

---

# 2. Evidencia temporal RED para GREEN

Antes da primeira instalacao, o contrato documental foi ampliado e executado:

- RED: 37 de 38 casos passaram;
- falha unica observada: `frontend/components.json ausente`;
- causa esperada: a foundation ainda nao existia;
- nenhum teste anterior foi removido ou relaxado para obter GREEN.

O estado final e as mutacoes negativas sao registrados pelos gates desta
sessao: 53 de 53 casos passam. O contrato rejeita remocao de token, foco ou reduced motion; cor
hardcoded; categoria com zero testes; axe ausente; viewport mobile ausente;
boolean soup; dependencia futura; conclusao indevida do IMP-287; allowlist
ampla e path backend no manifesto.

---

# 3. Stack e decisoes observadas

Dependencias runtime exatas:

- `@radix-ui/react-dialog` 1.1.23;
- `@radix-ui/react-slot` 1.3.3;
- `class-variance-authority` 0.7.1;
- `clsx` 2.1.1;
- `tailwind-merge` 3.6.0.

Dependencias de desenvolvimento exatas:

- `tailwindcss` 4.3.3;
- `@tailwindcss/postcss` 4.3.3;
- `postcss` 8.5.26;
- `@axe-core/playwright` 4.13.0.

O shadcn CLI 4.17.0 foi referencia oficial de materializacao e nao foi
persistido como dependencia. `components.json` fixa `new-york`, RSC, TSX,
CSS variables e base neutra. Os componentes pertencem ao repositorio. A pagina
e o showcase permanecem Server Components; somente a primitive Dialog e sua
demonstracao destrutiva possuem `use client`.

---

# 4. Foundation entregue

Os temas claro e escuro cobrem surfaces, texto, borda/input/ring, primary,
destructive, success, warning, information, tipografia, espaco, dimensao, raio,
elevacao, foco e motion. O CSS tambem cobre `forced-colors`,
`prefers-reduced-motion`, foco visivel, touch e overflow.

As primitives locais sao Button, Card, Alert, Input, Label, Skeleton e Dialog.
Os estados explicitos sao loading, empty, error, success, sem Permissao e 404
neutro, alem de pending/disabled e regiao de overflow acessivel. A foundation
somente apresenta decisoes recebidas; ela nao calcula autorizacao nem recebe
dado sensivel bruto.

---

# 5. Evidencia funcional, acessivel e visual

Os gates observam:

- component tests com queries por role/name, user-event e jest-dom;
- AxeBuilder no Chromium em claro/escuro e nos viewports 1440x900 e 390x844;
- teclado, skip link, foco inicial e retorno de foco do Dialog;
- foco visivel, reduced motion, ausencia de overflow global e regiao larga
  navegavel;
- console da aplicacao sem erro;
- screenshots tecnicos desktop/mobile anexados como evidencia governada.

Resultados focais observados: unit 1/1, component 7/7, contrato OpenAPI 1/1,
axe 4/4, captura visual 2/2 e Playwright completo 12/12. Lint, typecheck e build
Next.js 16.3.0 tambem passaram; `npm audit` observou 0 vulnerabilidades.

Os screenshots sao diagnosticos deterministas deste specimen, nao a regressao
visual final das jornadas, que permanece no IMP-302:

- `docs/audits/evidence/frontend-mvp-imp-286-foundation-desktop.png`;
- `docs/audits/evidence/frontend-mvp-imp-286-foundation-mobile.png`.

SHA-256 observados das capturas finais:

- desktop: `1c830b1f19c316fa326047d5b328a9a172581175eb07003647415bfe52c0775d`;
- mobile: `edd3bbed6288e84dc69d01a7b13d070070627730ad78728fbb0992867f4528a8`.

---

# 6. Evidencia de escopo

O manifesto `frontend-mvp-imp-286-protected-baseline.json` foi capturado antes
da implementacao com 74 paths da worktree, 14 paths mutaveis e 23 novos paths
exatos. Ele encadeia o manifesto IMP-285 pelo SHA-256
`aad63efd04a284ef2417a49a1b13bbd02acaab6bd5cba0b208c1e3299ef660a2`.

O gate corrente verifica o predecessor, recalcula os hashes protegidos, rejeita
diretorios em allowlists, bloqueia backend/migrations/testes Python/Product/
Registry/OpenAPI e compara o inventario completo de `git status -uall`. Os
relatorios e manifestos dos IMP-284/285 permaneceram historicos e imutaveis.

Na primeira autoexecucao do gate, um digest de `iam_catalogo.py` no manifesto
novo tinha 63 caracteres por erro de transcricao. A entrada foi corrigida para
o SHA-256 de 64 caracteres observado no arquivo protegido e inalterado; paths,
predecessor e demais hashes permaneceram iguais. O gate passou depois dessa
correcao fail-closed.

---

# 7. Arquivos do IMP-286

Alterados:

- `.github/workflows/quality.yml`;
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`;
- `docs/governance/frontend-mvp-traceability-matrix.md`;
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`;
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`;
- `frontend/.gitignore` e `frontend/README.md`;
- `frontend/package.json` e `frontend/package-lock.json`;
- `frontend/playwright.config.ts`;
- `frontend/src/app/globals.css`, `layout.tsx` e `page.tsx`;
- `scripts/tests/test-plan-025-contracts.js`.

Criados:

- `docs/audits/evidence/frontend-mvp-imp-286-protected-baseline.json`;
- os dois PNGs de evidencia desktop/mobile;
- este relatorio;
- `frontend/components.json` e `frontend/postcss.config.mjs`;
- `frontend/src/app/icon.svg` e `frontend/src/lib/utils.ts`;
- `frontend/src/components/ui/alert.tsx`, `button.tsx`, `card.tsx`,
  `dialog.tsx`, `input.tsx`, `label.tsx` e `skeleton.tsx`;
- `frontend/src/components/foundation/destructive-dialog-demo.tsx`,
  `feedback-state.tsx`, `foundation-showcase.tsx` e `overflow-region.tsx`;
- `frontend/tests/component/foundation.test.tsx`;
- `frontend/tests/e2e/foundation.spec.ts` e
  `frontend/tests/e2e/foundation-a11y.spec.ts`;
- `scripts/tests/test-imp-286-scope.js`.

---

# 8. Fronteiras, caveats e decisao do proximo IMP

Gates finais observados nesta sessao:

- `uv run pytest -q`: 100% verde;
- Ruff: todos os checks passaram;
- Black: 249 arquivos inalterados;
- mypy: 230 arquivos sem issues;
- `docs:validate`: 317 OK, 29 avisos historicos e 0 erros;
- `docs:test`: verde;
- contrato PLAN-025: 53/53;
- escopo IMP-286: predecessor verificado, 60 arquivos protegidos, inventario
  completo de 97 paths e 0 divergencia;
- migrations descartaveis: upgrade head, downgrade base e novo upgrade head
  verdes em PostgreSQL 16, sem container residual;
- `git diff --check`: verde;
- `HEAD`, `master` e `origin/master`: `e48cb72ee4f62428491e8b8c19a569611d83fca8`.

Fronteiras e caveats:

- identidade visual final ainda requer aprovacao Product/Design;
- a CI Linux/Windows esta configurada, mas a execucao remota nao foi observada
  porque nao houve commit ou push;
- as tags `actions/*@v4` continuam mutaveis, caveat de supply chain ja conhecido;
- a evidencia RED depende do transcript temporal desta sessao; ela nao e um
  estado externo assinado nem reproduzivel depois da materializacao GREEN;
- o contraste do focus ring nao e medido isoladamente pelo E2E; a verificacao
  visual completa desse criterio continua no IMP-302;
- os 29 avisos documentais existentes antes do IMP-286 nao devem aumentar;
- cliente OpenAPI, tipos de dominio, BFF, sessao e jornadas continuam ausentes;
- o OpenAPI permanece em 107 operacoes, 133 schemas e SHA-256
  `8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1`.

**Decisao:** o IMP-287 continua Planejado e nao esta autorizado nesta sessao.
Antes de gerar o cliente OpenAPI, executar `fable:fable-judge` focal sobre o
pacote completo do IMP-286.

---

# 9. Ataque adversarial interno

Tres atacantes independentes nao encontraram P1 nem defeito funcional. Eles
reexecutaram component, contract, axe, Playwright, escopo, contratos e docs;
tambem confirmaram OpenAPI 107/133/hash preservado, lockfile integro, audit 0,
server-first e ausencia de cliente/BFF/auth/calculo.

Os P2 acionaveis foram fechados no mesmo ciclo:

- o E2E passou a provar alcance do trigger por Tab real, containment com
  Tab/Shift+Tab, overflow efetivo e ArrowRight no mobile, e animationDuration
  do Dialog sob reduced motion;
- o contrato documental passou a verificar assinatura, largura, altura minima,
  SHA-256 real e SHA publicado das duas PNGs.

Permanecem somente os caveats explicitados acima: CI remota nao observada,
Actions `@v4` mutaveis, RED temporal dependente do transcript e contraste
isolado do focus ring reservado ao IMP-302. O veredito interno final e
`VERIFIED WITH CAVEATS`, sem bloqueio P1; o judge focal externo continua sendo
o gate formal para autorizar o IMP-287.

---

# 10. Correcao apos judge focal externo

O judge focal externo emitiu `REFUTED` porque o gate Playwright nao reproduziu
12/12: a execucao normal terminou 11/12 e uma repeticao de cinco ciclos por
viewport terminou 28/30. A falha ocorria quando o teste fechava o Dialog e
tentava focar imediatamente a regiao de overflow; a restauracao assincrona de
foco do Radix podia recuperar o trigger depois e retirar o foco da regiao.

A correcao foi estritamente focal:

- depois de `Escape`, o teste aguarda o Dialog ficar oculto e o trigger
  recuperar o foco antes de mover o foco para o overflow;
- os specs foundation e axe agora falham por `console.error` e `pageerror` em
  cada pagina, sem alterar o spec historico protegido do IMP-285;
- o script de lint ignora explicitamente `playwright-report`, `test-results`,
  `coverage` e `blob-report`, para permanecer verde mesmo depois da geracao de
  artifacts;
- o contrato documental ganhou mutacoes que rejeitam a remocao dos observers
  e dos ignores de lint, elevando o estado final para 53/53.

Evidencias posteriores a correcao:

- caso anteriormente instavel: 20/20 em dez repeticoes por viewport;
- Playwright completo: 12/12;
- lint posterior ao Playwright: verde;
- typecheck e build: verdes;
- contrato PLAN-025: 53/53;
- escopo IMP-286: 60 protegidos, inventario exato e 0 divergencia.

O IMP-287 permanece Planejado. Esta correcao precisa de novo
`fable:fable-judge` focal antes de sua autorizacao.
