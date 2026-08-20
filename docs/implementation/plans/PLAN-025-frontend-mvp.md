# PLAN-025 - Frontend MVP Transversal

**ID:** PLAN-025

**Versao:** 3.1.0

**Status:** Frontend MVP concluido localmente; IMP-274..IMP-303 recertificados; CI remota nao observada

---

# 1. Objetivo e autoridade

Ordenar o Frontend MVP operacional sobre os contratos do Backend MVP
certificado, sem criar Capability ou EPIC de interface e sem mover
autenticacao, autorizacao, isolamento ou regra financeira para o cliente.

Autoridades observadas:

- `master` e `origin/master` em
  `e48cb72ee4f62428491e8b8c19a569611d83fca8`;
- handoff Backend/Frontend de 2026-08-12;
- Discovery/SDD do Frontend MVP;
- OpenAPI gerado por `create_app().openapi()` como fonte oficial;
- matriz `docs/governance/frontend-mvp-traceability-matrix.md`;
- Registry consultado antes da emissao: FEATURE-045, US-124 e PLAN-024 eram
  os ultimos IDs historicos.

Baseline historico: OpenAPI 3.1.0, API 0.1.0, 105 operacoes, 126 schemas e
BearerAuth. A worktree de hardening derivada de `e48cb72` esta recertificada
com 107 operacoes, 133 schemas e snapshot SHA-256
`8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1`. O
backend permanece autoridade de Tenant, Carteira, IAM/RBAC, idempotencia,
correlation ID, transicoes e fatos financeiros.

O hardening autorizado altera apenas contratos backend, testes e governanca de
IMP-276..IMP-283. Nao autoriza scaffold, dependencia frontend, lockfile,
configuracao Next.js ou qualquer IMP posterior.

---

# 2. Decisao Product

Nao sera criada Capability chamada Frontend.

- reutilizar PRODUCT-001..PRODUCT-009 e EPIC-001..EPIC-010 sem novo ID;
- reutilizar FEATURE-001..FEATURE-045;
- versionar somente FEATURE-011 e FEATURE-012 para 1.1.0;
- emitir US-125, contexto operacional corrente, sob FEATURE-012;
- emitir US-126, catalogo canonico de Permissoes, sob FEATURE-011;
- nao emitir Capability Frontend, EPIC tecnico ou nova Feature;
- tratar auth tipado, idempotencia e 400/422 como hardening de contratos, nao
  como historias de negocio;
- limitar IAM P1 aos contratos existentes e ao catalogo da US-126; gestao
  integral de Usuarios exige futuro Discovery/Product/API.

A hierarquia permanece Capability -> Bounded Context -> EPIC -> Feature ->
User Story. Frontend MVP e canal de entrega transversal.

---

# 3. Stack governada

| Area | Decisao | Gate |
|---|---|---|
| runtime | Node LTS suportado pelo Next.js escolhido | confirmar em fonte oficial e fixar no lockfile no IMP de scaffold |
| framework | Next.js App Router e React suportado | build de producao, sem peer override |
| linguagem | TypeScript `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` | typecheck sem `any`/cast para contornar OpenAPI |
| UI | shadcn/ui sobre Radix, componentes pertencentes ao repo | tokens e estados base antes de telas complexas |
| estilo | Tailwind/CSS variables conforme shadcn | tokens semanticos governados |
| API | `openapi-typescript` + `openapi-fetch` | snapshot reproduzivel, `npm run api:check`, drift bloqueante |
| formularios | React Hook Form + Zod apenas onde necessario | validacao UX nao substitui backend |
| testes | Vitest, Testing Library, user-event, MSW | estados e interacoes observados |
| E2E/visual | Playwright | Next.js + FastAPI + PostgreSQL reais e screenshots |
| acessibilidade | axe-core e teclado manual | zero violacao critica/seria nova e foco visivel |

SWR e TanStack Query nao entram na foundation. So podem ser adicionados por
necessidade observada de polling, paginacao incremental ou cache cliente
complexo. O IMP-284 instala somente a allowlist minima do scaffold; as demais
dependencias permanecem nos IMPs que as governam.

## 3.1 Decisoes do IMP-284 anteriores a instalacao

1. o workspace oficial e `frontend/`, isolado do pacote documental npm da raiz;
2. o package manager oficial e npm 11.17.0, com `package-lock.json` v3 proprio;
3. as versoes fixadas sao Node.js 24.19.0 LTS, Next.js 16.3.0, React/React DOM
   19.2.8, TypeScript 5.9.3, ESLint 9.39.5 e eslint-config-next 16.3.0;
4. `package.json` e `package-lock.json` da raiz nao se tornam workspace e nao
   recebem dependencias frontend;
5. IMP-284 nao cria variavel de ambiente; futuros segredos e URLs autenticadas
   serao server-only, sem token ou URL backend sensivel em `NEXT_PUBLIC_*`;
6. layouts e paginas sao Server Components por padrao; nao ha `use client` no
   placeholder do scaffold;
7. a fronteira futura do BFF fica documentada, mas sua implementacao permanece
   exclusiva do IMP-288;
8. shadcn/ui, tokens e componentes base permanecem exclusivos do IMP-286;
9. geracao e cliente OpenAPI permanecem exclusivos do IMP-287.

O IMP-284 usa CSS minimo neutro, sem Tailwind ou tokens antecipados. A
instalacao deterministica ocorre somente depois de um contrato documental RED
que exija este scaffold.

## 3.2 Decisoes do IMP-285 anteriores a instalacao

1. o harness e estritamente tecnico e separado em unit, component, contract e
   Playwright; nenhuma categoria aceita zero testes;
2. as versoes diretas sao Vitest 4.1.10, jsdom 30.0.1, Testing Library React
   16.3.2, DOM 10.4.1, jest-dom 7.0.1, user-event 14.6.4, MSW 2.15.0 e
   Playwright 1.62.1, todas exatas no lockfile de `frontend/`;
3. MSW executa somente em Node/jsdom, inicia com `onUnhandledRequest: error`,
   reseta handlers e encerra o servidor; nao ha service worker no browser;
4. o contrato Vitest le o snapshot OpenAPI oficial e observa 107 operacoes,
   133 schemas e os endpoints certificados, sem gerar cliente ou tipos manuais;
5. Playwright inicia `next build` + `next start` em porta fixa, usa Chromium do
   projeto e nunca reutiliza servidor existente;
6. o harness sobe PostgreSQL 16 descartavel e FastAPI reais, observa `/health`
   e encerra ambos; consumo frontend desse stack depende do cliente e BFF dos
   IMP-287/IMP-288;
7. CI fica configurada em matriz Linux/Windows, com browser instalado
   explicitamente e artifacts de falha; execucao remota exige commit/push;
8. IMP-286 (design), IMP-287 (cliente), IMP-288 (BFF) e jornadas permanecem
   proibidos ate seus gates proprios.

## 3.3 Decisoes do IMP-286 anteriores a instalacao

1. a foundation materializa uma identidade funcional neutra; paleta de marca,
   tipografia proprietaria e densidade final continuam pendentes de aprovacao
   Product/Design antes da primeira jornada;
2. as dependencias diretas sao Tailwind CSS 4.3.3, PostCSS 8.5.26,
   `@tailwindcss/postcss` 4.3.3, Radix Dialog 1.1.23, Radix Slot 1.3.3,
   CVA 0.7.1, clsx 2.1.1, tailwind-merge 3.6.0 e
   `@axe-core/playwright` 4.13.0, todas exatas; shadcn CLI 4.17.0 foi somente
   a referencia de materializacao e nao virou dependencia persistente;
3. `components.json`, CSS variables e os componentes pertencentes ao repo
   fixam `new-york`, RSC, TSX, aliases governados e base neutra, com temas
   claro e escuro;
4. a pagina `/` e um specimen tecnico temporario e continua Server Component;
   somente Dialog e sua demonstracao interativa abrem fronteira `use client`;
5. loading, empty, error, overflow, disabled, pending, success, sem Permissao e
   404 neutro sao apresentacoes explicitas; nenhum componente decide RBAC,
   recebe dado sensivel bruto ou calcula regra financeira;
6. axe roda em Chromium nos temas claro/escuro; teclado, foco, retorno de foco,
   reduced motion e overflow sao observados nos viewports 1440x900 e 390x844;
   os screenshots sao evidencia diagnostica, enquanto regressao visual final
   permanece no IMP-302;
7. cliente OpenAPI, BFF, auth, formularios de negocio e jornadas continuam
   proibidos ate os IMPs 287 e posteriores.

## 3.4 Decisoes do IMP-287 anteriores a instalacao

1. `openapi-typescript` 7.13.0 e a dependencia de desenvolvimento que gera
   tipos imutaveis e alfabetizados; `openapi-fetch` 0.17.0 e a unica dependencia
   runtime de transporte tipado, ambas com versoes exatas no lockfile;
2. `server-only` 0.0.1 e o marcador explicito recomendado pelo Next.js para
   impedir environment poisoning; o cliente manual importa esse marcador;
3. a entrada unica e local e o snapshot governado de SHA-256
   `8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1`;
   nenhuma URL ou API em execucao participa da geracao;
4. `api:generate` grava um unico arquivo versionado e `api:check` regenera em
   memoria e compara bytes canonicos LF, falhando por drift sem reescrever o artefato;
5. a factory do cliente recebe `baseUrl` explicitamente e nao executa request;
   ela nao le ambiente, cookie ou token e nao registra middleware;
6. Authorization, refresh, CSRF, correlation ID, ciclo de Idempotency-Key,
   `ApiProblem`, Route Handlers e Server Actions permanecem exclusivos do
   IMP-288;
7. os testes contratuais devem derivar auth, contexto, catalogo, idempotencia e
   erros do snapshot/tipos gerados, sem interfaces manuais, `any` ou casts.

## 3.5 Decisoes do IMP-288 anteriores a instalacao

1. `jose` 6.2.8 e a unica dependencia nova e sera fixada no lockfile; a sessao
   usa JWE `dir`/`A256GCM`, em vez de criptografia propria ou cookie apenas
   codificado;
2. o payload minimo contem versao, Usuario, Tenant, access/refresh tokens e
   suas expiracoes; Perfil, Permissoes, Carteira e dados pessoais nao entram na
   sessao e continuam sob autoridade do backend;
3. o cookie `__Host-emprestimo-session` e `HttpOnly`, `SameSite=Lax`, `Path=/`,
   `Secure` em producao e expira no maximo com o refresh; a chave JWE atual tem
   32 bytes, `kid` explicito e pode conviver com uma chave anterior durante
   rotacao, sempre sem default;
4. as variaveis server-only sao `FRONTEND_BACKEND_URL`, `FRONTEND_ORIGIN`,
   `FRONTEND_SESSION_KEY_ID`, `FRONTEND_SESSION_KEY` e o par anterior opcional;
   nenhuma usa `NEXT_PUBLIC_` e a URL precisa ser absoluta, sem credenciais;
5. somente `POST /api/auth/login` e `POST /api/auth/logout` sao superficies
   publicas do BFF nesta fase; refresh e interno, nao ha Server Action nem proxy
   catch-all;
6. toda mutacao exige `Origin` exatamente igual a `FRONTEND_ORIGIN` e o header
   nao simples `X-CSRF-Protection: 1`; `SameSite` e defesa adicional, nao
   substituta;
7. refresh single-flight e garantido por processo/isolate e sessao mediante
   Promise indexada pelo SHA-256 do refresh, limitada e removida em `finally`;
   nao existe alegacao de coordenacao global entre instancias;
8. o refresh backend corrente nao rotaciona o refresh token. Retry automatico
   ocorre uma unica vez apenas para GET/HEAD ou mutacao que ja possua
   `Idempotency-Key`; as 32 mutacoes protegidas sem chave nao sao repetidas
   cegamente;
9. o mesmo deadline, payload clonado, correlation ID e Idempotency-Key
   atravessam request, refresh e eventual replay. Falha/segundo 401 encerra a
   sessao, sem loop;
10. `ApiProblem` preserva `status`, `codigo`, `mensagem` e `correlationId`,
    neutraliza 404 e sanitiza timeout, 5xx e resposta malformada sem recalcular
    qualquer valor financeiro.

## 3.6 Decisoes do IMP-289 anteriores a implementacao

1. `/login` coleta somente e-mail e senha e envia para o Route Handler BFF
   existente; o BFF deriva `identificador_institucional` de configuracao
   server-only antes de chamar o backend com `AuthLoginRequest`; o destino
   posterior e fixo em `/app`, sem redirect arbitrario vindo do browser;
2. o shell estrutural e Server Component. Tenant, Carteira, Usuario, Perfil e
   Permissoes vem apenas de `GET /iam/contexto-atual`, sem IDs em query/body e
   sem consulta ao catalogo administrativo de Permissoes;
3. a leitura normal do layout e read-only: abre o JWE no servidor e consulta o
   contexto sem mutar cookie durante render. Um 401 direciona uma unica vez
   para `/session/recover`, cujo POST CSRF-protegido `/api/auth/bootstrap` pode
   executar refresh e persistir a sessao antes de retornar ao shell;
4. resposta 200 malformada falha como 502; 409 apresenta contexto incompleto e
   nunca escolhe Carteira alternativa; 404 permanece neutro. O endpoint de
   contexto certificado nao declara 403/404/422, portanto esses estados nao
   sao falsamente atribuidos ao seu E2E real;
5. a navegacao usa igualdade exata sobre Permissoes efetivas, mas nesta fase
   publica somente o destino existente `/app`. Rotas e links de Dashboard,
   Devedores e demais jornadas pertencem aos IMP-290+;
6. o browser chama apenas os tres Route Handlers same-origin de login, logout
   e bootstrap. Tokens, JWE, URL backend e contexto bruto nao entram em HTML,
   storage ou JavaScript cliente;
7. `/` e `/foundation` preservam o specimen tecnico da foundation; `/app` e a
   primeira superficie autenticada, sem Dashboard ou calculo financeiro;
8. a suite combina unit, component, contrato, BFF e Playwright real em desktop
   e mobile, com axe, teclado, screenshots, 401, 409, 404 e logout.

## 3.7 Decisoes do IMP-290 anteriores a implementacao

1. `/app` passa a ser o Dashboard operacional P0; nao existe rota paralela
   `/dashboard` nem link para jornada futura;
2. resumo e vencimentos exigem igualdade exata de
   `relatorios.operacionais.ler`; agenda exige `agenda.ler`; fila exige
   `cobranca.caso.ler`. Secao sem permissao nao chama o backend;
3. toda consulta injeta a Carteira padrao da US-125. `tenant_id` e
   `carteira_id` do browser sao ignorados, e resposta com identidade divergente
   falha fechada;
4. `data_referencia=YYYY-MM-DD` e estado canonico da URL. Na ausencia, o
   servidor escolhe a data civil de `America/Sao_Paulo`; a agenda usa os
   limites civis inclusivos com o offset IANA vigente na data selecionada,
   inclusive em transicoes historicas. Isso e politica de apresentacao MVP,
   nao regra financeira nem timezone persistido do Tenant;
5. o frontend exibe contagens, estados e valores exatamente como retornados.
   Nao soma, reclassifica vencimento, calcula percentual ou substitui o Motor;
6. as quatro leituras sao independentes e concorrentes. 400, 401, 403, 404,
   500, timeout e resposta malformada possuem estados seguros, correlation ID
   e falha parcial; 409/422 nao sao inventados para estes GETs;
7. o Dashboard e somente uma composicao read-only dos contratos existentes.
   Nao declara US-079/084/085 integralmente concluidas e nao substitui o modulo
   Relatorios do IMP-297 nem Agenda/Cobranca dos IMP-295/296;
8. loading, empty, error, permission denied e overflow sao observados em
   desktop/mobile, com axe, teclado e quatro capturas governadas.

## 3.8 Decisoes do IMP-297 anteriores a implementacao

1. `/app/relatorios` e a superficie server-first do modulo Relatorios; nao ha
   Route Handler publico, Server Action, exportacao local ou rota paralela;
2. as quatro consultas oficiais sao `resumo`, `vencimentos`, `pagamentos` e
   `fluxo`, todas com `relatorios.operacionais.ler` por igualdade exata;
3. resumo/vencimentos exigem `data_referencia`; pagamentos/fluxo exigem
   `inicio` e `fim`. Sem parametros explicitos, a tela pede periodo e nao
   inventa data automatica;
4. a Carteira enviada ao backend e sempre `context.carteira_padrao.id`; qualquer
   `tenant_id` ou `carteira_id` vindo do browser e ignorado;
5. o frontend apresenta valores, contagens, estados e arrays exatamente como
   retornados. Nao soma, arredonda, reclassifica, calcula inadimplencia ou
   substitui o Motor;
6. os quatro GETs de Relatorios nao publicam `Idempotency-Key` no OpenAPI atual.
   O BFF nao inventa o header;
7. 400, 401, 403, 404, 500, timeout e resposta 200 malformada possuem estado
   seguro e correlation ID; 404 permanece neutro e mensagens backend
   estruturadas sao sanitizadas;
8. loading, empty, denied, error, overflow, axe, teclado e evidencias visuais
   desktop/mobile foram observados. Exportacao/paginacao so entram se futuro
   contrato as publicar.

## 3.9 Decisoes do IMP-298 anteriores a implementacao

1. `/app/configuracoes-financeiras` e a superficie server-first de
   Configuracoes Financeiras; nao ha Route Handler publico, rota paralela,
   interpretacao local de Motor ou dependencia nova;
2. as 13 operacoes oficiais cobrem configuracoes, vigente, modalidades,
   calendarios, aprovar/programar/ativar/inativar e snapshots;
3. RBAC usa igualdade exata para `configuracoes_financeiras.configuracao.ler`,
   `.gerir`, `.aprovar`, `.ativar`, `modalidade.gerir`,
   `calendario.gerir` e `snapshot.capturar`;
4. a Carteira enviada ao backend e sempre `context.carteira_padrao.id`; qualquer
   `tenant_id` ou `carteira_id` vindo do browser e ignorado;
5. parametros, taxas e politica de arredondamento sao tratados como payloads
   opacos retornados/aceitos pelo backend. O frontend nao calcula taxa, vigencia
   derivada, parcela, saldo, arredondamento ou elegibilidade;
6. as operacoes de Configuracoes Financeiras publicam somente
   `X-Correlation-ID` no OpenAPI atual. O BFF nao inventa `Idempotency-Key`;
7. 400, 401, 403, 404, 409, 422, 500, timeout e resposta 2xx malformada possuem
   estado seguro e correlation ID; 404 permanece neutro e mensagens backend
   estruturadas sao sanitizadas;
8. loading, empty, denied, error, overflow, axe, teclado e evidencias visuais
   desktop/mobile foram observados. IAM e Automacao permanecem bloqueados para
   IMP-299/IMP-300.

## 3.10 Decisoes do IMP-299 anteriores a implementacao

1. `/app/iam` e a superficie server-first de IAM permitido; nao ha Route
   Handler publico, rota paralela, credenciais, listagem de Usuarios ou gestao
   integral;
2. as 11 operacoes oficiais cobrem Perfis, catalogo canonico e permissoes
   efetivas de Usuario conhecido;
3. RBAC usa igualdade exata para `perfil.ler` e `perfil.gerir`;
4. `GET /iam/permissoes` e a unica fonte do catalogo; o frontend nao mantem
   lista paralela de permission codes;
5. os sete comandos oficiais de Perfil/atribuicao usam `Idempotency-Key`
   certificado;
6. 400, 401, 403, 404, 409, 422, 500, timeout e resposta 2xx malformada possuem
   estado seguro e correlation ID; 404 permanece neutro.

---

# 4. Arquitetura e fronteiras

| Camada | Pode | Nao pode |
|---|---|---|
| componentes | apresentar dados, coletar intencao, renderizar estados | acessar token, decidir RBAC, calcular financas |
| jornadas | compor queries/comandos e view models tipados | inventar campo, Permissao ou transicao |
| BFF server-only | sessao, Bearer, correlation, idempotencia e transporte | substituir autorizacao, escopo ou regra backend |
| cliente OpenAPI | tipar path/query/body/response | ocultar drift com tipo manual, `any` ou cast |
| backend | autenticar, autorizar, isolar, validar e calcular | delegar consistencia ao frontend |

## 4.1 Sessao e BFF

- access/refresh tokens nunca chegam ao JavaScript do navegador;
- sessao usa cookie cifrado e assinado, `HttpOnly`, `Secure` em producao,
  `SameSite=Lax` e prazo limitado pelo refresh;
- sessao e cliente autenticado sao `server-only`;
- refresh concorrente e single-flight; falha encerra sessao sem loop;
- Route Handlers e Server Actions revalidam auth, Origin/CSRF, input e escopo;
- `tenant_id` vem do Principal; `carteira_id`, da US-125;
- URL nao prova autorizacao; caches/queries incluem Tenant/Carteira;
- a mesma intencao preserva `Idempotency-Key`, inclusive apos refresh;
- `X-Correlation-ID` atravessa navegador -> BFF -> backend -> erro;
- token, segredo, DSN, PII e payload sensivel nao entram em log, HTML ou erro.

## 4.2 Criterios React e composicao futura

`vercel-react-best-practices` orienta o PLAN, sem gerar codigo:

- Server Components por padrao e Client Components apenas para interacao;
- I/O independente iniciado cedo e aguardado em paralelo;
- Suspense por secao com fallback significativo;
- auth tambem em Server Actions e Route Handlers;
- nenhum estado mutavel compartilhado em modulo server;
- serializacao minima e tipada; evitar barrels e codigo pesado antecipado.

`vercel-composition-patterns` orienta a futura biblioteca:

- variantes explicitas, sem proliferacao de props booleanas;
- compound components quando partes compartilham estado/semantica;
- interface de Context desacoplada da implementacao;
- estado elevado ao provider coordenador;
- `children` para composicao ordinaria; render props so quando necessarias.

`web-design-guidelines` fica reservado ao gate sobre UI implementada.

## 4.3 Fronteira financeira

Frontend/BFF podem formatar, coletar parametros aceitos e apresentar respostas.
Nao podem calcular ou reinterpretar juros, mora, multa, amortizacao, saldo,
quitacao, renegociacao, calendario ou memoria. Divergencia percebida e exibida
com correlation ID; nunca corrigida localmente.

---

# 5. API

A matriz oficial inventaria as 107 operacoes recertificadas. O hardening
adicionou somente as duas operacoes IAM descritas nas lacunas 1 e 3, tipou os
bodies auth, corrigiu 29 headers de idempotencia para um total final de 30
obrigatorios e normalizou os schemas 400/422. Cada contrato nasceu em teste
vermelho e ficou verde na fonte backend antes de qualquer consumo frontend.

Superficies aditivas certificadas neste pacote:

- `GET /iam/contexto-atual` - contexto do proprio Principal, sem IDs livres;
- `GET /iam/permissoes` - catalogo canonico protegido por `perfil.ler`.

---

# 6. Decisoes formais das lacunas

## Lacuna 1 - contexto sem Carteira padrao

- **Decisao:** US-125 sob FEATURE-012; o cliente nao escolhe Carteira por
  constante/input livre.
- **Contrato desejado:** `GET /iam/contexto-atual`, BearerAuth, sem Permissao
  administrativa; `usuario`, `tenant`, `carteira_padrao`, `perfil`,
  `permissoes`; 409 `contexto_operacional_incompleto` sem Carteira; 401 invalido.
- **Teste antes da correcao:** path/schema ausentes falham; testar pertenencia,
  Usuario inativo, 401 e 409 sem fallback.
- **Pacote:** IMP-276/IMP-277, backend hardening separado.
- **Impacto:** bloqueia scaffold funcional e shell.

## Lacuna 2 - Permissoes inadequadas ao bootstrap proprio

- **Decisao:** US-125 inclui Permissoes efetivas; a US-038 continua consulta
  administrativa de outro Usuario conhecido.
- **Contrato desejado:** mesma rota; Perfil nulo gera lista vazia, nunca acesso
  implicito; sem Permissao administrativa extra.
- **Teste antes da correcao:** Usuario comum consulta somente a si; resposta
  acompanha Perfil vigente; shape nao aceita IDs forjados; zero vazamento.
- **Pacote:** IMP-276/IMP-277.
- **Impacto:** bloqueia navegacao RBAC confiavel.

## Lacuna 3 - catalogo de permission codes

- **Decisao:** US-126 sob FEATURE-011; backend publica catalogo canonico,
  frontend nao duplica lista.
- **Contrato desejado:** `GET /iam/permissoes`, BearerAuth + `perfil.ler`,
  `{ versao, itens: [{ codigo, descricao, grupo }] }`; 401/403.
- **Teste antes da correcao:** runtime/OpenAPI/catalogo IAM coincidem; cada
  codigo aceito aparece uma vez; desconhecido segue rejeitado.
- **Pacote:** IMP-278/IMP-279.
- **Impacto:** bloqueia IAM P1, nao as demais jornadas P0.

## Lacuna 4 - auth com body generico

- **Decisao:** corrigir contrato existente, sem Story nova.
- **Contrato desejado:** o backend login referencia `AuthLoginRequest` com
  `identificador_institucional`, `email`, `segredo`; o login publico do
  frontend coleta somente `email` e `segredo`, e o BFF injeta
  `identificador_institucional` a partir de configuracao server-only;
  refresh/logout referenciam `AuthRefreshRequest` com `refresh_token`; nenhum
  `Payload` generico.
- **Teste antes da correcao:** OpenAPI exige schemas especificos e runtime
  valido/invalido preserva envelope uniforme.
- **Pacote:** IMP-280.
- **Impacto:** bloqueia cliente gerado e login.

## Lacuna 5 - Idempotency-Key opcional no OpenAPI

- **Decisao:** OpenAPI reflete required runtime; wrapper nao torna opcional nem
  gera nova chave ao repetir a mesma intencao.
- **Contrato desejado:** 30 operacoes runtime no total com header
  `Idempotency-Key required: true` e limites coerentes; uma ja estava correta,
  29 declaracoes opcionais foram corrigidas e nenhuma operacao nova foi criada.
- **Teste antes da correcao:** comparar guards/dependencies runtime e OpenAPI;
  falhar por ausente/opcional/extra/limite; replay igual e divergente 2xx/409.
- **Pacote:** IMP-281.
- **Impacto:** bloqueia comandos e cliente gerado.

## Lacuna 6 - 400 versus 422

- **Decisao:** 400 para sintaxe/shape/query/header; 422 para invariante/regra de
  dominio; ambos com `ErroResponse` fiel ao runtime.
- **Contrato desejado:** declarar apenas respostas aplicaveis; remover 422
  automatico conflitante; 409 permanece conflito/idempotencia/estado.
- **Teste antes da correcao:** payload/query/header invalido = 400; regra de
  dominio = 422; schema/status OpenAPI = runtime.
- **Pacote:** IMP-282.
- **Impacto:** bloqueia tratamento tipado comum.

## Lacuna 7 - administracao integral de Usuarios

- **Decisao:** nao ampliar agora. P1 gere Perfis, catalogo, atribuicao/revogacao
  para Usuario conhecido e redefinicao de credencial; nao lista/convida/inativa/
  reativa/remove Usuarios.
- **Contrato desejado:** nenhum endpoint novo alem da US-126.
- **Teste antes da correcao:** UI nao promete modulo integral nem chama endpoint
  inexistente; superficies permitidas exigem RBAC da matriz.
- **Pacote:** eventual ampliacao exige novo Discovery/Product/API.
- **Impacto:** caveat P1, nao bloqueia P0.

IMP-276..IMP-283 foram executados como pacote backend separado: testes
vermelhos observados, correcoes minimas, suite focal verde e snapshot
deterministico. O scaffold permanece bloqueado ate nova execucao de
`fable:fable-judge` sobre este pacote.

---

# 7. Fases

## Fase A - governanca documental

US-125/126, FEATURE-011/012 v1.1, matriz, PLAN, backlog e suite documental.
Gate: Registry, docs e diff verdes; nenhuma implementacao.

## Fase B - hardening bloqueante

IMP-276..IMP-283: testes anteriores, contratos aditivos, auth, idempotencia,
400/422, snapshot e recertificacao. Gate: lacunas 1..6 fechadas na fonte,
backend verde e regra financeira intacta.

## Fase C - foundation frontend

IMP-284..IMP-289: scaffold, harness, design foundation, OpenAPI, sessao/BFF e
shell. Gate: build, typecheck, lint, unit/component/contract/BFF/Playwright.

## Fase D - P0

IMP-290..IMP-294: Dashboard, Devedores, Comercial, Contratos, Motor/pagamentos.
Cada fatia termina com unit, component, contract, Playwright e observacao visual.

## Fase E - P1

IMP-295..IMP-300: Cobranca, Agenda/Comunicacao, Relatorios, Configuracoes,
IAM permitido e Automacao. A lacuna 7 permanece visivel.

## Fase F - certificacao

IMP-301..IMP-303: jornadas compostas, regressao visual/acessibilidade,
anti-calculo, relatorio e revisao adversarial.

---

# 8. Estrategia de testes

- **Unidade:** formatacao; lifecycle correlation/idempotency; mapeamento de
  erro; guards ergonomicos; nenhuma formula financeira.
- **Componente:** papel/nome acessivel; MSW tipado; loading/empty/error/overflow/
  sem Permissao; preservar input em 400/409/422; double submit.
- **Contrato:** snapshot reproduzivel; `npm run api:check` com comparacao de bytes canonicos LF; 107
  operacoes; auth tipado; 30 headers required; 400/401/403/404/409/422/5xx;
  falha para tipo manual, `any` ou cast.
- **BFF:** token nao serializado; flags do cookie/logout; refresh single-flight;
  mesma idempotencia apos refresh; cache isolado; CSRF; correlation ponta a ponta.
- **Playwright:** sessao/contexto; 403; 404 cross-scope; Devedor -> Proposta;
  Proposta -> Contrato -> Emprestimo; pagamento repetido; consultas do Motor
  sem calculo local; operacao diaria; IAM/automacao permitidos; 5xx correlacionado.
- **Visual/a11y:** 1440x900 e 390x844; login/dashboard/lista/detalhe/form/dialog;
  axe; teclado/foco; contraste; reduced motion; estados reais e overflow.

O caveat `playwright-cli` 0.1.18 no Windows deve ser resolvido no spike ou pelo
runner Playwright do projeto. Sem screenshot real nao ha validacao visual.

---

# 9. Design foundation

Antes das telas: tokens de cor, tipo, espaco, dimensao, raio, elevacao, borda,
foco e motion; componentes base; variantes explicitas; padroes de lista,
detalhe, formulario e comando destrutivo; densidade desktop e mobile; loading,
empty, error, overflow, disabled, pending, success e sem Permissao; teclado,
labels, live region, foco e contraste; 404 neutro e dados sensiveis mascarados.

Identidade/tokens finais exigem aprovacao Product/Design, sem adiar
acessibilidade e estados funcionais.

---

# 10. Bloqueios, caveats e riscos

**Gate de implementacao satisfeito:** a verificacao focal `fable:fable-judge`
da correcao documental emitiu `VERIFIED` e autorizou o IMP-284. As lacunas
contratuais 1..6 estao fechadas e o snapshot foi materializado; a certificacao
completa e registrada no relatorio PLAN-026.

**Decisao apos execucao:** IMP-284, IMP-285 e IMP-286 estao concluidos. O workspace
`frontend/` possui lockfile proprio, quatro categorias independentes e GREEN
local em Windows para unit, component/MSW, contract e Playwright, alem de lint,
typecheck e build. A foundation neutra inclui tokens semanticos claro/escuro,
primitives locais, estados explicitos, axe, teclado e screenshots desktop/mobile.
A CI Linux/Windows esta configurada, mas sua execucao remota nao foi observada
porque esta sessao nao pode fazer commit ou push. IMP-287 gerou tipos
deterministicos e o IMP-288 adicionou sessao JWE, Route Handlers minimos e
transporte autenticado. O single-flight e estritamente process-local; o retry
automatico nao repete mutacao sem `Idempotency-Key`. O IMP-289 adicionou login,
bootstrap controlado, shell server-first e contexto proprio da US-125. O
IMP-290 foi materializado com leituras server-first. O IMP-291 adicionou a
jornada Devedores sob `/app/devedores`, com listagem, consulta por documento,
detalhe, historico e comandos idempotentes governados pelo backend. O IMP-292
adicionou Comercial a partir de Devedor ativo, usando exclusivamente as 12
operacoes oficiais de simulacao e Proposta Comercial, RBAC exato e parametros
opacos retornados pelo backend. O IMP-293 adicionou Contratos server-first em
`/app/contratos`, com formalizacao a partir de Proposta aprovada, listagem,
detalhe, historico, assinatura, liberacao logica para Motor, cancelamento e
encerramento sem criar Emprestimo, Parcela, Pagamento ou calculo financeiro.
As 8 operacoes oficiais de Contratos nao publicam `Idempotency-Key`; o frontend
nao inventa esse header. O IMP-294 adicionou Motor/pagamentos em `/app/motor`,
com Emprestimo a partir de Contrato liberado, parcelas, pagamento, saldo,
memoria, quitacao e renegociacao sem recalculo local. Os 4 comandos que
publicam `Idempotency-Key` reutilizam a chave governada; geracao de parcelas
nao inventa esse header. O IMP-295 adicionou Cobranca em `/app/cobranca`, com
fila, acao, promessa e apropriacao sobre fatos oficiais, RBAC exato e 3 comandos
idempotentes certificados; o frontend nao calcula saldo ou cumprimento de
promessa localmente. O IMP-296 adicionou Agenda/Comunicacao em `/app/agenda`,
com compromissos, lembretes, conciliacao legada do envio e historico de
comunicacao conforme os 12 endpoints oficiais. Os 10 POSTs usam
`Idempotency-Key` certificado; os 2 GETs nao inventam esse header. Paginacao,
prioridade/responsavel e data_referencia de Agenda permanecem fronteiras
Product nao publicadas no OpenAPI atual. O IMP-297 adicionou Relatorios em
`/app/relatorios` com as 4 leituras oficiais, periodo explicito e nenhuma soma
financeira local. O IMP-298 adicionou Configuracoes Financeiras em
`/app/configuracoes-financeiras`, com 13 operacoes oficiais, RBAC exato,
Carteira propria, parametros opacos, correlation ID e ausencia deliberada de
`Idempotency-Key` inventada. O IMP-299 adicionou IAM permitido em `/app/iam`,
com 11 operacoes oficiais, catalogo canonico, Usuario conhecido, RBAC exato,
sete comandos com `Idempotency-Key` e sem credenciais/listagem de Usuarios. O
IMP-300 adicionou Automacao em `/app/automacao`, com 11 operacoes oficiais
de jobs, templates e notificacoes, RBAC exato, `Idempotency-Key` apenas em
conciliacao e sem iniciar worker, provider, auditoria ou observabilidade. O
IMP-301 certificou jornadas compostas P0/P1 em stack real
Next.js/FastAPI/PostgreSQL, sem mocks Playwright, cobrindo login, RBAC, 404
neutro, Devedor -> Proposta, Proposta -> Contrato -> Emprestimo, pagamento
idempotente, Motor, Cobranca -> Agenda -> Comunicacao, Relatorios,
Configuracoes, IAM, Automacao e 5xx correlacionado. O IMP-302 certificou UI,
seguranca e fronteiras com gate agregado de 50 PNGs, bundle publico, Client
Components, Web Interface Guidelines e anti-calculo financeiro. O IMP-303
recertificou a cadeia completa localmente, publicou o relatorio final de
prontidao e preservou a CI remota como caveat nao observado.

FastAPI/PostgreSQL reais tiveram readiness observada em processo/container
isolados. Desde o IMP-288, o frontend consome o backend exclusivamente por
fronteiras server-only/BFF; desde o IMP-290, `/app` e o Dashboard operacional.
O specimen tecnico permanece isolado em `/foundation` e nao e tela de negocio.

**Caveats nao bloqueantes para P0:** lacuna 7; identidade visual pendente; 29
avisos historicos do PLAN-024 sem aumento; `.claude/skills/playwright-cli/`
preexistente fora de escopo; multi-Carteira/troca de Tenant fora do MVP.

Riscos continuos: token no browser, cache cruzado, double submit, drift
OpenAPI, Permissao stale, 404 revelador, bundle/waterfalls, overflow e motor
financeiro paralelo. Gates e E2E devem tornar todos observaveis.

---

# 11. Gates finais

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate` com 0 erros e sem avisos novos;
- `npm run docs:test`;
- `node scripts/tests/test-plan-025-contracts.js`;
- `npm run quality:migrations` em banco descartavel;
- `git diff --check`;
- typecheck, lint, unit, component, contract, BFF integration e build frontend;
- Playwright contra Next.js + FastAPI + PostgreSQL;
- regressao visual desktop/mobile, axe e teclado;
- Registry e IMP-274..IMP-303 consistentes;
- matriz sem lacunas; 404 neutro; nenhum token no browser;
- nenhum calculo financeiro fora do Motor;
- bloqueios/riscos explicitados no relatorio;
- `fable:fable-judge` antes da implementacao e da declaracao final.

O PLAN so passa a execucao apos veredito adversarial e aprovacao do pacote de
hardening. Gates documentais nao substituem gates futuros.

---

# 12. Historico de versoes

| Versao | Data | Descricao |
|---|---|---|
| 3.1.0 | 2026-08-14 | IMP-303 concluido com recertificacao final local do Frontend MVP, scope encadeado 401/66/335/3/404, OpenAPI 107/133 preservado, relatorio final publicado e CI remota declarada como nao observada. |
| 3.0.0 | 2026-08-14 | IMP-302 concluido com certificacao agregada de UI, seguranca e fronteiras: 50 PNGs vigentes, bundle publico sem tokens, Client Components sem backend direto, Web Interface Guidelines e scanner anti-calculo financeiro; IMP-303 sob judge. |
| 2.9.0 | 2026-08-14 | IMP-301 concluido com jornadas compostas P0/P1 em stack real Next.js/FastAPI/PostgreSQL, sem mocks Playwright, cobrindo login, RBAC, 404 neutro, fluxos Devedor-Proposta-Contrato-Emprestimo, pagamento idempotente, Motor, operacao diaria, IAM, Automacao e 5xx correlacionado; IMP-302 sob judge. |
| 2.8.0 | 2026-08-14 | IMP-300 concluido com Automacao server-first, 11 operacoes oficiais, jobs/templates/notificacoes, RBAC exato, unica `Idempotency-Key` em conciliacao, evidencias desktop/mobile e IMP-301 sob judge. |
| 2.7.0 | 2026-08-14 | IMP-299 concluido com IAM permitido server-first, 11 operacoes oficiais, catalogo canonico, Usuario conhecido, RBAC exato, sete comandos com `Idempotency-Key` e evidencias desktop/mobile; IMP-300 sob judge. |
| 2.6.0 | 2026-08-14 | IMP-298 concluido com Configuracoes Financeiras server-first, 13 operacoes oficiais, RBAC exato, parametros opacos, correlation ID, ausencia de `Idempotency-Key` inventada e evidencias desktop/mobile; IMP-299 sob judge. |
| 2.5.0 | 2026-08-14 | IMP-297 concluido com Relatorios server-first, 4 GETs oficiais, periodo explicito, ausencia de `Idempotency-Key` inventada, nenhuma soma financeira local e evidencias desktop/mobile; IMP-298 sob judge. |
| 2.4.0 | 2026-08-14 | IMP-296 concluido com Agenda/Comunicacao server-first, 12 operacoes oficiais, 10 comandos idempotentes certificados, 2 consultas sem Idempotency-Key, historico conforme OpenAPI atual e evidencias desktop/mobile; IMP-297 sob judge. |
| 2.3.0 | 2026-08-14 | IMP-295 concluido com Cobranca server-first, 4 operacoes oficiais, 3 comandos idempotentes certificados, fila/acao/promessa/apropriacao sem saldo local e evidencias desktop/mobile; IMP-296 sob judge. |
| 2.2.0 | 2026-08-14 | IMP-294 concluido com Motor/pagamentos server-first, 11 operacoes oficiais, 4 comandos idempotentes certificados, ausencia de calculo financeiro local e evidencias desktop/mobile; IMP-295 sob judge. |
| 2.1.0 | 2026-08-14 | IMP-293 concluido com Contratos server-first, 8 operacoes oficiais, RBAC exato, historico, liberacao logica sem Motor/pagamentos, ausencia deliberada de Idempotency-Key inventada e evidencias desktop/mobile; IMP-294 sob judge. |
| 2.0.0 | 2026-08-14 | IMP-292 concluido com Comercial server-first a partir de Devedor ativo, 12 operacoes oficiais, RBAC exato, ausencia deliberada de Idempotency-Key inventada, parametros opacos e evidencias desktop/mobile; IMP-293 sob judge. |
| 1.9.0 | 2026-08-14 | IMP-291 concluido com Devedores server-first, Carteira propria, RBAC exato, comandos idempotentes, 404 neutro, 400/409/422/5xx correlacionados e evidencias desktop/mobile; IMP-292 sob judge. |
| 1.8.0 | 2026-08-14 | IMP-290 concluido com Dashboard read-only, RBAC exato, Carteira propria, periodo canonico, estados independentes e evidencias desktop/mobile; IMP-291 sob judge. |
| 1.7.0 | 2026-08-13 | IMP-289 concluido com login, contexto proprio server-side, bootstrap de refresh, shell e navegacao estrita; IMP-290 sob judge. |
| 1.6.0 | 2026-08-13 | IMP-288 concluido com sessao JWE, BFF auth minimo, refresh process-local, CSRF, correlation e replay idempotente; IMP-289 sob judge. |
| 1.5.0 | 2026-08-13 | IMP-287 concluido com tipos OpenAPI deterministicos, factory server-only inerte e drift check; IMP-288 sob judge. |
| 1.4.0 | 2026-08-13 | IMP-286 concluido com foundation funcional neutra, componentes locais, estados acessiveis, axe e evidencias desktop/mobile; IMP-287 sob judge. |
| 1.3.0 | 2026-08-13 | IMP-285 concluido com harness separado, smokes executaveis, CI Linux/Windows configurada e IMP-286 sob judge. |
| 1.2.0 | 2026-08-12 | Gate adversarial satisfeito; decisoes registradas antes da instalacao e IMP-284 concluido com gates verdes. |
| 1.1.0 | 2026-08-12 | Hardening IMP-276..IMP-283 executado; OpenAPI 107/133 congelado e scaffold mantido sob gate adversarial. |
| 1.0.0 | 2026-08-12 | Plano transversal com Product reutilizado, sete lacunas decididas e hardening separado. |
