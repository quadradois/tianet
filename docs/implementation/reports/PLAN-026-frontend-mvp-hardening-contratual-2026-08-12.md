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
`primeiro_acerto_em`. O snapshot foi regerado: **108 operacoes, 137 schemas**,
SHA-256
`75a15e1f119a0fe01cbf3401a202680b0bb812f191fd1c00e5d3c9fcef123d34`.

Em 2026-08-19 o IMP-326 acrescentou `dia_de_acerto`, `proximo_acerto_em` e
`acerto_pendente_desde` a `EmprestimoResponse`, para que a tela do emprestimo
nao precise recalcular calendario no navegador. Mudanca **aditiva**; contagem
inalterada em 108 operacoes e 137 schemas.

A regeracao de 2026-08-17 e a de 2026-08-18 estao registradas acima; o hash
vigente e o desta ultima. Diferente das duas primeiras, a mudanca do IMP-324
**nao foi aditiva**: campos exigidos
sairam do contrato. E deliberada e esta na resolucao da DR-004. A contagem de
operacoes e de schemas nao muda porque a alteracao e de campo, nao de
superficie. Nada do hardening foi desfeito.

---

# 8. Historico de versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.2.0 | 2026-08-17 | Registrada a regeracao do snapshot pela DR-004/PLAN-030: lancamento passa a receber dia de acerto. |
| 1.1.0 | 2026-08-16 | Registrada a regeracao do snapshot pelo PLAN-027/IMP-306, sem alterar o registro original do hardening. |
| 1.0.0 | 2026-08-12 | Execucao IMP-276..IMP-283, snapshot OpenAPI e decisao de manter IMP-284 bloqueado ate judge. |
