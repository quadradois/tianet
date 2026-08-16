# Relatorio de execucao - IMP-287 Cliente OpenAPI do Frontend MVP

**Data:** 2026-08-13

**Plano relacionado:** PLAN-025

**Status:** IMP-287 concluido; IMP-288 nao iniciado e sob gate adversarial

---

# 1. Resultado

O IMP-287 transformou o snapshot OpenAPI governado na unica tipagem HTTP do
frontend. O pacote gera um artefato TypeScript versionado, compara a geracao
esperada em bytes canonicos LF e oferece somente uma factory `openapi-fetch` inerte,
protegida por `server-only`.

Nenhum request foi executado pelo cliente. Bearer, cookies, refresh, CSRF,
correlation ID, ciclo de Idempotency-Key, normalizacao `ApiProblem`, Route
Handlers, Server Actions, sessao e BFF permanecem exclusivos do IMP-288.

---

# 2. Evidencia temporal RED para GREEN

Antes da instalacao e da geracao, o contrato documental foi ampliado:

- RED: 53 de 54 casos passaram;
- falha unica observada:
  `frontend/src/lib/api/openapi.generated.ts ausente`;
- nenhum teste anterior falhou ou foi relaxado.

Depois da implementacao, os contratos positivos e as mutacoes negativas ficam
integrados ao PLAN-025 e ao gate de escopo encadeado. O estado RED e uma
evidencia temporal observada nesta sessao; depois do GREEN ele permanece no
relatorio e no transcript, mas nao e reproduzivel sem remover deliberadamente
o artefato gerado.

---

# 3. Stack e decisoes

Versoes exatas:

- `openapi-typescript` 7.13.0, desenvolvimento;
- `openapi-fetch` 0.17.0, runtime;
- `server-only` 0.0.1, runtime.

As versoes foram confirmadas no registry npm e na documentacao oficial
openapi-ts. `openapi-typescript` 7.13.0 declara peer TypeScript `^5.x`,
compativel com TypeScript 5.9.3 e Node 24.19.0.

O gerador usa somente o arquivo local
`docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json`, com
`alphabetize` e `immutable`. O snapshot permanece em 107 operacoes, 133 schemas
e SHA-256
`8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1`.

---

# 4. Contratos observados

Os testes derivam diretamente de `paths` e `components` gerados:

- login usa `AuthLoginRequest`;
- refresh e logout usam `AuthRefreshRequest`;
- contexto corrente usa `ContextoOperacionalResponse`;
- catalogo usa `PermissoesCatalogoResponse`;
- erros usam `ErroResponse`, preservando a excecao `HealthResponse` do 503 de
  `/health`;
- exatamente 30 headers `Idempotency-Key` sao obrigatorios e conservam limites
  de 1 a 255 caracteres;
- negativos de tipo rejeitam login incompleto, `Payload` no refresh e comando
  idempotente sem o header obrigatorio.

O cliente manual nao declara interfaces de dominio, `any`, casts, suppressions
TypeScript ou modelos paralelos.

---

# 5. Determinismo e ataques de drift

Duas geracoes consecutivas produziram o mesmo SHA-256 do artefato:

`606364fae25bf2614d6ab8bc9734829276c6f556a7623e6ffb786e23e1eb667b`.

Ataques observados em copias temporarias, removidas ao final:

- acrescentar um byte ao gerado: `api:check` terminou com codigo 1;
- remover `/iam/contexto-atual` de uma copia do snapshot: o hash governado
  terminou com codigo 1;
- materializar CRLF em copia do gerado nao causa falso drift no Windows; o
  check canonicaliza EOL para LF antes da comparacao;
- mutacoes documentais removendo `server-only`, trocando `paths` por `any`,
  introduzindo cast/modelo manual, removendo o check da CI, antecipando
  Authorization ou dependencia futura sao rejeitadas.

---

# 6. Escopo e arquivos

O baseline foi capturado antes da primeira mudanca funcional com 97 paths,
9 mutaveis e 7 novos. Ele encadeia o manifesto IMP-286 pelo SHA-256
`220ff581fa5843ab37930173becf1963b75107fa3791e8854d2abcde774ffeda`.

Alterados:

- `.github/workflows/quality.yml`;
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`;
- `docs/governance/frontend-mvp-traceability-matrix.md`;
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`;
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`;
- `frontend/README.md`;
- `frontend/package.json` e `frontend/package-lock.json`;
- `scripts/tests/test-plan-025-contracts.js`.

Criados:

- `docs/audits/evidence/frontend-mvp-imp-287-protected-baseline.json`;
- este relatorio;
- `frontend/scripts/openapi-codegen.mjs`;
- `frontend/src/lib/api/openapi.generated.ts`;
- `frontend/src/lib/api/client.server.ts`;
- `frontend/tests/contract/openapi-client.test.ts`;
- `scripts/tests/test-imp-287-scope.js`.

Backend, migrations, testes Python, Product, Registry, snapshot OpenAPI,
foundation, jornadas e evidencias historicas dos IMP-284..IMP-286 nao foram
alterados pelo IMP-287.

---

# 7. Gates, caveats e decisao

Resultados observados:

- instalacao limpa com `npm ci --ignore-scripts` e `npm audit`: 0
  vulnerabilidades;
- `api:check`, lint, typecheck e build: verdes;
- unit 1/1, component 7/7, contrato 3/3 e Playwright 12/12;
- contrato documental PLAN-025: 67/67, incluindo mutacoes negativas;
- gate IMP-287: predecessor verificado, 88 arquivos protegidos, 104 paths no
  delta final e 0 divergencia;
- `uv run pytest -q`, Ruff, Black e mypy: verdes;
- `docs:validate`: 318 OK, 29 avisos historicos e 0 erros;
- `docs:test` e `git diff --check`: verdes.

O gate de escopo combina o delta commitado desde `e48cb72` com mudancas locais,
portanto funciona tanto na worktree desta sessao quanto no checkout limpo do
primeiro commit/PR; o workflow usa `fetch-depth: 0`. A execucao remota
Linux/Windows permanece nao observada porque nao houve commit ou push; ela
continua obrigatoria no primeiro commit/PR. As Actions `@v4` mutaveis
permanecem caveat de supply chain ja conhecido.

**Decisao:** o IMP-288 permanece Planejado e nao esta autorizado nesta sessao.
Executar `fable:fable-judge` focal sobre o pacote IMP-287 antes de implementar
sessao ou BFF.
