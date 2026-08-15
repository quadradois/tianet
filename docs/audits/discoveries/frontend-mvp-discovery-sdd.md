# Frontend MVP — Discovery e Software Design Description

**Vers?o:** 3.2.0

**Status:** Frontend MVP concluido localmente; IMP-274..IMP-303 recertificados; CI remota nao observada

**Data:** 2026-08-13

**Base certificada:** `master` em `e48cb72`

---

# 1. Parecer executivo

O Frontend MVP deve ser uma aplicação web operacional baseada em Next.js App
Router e TypeScript, com shadcn/ui, cliente tipado gerado do OpenAPI e uma
camada BFF (Backend for Frontend) no próprio Next.js. O navegador não deve
receber tokens do backend nem chamar a API FastAPI diretamente: autenticação,
refresh, propagação de Bearer token, `X-Correlation-ID` e
`Idempotency-Key` devem permanecer em código server-only.

O backend está certificado e é a fonte de verdade de contratos e regras. O
frontend apresenta dados e envia comandos; ele não calcula juros, mora, multa,
parcelas, amortização, saldo, quitação, renegociação, inadimplência ou memória
de cálculo.

Não se recomenda criar uma Capability chamada “Frontend” nem um EPIC técnico
transversal. A camada Product já descreve as capacidades e jornadas do MVP de
forma independente de canal. A materialização deve reutilizar PRODUCT-001 a
PRODUCT-009, EPIC-001 a EPIC-010 e suas Features/User Stories, emitindo apenas
os deltas funcionais realmente ausentes. Depois disso, um PLAN transversal de
frontend pode organizar a implementação por fatias verticais.

Na fotografia original de 105 operacoes/126 schemas havia três bloqueios de
contrato antes do scaffold de produto:

1. não existe operação autenticada que devolva, em uma única resposta, o
   usuário corrente, Tenant, Carteira padrão e permissões efetivas;
2. `login`, `refresh` e `logout` usam corpo OpenAPI genérico `Payload`, embora o
   runtime possua schemas específicos;
3. 29 operações exigem `Idempotency-Key` no runtime, mas o OpenAPI marca o
   header como opcional.

Esses bloqueios não reabrem regra de negócio financeira. Eles requerem decisão
e hardening aditivo do contrato público antes da geração definitiva do cliente.

Atualização de materialização em 2026-08-12: a recomendação deste Discovery foi
convertida na matriz oficial
`docs/governance/frontend-mvp-traceability-matrix.md`, nas US-125/US-126, nas
versões 1.1.0 de FEATURE-011/FEATURE-012 e no PLAN-025 com backlog
IMP-274..IMP-303.

Adendo pós-hardening de 2026-08-12: IMP-276..IMP-283 foram executados e as
lacunas contratuais 1..6 foram fechadas no OpenAPI recertificado com 107
operacoes e 133 schemas. O snapshot e o relatorio PLAN-026 preservam a
evidencia. IMP-284 continua bloqueado exclusivamente pelo novo
`fable:fable-judge`; tokens/design foundation, ambiente Playwright e validacao
visual sao gates dos IMPs frontend posteriores, nao pre-condicoes adicionais
para autorizar o scaffold.

Adendo pós-scaffold de 2026-08-12: o gate adversarial focal emitiu `VERIFIED` e
o IMP-284 materializou o workspace isolado `frontend/` com Next.js App Router,
TypeScript estrito, lockfile npm próprio e gates de lint/typecheck/build. Não
foram antecipados harness de testes, shadcn/ui, cliente OpenAPI, BFF, sessão ou
jornada de negócio. O IMP-285 permanece planejado até novo judge focal.

Adendo pós-harness de 2026-08-13: o IMP-285 instalou exclusivamente Vitest,
Testing Library, user-event, jest-dom, jsdom, MSW e Playwright, com smokes
separados de unidade, componente, contrato e E2E. O E2E atual observa apenas o
placeholder Next; PostgreSQL/FastAPI reais possuem smoke independente de
readiness e cleanup, enquanto seu consumo pelo frontend permanece bloqueado até
cliente OpenAPI e BFF nos IMP-287/IMP-288. Nenhum design, jornada ou regra
financeira foi iniciado. O IMP-286 depende de novo judge focal.

Adendo pós-foundation de 2026-08-13: o IMP-286 materializou uma foundation
funcional neutra com tokens semânticos claro/escuro, primitives locais e estados
explícitos de loading, vazio, erro, overflow, disabled, pending, success, sem
Permissão e 404 neutro. O specimen técnico `/` continua server-first; somente
Dialog e sua demonstração interativa são Client Components. Axe, teclado,
retorno de foco, reduced motion e screenshots 1440x900/390x844 foram observados.
Isto não aprova identidade de marca nem inicia jornada, cliente OpenAPI, BFF,
sessão, RBAC de produto ou cálculo financeiro. O IMP-287 depende de novo judge
focal.

Adendo pós-cliente de 2026-08-13: o IMP-287 materializou tipos versionados e
determinísticos a partir do snapshot governado de 107 operações/133 schemas,
uma factory `openapi-fetch` inerte protegida por `server-only` e um gate de
drift por bytes canônicos LF. Nenhum request, token, cookie, middleware, BFF, sessão,
Route Handler, Server Action, jornada ou cálculo financeiro foi iniciado. O
IMP-288 depende de novo judge focal.

Adendo pós-sessão/BFF de 2026-08-13: o IMP-288 materializou sessão stateless
JWE com `jose` 6.2.8, cookie HttpOnly, Route Handlers mínimos de login/logout e
transporte autenticado server-only. Origin/CSRF, correlation, timeout e erros
seguros são observáveis. O refresh é single-flight somente por processo Next e
sessão; não há alegação distribuída. Retry automático ocorre apenas para
GET/HEAD ou mutações já protegidas por `Idempotency-Key`. Nenhuma tela, shell,
RBAC visual, contexto operacional ou cálculo financeiro foi iniciado. O
IMP-289 depende de novo judge focal.

Adendo pós-shell/contexto de 2026-08-13: o IMP-289 materializou `/login`, o
shell server-first em `/app`, logout e o bootstrap do contexto operacional da
US-125. O layout lê o JWE e `GET /iam/contexto-atual` somente no servidor, sem
aceitar IDs de Usuário, Tenant ou Carteira e sem buscar o catálogo
administrativo de Permissões. Um 401 usa uma única passagem por recovery e
POST CSRF-protegido para permitir refresh/persistência fora do render; 409 não
fabrica Carteira. A navegação usa igualdade exata, mas publica somente `/app`:
Dashboard e demais destinos continuam nos IMP-290+. Tokens não chegaram ao
HTML, storage ou JavaScript cliente. Nenhum cálculo financeiro foi criado.

Adendo pós-Dashboard de 2026-08-14: o IMP-290 converteu `/app` na primeira
superfície operacional read-only. Resumo, vencimentos, agenda e fila de
cobrança são consultados somente pelas Permissões exatas e pela Carteira padrão
do próprio Principal; valores e estados são apresentados sem cálculo no
frontend. A data civil canônica usa `America/Sao_Paulo` como política MVP de
apresentação até existir timezone governado por Tenant. As APIs não paginadas e
os deltas de período/campos das US-079/084/085 permanecem dívida contratual;
nenhuma dessas jornadas foi declarada integralmente concluída.

---

# 2. Autoridades e evidências consultadas

Fontes locais primárias:

- [handoff Backend MVP → Frontend MVP](../../governance/handoffs/2026-08-12-handoff-backend-mvp-frontend-mvp.md);
- [Product Vision](../../foundation/FOUNDATION-001-product-vision.md);
- [Product Map](../../foundation/FOUNDATION-007-product-map.md);
- [Escopo oficial do MVP](../../foundation/FOUNDATION-008-mvp-scope.md);
- [Capability Map](../../foundation/FOUNDATION-009-capability-map.md);
- [ADR de stack do MVP](../../architecture/adrs/ADR-001-stack-tecnologica-oficial-mvp.md);
- [ADR de autenticação e autorização](../../architecture/adrs/ADR-004-autenticacao-e-autorizacao-iam.md);
- [ADR de identidade externa do Devedor](../../architecture/adrs/ADR-018-identidade-externa-do-devedor.md);
- [PLAN de certificação do Backend MVP](../../implementation/plans/PLAN-020-fechamento-certificacao-backend-mvp.md);
- [relatório de prontidão](../../implementation/reports/PLAN-023-backend-mvp-readiness-2026-08-12.md);
- factory FastAPI, rotas, dependências, schemas e OpenAPI em
  `src/emprestimo/presentation/api/`;
- suites `test_backend_mvp_inventory.py`, `test_backend_mvp_contracts.py`,
  `test_backend_mvp_e2e.py`, `test_backend_mvp_security.py` e
  `test_backend_mvp_operations.py`.

Fontes oficiais atuais para a decisão de stack:

- [Next.js App Router](https://nextjs.org/docs/app);
- [autenticação no Next.js](https://nextjs.org/docs/app/guides/authentication);
- [Server e Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components);
- [cookies no App Router](https://nextjs.org/docs/app/api-reference/functions/cookies);
- [instalação do shadcn/ui](https://ui.shadcn.com/docs/installation);
- [openapi-typescript CLI](https://openapi-ts.dev/cli);
- [openapi-fetch](https://openapi-ts.dev/openapi-fetch/);
- [TanStack Query com Server Components](https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr).

Evidência observada nesta sessão:

| Verificação | Resultado |
|---|---|
| `HEAD` e `origin/master` | ambos em `e48cb72` |
| `uv run pytest -q` | suíte completa verde, 100% |
| `uv run ruff check .` | verde |
| `uv run black --check .` | 247 arquivos sem mudança |
| `uv run mypy src tests` | 229 arquivos sem issues |
| `npm run docs:validate` | 307 OK, 29 avisos históricos, 0 erros antes deste documento |
| `npm run docs:test` | todas as suites passaram |
| OpenAPI gerado por `create_app().openapi()` na fotografia histórica pré-hardening | OpenAPI 3.1.0, API 0.1.0, 105 operações, 126 schemas |

Na fotografia histórica pré-scaffold não existiam aplicação frontend, arquivo
TSX/JSX, token visual, `globals.css`, `components.json`, configuração Next.js
ou superfície renderizada. Por isso, auditoria visual, browser verify e
Playwright não produziram evidência naquela fase. Os adendos 1.3.0 a 1.6.0
registram o estado corrente após scaffold, harness, design foundation e cliente
OpenAPI.

---

# 3. Objetivo e definição de pronto

O Frontend MVP deve permitir que pessoas autorizadas executem as jornadas F1 a
F6 certificadas no backend, com contexto Tenant/Carteira correto, RBAC,
idempotência, erros correlacionáveis e apresentação fiel dos resultados do
Motor Financeiro.

Esta fase documental está pronta quando:

- a stack possui uma recomendação única e fronteiras explícitas;
- todas as jornadas MVP estão ligadas a contratos HTTP e permissões;
- lacunas de contrato são separadas de requisitos de interface;
- Product existente e deltas candidatos estão identificados;
- o PLAN futuro possui ordem, gates e estratégia de testes;
- nenhuma implementação ou alteração backend foi iniciada.

---

# 4. Usuários e necessidades operacionais

| Papel | Necessidade principal | Limite |
|---|---|---|
| Operador de crédito | cadastrar Devedor e conduzir proposta, contrato e operação | somente Tenant/Carteira e comandos permitidos |
| Operador de cobrança | consultar fila, registrar ação, promessa, agenda e comunicação | nunca recalcular dívida ou inadimplência |
| Gestor | acompanhar carteira, vencimentos, fluxo e decisões | indicadores vêm integralmente do backend |
| Administrador do Tenant | gerir perfis, permissões e configurações autorizadas | não administra outro Tenant |
| Administrador da plataforma | provisionar e manter Tenants | superfície segregada das jornadas de crédito |

A navegação pode omitir ou desabilitar ações sem permissão para melhorar a
experiência, mas a autorização do backend continua obrigatória em cada comando.
Um elemento oculto na interface não é um controle de segurança.

---

# 5. Decisões de produto e governança

## 5.1 Frontend não é Capability

FOUNDATION-007 define capacidades como o que o produto faz,
independentemente de telas, menus ou APIs. FOUNDATION-009 exige que todo EPIC
pertença a uma Capability e a um contexto primário. Criar uma Capability
“Frontend” misturaria canal técnico com valor de negócio e duplicaria o mapa
existente.

Decisão: reutilizar a hierarquia Product atual. O frontend será um plano de
entrega transversal rastreado para os mesmos resultados de negócio.

## 5.2 Cobertura Product existente

| Jornada de interface | Product/EPIC/Feature já governados |
|---|---|
| autenticar, renovar, sair e autorizar | PRODUCT-001, EPIC-006, FEATURE-009 a FEATURE-012 |
| operar Tenant | PRODUCT-001, EPIC-001, FEATURE-001 a FEATURE-004 |
| cadastrar e consultar Devedor | PRODUCT-002, EPIC-002, FEATURE-005 a FEATURE-008 |
| simular e decidir proposta | PRODUCT-003, EPIC-003, FEATURE-013 a FEATURE-017 |
| formalizar e liberar contrato | PRODUCT-004, EPIC-004, FEATURE-018 a FEATURE-022 |
| operar empréstimo e pagamentos | PRODUCT-004, EPIC-005, FEATURE-023 a FEATURE-027 |
| cobrança, agenda, comunicação e relatórios | PRODUCT-005 a PRODUCT-008, EPIC-007, FEATURE-028 a FEATURE-031 |
| configurações financeiras | PRODUCT-009, EPIC-009, FEATURE-037 a FEATURE-041 |
| automação e notificações | PRODUCT-006/PRODUCT-007, EPIC-010, FEATURE-042 a FEATURE-045 |

## 5.3 Deltas Product candidatos

Antes do PLAN, Produto deve decidir se os itens abaixo exigem novas User
Stories dentro de Features existentes ou uma nova Feature de Platform:

- resolver o contexto operacional corrente com usuário, Tenant, Carteira
  padrão e permissões efetivas;
- apresentar navegação e comandos coerentes com permissões efetivas, mantendo
  o backend como autoridade;
- recuperar sessão expirada sem perder uma intenção de escrita e sem repetir
  o comando com uma nova chave de idempotência;
- oferecer estado operacional seguro para erro, vazio, carregamento,
  indisponibilidade e conflito concorrente.

Não reservar identificadores neste Discovery. A numeração deve ser obtida do
Registry somente no ato de materialização.

---

# 6. Escopo do Frontend MVP

## 6.1 P0 — núcleo demonstrável e operacional

- login, refresh, logout e proteção de rotas;
- resolução do contexto Tenant/Carteira e permissões;
- shell autenticado, navegação e dashboard operacional;
- lista, busca, detalhe, histórico, criação e atualização de Devedor;
- jornada Devedor → Simulação → Proposta → Aprovação;
- jornada Proposta → Contrato → Assinatura → Liberação;
- jornada Contrato → Empréstimo → Parcelas → Pagamento → Saldo/Memória;
- erros, loading, vazio, retry seguro, confirmação destrutiva e correlation ID.

## 6.2 P1 — operação diária e administração

- fila de cobrança, ações e promessas;
- agenda, compromissos, lembretes e comunicação;
- relatórios de resumo, vencimentos, pagamentos e fluxo;
- consulta de configurações financeiras;
- perfis e permissões conforme contratos disponíveis;
- jobs, notificações e templates para papéis administrativos.

## 6.3 Fora do escopo

- aplicativo mobile nativo, PWA offline e sincronização offline;
- multi-Carteira operacional, troca entre múltiplas Carteiras ou consolidação
  entre Tenants;
- API pública, integrações bancárias, PIX, boleto, billing ou marketplace;
- criação de motor de cálculo, arredondamentos ou projeções financeiras no
  navegador;
- edição arbitrária de permission codes sem catálogo governado;
- observabilidade externa, analytics de produto ou deploy nesta fase;
- alteração do backend durante este Discovery.

---

# 7. Arquitetura recomendada

```text
Navegador
  └─ HTTPS + cookie HttpOnly/Secure/SameSite
      └─ Next.js App Router (UI + BFF server-only)
          ├─ sessão, refresh e CSRF
          ├─ cliente OpenAPI tipado
          ├─ correlation ID e idempotência
          └─ FastAPI Backend MVP
              └─ PostgreSQL / Worker / Notification
```

## 7.1 Fronteiras

| Camada | Pode | Não pode |
|---|---|---|
| componentes visuais | formatar, coletar intenção, exibir estados | acessar token, decidir permissão, calcular finanças |
| módulos de feature | compor queries/comandos e mapear view models | inventar campos ou transições fora do OpenAPI |
| BFF server-only | manter sessão, anexar headers, traduzir erro técnico de transporte | substituir autorização ou regra do backend |
| cliente OpenAPI | garantir tipos de path/query/body/response | mascarar drift do schema com `any`/casts |
| backend | autenticar, autorizar, isolar e executar regra | delegar cálculo ou consistência ao frontend |

## 7.2 Sessão e segurança

- receber access/refresh tokens somente no servidor Next.js;
- persistir sessão em cookie cifrado e assinado, `HttpOnly`, `Secure` em
  produção, `SameSite=Lax` e prazo não superior ao refresh token;
- não usar `localStorage` ou `sessionStorage` para Bearer/refresh token;
- realizar refresh single-flight no servidor e encerrar a sessão quando o
  refresh falhar;
- validar `Origin`/CSRF em mutações recebidas pelo BFF;
- marcar módulos de sessão e cliente autenticado como `server-only`;
- nunca incluir token, segredo ou payload sensível em logs, HTML ou erros;
- tratar Route Handlers e Server Actions como superfícies públicas que também
  exigem autenticação e autorização contextual.

Uma biblioteca de sessão madura deve ser avaliada no PLAN. Se o adapter para o
IAM próprio não for suficiente, usar uma implementação pequena e auditável com
criptografia autenticada; nunca um cookie apenas codificado.

## 7.3 Tenant e Carteira

- `tenant_id` vem da sessão autenticada e não de input livre da interface;
- `carteira_id` deve vir do contrato de contexto operacional, não de constante,
  variável pública ou campo editável;
- IDs em URLs são navegação, não prova de autorização;
- `404` para recurso de outro Tenant/Carteira deve permanecer indistinguível de
  recurso inexistente;
- caches e query keys devem incluir o contexto operacional para impedir mistura
  acidental de dados.

## 7.4 Server e Client Components

- layouts e páginas são Server Components por padrão;
- Client Components ficam restritos a interação, estado transitório e APIs do
  navegador;
- leituras iniciais usam `fetch`/openapi-fetch no servidor e limites de
  Suspense por seção;
- mutações simples usam Server Actions ou Route Handlers server-only e fazem
  revalidação explícita;
- TanStack Query não entra no foundation por padrão. Pode ser introduzido em
  telas realmente interativas, com polling, paginação incremental ou cache
  cliente comprovadamente necessário.

Essa decisão reduz JavaScript no navegador e evita duas fontes de cache no
início. SWR e TanStack Query foram considerados; ambos perdem como dependência
global enquanto os recursos nativos do App Router atendem o P0.

---

# 8. Stack governada recomendada

| Área | Decisão | Gate |
|---|---|---|
| framework | Next.js App Router, versão estável fixada no PLAN | build de produção e suporte Node LTS confirmados |
| linguagem | TypeScript strict | `tsc --noEmit`, sem `any`/casts para contratos |
| React | versão suportada pelo Next.js escolhido | sem override de peer dependency |
| UI | shadcn/ui sobre primitives Radix | componentes pertencem ao repo e seguem tokens |
| estilo | Tailwind/CSS variables gerados pelo shadcn | nenhum valor de marca antes de tokens aprovados |
| API | openapi-typescript + openapi-fetch | geração reproduzível e `npm run api:check` no CI |
| formulários | React Hook Form + Zod somente onde a complexidade justificar | validação UX não substitui backend |
| testes rápidos | Vitest, Testing Library, user-event e MSW | estados e interação observados |
| E2E | Playwright contra frontend + backend + PostgreSQL reais | jornadas canônicas e screenshots |
| acessibilidade | axe-core + percurso manual de teclado | sem violações bloqueantes e foco visível |

Configurações TypeScript mínimas: `strict`, `noUncheckedIndexedAccess` e
`exactOptionalPropertyTypes`. A versão concreta de cada pacote deve ser fixada
no lockfile no início do PLAN, não neste Discovery.

shadcn/ui é escolhido como fonte de componentes editáveis, não como design
system pronto. Antes de telas complexas, devem existir tokens semânticos de cor,
tipografia, espaçamento, raio, elevação e motion, além de componentes base e
seus estados. Não há brand/tokens existentes para herdar; a identidade visual
continua uma decisão explícita de Produto/Design.

---

# 9. Estratégia de cliente OpenAPI

## 9.1 Fonte e geração

1. exportar deterministicamente `create_app().openapi()` do commit backend
   aprovado;
2. versionar um snapshot OpenAPI consumido pelo frontend;
3. gerar `paths`/`components` com openapi-typescript;
4. usar openapi-fetch sem wrappers que apaguem os tipos;
5. falhar CI quando snapshot, tipos gerados ou backend divergirem;
6. proibir `any`, interfaces manuais equivalentes a schemas e coerções para
   contornar drift.

## 9.2 Middleware server-only

O cliente deve concentrar:

- `Authorization: Bearer <access_token>`;
- geração/propagação de `X-Correlation-ID` por interação;
- `Idempotency-Key` estável para a mesma intenção de comando;
- timeout/abort de transporte;
- leitura do header de correlation ID da resposta;
- normalização para um `ApiProblem` que preserve `status`, `codigo`, `mensagem`
  e `correlationId`.

Não normalizar payloads financeiros para novos números. Valores monetários e
taxas devem permanecer na representação contratual até a camada de formatação.

---

# 10. Inventário dos contratos públicos

Na fotografia histórica anterior ao hardening, o OpenAPI possuía 105 operações
e 126 schemas. O estado corrente certificado e consumido pelo cliente possui
107 operações, 133 schemas e BearerAuth. Todas as operações recebem
`X-Correlation-ID` opcional e documentam o header na resposta.

| Tag | Operações | Uso no frontend |
|---|---:|---|
| operations | 1 | health técnico, não dashboard de negócio |
| auth | 4 | ativação, login, refresh e logout |
| iam | 12 | credencial, perfis e permissões |
| platform | 6 | provisionamento e manutenção de Tenant |
| credit | 7 | Devedores e histórico |
| commercial | 12 | simulações, propostas e decisões |
| contracts | 8 | contratos, histórico, assinatura e liberação |
| financial-engine | 11 | empréstimos, parcelas, pagamentos, saldo e quitação |
| daily-operations | 20 | cobrança, agenda, comunicação e relatórios |
| financial-configurations | 13 | modalidades, calendário e configurações |
| Automacao | 11 | jobs, templates e notificações |

## 10.1 Matriz de jornadas e contratos

| Jornada | Leituras principais | Comandos principais | RBAC/fonte de contexto | E2E frontend |
|---|---|---|---|---|
| F1 acesso | permissões efetivas; Tenant corrente; contexto ausente | `/auth/ativar`, `/auth/login`, `/auth/refresh`, `/auth/logout` | BearerAuth, Tenant do token; Carteira ainda sem bootstrap | login, refresh, logout, 401, 403 e cross-tenant |
| F2 cadastro → proposta | Devedor, histórico, simulação e propostas | criar/editar/ativar Devedor; simular; criar/enviar/aprovar proposta | `devedor.*`, `comercial.*`, Carteira na rota | Devedor com contato até proposta aprovada |
| F3 proposta → contrato | proposta, contrato lógico, contrato/histórico | formalizar, assinar e liberar | `comercial.proposta.integrar`, `contratos.contrato.*` | proposta aprovada até contrato liberado |
| F4 contrato → Motor | empréstimo, parcelas, saldo, memória e quitação | criar empréstimo/parcelas, pagar, quitar, renegociar | `motor.*`; backend é autoridade financeira | pagamento idempotente e valores reconsultados |
| F5 operação diária | cobrança, agenda, comunicação e relatórios | ação, promessa, compromisso, lembrete e comunicação | `cobranca.*`, `agenda.*`, `comunicacao.*`, `relatorios.*` | fatos do Motor exibidos sem recálculo |
| F6 agenda → automação | jobs, notificações e templates | cancelar/retry job, gerir template, conciliar | `automacao.*`, `notificacao.*` | job/notificação observáveis sem disparo arbitrário |

## 10.2 Erros e comportamento da interface

| HTTP | Interpretação | Comportamento |
|---|---|---|
| 400 | payload, query ou header inválido | preservar campos do formulário e orientar correção |
| 401 | sessão ausente/inválida/expirada | tentar um refresh single-flight; depois redirecionar para login |
| 403 | permissão ausente | bloquear comando, não sugerir troca de Tenant, manter evento correlacionável |
| 404 | inexistente ou fora do Tenant/Carteira | mensagem neutra, sem inferir existência em outro escopo |
| 409 | idempotência ou estado concorrente | não repetir com nova chave; reconsultar e mostrar estado atual |
| 422 | regra de domínio | exibir mensagem segura do backend; nunca “corrigir” por cálculo local |
| 5xx | erro técnico | exibir correlation ID e retry apenas quando seguro |

O handoff destaca 400/401/403/404/409/5xx, mas o runtime também usa 422 para
violação de regra. O PLAN deve incluir 422 explicitamente.

## 10.3 Idempotência

- uma chave representa uma intenção do usuário;
- retry de transporte ou refresh repete a mesma chave e o mesmo payload;
- editar payload ou iniciar novo comando gera nova chave;
- botões de submit ficam protegidos contra duplo clique, mas isso não substitui
  o header;
- 409 de idempotência não deve ser convertido em sucesso local;
- o estado final deve ser reconsultado quando a resposta for ambígua.

---

# 11. Lacunas contratuais e decisões requeridas

| ID local | Achado observado | Impacto | Recomendação antes do código |
|---|---|---|---|
| Lacuna 1 | login retorna `usuario_id` e `tenant_id`, mas não há operação de contexto corrente/Carteira padrão | frontend não consegue montar rotas de crédito com fonte confiável de `carteira_id` | contrato autenticado aditivo de contexto operacional |
| Lacuna 2 | permissões efetivas exigem consultar um `usuario_id` e a própria leitura é protegida por RBAC | usuário comum pode não conseguir descobrir sua navegação autorizada | incluir permissões efetivas no contexto corrente, acessível ao próprio principal |
| Lacuna 3 | não existe catálogo público governado de permission codes | gestão de perfil não pode montar seleção segura sem lista estática | endpoint de catálogo ou schema enum/versionado |
| Lacuna 4 | auth aparece como corpo genérico `Payload` no OpenAPI | cliente gerado não tipa login/refresh/logout | publicar os schemas específicos no contrato OpenAPI |
| Lacuna 5 | 29 mutações exigem idempotência no runtime, mas OpenAPI diz opcional | cliente gerado permite chamadas inválidas | marcar o header required no OpenAPI e testar drift |
| Lacuna 6 | request validation é traduzida para 400, mas FastAPI ainda inclui respostas automáticas 422 HTTPValidationError | tipos podem prometer envelope diferente do runtime | alinhar matriz 400/422 e `ErroResponse` no OpenAPI |
| Lacuna 7 | não há listagem/gestão completa de usuários | administração IAM no frontend seria parcial | restringir P1 ao contrato existente ou aprovar novo escopo Product/API |

Alternativas rejeitadas:

- fixar `carteira_id` em configuração pública: quebra isolamento e portabilidade;
- decodificar o access token no navegador para autorizar UI: expõe token e não
  representa o RBAC corrente consultado pelo backend;
- manter lista manual de permission codes no frontend: cria drift silencioso;
- tornar `Idempotency-Key` “sempre opcional” no wrapper: esconde divergência em
  vez de corrigi-la na fonte;
- começar telas com mocks antes desses contratos: produz uma UI que não pode
  ser conectada com segurança à API certificada.

---

# 12. Guardrails financeiros

O frontend pode:

- formatar valores recebidos para moeda, percentual e data;
- ordenar, filtrar e agrupar registros já calculados;
- coletar parâmetros de um comando aceito pelo OpenAPI;
- apresentar saldo, memória, quitação, fluxo e inadimplência retornados.

O frontend não pode:

- usar fórmulas de juros, atraso, amortização, multa ou quitação;
- somar parcelas para fabricar saldo ou “saldo previsto”;
- inferir inadimplência comparando datas localmente;
- gerar plano de parcelas ou memória de cálculo;
- decidir modalidade, taxa ou configuração vigente;
- transformar número de ponto flutuante em autoridade financeira;
- manter um estado otimista que contradiga transição confirmada pelo backend.

Testes de arquitetura devem procurar termos e padrões proibidos em módulos de
UI (`juros`, `multa`, `amortizacao`, `saldoCalculado`, bibliotecas financeiras e
fórmulas monetárias) e exigir justificativa para formatação legítima.

---

# 13. UX e design system mínimo

Não existe sistema visual no repositório. Antes da primeira tela de produto,
Produto/Design deve aprovar:

- paleta semântica, tipografia, densidade, espaçamento, raios e elevação;
- breakpoints e política de tabelas no mobile;
- foco, contraste, teclado, redução de movimento e leitura por screen reader;
- padrões de confirmação, feedback, toast, banner e erro de campo;
- navegação principal por papel e contexto;
- máscara de documento/contato sem alterar o valor contratual.

Cada página e componente deve cobrir e observar:

- loading/skeleton;
- vazio com ação permitida;
- erro recuperável e não recuperável;
- 401, 403, 404 e 409;
- overflow, conteúdo longo e tabelas densas;
- desktop e mobile;
- hover, focus-visible, disabled, pending e success;
- confirmação para transições irreversíveis ou sensíveis.

A primeira superfície recomendada é o dashboard operacional autenticado, não
uma landing page. Ele combina resumo da Carteira, vencimentos, agenda e fila de
cobrança, sempre consumindo respostas oficiais.

---

# 14. Plano de testes

## 14.1 Unidade

- formatação de datas, moeda, documento e estados;
- geração e retenção de correlation/idempotency IDs;
- mapeamento de `ApiProblem`;
- guards de navegação como ergonomia, nunca como segurança;
- nenhum teste que reproduza cálculo financeiro esperado.

## 14.2 Componente

- Testing Library com interação por papel/nome acessível;
- MSW usando exemplos compatíveis com schemas gerados;
- loading, vazio, erro, overflow e permissão ausente para cada componente de
  domínio;
- formulários preservam dados em 400/409/422;
- confirmação e bloqueio de duplo submit em comandos.

## 14.3 Contrato

- snapshot OpenAPI reproduzível a partir do backend aprovado;
- wrapper `npm run api:check` executado com geração programática e comparação de bytes canônicos LF;
- 107 operações e conjuntos obrigatórios por jornada sem drift não aprovado;
- BearerAuth em todas as operações protegidas;
- `X-Correlation-ID` em requests/responses;
- required real de idempotência refletido pelo schema;
- auth com request bodies específicos;
- envelopes de 400/401/403/404/409/422/500 compatíveis com runtime;
- testes negativos que falham quando um tipo manual ou `any` contorna o schema.

## 14.4 Integração frontend

- BFF injeta Bearer e nunca o serializa para o cliente;
- cookie tem flags esperadas e logout o remove;
- refresh concorrente ocorre uma vez;
- mutação após refresh preserva a mesma idempotency key;
- cache/query keys isolam Tenant/Carteira;
- correlation ID atravessa navegador → BFF → backend → mensagem de erro.

## 14.5 Playwright E2E

Executar contra Next.js, FastAPI e PostgreSQL reais, com dados determinísticos:

1. login, refresh e logout;
2. acesso negado por RBAC;
3. tentativa cross-tenant/carteira com 404 neutro;
4. Devedor com contato → Simulação → Proposta aprovada;
5. Proposta → Contrato assinado/liberado → Empréstimo/parcelas;
6. Pagamento repetido com a mesma chave sem efeito duplicado;
7. consulta de saldo/memória/quitação sem cálculo local;
8. cobrança → promessa → agenda → comunicação;
9. job/notificação administrativa conforme permissão;
10. falha 5xx mostrando correlation ID sem detalhe interno.

## 14.6 Visual e acessibilidade

- screenshots de referência em pelo menos 1440×900 e 390×844;
- comparação visual de login, dashboard, lista, detalhe, formulário e diálogo;
- axe-core sem violações críticas/sérias novas;
- caminho completo por teclado, foco visível e retorno de foco após diálogo;
- contraste calculado para todos os novos pares de cor;
- inspeção real de loading, vazio, erro e overflow, não apenas stories estáticas.

`product-design:audit`, browser verify e Playwright passam a ser aplicáveis
somente quando uma superfície executável existir. A falha conhecida do
`playwright-cli` 0.1.18 no Windows deve ser resolvida no spike técnico ou
contornada pelo runner Playwright do projeto, sem declarar verificação visual
antes de screenshots reais.

---

# 15. Ordem recomendada do futuro PLAN

## Fase A — materialização governada

- confirmar que não haverá Capability/EPIC técnico artificial;
- mapear Product/EPIC/Feature/User Story existente para cada fatia;
- emitir apenas deltas funcionais aprovados;
- decidir e registrar arquitetura web/sessão em ADR, se a governança exigir;
- reservar o próximo ID de PLAN e o range de IMPs no Registry.

## Fase B — hardening contratual bloqueante

- fechar as lacunas 1 a 6 com testes de contrato antes da correção;
- exportar snapshot OpenAPI determinístico;
- recertificar backend sem mudança de regra financeira.

## Fase C — foundation frontend

- scaffold Next.js/TypeScript;
- design tokens e componentes base;
- BFF server-only, sessão, CSRF, correlation e idempotência;
- cliente gerado e gates de lint, typecheck, unit, component e build.

## Fase D — fatias verticais

1. acesso e contexto operacional;
2. dashboard e Devedores;
3. Comercial e Contratos;
4. Motor e pagamentos;
5. operação diária e relatórios;
6. administração de configurações, IAM e automação.

Cada fatia termina com testes de unidade, componente, contrato e Playwright,
além de observação visual desktop/mobile. Não acumular E2E para o final.

## Fase E — certificação

- build de produção, lint e typecheck;
- suites frontend e backend verdes;
- jornadas canônicas com banco real;
- auditoria de segurança, acessibilidade e cálculo financeiro;
- revisão visual em duas larguras;
- revisão adversarial documental e técnica;
- relatório de prontidão sem caveat bloqueante oculto.

---

# 16. Riscos

| Risco | Severidade | Mitigação |
|---|---|---|
| ausência de bootstrap de Carteira/permissões | bloqueante | contrato corrente antes do scaffold |
| drift OpenAPI/runtime em auth e idempotência | bloqueante | testes e schema corrigido na fonte |
| token exposto ao navegador | crítica | BFF e módulos server-only |
| cálculo financeiro duplicado | crítica | guardrail arquitetural e E2E por valores do backend |
| UI ocultar ação e ser tratada como segurança | alta | backend sempre autoriza; testes 403 |
| cache misturar contexto | alta | chaves com contexto e sessão server-side |
| retry duplicar comando | alta | idempotency key por intenção |
| 404 revelar cross-tenant | alta | mensagem neutra e testes negativos |
| design system inexistente | média | foundation visual antes de telas complexas |
| excesso de Client Components/cache global | média | Server Components por padrão |
| IAM administrativo parcial | média | restringir escopo ou aprovar contratos adicionais |
| runner Playwright Windows instável | média | spike inicial e runner local do projeto |
| handoff/skill locais não rastreados | governança | decisão consciente antes de qualquer stage/PR |

---

# 17. Gates para iniciar implementação

Na passagem da fase documental para o pacote contratual, os gates abaixo
governaram a prontidao. Product, contexto, auth, idempotencia, matriz 400/422,
PLAN e backlog estao agora atendidos; o scaffold aguarda o judge formal:

- Product existente está mapeado e deltas aprovados/materializados;
- nenhum novo EPIC/Capability artificial foi criado;
- contrato de contexto corrente inclui Carteira e permissões;
- auth e idempotência estão fiéis no OpenAPI;
- matriz 400/422 está resolvida;
- ADR de arquitetura/sessão, se exigida, está aceita;
- PLAN e backlog de IMPs estão aprovados;
- tokens e componentes base têm decisão mínima;
- estratégia de ambiente E2E e dados determinísticos está pronta;
- Playwright executa no ambiente escolhido.

---

# 18. Recomendação de materialização Product

Recomenda-se materializar o frontend como cobertura de canal das hierarquias já
aprovadas, e não como nova Capability:

1. criar uma matriz oficial de cobertura `jornada frontend →
   Product/EPIC/Feature/User Story → endpoint → permissão → teste E2E`;
2. versionar as Features/User Stories existentes somente quando o critério de
   aceitação de interface representar o mesmo resultado de negócio;
3. emitir novos artefatos Product apenas para os deltas de contexto operacional
   e experiência autorizada que não estejam cobertos;
4. criar um PLAN transversal com fatias verticais e gates por jornada;
5. iniciar implementação apenas após as lacunas 1 a 6 estarem fechadas ou
   formalmente aceitos com solução equivalente segura.

Parecer final atualizado: **Discovery/SDD, hardening contratual, scaffold,
harness, foundation, cliente tipado, sessao/BFF, shell/contexto, Dashboard
IMP-290, Devedores IMP-291, Comercial IMP-292, Contratos IMP-293,
Motor/pagamentos IMP-294, Cobranca IMP-295 e Agenda/Comunicacao IMP-296
aprovados por evidencia observada; IMP-294 materializa
`/app/motor` com Emprestimo a partir de Contrato liberado, parcelas, pagamento,
saldo, memoria, quitacao e renegociacao sem calculo financeiro local.
O OpenAPI do Motor publica `Idempotency-Key` somente para 4 comandos; o frontend
nao inventa esse header na geracao de parcelas. IMP-295 materializa
`/app/cobranca` com fila, acao, promessa e apropriacao, 3 comandos com
`Idempotency-Key` certificado e sem calculo local de saldo ou cumprimento.
IMP-296 materializa `/app/agenda` com 12 operacoes oficiais, 10 comandos com
`Idempotency-Key` certificado, 2 consultas sem header inventado, historico de
comunicacao conforme OpenAPI atual e fronteira explicita para paginacao,
prioridade, responsavel e `data_referencia` ainda nao publicados. IMP-297
materializa `/app/relatorios` com 4 GETs oficiais, periodo explicito, RBAC
exato, ausencia de `Idempotency-Key` inventada, Carteira propria e nenhuma soma
financeira local. Exportacao, paginacao e filtros alem dos parametros
publicados permanecem fronteira futura. IMP-298 materializa
`/app/configuracoes-financeiras` com 13 operacoes oficiais de configuracoes,
vigente, modalidades, calendarios, transicoes e snapshots, RBAC exato, Carteira
propria, parametros opacos e ausencia de `Idempotency-Key` inventada. O
frontend nao calcula taxa, vigencia derivada, arredondamento, parcela ou saldo.
IMP-299 materializa `/app/iam`, restrito a Perfis, catalogo canonico e
atribuicoes/permissoes efetivas de Usuario conhecido. A lacuna 7 permanece:
nao ha listagem/ciclo de vida integral de Usuarios nem gestao de credenciais.
IMP-300 materializa `/app/automacao`, restrito a jobs, templates e
notificacoes, com 11 operacoes oficiais, RBAC exato, conciliacao idempotente
quando contratada e sem worker/provider disparado pelo frontend. IMP-301
certifica jornadas compostas P0/P1 em stack real Next.js/FastAPI/PostgreSQL,
sem mocks Playwright, cobrindo login, RBAC, 404 neutro, Devedor -> Proposta,
Proposta -> Contrato -> Emprestimo, pagamento idempotente, Motor, operacao
diaria, Relatorios, Configuracoes, IAM, Automacao e 5xx correlacionado.
IMP-302 certifica UI, seguranca e fronteiras com gate agregado sobre 50 PNGs
de evidencia, bundle publico, Client Components, Web Interface Guidelines e
ausencia de calculo financeiro paralelo. O IMP-303 recertificou a cadeia
completa localmente e publicou o relatorio final de prontidao.**

---

# 19. Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 3.2.0 | 2026-08-14 | Adendo final: IMP-303 recertificou localmente o Frontend MVP completo, preservou OpenAPI 107/133, publicou relatorio final e manteve CI remota como caveat nao observado. |
| 3.1.0 | 2026-08-14 | Adendo pos-certificacao UI/seguranca: IMP-302 valida 50 PNGs vigentes, bundle publico sem tokens, Client Components sem backend direto, Web Interface Guidelines e anti-calculo financeiro; IMP-303 sob judge. |
| 3.0.0 | 2026-08-14 | Adendo pos-jornadas compostas: IMP-301 observa P0/P1 em stack real Next.js/FastAPI/PostgreSQL com seed integrado, sem mocks Playwright, cobrindo login/RBAC/404/5xx, fluxos Devedor-Proposta-Contrato-Emprestimo, pagamento idempotente, operacao diaria, IAM e Automacao; IMP-302 sob judge. |
| 2.9.0 | 2026-08-14 | Adendo pos-Automacao: IMP-300 materializa `/app/automacao` com 11 operacoes oficiais de jobs/templates/notificacoes, RBAC exato, conciliacao com `Idempotency-Key`, sem worker/provider e IMP-301 sob judge. |
| 2.8.0 | 2026-08-14 | Adendo pos-IAM: IMP-299 materializa `/app/iam` com 11 operacoes oficiais, catalogo canonico, Usuario conhecido, RBAC exato, sete comandos com `Idempotency-Key` e sem credenciais/listagem de Usuarios; IMP-300 sob judge. |
| 2.7.0 | 2026-08-14 | Adendo pos-Configuracoes: IMP-298 materializa `/app/configuracoes-financeiras` com 13 operacoes oficiais, RBAC exato, Carteira propria, parametros opacos, correlation ID e sem `Idempotency-Key` inventada; IMP-299 sob judge. |
| 2.6.0 | 2026-08-14 | Adendo pos-Relatorios: IMP-297 materializa `/app/relatorios` com 4 GETs oficiais, periodo explicito, RBAC exato, ausencia de `Idempotency-Key` inventada e sem soma financeira local; IMP-298 sob judge. |
| 2.5.0 | 2026-08-14 | Adendo pos-Agenda/Comunicacao: IMP-296 materializa `/app/agenda` com 12 operacoes oficiais, RBAC exato, 10 comandos idempotentes certificados, consultas sem header inventado e historico conforme OpenAPI atual; IMP-297 sob judge. |
| 2.4.0 | 2026-08-14 | Adendo pós-Cobranca: IMP-295 materializa fila, acao, promessa e apropriacao sobre fatos oficiais, com RBAC exato, 3 comandos idempotentes certificados e sem saldo local; IMP-296 sob judge. |
| 2.3.0 | 2026-08-14 | Adendo pós-Motor: IMP-294 materializa Emprestimo, parcelas, pagamento, saldo, memoria, quitacao e renegociacao sem calculo financeiro local; IMP-295 sob judge. |
| 2.2.0 | 2026-08-14 | Adendo pós-Contratos: IMP-293 materializa formalizacao, historico, assinatura e liberacao logica sem Motor/pagamentos, preservando OpenAPI 107/133 e fronteira sem Idempotency-Key inventada; IMP-294 sob judge. |
| 2.1.0 | 2026-08-14 | Adendo pós-Comercial: jornada P0 Devedor ativo -> Simulacao -> Proposta materializada sem Contratos/Motor, sem calculo financeiro e sem Idempotency-Key inventada; IMP-293 sob judge. |
| 2.0.0 | 2026-08-14 | Adendo pós-Devedores: jornada P0 de Cadastro concluída em `/app/devedores`, consumindo somente contratos oficiais, Carteira própria e comandos idempotentes; IMP-292 sob judge. |
| 1.9.0 | 2026-08-14 | Adendo pós-Dashboard: primeira superfície operacional read-only concluída com RBAC exato, período canônico e fronteira financeira preservada; IMP-291 sob judge. |
| 1.8.0 | 2026-08-13 | Adendo pós-shell/contexto: login, bootstrap, contexto US-125, logout e shell server-first concluídos sem antecipar Dashboard ou jornada de negócio. |
| 1.7.0 | 2026-08-13 | Adendo pós-sessão/BFF: JWE server-only, auth mínimo, refresh process-local, CSRF e replay idempotente; jornadas continuam não iniciadas. |
| 1.6.0 | 2026-08-13 | Adendo pós-cliente: IMP-287 concluiu geração tipada e drift check sem antecipar BFF, sessão ou jornadas. |
| 1.5.0 | 2026-08-13 | Adendo pós-foundation: IMP-286 concluído com identidade funcional neutra, estados acessíveis e evidência browser, sem antecipar cliente, BFF ou jornadas. |
| 1.4.0 | 2026-08-13 | Adendo pós-harness: IMP-285 concluído sem antecipar design, cliente, BFF ou jornadas. |
| 1.3.0 | 2026-08-12 | Adendo pós-scaffold: IMP-284 concluído sem antecipar IMP-285 ou funcionalidades. |
| 1.2.0 | 2026-08-12 | Adendo pós-hardening: lacunas 1..6 fechadas; scaffold aguarda somente o judge formal. |
| 1.1.0 | 2026-08-12 | Registra a materialização Product/PLAN e mantém explícitos os bloqueios anteriores ao scaffold. |
| 1.0.0 | 2026-08-12 | Discovery/SDD inicial do Frontend MVP sobre Backend MVP certificado. |
