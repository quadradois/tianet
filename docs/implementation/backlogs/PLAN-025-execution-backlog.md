# PLAN-025-EXEC - Backlog do Frontend MVP Transversal

**ID:** PLAN-025-EXEC

**Versao:** 3.1.0

**Status:** Frontend MVP concluido localmente; IMP-274..IMP-303 recertificados; CI remota nao observada

---

# 1. Contexto

Ordem executavel do PLAN-025. A numeracao continua apos IMP-273, ultimo item do
PLAN-020. IMP-274..IMP-303 preservam teste antes de correcao, hardening backend
separado e fatias frontend completas. O pacote IMP-276..IMP-283 foi executado
em ordem; gates adversariais autorizaram o scaffold e o harness. IMP-284
materializou somente o scaffold, IMP-285 somente a infraestrutura executavel
de testes, IMP-286 somente a foundation funcional neutra e IMP-287 somente a
tipagem OpenAPI e o cliente server-only inerte. IMP-288 materializou somente
sessao JWE, BFF auth minimo e transporte autenticado; IMP-289..IMP-301
materializaram shell, Dashboard e jornadas operacionais ate Configuracoes
Financeiras, IAM permitido, Automacao, certificacao composta em stack real e
certificacao agregada de UI/seguranca/fronteiras. IMP-303 recertificou a cadeia
localmente e publicou o relatorio final de prontidao.

---

# 2. P0 - Governanca documental

### IMP-274 - Proteger contratos documentais do PLAN-025

- **Objetivo:** validar arquivos, Registry, matriz, faixa de IMPs, gates e
  proibicoes de Capability/EPIC/Feature artificiais.
- **Componentes afetados:** `scripts/tests/`, `package.json`, docs PLAN-025.
- **Dependencias:** PLAN-025.
- **Criterios de conclusao:** suite detecta arquivo/ID ausente, faixa
  IMP-274..IMP-303 incompleta, dependencia futura, lacuna sem decisao, suite
  fora de `docs:test` e gate removido; a evidencia temporal preserva a
  fotografia historica anterior ao hardening, com 105 operacoes e os dois
  endpoints IAM apenas desejados; o estado final apos IMP-283, com 107
  operacoes e os dois endpoints IAM certificados, e exigido pela suite
  recertificada.
- **Suite minima:** `node scripts/tests/test-plan-025-contracts.js`.
- **Status:** Concluido.

### IMP-275 - Materializar Product e matriz oficial

- **Objetivo:** publicar US-125/US-126, versionar FEATURE-011/012 e fechar a
  matriz jornada -> Product -> API -> RBAC -> Playwright.
- **Componentes afetados:** `docs/product/`, Registry e Discovery/SDD.
- **Dependencias:** IMP-274.
- **Criterios de conclusao:** nenhum novo Product/EPIC/Feature; IDs consistentes;
  a materializacao registra a fotografia historica anterior ao hardening, com
  105 operacoes e os dois endpoints IAM apenas desejados; o estado final apos
  IMP-283, com 107 operacoes e os dois endpoints IAM certificados, preserva a
  transicao RED -> GREEN; `docs:validate`, `docs:test` e `git diff --check`
  verdes.
- **Suite minima:** `npm run docs:validate && npm run docs:test`.
- **Status:** Concluido.

---

# 3. P1 - Hardening contratual backend bloqueante

### IMP-276 - Escrever contratos vermelhos de contexto corrente

- **Objetivo:** reproduzir lacunas 1/2 antes da correcao.
- **Componentes afetados:** `tests/integration/api/test_frontend_mvp_contracts.py`.
- **Dependencias:** IMP-275.
- **Criterios de conclusao:** testes exigem rota, schema, Carteira padrao,
  Permissoes proprias, 401, 409, Perfil vazio e isolamento; falham no baseline.
- **Suite minima:** `pytest -k imp_276` no contrato focal IAM/OpenAPI.
- **Status:** Concluido.

### IMP-277 - Implementar contrato de contexto corrente

- **Objetivo:** entregar US-125 de forma aditiva no backend.
- **Componentes afetados:** IAM application/presentation/OpenAPI e testes.
- **Dependencias:** IMP-276.
- **Criterios de conclusao:** `GET /iam/contexto-atual` retorna o proprio
  contexto tipado, sem Permissao admin, sem IDs livres e sem vazamento.
- **Suite minima:** contratos do IMP-276 e suites IAM/API.
- **Status:** Concluido.

### IMP-278 - Escrever contratos vermelhos do catalogo IAM

- **Objetivo:** reproduzir a lacuna 3 antes da correcao.
- **Componentes afetados:** `tests/integration/api/test_frontend_mvp_contracts.py`.
- **Dependencias:** IMP-275.
- **Criterios de conclusao:** testes exigem catalogo versionado, unicidade,
  igualdade com runtime, `perfil.ler`, 401/403 e rejeicao de desconhecido.
- **Suite minima:** `pytest -k imp_278` no contrato focal IAM/OpenAPI.
- **Status:** Concluido.

### IMP-279 - Implementar consulta do catalogo IAM

- **Objetivo:** entregar US-126 sem permitir configuracao de codigo por Tenant.
- **Componentes afetados:** catalogo IAM, presentation/OpenAPI e testes.
- **Dependencias:** IMP-278.
- **Criterios de conclusao:** `GET /iam/permissoes` e tipado, canonico,
  versionado, protegido por `perfil.ler` e passa os contratos anteriores.
- **Suite minima:** contratos do IMP-278 e suites IAM/API.
- **Status:** Concluido.

### IMP-280 - Tipar request bodies de autenticacao

- **Objetivo:** fechar a lacuna 4 sem alterar semantica de autenticacao.
- **Componentes afetados:** auth routes/schemas/OpenAPI e testes.
- **Dependencias:** IMP-275.
- **Criterios de conclusao:** teste vermelho antecede correcao; login usa
  `AuthLoginRequest`, refresh/logout usam `AuthRefreshRequest`; nenhum body
  `Payload`; respostas de recusa continuam uniformes.
- **Suite minima:** testes auth runtime e OpenAPI.
- **Status:** Concluido.

### IMP-281 - Alinhar required de idempotencia

- **Objetivo:** fechar a lacuna 5 nas 29 operacoes observadas.
- **Componentes afetados:** dependencies/headers, OpenAPI e testes de replay.
- **Dependencias:** IMP-275.
- **Criterios de conclusao:** teste vermelho compara runtime/OpenAPI; header e
  required apenas onde exigido; limites coincidem; replay igual e divergente
  preservam resultado e 409.
- **Suite minima:** inventario OpenAPI e suites de idempotencia.
- **Status:** Concluido.

### IMP-282 - Normalizar matriz 400/422

- **Objetivo:** fechar a lacuna 6 com status e schemas fieis ao runtime.
- **Componentes afetados:** handlers/OpenAPI e testes negativos de API.
- **Dependencias:** IMP-275.
- **Criterios de conclusao:** teste vermelho antecede correcao; shape/query/
  header invalido responde 400; regra de dominio, 422; OpenAPI declara
  `ErroResponse`; 409 nao muda.
- **Suite minima:** matriz de erros de todas as superficies.
- **Status:** Concluido.

### IMP-283 - Recertificar hardening e congelar OpenAPI

- **Objetivo:** publicar snapshot deterministico que desbloqueia o frontend.
- **Componentes afetados:** backend, testes de contrato e snapshot OpenAPI.
- **Dependencias:** IMP-277, IMP-279, IMP-280, IMP-281 e IMP-282.
- **Criterios de conclusao:** lacunas 1..6 verdes; backend completo verde;
  107 operacoes/133 schemas inventariados; sem regra financeira alterada;
  revisao adversarial interna concluida e judge formal mantido antes do IMP-284.
- **Suite minima:** pytest, Ruff, Black, mypy, migrations e contratos OpenAPI.
- **Status:** Concluido.

---

# 4. P2 - Foundation frontend

### IMP-284 - Criar scaffold governado

- **Objetivo:** iniciar Next.js App Router/TypeScript somente apos hardening.
- **Componentes afetados:** `frontend/`, `.gitignore`, workflow de qualidade,
  ADR-001 e governanca de execucao do PLAN-025.
- **Dependencias:** IMP-283.
- **Criterios de conclusao:** Node 24.19.0 LTS, npm 11.17.0, Next.js 16.3.0,
  React 19.2.8 e TypeScript 5.9.3 fixados; App Router server-first; instalacao
  pelo lockfile e lint/typecheck/build locais verdes; job de CI configurado,
  com execucao remota dependente de commit/push fora desta sessao; nenhuma regra, endpoint,
  BFF, design foundation, cliente OpenAPI ou harness antecipado.
- **Suite minima:** `npm ci --ignore-scripts`, lint, typecheck, build de producao e contrato
  documental com mutacoes negativas.
- **Status:** Concluido.

### IMP-285 - Instalar harness de testes

- **Objetivo:** tornar unit, component, contract e Playwright executaveis antes
  das telas.
- **Componentes afetados:** configuracoes Vitest/Testing Library/MSW/Playwright.
- **Dependencias:** IMP-284.
- **Criterios de conclusao:** categorias unit/component/contract/E2E descobrem
  pelo menos um teste e passam isoladas/agregadas; runner local Windows
  validado; Next sobe por `build` + `start` em porta fixa sem reuso; MSW falha
  para request inesperada e limpa lifecycle; snapshot 107/133 e `/health` sao
  observados sem cliente manual; PostgreSQL 16 descartavel e FastAPI reais sobem,
  ficam ready e sao encerrados deterministicamente; artifacts Playwright sao
  governados. O consumo frontend do stack permanece bloqueado ate IMP-287/IMP-288.
- **Suite minima:** Vitest unit, Testing Library/user-event + MSW, contrato do
  snapshot, Playwright Chromium, lint, typecheck, build e gate de escopo.
- **Status:** Concluido.

### IMP-286 - Materializar design foundation

- **Objetivo:** criar tokens, primitives shadcn e estados base acessiveis.
- **Componentes afetados:** CSS variables/Tailwind, `components.json`,
  primitives locais, estados da foundation e specimen tecnico `/`.
- **Dependencias:** IMP-284 e IMP-285.
- **Criterios de conclusao:** tokens semanticos claro/escuro; variantes
  explicitas; loading/empty/error/overflow/disabled/pending/success/sem
  Permissao e 404 neutro; specimen Server Component; somente Dialog client;
  desktop/mobile, teclado, retorno de foco, contraste e reduced motion
  observados; nenhuma tela de negocio, cliente, BFF ou regra financeira.
- **Suite minima:** component 7/7, axe 4/4, Playwright funcional 12/12,
  screenshots 1440x900 e 390x844, lint, typecheck, build e gate encadeado.
- **Status:** Concluido.

### IMP-287 - Gerar cliente OpenAPI e gate de drift

- **Objetivo:** transformar o snapshot aprovado na unica tipagem HTTP.
- **Componentes afetados:** snapshot protegido, gerador, tipos versionados,
  cliente server-only inerte e CI.
- **Dependencias:** IMP-283, IMP-284 e IMP-285.
- **Criterios de conclusao:** geracao reproduzivel/check; auth/contexto/
  idempotencia/erros tipados; nenhum `any`, cast ou modelo manual paralelo.
- **Suite minima:** `api:check`, contrato 3/3, typecheck, build e gate encadeado.
- **Status:** Concluido.

### IMP-288 - Implementar sessao e BFF server-only

- **Objetivo:** proteger tokens e padronizar comandos/erros.
- **Componentes afetados:** sessao JWE, Route Handlers de login/logout,
  transporte autenticado e configuracao server-only; nenhuma Server Action.
- **Dependencias:** IMP-287.
- **Criterios de conclusao:** cookie seguro observado; refresh single-flight
  por processo/sessao; logout local fail-safe; CSRF/Origin; Bearer oculto;
  idempotencia/correlation preservadas; mutacao sem chave nao sofre replay.
- **Suite minima:** Vitest BFF 49/49 com concorrencia, JWE, auth, transporte,
  erros e negativos; typecheck/lint/build e gates encadeados.
- **Status:** Concluido.

### IMP-289 - Implementar shell e contexto operacional

- **Objetivo:** montar navegacao, layout e guards ergonomicos pela US-125.
- **Componentes afetados:** auth pages, shell, navigation e error boundaries.
- **Dependencias:** IMP-286, IMP-287 e IMP-288.
- **Criterios de conclusao:** login/contexto/logout observados; Tenant/Carteira
  vindos do proprio Principal; navegacao por igualdade exata de Permissao e
  limitada a rotas existentes; 401/409/5xx do contexto, 403/404 genericos,
  loading/error, responsive e ausencia de token no browser.
- **Suite minima:** unit 3/3, component 10/10, contract 4/4, BFF 59/59 e
  Playwright sessao/contexto 16/16, alem de axe, teclado e screenshots.
- **Status:** Concluido.

---

# 5. P3 - Fatias P0

### IMP-290 - Implementar dashboard operacional

- **Objetivo:** compor resumo, vencimentos, agenda e cobranca oficiais.
- **Componentes afetados:** dashboard e modulos de leitura.
- **Dependencias:** IMP-289.
- **Criterios de conclusao:** quatro GETs tipados e read-only; Carteira propria;
  RBAC exato por secao; `data_referencia` canonica; loading/empty/error/denied/
  overflow, falha parcial e correlation; nenhum calculo financeiro.
- **Suite minima:** observados unit 8/8, component 15/15, BFF 65/65, contract
  7/7, Playwright Dashboard 12/12 desktop/mobile, foundation 12/12 e sessao
  16/16; axe, teclado, imagens, scope e mutacoes documentais.
- **Status:** Concluido.

### IMP-291 - Implementar Devedores

- **Objetivo:** listar, cadastrar, detalhar, editar e transicionar Devedor.
- **Componentes afetados:** modulo Cadastro.
- **Dependencias:** IMP-289.
- **Criterios de conclusao:** contato, historico, idempotencia, 400/409/422,
  403/404 neutro, teclado e mobile observados.
- **Suite minima:** observados unit 12/12, component 19/19, BFF 71/71,
  contract 11/11, Playwright Devedores 10/10, sessao 16/16, dashboard 12/12,
  lint, typecheck, build, scope e mutacoes documentais.
- **Status:** Concluido.

### IMP-292 - Implementar Comercial

- **Objetivo:** operar Simulacao e Proposta a partir de Devedor ativo.
- **Componentes afetados:** modulo Comercial.
- **Dependencias:** IMP-291.
- **Criterios de conclusao:** criar/consultar/decidir/integrar conforme estados;
  valores somente exibidos; comandos nao inventam Idempotency-Key ausente no
  OpenAPI Comercial; erros completos.
- **Suite minima:** observados unit 4/4, component Comercial+Devedores 9/9,
  BFF 7/7, contract 3/3, Playwright Comercial 10/10, typecheck, build parcial
  via Playwright, scope e mutacoes documentais.
- **Status:** Concluido.

### IMP-293 - Implementar Contratos

- **Objetivo:** formalizar, assinar, liberar, cancelar e encerrar Contrato.
- **Componentes afetados:** modulo Contratos.
- **Dependencias:** IMP-292.
- **Criterios de conclusao:** estados/acoes vem do backend; ausencia deliberada
  de `Idempotency-Key` inventada porque o OpenAPI de Contratos nao publica esse
  header; RBAC; historico; 404 neutro; zero recalculo da Proposta.
- **Suite minima:** observados unit 21/21, component 28/28, BFF 85/85,
  contract 18/18, Playwright Contratos 8/8, lint, typecheck, build, scope e
  mutacoes documentais.
- **Status:** Concluido.

### IMP-294 - Implementar Motor e pagamentos

- **Objetivo:** operar Emprestimo, parcelas, pagamento e consultas financeiras.
- **Componentes afetados:** modulo Motor Financeiro.
- **Dependencias:** IMP-293.
- **Criterios de conclusao:** respostas apresentadas sem formula local; pagamento
  replayavel; saldo/memoria/quitacao/renegociacao; precision/overflow visuais.
- **Suite minima:** unit anti-calculo, component, contract e Playwright Motor.
- **Evidencia observada:** RED documental 136/137 por `motor.server.ts` ausente;
  GREEN com unit Motor 5/5, component 4/4, BFF 6/6, contract 3/3,
  Playwright Motor 8/8, lint, typecheck, build, scope e mutacoes documentais.
- **Status:** Concluido.

---

# 6. P4 - Fatias P1

### IMP-295 - Implementar Cobranca

- **Objetivo:** operar fila, acao e promessa sobre fatos oficiais.
- **Componentes afetados:** modulo Cobranca.
- **Dependencias:** IMP-294.
- **Criterios de conclusao:** filtro/empty/overflow; acao/promessa/apropriacao;
  idempotencia, RBAC, 404 neutro e nenhum saldo local.
- **Suite minima:** unit, component, contract e Playwright Cobranca.
- **Evidencia observada:** RED documental 137/138 por `cobranca.server.ts`
  ausente; GREEN com unit Cobranca+navigation 9/9, component 3/3, BFF 5/5,
  contract 3/3, Playwright Cobranca 8/8, lint, typecheck, build, scope e
  mutacoes documentais.
- **Status:** Concluido.

### IMP-296 - Implementar Agenda e Comunicacao

- **Objetivo:** operar compromissos, lembretes e historico de contato.
- **Componentes afetados:** modulos Agenda e Comunicacao.
- **Dependencias:** IMP-295.
- **Criterios de conclusao:** periodo, transicoes, conciliacao governada,
  historico de contato conforme OpenAPI atual, datas/teclado/mobile e
  isolamento completos. Paginacao/prioridade/responsavel permanecem fronteira
  Product nao publicada no contrato OpenAPI certificado.
- **Suite minima:** unit, component, contract e Playwright Agenda/Comunicacao.
- **Evidencia observada:** RED documental 144/145 por
  `agenda-comunicacao.server.ts` ausente; GREEN com unit Agenda+navigation
  10/10, component 3/3, BFF 5/5, contract 3/3, Playwright Agenda/Comunicacao
  8/8, lint, typecheck, build, scope e mutacoes documentais.
- **Status:** Concluido.

### IMP-297 - Implementar Relatorios

- **Objetivo:** apresentar resumo, vencimentos, pagamentos e fluxo oficiais.
- **Componentes afetados:** modulo Relatorios.
- **Dependencias:** IMP-296.
- **Criterios de conclusao:** periodos/overflow/exportacao apenas se contratada;
  sem recomputar agregados; 400/403/404/500 observados; 422 nao e inventado.
- **Suite minima:** unit anti-calculo, component, contract e Playwright Relatorios.
- **Evidencia observada:** RED documental 157/158 por
  `relatorios.server.ts` ausente; GREEN com unit Relatorios+navigation 12/12,
  component 4/4, BFF 6/6, contract 3/3, Playwright Relatorios 8/8,
  contrato documental 160/160, lint, typecheck, build, scope e mutacoes documentais. O OpenAPI de Relatorios
  publica 400/401/403/404/500; 422 nao e inventado nesta fatia.
- **Status:** Concluido.

### IMP-298 - Implementar Configuracoes Financeiras

- **Objetivo:** gerir modalidades, calendarios, vigencias e snapshots.
- **Componentes afetados:** modulo Configuracoes Financeiras.
- **Dependencias:** IMP-294 e IMP-297.
- **Criterios de conclusao:** parametros enviados conforme schema; estados e
  aprovacoes backend; nenhuma interpretacao/calculo; RBAC e auditoria visiveis.
- **Suite minima:** unit anti-calculo, component, contract e Playwright Configuracoes.
- **Evidencia observada:** RED documental 160/161 por
  `configuracoes-financeiras.server.ts` ausente; GREEN com unit
  Configuracoes+navigation 12/12, component 5/5, BFF 5/5, contract 3/3,
  Playwright Configuracoes 8/8, contrato documental e mutacoes especificas,
  lint, typecheck, build, scope e docs. O OpenAPI de Configuracoes publica 13
  operacoes sem `Idempotency-Key`; o frontend preserva correlation ID e nao
  inventa o header.
- **Status:** Concluido.

### IMP-299 - Implementar IAM permitido

- **Objetivo:** gerir Perfis/catalogo/atribuicoes sem prometer gestao integral.
- **Componentes afetados:** modulo IAM administrativo.
- **Dependencias:** IMP-279 e IMP-289.
- **Criterios de conclusao:** catalogo canonico; Usuario conhecido; RBAC;
  limite da Lacuna 7 explicito; nenhum endpoint/lista inventado.
- **Suite minima:** unit, component, contract e Playwright IAM.
- **Evidencia observada:** `/app/iam` server-first com 11 operacoes oficiais,
  catalogo canonico, Perfis, permissoes efetivas de Usuario conhecido, sete
  comandos com `Idempotency-Key`, RBAC exato, 404 neutro, correlation ID,
  unit/navigation 13/13, component IAM 4/4, BFF 6/6, contract 4/4,
  Playwright IAM 8/8, `test-plan` 169/169 e evidencias desktop/mobile.
  Nao ha credenciais, lista de Usuarios, backend, Product,
  Registry, OpenAPI, dependencia ou lockfile novo.
- **Status:** Concluido.

### IMP-300 - Implementar Automacao

- **Objetivo:** operar jobs, templates, notificacoes e conciliacao autorizados.
- **Componentes afetados:** modulo Automacao.
- **Dependencias:** IMP-296 e IMP-299.
- **Criterios de conclusao:** retry/cancel/conciliar conforme estado e RBAC;
  resultado desconhecido seguro; sem envio arbitrario ou calculo financeiro.
- **Suite minima:** unit, component, contract e Playwright Automacao.
- **Suite observada:** unit Automacao + navegacao 14/14; component 3/3; BFF
  7/7; contract 3/3 com `api:check` e `typecheck`; Playwright Automacao 8/8;
  lint e typecheck verdes; scope 359 protegidos, inventario 390 e 0
  divergencia.
- **Status:** Concluido.

---

# 7. P5 - Certificacao

### IMP-301 - Certificar jornadas compostas

- **Objetivo:** provar P0/P1 ponta a ponta com stack real.
- **Componentes afetados:** Playwright, fixtures e ambiente integrado.
- **Dependencias:** IMP-290..IMP-300.
- **Criterios de conclusao:** sessoes, 403, 404 neutro, jornadas Product,
  idempotencia, correlation e recuperacao de erro passam sem ordem acidental.
- **Suite minima:** observado Playwright jornadas compostas 6/6 com
  Next.js/FastAPI/PostgreSQL reais, seed integrado, ausencia de mocks
  Playwright, login/refresh/logout, RBAC, 404 neutro, 5xx correlacionado e
  pagamento idempotente comprovado no backend.
- **Status:** Concluido.

### IMP-302 - Certificar UI, seguranca e fronteiras

- **Objetivo:** auditar visual/a11y/performance e provar ausencia de vazamentos
  e Motor paralelo.
- **Componentes afetados:** UI real, reports Playwright/axe e bundle analysis.
- **Dependencias:** IMP-301.
- **Criterios de conclusao:** screenshots 1440x900/390x844; axe/teclado/foco;
  web-design-guidelines; tokens/overflow; token ausente do browser; testes e
  busca anti-calculo; criterios Vercel observados.
- **Suite minima:** observado `npm run test:certification`, build, lint,
  typecheck, contrato documental, scope encadeado, docs e diff-check; 50 PNGs,
  bundle publico, Client Components, Web Interface Guidelines e anti-calculo
  verificados.
- **Status:** Concluido.

### IMP-303 - Recertificar e publicar relatorio final

- **Objetivo:** executar todos os gates e obter revisao adversarial.
- **Componentes afetados:** repo completo, docs e relatorio de prontidao.
- **Dependencias:** IMP-302.
- **Criterios de conclusao:** gates abaixo verdes; matriz/Registry consistentes;
  riscos e caveats honestos; zero bloqueio oculto; veredito fable-judge apto.
- **Suite minima:** gates completos do PLAN-025.
- **Status:** Concluido.

---

# 8. Gates

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate` com 0 erros e sem avisos novos;
- `npm run docs:test`;
- `node scripts/tests/test-plan-025-contracts.js`;
- `npm run quality:migrations` em banco descartavel;
- `git diff --check`;
- gates frontend de typecheck/lint/unit/component/contract/BFF/build;
- Playwright, visual, axe e teclado;
- nenhum calculo financeiro fora do Motor e nenhum token no browser;
- `fable:fable-judge` antes de iniciar implementacao.

---

# 9. Historico de versoes

| Versao | Data | Descricao |
|---|---|---|
| 3.1.0 | 2026-08-14 | IMP-303 concluido com recertificacao final local do Frontend MVP, relatorio de prontidao publicado, scope encadeado 401/66/335/3/404 e CI remota mantida como caveat nao observado. |
| 3.0.0 | 2026-08-14 | IMP-302 concluido com certificacao agregada de UI, seguranca e fronteiras: 50 PNGs vigentes, bundle publico sem tokens, Client Components sem backend direto, Web Interface Guidelines e scanner anti-calculo financeiro; IMP-303 permanece planejado. |
| 2.9.0 | 2026-08-14 | IMP-301 concluido com jornadas compostas P0/P1 em stack real Next.js/FastAPI/PostgreSQL, seed integrado, ausencia de mocks Playwright, login/RBAC/404/5xx, fluxos Devedor-Proposta-Contrato-Emprestimo, pagamento idempotente, operacao diaria, IAM e Automacao; IMP-302 permanece planejado. |
| 2.8.0 | 2026-08-14 | IMP-300 concluido com Automacao server-first em `/app/automacao`, 11 operacoes oficiais de jobs/templates/notificacoes, RBAC exato, unica `Idempotency-Key` em conciliacao e sem worker/provider disparado pelo frontend; IMP-301 permanece planejado. |
| 2.7.0 | 2026-08-14 | IMP-299 concluido com IAM permitido: Perfis, catalogo canonico, atribuicoes a Usuario conhecido, RBAC exato, sete comandos com `Idempotency-Key` e sem gestao integral/listagem de Usuarios; IMP-300 permanece planejado. |
| 2.6.0 | 2026-08-14 | IMP-298 concluido com Configuracoes Financeiras server-first, 13 operacoes oficiais, RBAC exato, parametros opacos, correlation ID, ausencia de `Idempotency-Key` inventada e evidencias desktop/mobile; IMP-299 permanece planejado. |
| 2.5.0 | 2026-08-14 | IMP-297 concluido com Relatorios server-first, 4 GETs oficiais, periodo explicito, ausencia de `Idempotency-Key` inventada, sem soma financeira local e evidencias desktop/mobile; IMP-298 permanece planejado. |
| 2.4.0 | 2026-08-14 | IMP-296 concluido com Agenda/Comunicacao server-first, 12 operacoes oficiais, 10 comandos idempotentes certificados, historico de contato conforme OpenAPI e evidencia visual; IMP-297 permanece planejado. |
| 2.3.0 | 2026-08-14 | IMP-295 concluido com Cobranca server-first, fila, acao, promessa, apropriacao, RBAC exato, 3 comandos idempotentes certificados, ausencia de saldo local e evidencia visual; IMP-296 permanece planejado. |
| 2.2.0 | 2026-08-14 | IMP-294 concluido com Motor/pagamentos, 11 operacoes oficiais, 4 comandos idempotentes certificados, ausencia de calculo financeiro local e evidencia visual; IMP-295 permanece planejado. |
| 2.1.0 | 2026-08-14 | IMP-293 concluido com Contratos server-first, historico, acoes de assinatura/liberacao/cancelamento/encerramento, 8 operacoes oficiais e sem Motor/pagamentos; IMP-294 permanece planejado. |
| 2.0.0 | 2026-08-14 | IMP-292 concluido com jornada Comercial partindo de Devedor ativo, sem Contratos/Motor, sem calculo financeiro e sem Idempotency-Key inventada; IMP-293 permanece planejado. |
| 1.9.0 | 2026-08-14 | IMP-291 concluido com jornada Devedores server-first, RBAC exato, Carteira propria, comandos idempotentes e evidencias desktop/mobile; IMP-292 permanece planejado. |
| 1.8.0 | 2026-08-14 | IMP-290 concluido com composicao operacional read-only de resumo, vencimentos, agenda e cobranca; IMP-291 permanece planejado. |
| 1.7.0 | 2026-08-13 | IMP-289 concluido com login, shell, contexto US-125, recovery controlado e evidencias desktop/mobile; IMP-290 permanece planejado. |
| 1.6.0 | 2026-08-13 | IMP-288 concluido com sessao/BFF server-only e limite process-local do single-flight; IMP-289 permanece planejado. |
| 1.5.0 | 2026-08-13 | IMP-287 concluido com geracao OpenAPI canonica LF, cliente server-only inerte e drift bloqueante; IMP-288 permanece planejado. |
| 1.4.0 | 2026-08-13 | IMP-286 concluido com foundation neutra, estados acessiveis e evidencias component/axe/desktop/mobile; IMP-287 permanece planejado. |
| 1.3.0 | 2026-08-13 | IMP-285 concluido com quatro categorias, runner Windows e readiness real de FastAPI/PostgreSQL observados. |
| 1.2.0 | 2026-08-12 | IMP-284 concluido com scaffold Next.js isolado; IMP-285 permanece planejado sob gate adversarial. |
| 1.1.0 | 2026-08-12 | IMP-276..IMP-283 concluidos; snapshot recertificado e IMP-284 mantido planejado sob gate adversarial. |
| 1.0.0 | 2026-08-12 | Backlog inicial IMP-274..IMP-303, com hardening anterior ao scaffold. |
