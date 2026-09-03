# PLAN-026 - Relatorio do Hardening Contratual do Frontend MVP

**ID:** PLAN-026

**Data:** 2026-08-12

**Escopo:** IMP-276..IMP-283 do PLAN-025

**Plano relacionado:** PLAN-025

**Status:** Pacote implementado e recertificado; IMP-284 bloqueado ate fable-judge

---

# 1. Resultado

As lacunas contratuais 1..6 do Frontend MVP foram fechadas na fonte backend,
sem scaffold, dependencia ou configuracao frontend. O pacote adiciona contexto
operacional proprio e catalogo IAM canonico, tipa auth, alinha idempotencia e
400/422 e congela o OpenAPI deterministico.

O trabalho parte de `master` e `origin/master` em
`e48cb72ee4f62428491e8b8c19a569611d83fca8`. Nao existe commit novo nesta
evidencia: o contrato certificado e a worktree derivada desse commit.

---

# 2. Evidencia RED antes da correcao

| IMP | Comando focal | Falha observada |
|---|---|---|
| IMP-276 | `pytest -k imp_276` | 5 falhas: path OpenAPI ausente e runtime 404 para contexto, perfil vazio, 409 e 401 |
| IMP-278 | `pytest -k imp_278` | 3 falhas: path OpenAPI ausente e runtime 404 em vez de 200/403/401 |
| IMP-280 | `pytest -k imp_280` | 3 falhas: `requestBody.required` ausente e body generico `Payload` |
| IMP-281 | `pytest -k imp_281` | 1 falha: 30 headers runtime, somente 1 required e 29 opcionais |
| IMP-282 | `pytest -k imp_282` | 1 falha: 102 respostas automaticas `HTTPValidationError` em 422 e matriz 400 incompleta |
| IMP-283 | `pytest -k imp_283` | 1 falha: snapshot governado inexistente |

Todas as falhas ocorreram pelo motivo contratual esperado antes de sua menor
correcao correspondente.

A revisao adversarial posterior tambem produziu RED observavel para Perfil
inativo com permissoes nao efetivas, 422 aplicado por heuristica a toda
mutacao, operacoes com 422/409 alcancavel ausente e shape invalido de auth
respondendo 401. Cada contraprova foi incorporada antes da recertificacao.

---

# 3. Resultado por IMP

| IMP | Resultado observado | Evidencia verde focal |
|---|---|---|
| IMP-276 | Contratos do contexto proprio, perfil vazio, 401 e 409 materializados | 5 testes inicialmente vermelhos |
| IMP-277 | `GET /iam/contexto-atual` usa apenas o Principal, exige uma Carteira e nao exige permissao administrativa | 5/5 verdes |
| IMP-278 | Contratos de fonte canonica, versao, grupo, 401 e `perfil.ler` materializados | 3 testes inicialmente vermelhos |
| IMP-279 | `GET /iam/permissoes` publica 55 codigos de `CATALOGO_PERMISSOES`, versao `1.0.0` | suíte IAM focal verde |
| IMP-280 | Login referencia `AuthLoginRequest`; refresh/logout, `AuthRefreshRequest`; shape invalido retorna 400 sem eco e credencial/token recusado permanece 401 uniforme | 4/4 verdes e regressao auth verde |
| IMP-281 | As 30 operacoes runtime/OpenAPI publicam `Idempotency-Key` required, 1..255; 29 foram corrigidas | comparacao automatica verde |
| IMP-282 | Validacao de shape/query/header declara e retorna 400; comandos de dominio declaram 422; ambos usam `ErroResponse` | matriz focal verde |
| IMP-283 | Snapshot ordenado, UTF-8 e byte-identico ao OpenAPI gerado | contratos focais e inventarios verdes |

---

# 4. Inventario OpenAPI congelado

| Medida | Resultado |
|---|---:|
| Operacoes totais | 107 |
| Operacoes publicas | 5 |
| Operacoes protegidas | 102 |
| Schemas | 133 |
| Headers `Idempotency-Key` obrigatorios | 30 |
| Itens do catalogo IAM | 55 |
| Tamanho do snapshot | 674224 bytes |

Snapshot:
`docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json`.

SHA-256:
`8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1`.

O teste `test_imp_283_snapshot_openapi_e_deterministico` compara os bytes do
arquivo ao resultado normalizado de `create_app().openapi()`.

---

# 5. Gates de recertificacao

| Gate | Resultado observado | Estado |
|---|---|---|
| suíte focal PLAN-025 | 16 testes passaram | Verde |
| inventarios/contratos OpenAPI | 23 testes passaram | Verde |
| `uv run pytest -q` | 951 testes passaram em 293,7 s | Verde |
| `uv run ruff check .` | `All checks passed!` | Verde |
| `uv run black --check .` | 249 arquivos sem mudanca | Verde |
| `uv run mypy src tests` | sem issue em 230 source files | Verde |
| `npm run docs:validate` | 314 OK, 29 avisos historicos, 0 erros | Verde |
| `npm run docs:test` | suites documentais verdes | Verde |
| `node scripts/tests/test-plan-025-contracts.js` | contratos e mutacoes verdes | Verde |
| `npm run quality:migrations` | upgrade head -> downgrade base -> upgrade head no PostgreSQL local descartavel | Verde |
| `git diff --check` | sem erro de whitespace | Verde |

O primeiro pytest foi encerrado pelo limite de 120 s sem falha reportada; a
repeticao com janela suficiente concluiu o baseline anterior; apos as
correcoes adversariais, a recertificacao final concluiu 951 testes com exit
code 0.

---

# 6. Fronteiras e arquivos

Arquivos de runtime alterados:

- `src/emprestimo/application/autorizacao.py`;
- `src/emprestimo/application/errors.py`;
- `src/emprestimo/application/iam_catalogo.py`;
- `src/emprestimo/presentation/api/auth_routes.py`;
- `src/emprestimo/presentation/api/devedores_routes.py`;
- `src/emprestimo/presentation/api/iam_routes.py`;
- `src/emprestimo/presentation/api/main.py`;
- `src/emprestimo/presentation/api/motor_routes.py`;
- `src/emprestimo/presentation/api/openapi.py`;
- `src/emprestimo/presentation/api/operacao_diaria_routes.py`;
- `src/emprestimo/presentation/api/routes.py`;
- `src/emprestimo/presentation/api/schemas.py`.

Testes, snapshot, exportador e governanca alterados/criados:

- `tests/integration/api/test_frontend_mvp_contracts.py`;
- `tests/integration/api/test_api_auth.py`;
- `tests/integration/api/test_backend_mvp_contracts.py`;
- `tests/integration/api/test_backend_mvp_inventory.py`;
- `tests/integration/api/test_api_protected_endpoints.py`;
- `scripts/export_openapi.py`;
- `scripts/tests/test-plan-025-contracts.js`;
- snapshot, Registry, matriz, PLAN-025, backlog, US-125/126,
  FEATURE-011/012 e este relatorio PLAN-026.

Nao houve alteracao em migrations, formulas, entidades ou servicos do Motor
Financeiro. `motor_routes.py` mudou somente a declaracao do header HTTP ja
exigido pelo guard runtime. Nenhum arquivo Next.js, dependencia frontend ou
lockfile foi criado.

---

# 7. Caveats e decisao do IMP-284

A revisao adversarial interna encontrou e corrigiu falsos verdes antes do
encerramento: Perfil inativo publicava permissoes nao efetivas; uma heuristica
OpenAPI superdocumentava 422 para toda mutacao; a primeira matriz explicita
subdocumentava operacoes IAM e adjacentes; um 409 aplicavel estava ausente; e
shape invalido de auth respondia 401. O contexto agora falha fechado com lista
vazia para Perfil inativo; 422 usa matriz explicita das 24 operacoes com
violacao de dominio alcancavel; 409 aplicavel foi preservado; shape invalido
responde 400 sem eco, enquanto credencial/token recusado permanece 401.

Bloqueio restante:

- IMP-284 continua **bloqueado** ate uma nova execucao de `fable:fable-judge`
  verificar este pacote completo.

Caveats nao bloqueantes para a avaliacao:

- os 29 avisos documentais historicos permanecem aceitaveis apenas se nao
  aumentarem no gate final;
- o catalogo retorna os 55 codigos suportados; os cinco `tenant.*` continuam
  sujeitos ao guard runtime que impede associacao por administrador de Tenant;
- a administracao integral do ciclo de vida de Usuarios continua fora do
  contrato, conforme a lacuna 7;
- validacao visual e Playwright pertencem aos IMPs frontend posteriores e sao
  N/A neste pacote backend.

---

# 7.1 Atualizacao posterior do snapshot

O registro de 2026-08-12 permanece integro: o hardening deste PLAN produziu 107
operacoes com o SHA-256
`8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1`.

Em 2026-08-16 o PLAN-027/IMP-306 publicou
`POST /credit/carteiras/{carteira_id}/lancamentos`. O snapshot governado deve
bater byte a byte com o runtime, entao foi regerado: **108 operacoes, 137
schemas**, SHA-256
`5ebbe33b73ffa20de28a11240bbd53660bb15f989a82fc48456358786a58b153`.

Em 2026-08-17 a DR-004 trocou o modelo do emprestimo: o plano de parcelas deu
lugar ao acerto mensal no dia combinado. O lancamento deixou de receber
`quantidade_parcelas` e `primeiro_vencimento` e passou a receber `dia_de_acerto`;
a resposta deixou de devolver `quantidade_parcelas` e passou a devolver
`primeiro_acerto_em`. O snapshot foi regerado pelo IMP-324: **108 operacoes,
137 schemas**, SHA-256
`ba4342af3a977fe65e0f0af60d7e6fd7cab219b386a4f9c03b9167051a1c02cd`.

Ainda em 2026-08-17 o IMP-325 trocou a ancora do Resumo da Carteira
(`acertos_pendentes` e `principal_a_receber` no lugar de `parcelas_previstas`,
`parcelas_vencidas` e `total_previsto`). Alteracao de campo; **108 operacoes,
137 schemas**, SHA-256
`367381a54d6f4d2430a3be0bc18c39af3ef5a66364daa5f0c95f9dc37d1ec119`.

Em 2026-08-19 o IMP-326 acrescentou `dia_de_acerto`, `proximo_acerto_em` e
`acerto_pendente_desde` a `EmprestimoResponse`, para que a tela do emprestimo
nao precise recalcular calendario no navegador. Mudanca **aditiva**; contagem
inalterada em **108 operacoes, 137 schemas**, SHA-256
`6b24001ab24f9e4c47764d93fa8c640115dedd2f77bbc0df290d4145934b953d`.

Em 2026-08-19 o IMP-327 removeu o plano de parcelas do contrato: sairam
`GET` e `POST /credit/emprestimos/{emprestimo_id}/parcelas` e os quatro schemas
de parcela. **Reducao de superficie: 106 operacoes, 133 schemas**, 671442 bytes,
SHA-256
`75a15e1f119a0fe01cbf3401a202680b0bb812f191fd1c00e5d3c9fcef123d34`.

Em 2026-08-20 o IMP-328 retirou `parcela_id` de sete schemas. A migracao `0017`
ja havia derrubado as colunas correspondentes, entao o campo era aceito pela API
e descartado na gravacao. **Nao aditivo**, e sem mudanca de superficie: 106
operacoes, 133 schemas, 669593 bytes, SHA-256
`ff101380ddbc11cdcd93f019c149f9819fbd7091cb42e3feb72f7e0f67189248`.

Ainda em 2026-08-20 o IMP-307 acrescentou `whatsapp` ao enum de canal de
comunicacao. Mudanca **aditiva**, sem alteracao de superficie: 106 operacoes,
133 schemas, 669615 bytes, SHA-256
`d9521145dadfe95295eca3f4e720c621eaeb075b146b83a4bdad7fdf6b4b95`.

Em 2026-08-22 o IMP-332 acrescentou o estorno parcial de Pagamento e explicitou
devolucao, estorno, sobra e reconciliacao em `PagamentoResponse`. Mudanca
**aditiva**: 107 operacoes, 134 schemas, SHA-256
`ce27826a5b05235ede9e590f04174878c614a3235d0602622df8d17c5fcae0d0`.

Ainda em 2026-08-22 o IMP-333 tornou `Idempotency-Key` obrigatoria nas 31
escritas de negocio que ainda nao a publicavam. O contrato manteve **107
operacoes e 134 schemas**, e o inventario de rotas com o header passou de 32
para 63. As quatro escritas restantes (`POST /auth/ativar`, `/auth/login`,
`/auth/refresh` e `/auth/logout`) sao excecoes nominais e justificadas no
guardrail estrutural. O snapshot e o cliente tipado foram regerados; SHA-256
`fa872ddc172c9e989f8c760822c46f5e2d2db85df83ecddd30baf7a6e83e8649`.

Em 2026-08-23 o IMP-333 foi seguido pelo IMP-336, que retirou o ultimo residuo
do plano de parcelas do contrato publico: o campo `parcelas_liquidadas` saiu de
`PagamentoResponse`, junto com a coluna correspondente em `pagamento` (migration
`a2109be3d0df`) e o enum orfao `TipoRegraCalculo.PRAZO_FIXO`. **A mudanca e nao
aditiva** — o campo era obrigatorio na resposta —, amparada pela resolucao da
DR-004, que removeu o plano de parcelas do produto. O contrato manteve **107
operacoes e 134 schemas**, porque nenhum schema foi criado ou destruido; apenas
um campo obrigatorio deixou de existir. Snapshot e cliente tipado regerados;
SHA-256
`d65e8d85297a0b1dbbe53b67dade22dfe6fb4986267e1f8648b51f865fff1d0b`.
Este e o hash **vigente**.

Correcao de registro (2026-08-20): ate esta versao, o hash `75a15e1f...` estava
lancado na entrada de 2026-08-17 ao lado de "108 operacoes, 137 schemas". Era
impossivel — ele pertence ao snapshot de 106/133 produzido pelo IMP-327. Os
hashes acima foram reconstruidos a partir do proprio historico do arquivo em
`git`, e cada um foi conferido contra a contagem de operacoes e schemas do
commit correspondente.

Em 2026-08-26 o IMP-351 removeu o provisionamento de Tenant por API e o fluxo
de ativacao inteiro. Sairam `POST /platform/tenants` e `POST /auth/ativar`, mais
os schemas `TenantCreateRequest`, `TenantProvisioningResponse` e
`AtivacaoRequest`. **Reducao de superficie: 105 operacoes, 131 schemas**,
674250 bytes, SHA-256
`e87bdad9b000959dea7809878cdd69c6cfcdfca2a2dc5fa8e9cc4cc7bd5e16e6`.

A remocao e **nao aditiva** e amparada por decisao do fundador: o Administrador
da Plataforma e o unico Tenant, e nao havera outros. O Tenant nasce pela CLI
`bootstrap_plataforma`, que define credencial diretamente e nunca emitiu token.
O que saiu nao era so codigo sem uso — era um beco sem saida: `TokenAtivacao`
expirava em 24h, `credencial.redefinir` exige estado ATIVO e a CLI recusa quando
a raiz ja existe, entao um administrador convidado com token vencido ficava sem
nenhuma saida.

Em 2026-08-27 o IMP-355 publicou `POST /iam/usuarios`, fechando a lacuna de nao
existir caminho para criar Usuario — ate entao cada Tenant ficava limitado ao
administrador criado pela CLI de bootstrap. Mudanca **aditiva**: **106
operacoes, 133 schemas**, SHA-256
`63f7331c1b9aee898c1c6426aa9e1f64effe59a5536e022ccc29311685f21957`. No mesmo
ciclo, o IMP-360 trocou a permissao de `enviar-para-analise` sem mexer no
caminho, entao a superficie nao mudou por causa dele.

Ainda em 2026-08-27 o IMP-362 publicou
`GET /credit/devedores/{devedor_id}/saldo`, que soma no Motor o saldo dos
emprestimos ativos de um Devedor. Sem ele, responder "quanto o Devedor deve?"
obrigaria o consumidor a somar valores fora do Motor. Mudanca **aditiva**:
**107 operacoes, 135 schemas**, SHA-256
`23d8d91f5f5890ef5ca010d1fc45a458458e5028042c80e7e15dbf82052af76a`.

Em 2026-09-02 o IMP-368 publicou as quatro operacoes da conexao de WhatsApp
(`GET`, `POST` e `DELETE` em `/platform/whatsapp/conexao`, mais
`DELETE /platform/whatsapp/conexao/instancia`). A quarta apaga a instancia no
provedor, e entrou porque o `logout` sozinho acumula sessao morta no Evolution.
Mudanca **aditiva**: **111 operacoes, 137 schemas**, SHA-256
`95c45df44bf638233fe9d38d44398867d09d7f7b0a8a8fdc0e48c5c99597cb82`.
Este e o hash **vigente**. As tres escritas novas nao publicam
`Idempotency-Key` e estao registradas como excecao justificada no guardrail do
IMP-333 — o replay devolveria um QR expirado, e o `POST` nao tem corpo a
divergir.

Das dez regeracoes registradas, as do IMP-326, IMP-355, IMP-362 e IMP-368 sao
aditivas. A do IMP-324
retirou campos exigidos, a do IMP-327 retirou operacoes e schemas, a do
IMP-328 retirou campos de sete schemas e a do IMP-351 retirou duas operacoes e
tres schemas: as quatro **nao aditivas**, deliberadas, e amparadas pela
resolucao da DR-004 ou por decisao registrada. Nada do hardening foi desfeito.

---

# 8. Historico de versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.10.0 | 2026-09-02 | IMP-368: as quatro operacoes de `/platform/whatsapp/conexao` publicadas; snapshot 111/137 regerado. |
| 1.9.0 | 2026-08-27 | IMP-362: `GET /credit/devedores/{devedor_id}/saldo` publicado; snapshot 107/135 regerado. |
| 1.8.0 | 2026-08-27 | IMP-355: `POST /iam/usuarios` publicado; snapshot 106/133 regerado. Entrada acrescentada a cadeia, sem reescrever as anteriores. |
| 1.7.0 | 2026-08-26 | IMP-351: provisionamento de Tenant por API e fluxo de ativacao removidos; snapshot 105/131 regerado. O registro de cada snapshot anterior permanece intacto — cadeia se acrescenta, nao se reescreve. |
| 1.6.0 | 2026-08-22 | IMP-333: `Idempotency-Key` passou de 32 para 63 rotas; guardrail estrutural deixa somente quatro excecoes auth nominais; snapshot 107/134 regerado. |
| 1.5.0 | 2026-08-22 | Registrado o snapshot aditivo do IMP-332: estorno parcial e reconciliacao explicita de Pagamento, com 107 operacoes e 134 schemas. |
| 1.4.0 | 2026-08-20 | Registrada a regeracao do IMP-328: `parcela_id` sai de sete schemas, sem mudanca de superficie. |
| 1.3.0 | 2026-08-20 | Corrigido o registro de snapshots: o hash vigente estava atribuido ao inventario errado. Reconstruidas as cinco regeracoes (IMP-306, 324, 325, 326, 327) com hash e contagem conferidos no historico do arquivo. |
| 1.2.0 | 2026-08-17 | Registrada a regeracao do snapshot pela DR-004/PLAN-030: lancamento passa a receber dia de acerto. |
| 1.1.0 | 2026-08-16 | Registrada a regeracao do snapshot pelo PLAN-027/IMP-306, sem alterar o registro original do hardening. |
| 1.0.0 | 2026-08-12 | Execucao IMP-276..IMP-283, snapshot OpenAPI e decisao de manter IMP-284 bloqueado ate judge. |
