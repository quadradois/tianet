# Relatório do IMP-288 — Sessão e BFF server-only

**Data:** 2026-08-13  
**Plano relacionado:** PLAN-025 / IMP-288  
**Status:** implementação local concluída; IMP-289 bloqueado até fable:fable-judge focal

---

# 1. Resultado

O IMP-288 materializou exclusivamente sessão stateless JWE, dois Route Handlers
de autenticação e transporte backend autenticado server-only. Nenhuma página de
login, shell, navegação, contexto visual, RBAC de componentes ou jornada foi
iniciada.

A sessão usa `jose` 6.2.8 com `alg=dir` e `enc=A256GCM`. Access e refresh
tokens ficam dentro do JWE em cookie HttpOnly. A única dependência adicionada
foi `jose@6.2.8`, fixada no lockfile e auditada com zero vulnerabilidades.

Fontes oficiais consultadas:

- [jose](https://github.com/panva/jose);
- [Node.js Web Crypto](https://nodejs.org/docs/latest-v24.x/api/webcrypto.html);
- [Next.js cookies](https://nextjs.org/docs/app/api-reference/functions/cookies);
- [Next.js Route Handlers](https://nextjs.org/docs/app/getting-started/route-handlers);
- [Next.js data security](https://nextjs.org/docs/app/guides/data-security).

---

# 2. Evidência temporal RED → GREEN

O primeiro comando após ampliar o contrato produziu 66/68: a ausência esperada
de `frontend/src/lib/bff/session.server.ts` e o gate histórico IMP-287, que
corretamente recusou o novo manifesto IMP-288. A invocação corrente foi então
encadeada ao manifesto predecessor, sem editar ou enfraquecer o gate IMP-287.

O RED canônico, ainda anterior à instalação e ao código de sessão, produziu
67/68. A única falha foi:

```text
frontend/src/lib/bff/session.server.ts ausente
```

Os 67 contratos anteriores permaneceram verdes. O RED é evidência temporal do
transcript desta sessão; não é um estado reproduzível após o GREEN.

O GREEN focal observado após a implementação:

- TypeScript typecheck: verde;
- ESLint sem warnings: verde;
- Vitest BFF: 49/49;
- JWE, cookie, Origin/CSRF, login/logout, concorrência, retry, erros e timeout:
  verdes.

A contagem final do contrato documental e os gates completos são registrados
na seção 7 após a recertificação.

---

# 3. Decisão arquitetural

- Chave JWE atual de exatamente 32 bytes base64url, `kid` obrigatório e chave
  anterior opcional para rotação;
- payload mínimo: versão, Usuario/Tenant, access/refresh e suas expirações;
- cookie produtivo `__Host-emprestimo-session` e nome local sem prefixo
  `emprestimo-session`; ambos HttpOnly, SameSite=Lax, Path=/, prioridade alta,
  Secure em produção e prazo limitado pelo refresh;
- variáveis: `FRONTEND_BACKEND_URL`, `FRONTEND_ORIGIN`,
  `FRONTEND_SESSION_KEY_ID`, `FRONTEND_SESSION_KEY` e par anterior opcional;
- somente `POST /api/auth/login` e `POST /api/auth/logout`;
- nenhum endpoint público de refresh, Server Action ou proxy catch-all;
- mutações exigem Origin exata e `X-CSRF-Protection: 1`;
- logout confiável tenta revogação backend, sempre limpa a sessão local e
  impede que refresh já em voo a ressuscite dentro do mesmo processo;
- `ApiProblem` preserva status/código/mensagem/correlation ID, neutraliza 404 e
  sanitiza 5xx/timeout/resposta malformada.

## Limite do single-flight

A coalescência usa um Map limitado de Promises, indexado pelo SHA-256 do refresh
token e limpo em `finally`. A garantia é somente por processo/isolate Next e
sessão. Instâncias distintas podem renovar em paralelo. O refresh backend atual
não é rotativo, portanto duplicatas cross-instance são toleráveis; uma garantia
global exigiria lock/store distribuído fora deste IMP.

O mesmo limite vale para a coordenação `logout-wins`: o tombstone process-local
impede regravação tardia do cookie no isolate que observou o logout. Garantia
entre instâncias exigiria store/versionamento distribuído e não é alegada aqui.

## Política de replay

Há 32 mutações protegidas sem `Idempotency-Key`. Elas não são repetidas
automaticamente após 401. O transporte renova a sessão, mas só repete uma vez
GET/HEAD ou mutação que já tenha chave idempotente. O replay usa clone do
request e preserva payload, correlation ID e Idempotency-Key.

---

# 4. Evidências observáveis

- o JSON de login retorna apenas `authenticated` e `correlationId`;
- testes provam que access/refresh não aparecem no retorno e não aparecem em
  claro no cookie;
- adulteração, chave errada, expiração e rotação JWE foram exercitadas;
- Origin ausente, `null`, hostil, same-site/cross-site e CSRF incorreto falham
  antes do backend;
- logout hostil não apaga sessão; logout confiável apaga mesmo sob 5xx;
- quatro requests concorrentes da mesma sessão produziram uma chamada de
  refresh; falha concorrente também produziu uma chamada e encerrou todas;
- aborto do líder não cancela o refresh compartilhado de seguidores vivos, e
  aborto de um seguidor encerra apenas sua própria espera;
- corrida logout versus refresh termina sem cookie ressuscitado no mesmo
  processo;
- redirects de login, refresh e logout falham fechados e a origem backend é
  validada antes do envio de credenciais;
- o corpo público de login é lido incrementalmente, interrompido acima de 16
  KiB ou por timeout e aceita somente `application/json` com charset UTF-8;
- a sessão é revalidada após a cifra e imediatamente antes do `Set-Cookie`,
  fechando a janela logout versus persistência tardia;
- configuração rejeita chave base64url não canônica, `kid` duplicado, protocolo
  fora de HTTP(S) e URL backend com path;
- o inventário consumido prova 5 operações públicas e 102 Bearer; o transporte
  autenticado rejeita operações públicas e remove headers do navegador;
- 403, 404, 409, 422 e 5xx não provocam refresh;
- segundo 401 encerra sessão sem terceiro ciclo;
- timeout e payload malformado produzem erro seguro correlacionável;
- 404 usa mensagem neutra;
- não há cálculo financeiro, Tenant/Carteira vindos do navegador, UI ou jornada.

---

# 5. Escopo temporal

- HEAD/master/origin/master: `e48cb72ee4f62428491e8b8c19a569611d83fca8`;
- predecessor IMP-287:
  `c3149ed549e5de78cd5e23c7f0499ef11bf705ddb4b56852cccfff73c3707c58`;
- baseline pré-IMP-288: 104 paths;
- mutáveis exatos: 11;
- protegidos por hash: 93;
- novos exatos: 12;
- inventário final esperado: 116 paths.

Backend, migrations, testes Python, Product, Registry, snapshot OpenAPI, arquivo
gerado e evidências IMP-284..IMP-287 permanecem protegidos.

---

# 6. Arquivos do IMP-288

## Alterados

- `.github/workflows/quality.yml`
- `docs/architecture/adrs/ADR-001-stack-tecnologica-oficial-mvp.md`
- `docs/audits/discoveries/frontend-mvp-discovery-sdd.md`
- `docs/governance/frontend-mvp-traceability-matrix.md`
- `docs/implementation/backlogs/PLAN-025-execution-backlog.md`
- `docs/implementation/plans/PLAN-025-frontend-mvp.md`
- `frontend/README.md`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src/lib/api/client.server.ts`
- `scripts/tests/test-plan-025-contracts.js`

## Criados

- `docs/audits/evidence/frontend-mvp-imp-288-protected-baseline.json`
- `docs/audits/reports/frontend-mvp-imp-288-session-bff-report-2026-08-13.md`
- `frontend/.env.example`
- `frontend/src/lib/bff/session.server.ts`
- `frontend/src/lib/bff/backend.server.ts`
- `frontend/src/app/api/auth/login/route.ts`
- `frontend/src/app/api/auth/logout/route.ts`
- `frontend/vitest.bff.config.ts`
- `frontend/tests/bff/session.test.ts`
- `frontend/tests/bff/bff.test.ts`
- `frontend/tests/bff/server-only-shim.ts`
- `scripts/tests/test-imp-288-scope.js`

---

# 7. Gates observados

| Gate | Resultado |
|---|---|
| Node/npm governados | `v24.19.0` / `11.17.0` |
| `npm ci --ignore-scripts` | verde; 550 pacotes auditados |
| `npm run api:check` | verde; bytes LF idênticos |
| `npm run lint` | verde; zero warnings |
| `npm run typecheck` | verde |
| `npm run build` | verde; somente `/`, login/logout e assets |
| `npm run test:unit` | 1/1 |
| `npm run test:component` | 7/7 |
| `npm run test:contract` | 3/3 |
| `npm run test:bff` | 49/49 após reforços de redirect, leitura limitada, cancelamento prévio/concorrente, logout-wins e configuração fail-closed |
| `npm run test:e2e` | 12/12 |
| `npm audit` | zero vulnerabilidades |
| `uv run pytest -q` | verde, suíte completa |
| Ruff / Black / mypy | verdes; mypy em 230 arquivos |
| `npm run quality:migrations` | verde em PostgreSQL 16 descartável; container removido |
| `npm run docs:validate` | 319 OK, 29 avisos históricos, 0 erros |
| `npm run docs:test` | verde |
| contrato PLAN-025 | 90/90, incluindo mutações IMP-288 |
| scope IMP-288 | 93 protegidos, inventário 116, 0 divergência |
| `git diff --check` | verde |
| OpenAPI | 107 operações / 133 schemas |
| SHA snapshot | `8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1` |
| SHA gerado | `606364fae25bf2614d6ab8bc9734829276c6f556a7623e6ffb786e23e1eb667b` |

Durante a primeira cadeia completa, o teste de adulteração trocava o último
caractere Base64URL e podia produzir outra representação dos mesmos bits de
padding. O ataque foi corrigido para alterar um byte efetivo do ciphertext; a
suite BFF passou duas vezes consecutivas. A implementação JWE não mudou por
causa desse falso negativo.

A CI Linux/Windows está configurada com `fetch-depth: 0`, suite BFF e gate
IMP-288, mas sua execução remota não foi observada porque não houve
commit/push/PR.

Caveats operacionais não bloqueantes:

- se o único chamador abandona uma renovação já compartilhada, o trabalho
  server-side continua somente até concluir ou atingir o timeout limitado do
  coordenador; o chamador recebe 499 e nenhuma sessão é persistida por ele;
- um 401 deliberadamente atrasado até depois de outra renovação completar pode
  iniciar uma segunda renovação. O refresh backend certificado é não rotativo,
  portanto não duplica comando de negócio nem invalida a sessão, mas permanece
  uma oportunidade futura de eficiência;
- `single-flight` e `logout-wins` não são alegados entre processos/isolates;
  uma garantia global depende de store/lock distribuído fora deste IMP.

---

# 8. Decisão sobre IMP-289

IMP-289 permanece Planejado e bloqueado. O próximo passo obrigatório é executar
`fable:fable-judge` focal sobre este pacote. A execução remota da CI continua
gate obrigatório no primeiro commit/PR.
