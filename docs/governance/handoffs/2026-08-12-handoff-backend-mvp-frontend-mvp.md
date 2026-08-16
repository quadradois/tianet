# 2026-08-12 - Handoff: Backend MVP Certificado e Preparacao do Frontend MVP

**Periodo coberto:** encerramento pos-merge do Backend MVP ate hardening tecnico
**Status:** Backend MVP recertificado no `master`; proximo ciclo recomendado e Frontend MVP
**Branch base:** `master`
**Commit base observado:** `e48cb72` - Merge pull request #9 from quadradois/codex/backend-mvp-hardening-warnings

---

## 1. Estado Executivo

O backend MVP foi concluido e recertificado apos os ciclos EPIC-001 a EPIC-010,
PLAN-020 e hardening tecnico PLAN-024. O repositorio esta pronto para iniciar a
fase de definicao do Frontend MVP, desde que a nova sessao preserve os contratos
publicos do backend e nao reabra regra de negocio ja certificada.

Nao ha, ate este handoff, um frontend de produto materializado no repositorio. O
proximo ciclo deve iniciar por Discovery/SDD do Frontend MVP, escolha governada
de stack e mapeamento de telas/fluxos contra OpenAPI, IAM/RBAC e jornadas E2E.

---

## 2. Backend Certificado

| Area | Estado |
|---|---|
| EPIC-001 | Plataforma/Tenant implementado |
| EPIC-002 | Cadastro de Devedores implementado |
| EPIC-003 | Comercial implementado |
| EPIC-004 | Contratos implementado |
| EPIC-005 | Motor Financeiro implementado |
| EPIC-006 | IAM/RBAC implementado |
| EPIC-007 | Operacao Diaria implementada |
| EPIC-008 | Fundacao Operacional e Observabilidade implementada |
| EPIC-009 | Configuracoes Financeiras e Calendario Operacional implementados |
| EPIC-010 | Automacao Operacional, Scheduler e Notifications implementados |
| PLAN-020 | Fechamento e Certificacao do Backend MVP concluido |
| PLAN-024 | Hardening tecnico de warnings concluido |

Escopo backend certificado:

- API publica com contratos HTTP, OpenAPI, RBAC e isolamento Tenant/Carteira;
- IAM, credenciais, sessoes, perfis e permissoes;
- Cadastro, Comercial, Contratos, Motor Financeiro, Operacao Diaria,
  Configuracoes Financeiras, Scheduler e Notification;
- healthcheck real, correlation ID, logs estruturados e tratamento tecnico de
  erro;
- migrations reproduziveis e gates de qualidade;
- guardrails para impedir calculo financeiro fora do Motor Financeiro.

---

## 3. Evidencias de Recertificacao

Ultima recertificacao/hardening conhecida:

- `uv run pytest -q` - verde;
- `uv run ruff check .` - verde;
- `uv run black --check .` - verde;
- `uv run mypy src tests` - verde;
- `npm run docs:validate` - verde com `0 erro(s)` e 29 avisos historicos
  governados;
- `npm run docs:test` - verde;
- `npm run quality:migrations` - verde;
- `git diff --check` - verde.

GitHub:

- PR #8: PLAN-020 / Backend MVP mergeado;
- PR #9: hardening tecnico de warnings mergeado;
- `master` local observado no commit `e48cb72`.

---

## 4. Caveats Operacionais

- `docs:validate` ainda reporta 29 avisos historicos. Eles estao aceitos como
  caveat governado pelo PLAN-024 e nao bloqueiam o Backend MVP.
- `npm run quality:migrations` executa ciclo destrutivo controlado de migrations
  e exige ambiente PostgreSQL/Docker saudavel conforme scripts do projeto.
- Durante a instalacao da skill Playwright foi criada uma copia local nao
  versionada em `.claude/skills/playwright-cli/`. Ela deve ser removida ou
  ignorada conscientemente antes de commit/PR, conforme decisao do usuario.
- O comando `playwright-cli --version` exibiu `0.1.18`, mas retornou uma falha
  interna do runtime no Windows apos imprimir a versao. A skill ficou instalada
  globalmente em `C:\Users\Atual Master\.agents\skills\playwright-cli`; tratar a
  falha do executavel como caveat a validar antes dos testes visuais.

---

## 5. Ferramentas e Skills Recomendadas para o Frontend

Skills ja disponiveis e recomendadas:

- `fable:fable-method` - Discovery/SDD, decisoes e materializacao Product;
- `fable:fable-loop` - macro-loop de implementacao apos Product/PLAN aprovados;
- `fable:fable-judge` e `review-agent` - revisao adversarial e recertificacao;
- `product-design:audit` - auditar fluxos, jornadas e ergonomia de produto;
- `product-design:ideate` - explorar alternativas visuais;
- `product-design:image-to-code` - implementar referencia visual aprovada;
- `figma:*` - criar/usar Figma e design system, se a frente visual exigir;
- `vercel:nextjs` - arquitetura Next.js/App Router;
- `vercel:shadcn` - componentes shadcn/ui e theming;
- `vercel:react-best-practices` - revisao de componentes TSX;
- `vercel:swr` - data fetching e cache client-side, se adotado;
- `vercel:agent-browser` e `vercel:agent-browser-verify` - verificacao visual;
- `playwright-cli` - E2E, screenshots e validacao de fluxos no navegador.

Plugin adicional avaliado:

- Nao e necessario instalar outro plugin antes de iniciar o Frontend MVP. O
  conjunto atual cobre produto, design, Next.js, componentes, browser e testes.

---

## 6. Diretrizes para o Frontend MVP

O Frontend MVP deve ser uma aplicacao operacional, nao uma landing page. A
primeira tela deve priorizar fluxo real de trabalho, navegacao clara,
informacao densa e comandos seguros.

Diretrizes obrigatorias:

- consumir contratos oficiais do backend/OpenAPI;
- preservar IAM/RBAC, Tenant e Carteira;
- nao calcular juros, mora, multa, saldo, quitacao, amortizacao, renegociacao
  ou memoria de calculo no frontend;
- tratar `400`, `401`, `403`, `404`, `409` e `5xx` conforme contratos publicos;
- propagar e exibir `X-Correlation-ID` em erros operacionais;
- respeitar idempotencia onde a API exigir chave;
- nunca expor segredos, tokens, dados sensiveis ou detalhes tecnicos indevidos;
- criar testes de fluxo antes ou junto das implementacoes;
- validar UI em desktop e mobile com Playwright/browser.

Stack inicial recomendada para decisao no Discovery:

- Next.js App Router + TypeScript;
- shadcn/ui como base de componentes;
- camada de cliente API gerada ou tipada a partir do OpenAPI;
- data fetching com SWR ou alternativa equivalente definida no PLAN;
- Playwright para E2E e screenshots;
- design system minimo governado antes de telas complexas.

Esta stack e recomendacao inicial, nao decisao irrevogavel. A nova sessao deve
validar contra o repositorio, o escopo do MVP e a experiencia esperada.

---

## 7. Proximo Ciclo Recomendado

Comecar por uma fase documental curta:

1. Discovery/SDD do Frontend MVP;
2. Product/Capability ou ajuste governado da capability existente;
3. EPIC formal do Frontend MVP;
4. Features e User Stories candidatas;
5. PLAN tecnico de frontend com backlog de IMPs;
6. revisao adversarial documental;
7. somente depois iniciar macro-loop de implementacao.

Focos iniciais provaveis:

- login/autenticacao e bootstrap de sessao;
- selecao de Tenant/Carteira;
- dashboard operacional;
- cadastro de Devedor;
- fluxo Comercial -> Contrato -> Motor;
- operacao diaria, agenda, lembretes e notificacoes;
- telas administrativas de IAM/configuracoes conforme permissao;
- estados vazios, erros, carregamento, retry e auditoria operacional.

---

## 8. Prompt Recomendado para a Nova Sessao

```text
[$fable:fable-method](C:\Users\Atual Master\.codex\plugins\cache\fable-method\fable\1.4.0\skills\fable-method\SKILL.md)

Iniciar a nova sessao do Frontend MVP a partir do handoff em:
C:\emprestimo\docs\governance\handoffs\2026-08-12-handoff-backend-mvp-frontend-mvp.md

Objetivo:
Fazer Discovery/SDD do Frontend MVP antes de qualquer implementacao de codigo,
usando o Backend MVP ja certificado no master como fonte de contratos.

Diretrizes:
- ler o handoff e confirmar o estado do backend;
- nao alterar backend nesta fase;
- nao iniciar implementacao antes de Product/EPIC/Features/User Stories e PLAN;
- definir stack frontend governada, preferencialmente validando Next.js App
  Router + TypeScript + shadcn/ui + cliente OpenAPI;
- mapear fluxos MVP contra OpenAPI, IAM/RBAC, Tenant/Carteira e jornadas E2E;
- garantir que o frontend nao calcule regra financeira, apenas consuma dados e
  comandos do backend;
- planejar testes de unidade, componente, contrato, Playwright E2E e validacao
  visual;
- usar, quando aplicavel, product-design:audit, vercel:nextjs,
  vercel:shadcn, vercel:react-best-practices, vercel:agent-browser-verify e
  playwright-cli;
- ao final, entregar Discovery/SDD, recomendacao de stack, riscos, fronteiras,
  contratos de API, plano de testes e recomendacao para materializar Product.
```

---

## 9. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-12 | Handoff entre Backend MVP certificado e inicio planejado do Frontend MVP. |
