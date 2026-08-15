# Frontend MVP

Workspace isolado do canal web, materializado pelo IMP-284, equipado com o
harness tecnico do IMP-285, a design foundation neutra do IMP-286, o cliente
OpenAPI tipado do IMP-287, a sessao/BFF do IMP-288, o shell autenticado do
IMP-289, o Dashboard operacional read-only do IMP-290, Devedores do IMP-291,
Comercial do IMP-292, Contratos do IMP-293, Motor/pagamentos do IMP-294,
Cobranca do IMP-295 e Agenda/Comunicacao do IMP-296. O
pacote documental da raiz permanece independente e conserva seu proprio
lockfile.

## Toolchain fixada

- Node.js 24.19.0 LTS;
- npm 11.17.0;
- Next.js 16.3.0 com App Router;
- React e React DOM 19.2.8;
- TypeScript 5.9.3 em modo estrito.

## Fronteiras

- Server Components por padrao; Client Components entram apenas quando uma
  interacao ou API do navegador exigir.
- o IMP-288 cria sessao JWE e transporte autenticado server-only; o IMP-289
  acrescenta login, logout, bootstrap de contexto e shell; o IMP-290 usa
  `/app` para apresentar apenas leituras oficiais do Dashboard; o IMP-291 cria
  Devedores; o IMP-292 cria Comercial a partir de Devedor ativo; o IMP-293 cria
  Contratos a partir de Proposta aprovada.
- Motor, pagamentos, Cobranca e Agenda/Comunicacao foram materializados nos
  IMP-294..296; Relatorios e demais jornadas permanecem no IMP-297+.
- shadcn/ui e tokens semanticos materializados no IMP-286 pertencem ao repo;
  identidade de marca e tokens finais continuam sujeitos a Product/Design.
- o cliente OpenAPI e gerado exclusivamente do snapshot certificado; sua
  factory recebe transporte explicitamente e os tokens permanecem cifrados no
  cookie server-only.
- regras financeiras, autorizacao, Tenant e Carteira continuam exclusivamente
  sob autoridade do backend.
- nenhuma variavel sensivel usa `NEXT_PUBLIC_`; os placeholders governados
  ficam em `.env.example`, sem credenciais reais.
- scripts de instalacao transitivos nao sao executados: o comando governado usa
  `--ignore-scripts`, e o build validado nao depende deles.
- a foundation permanece disponivel em `/` e `/foundation`; nao e uma jornada
  de produto nem autoriza regra financeira.

## Design foundation

- Tailwind CSS 4 em modo CSS-first e CSS variables semanticas;
- primitives shadcn-owned: Button, Card, Alert, Input, Label, Skeleton e Dialog;
- estados explicitos de loading, empty, error, success, sem permissao e 404
  neutro, mais pending, disabled e overflow;
- Server Components por padrao; somente Dialog e seu exemplo interativo usam
  `use client`;
- tema claro/escuro, foco visivel, forced colors e reduced motion;
- axe no Chromium real e screenshots diagnosticas em 1440x900 e 390x844.

O showcase nao e tela de produto nem identidade final. O Dashboard governado
vive separadamente em `/app`; a foundation continua em `/foundation`.

## Harness de testes

- `test:unit`: Vitest em Node para funcoes tecnicas puras;
- `test:component`: Testing Library/user-event em jsdom, com MSW Node
  fail-closed e lifecycle limpo entre testes;
- `test:contract`: leitura estrutural do snapshot OpenAPI certificado, sem
  cliente ou modelo manual paralelo;
- `test:e2e`: Playwright Chromium contra o build de producao Next em porta fixa,
  sem reutilizar servidor existente;
- `test:a11y`: axe em tema claro/escuro, desktop/mobile;
- `test:visual`: screenshots diagnosticas da foundation, sem reivindicar a
  regressao visual final reservada ao IMP-302;
- `test:infrastructure`: PostgreSQL 16 descartavel e FastAPI reais, observados
  por `/health` e sempre encerrados pelo runner;
- `test:harness`: agrega as quatro categorias.

O browser e instalado explicitamente com `npm run test:e2e:install`. O harness
prova readiness isolada de FastAPI/PostgreSQL; a integracao do frontend com esse
stack permanece bloqueada ate o IMP-288, quando sessao e BFF existirem.

## Cliente OpenAPI

- `openapi-typescript` gera `src/lib/api/openapi.generated.ts` somente do
  snapshot governado 107/133;
- `npm run api:generate` grava o artefato versionado;
- `npm run api:check` regenera em memoria, canonicaliza EOL para LF e falha se os bytes canonicos divergirem;
- `openapi-fetch` recebe `paths` gerados sem wrapper que apague tipos;
- `client.server.ts` importa `server-only` e apenas cria uma factory por
  `baseUrl`, sem request, token, cookie, header, env ou middleware;
- Authorization, refresh, correlation, idempotencia operacional e erros BFF
  sao adicionados pelo IMP-288 sem alterar o artefato gerado.

## Sessao e BFF server-only

- `jose` 6.2.8 produz JWE `dir`/`A256GCM`; access/refresh tokens nunca entram em
  JSON, HTML, log ou Client Component;
- configure `FRONTEND_BACKEND_URL`, `FRONTEND_ORIGIN`,
  `FRONTEND_SESSION_KEY_ID` e `FRONTEND_SESSION_KEY` somente no servidor;
- a chave e base64url de exatamente 32 bytes. O par `PREVIOUS` e opcional e
  serve apenas para rotacao por `kid`;
- cookie `__Host-emprestimo-session`: HttpOnly, SameSite=Lax, Path=/, Secure em
  producao, prioridade alta e prazo nunca superior ao refresh;
- `POST /api/auth/login` e `POST /api/auth/logout` exigem Origin exata e
  `X-CSRF-Protection: 1`; nao existe endpoint publico de refresh ou proxy
  catch-all;
- single-flight vale por processo/isolate Next e sessao. Nao e uma garantia
  global entre instancias;
- apos 401, o transporte repete uma unica vez apenas GET/HEAD ou mutacao que ja
  possua `Idempotency-Key`, preservando request, chave e correlation ID.

## Shell autenticado e contexto operacional

- `/login` envia somente o `AuthLoginRequest` certificado ao BFF same-origin;
- `/app` e Server Component e apresenta Usuario, Tenant, Carteira e Perfil
  retornados pelo `GET /iam/contexto-atual` do proprio Principal;
- a leitura normal do shell nao muta cookie. Um 401 passa uma unica vez por
  `/session/recover` e pelo POST CSRF-protegido `/api/auth/bootstrap`;
- a navegacao usa igualdade exata de Permissao e publica `/app`, Devedores,
  Comercial, Contratos, Motor e Cobranca somente quando autorizados;
- 409 nao cria Carteira alternativa, 404 e neutro e 5xx exibe correlation ID
  seguro;
- `test:session` executa login, contexto, refresh, logout, axe, teclado e
  screenshots em 1440x900 e 390x844 contra Next e fixture backend reais.

## Dashboard operacional

- `/app` compoe, sem recalculo, as respostas oficiais de resumo,
  vencimentos, agenda e fila de cobranca;
- as secoes sao consultadas somente com igualdade exata das permissoes
  `relatorios.operacionais.ler`, `agenda.ler` e `cobranca.caso.ler`;
- `carteira_id` vem exclusivamente do contexto US-125. Query strings do
  browser nunca selecionam Tenant ou Carteira;
- `data_referencia=YYYY-MM-DD` e canonica na URL. A ausencia usa a data civil
  de `America/Sao_Paulo`; a agenda usa a janela inclusiva desse dia em
  UTC-03:00;
- 400, 401, 403, 404, 5xx, timeout, resposta malformada e falha parcial sao
  estados seguros e correlacionados. O 404 permanece neutro;
- as APIs atuais nao paginam agenda, vencimentos ou fila. O Dashboard limita
  apenas a apresentacao/overflow e nao mascara essa divida contratual;
- `test:dashboard` cobre RBAC, contratos, estados independentes, axe, teclado,
  desktop/mobile e ausencia de tokens ou chamadas browser-backend.

## Comercial

- Comercial inicia em `/app/devedores/[devedorId]/comercial`; o Devedor ativo
  e a Carteira padrao vem do contexto/server-side, nunca de query string;
- usa somente as 12 operacoes oficiais de simulacao e Proposta Comercial;
- permissoes sao comparadas por igualdade exata:
  `comercial.simulacao.criar`, `comercial.proposta.criar`,
  `comercial.proposta.ler`, `comercial.proposta.decidir` e
  `comercial.proposta.integrar`;
- parametros retornados pelo backend sao tratados como JSON opaco. O frontend
  nao calcula regra financeira, nao cria Contrato e nao aciona Motor;
- o OpenAPI Comercial atual nao publica `Idempotency-Key`; por isso o frontend
  nao inventa o header e registra essa fronteira como caveat contratual;
- o OpenAPI Comercial tambem nao possui trilha detalhada de decisoes nem filtro
  por periodo; a UI mostra apenas contador/estado e filtros contratados;
- 400, 401, 403, 404, 409, 422, 5xx, timeout e resposta malformada sao estados
  seguros e correlacionados; 404 permanece neutro;
- `test:comercial` cobre jornada Devedor ativo -> simulacao -> Proposta ->
  decisao, RBAC, estados, axe, teclado, desktop/mobile e ausencia de tokens ou
  chamadas browser-backend.

## Motor e pagamentos

- Motor inicia em `/app/motor` e tambem pode receber `contrato_id` de Contratos
  liberados para criar Emprestimo;
- usa somente as 11 operacoes oficiais de Emprestimo, parcelas, pagamento,
  saldo, memoria, quitacao e renegociacao;
- permissoes sao comparadas por igualdade exata:
  `motor.emprestimo.criar`, `motor.emprestimo.ler`, `motor.parcela.gerar`,
  `motor.parcela.ler`, `motor.pagamento.registrar`, `motor.saldo.ler`,
  `motor.memoria.ler`, `motor.quitacao.executar` e
  `motor.renegociacao.criar`;
- valores financeiros, memoria e parametros sao exibidos como retornados pelo
  backend. O frontend nao soma, arredonda, reclassifica nem calcula regra
  financeira;
- `Idempotency-Key` e enviada somente nos 4 comandos certificados pelo OpenAPI:
  criar Emprestimo, registrar pagamento, executar quitacao e registrar
  renegociacao. Gerar parcelas nao inventa esse header;
- 400, 401, 403, 404, 409, 422, 5xx, timeout e resposta malformada sao estados
  seguros e correlacionados; 404 permanece neutro;
- `test:motor` cobre listagem, detalhe, comandos, RBAC, estados, axe,
  teclado, desktop/mobile e ausencia de tokens ou chamadas browser-backend.

## Cobranca

- Cobranca inicia em `/app/cobranca` e opera fila, acao, promessa e apropriacao
  a partir dos fatos oficiais do backend;
- usa somente as 4 operacoes oficiais de Cobranca;
- permissoes sao comparadas por igualdade exata:
  `cobranca.caso.ler`, `cobranca.acao.registrar`,
  `cobranca.promessa.registrar` e `cobranca.promessa.apropriar`;
- `Idempotency-Key` nao e enviado na fila e e enviado somente nos 3 comandos
  certificados: acao, promessa e apropriacao;
- valores pendentes, promessa e apropriacao sao exibidos como retornados pelo
  backend. O frontend nao calcula saldo, cumprimento ou apropriacao financeira;
- 400, 401, 403, 404, 409, 422, 5xx, timeout e resposta malformada sao estados
  seguros e correlacionados; 404 permanece neutro;
- `test:cobranca` cobre fila, comandos, RBAC, estados, axe, teclado,
  desktop/mobile e ausencia de tokens ou chamadas browser-backend.

## Agenda e Comunicacao

- Agenda e Comunicacao iniciam em `/app/agenda` e operam consulta de periodo,
  compromissos, lembretes, conciliacao legada de notificacao e historico de
  comunicacao a partir dos fatos oficiais do backend;
- usam somente as 12 operacoes oficiais de Agenda/Comunicacao;
- permissoes sao comparadas por igualdade exata:
  `agenda.ler`, `agenda.compromisso.gerir`, `agenda.lembrete.gerir`,
  `notificacao.conciliar`, `comunicacao.registrar` e `comunicacao.ler`;
- `Idempotency-Key` nao e enviado nas consultas de Agenda e Comunicacao e e
  enviado somente nos 10 comandos certificados pelo OpenAPI;
- prioridade, responsavel, `data_referencia` e paginacao de historico nao
  estao publicados no contrato atual. A UI mostra a fronteira em vez de
  inventar campos;
- 400, 401, 403, 404, 409, 422, 5xx, timeout e resposta malformada sao estados
  seguros e correlacionados; 404 permanece neutro;
- `test:agenda` cobre consulta, comandos, RBAC, estados, axe, teclado,
  desktop/mobile e ausencia de tokens ou chamadas browser-backend.

## Comandos

```powershell
npm ci --ignore-scripts
npm run api:check
npm run lint
npm run typecheck
npm run build
npm run test:unit
npm run test:component
npm run test:contract
npm run test:bff
npm run test:session
npm run test:session:a11y
npm run test:dashboard
npm run test:devedores
npm run test:comercial
npm run test:contratos
npm run test:motor
npm run test:cobranca
npm run test:agenda
npm run test:infrastructure
npm run test:e2e:install
npm run test:a11y
npm run test:visual
npm run test:harness
```
