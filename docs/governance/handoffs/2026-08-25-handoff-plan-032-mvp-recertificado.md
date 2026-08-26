# 2026-08-25 - Handoff: PLAN-032 Fechado e MVP Recertificado

**Versao:** 1.1.0

**Status:** PLAN-032 concluido — 18 de 18 itens elegiveis. MVP recertificado
sobre arvore limpa, com cobertura em 90,02% contra a meta de 90% do IMP-063.

**Periodo coberto:** do raio-X AS-IS/TO-BE de 2026-08-22 ao fechamento em
2026-08-25

**Base:** `origin/master` em `c2fc926` (merge do PR #24)

**Backlog do ciclo:**
`docs/implementation/backlogs/PLAN-032-execution-backlog.md` (v1.5.0)

**PRs do ciclo:** #22 (auditoria de CI), #23 (Fase D), #24 (IMP-350) — todos
verdes na primeira tentativa apos a auditoria de CI, todos mergeados.

---

## 1. Estado Executivo

O PLAN-032 fechou os bloqueadores, a conformidade transversal e os residuos que
separavam o MVP de "declarado pronto" e "pronto de fato". O padrao que se
repetiu em quase todo item nao foi funcionalidade faltando: foi **funcionalidade
existente cujo caminho de falha ninguem exercitava**, e que por isso falhava em
silencio.

Tres exemplos do mesmo defeito, achados em momentos diferentes:

- o comprovante virava `handler_ausente` porque o worker nao tinha o handler
  registrado — **todo comprovante emitido era falha permanente silenciosa**
  (IMP-330);
- a entrega do aviso de sobra estourava `VARCHAR(20)` no caminho de resultado
  desconhecido, derrubando a entrega (IMP-350);
- o hook de pre-push silenciava a restauracao de evidencia com
  `2>/dev/null || true`, e a arvore suja fazia o push seguinte reprovar num
  gate sem relacao com a causa (§9.3 do backlog).

**A licao operacional do ciclo:** erro silenciado nao desaparece — reaparece
como sintoma distante da causa, e custa mais caro. Cada correcao deste ciclo
trocou silencio por sinal.

---

## 2. O que foi entregue

| Fase | Itens | Conteudo |
|---|---|---|
| A - Bloqueadores | IMP-330, 331, 332, 346 | Transporte WhatsApp (Evolution Go), entrega do comprovante, ciclo de vida do CobrancaCaso, aviso e estorno da sobra |
| B - Conformidade | IMP-333, 334, 335 | Idempotencia em toda escrita com guardrail, auditoria onde a ADR-002 exige, append-only garantido pelo banco e nao por convencao |
| C - Residuos | IMP-336, 337, 338, 339 | Ultimos restos do plano de parcelas, documentacao de dominio sem parcelas, Tenant como credor individual, `CLAUDE.md` e status do PLAN-003 reconciliados |
| D - Operabilidade | IMP-340, 341, 342, 343 | Bootstrap reproduzivel, token de ativacao com as tres vozes alinhadas, politica minima de credencial, heartbeat com consumidor |
| E - Fechamento | IMP-344, 350, 345 | Arvore fechada, caminho de entrega coberto, recertificacao |

**Fora do MVP, registrados para nao voltarem como surpresa:** IMP-347
(notificacoes diarias), IMP-348 (dispatcher de `EventPublisher`), IMP-349
(reemissao do token de ativacao).

### Contrato publico

Snapshot vigente
(`docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json`),
conferido em 2026-08-25: **685721 bytes**, SHA-256
`d65e8d85297a0b1dbbe53b67dade22dfe6fb4986267e1f8648b51f865fff1d0b`,
**107 operacoes e 134 schemas**.

Os itens da Fase D foram entregues **sem alterar o contrato publico**, e isso
foi decisao, nao acaso — ver o caveat 4.2.

> **Superado em 2026-08-26 pelo IMP-351.** Os numeros e o SHA acima continuam
> corretos **para 2026-08-25** e nao foram reescritos de proposito: registro
> historico que se atualiza deixa de ser registro. O contrato vigente hoje tem
> **105 operacoes e 131 schemas**, depois da remocao do provisionamento por API
> e do fluxo de ativacao. O SHA vigente esta na matriz de rastreabilidade, que e
> o documento que acompanha o contrato atual.

---

## 3. Evidencias da recertificacao

Executadas em 2026-08-25 sobre **arvore limpa** em `c2fc926`, na ordem do CI.
**33 gates, exit 0.** Numeros conferidos nesta execucao, nao herdados de commit
anterior — que era o criterio de pronto do IMP-345.

### 3.1 Backend

| Gate | Resultado |
|---|---|
| `uv run pytest` (PostgreSQL 16 real) | **1045 verdes** em 466,16 s |
| Cobertura (`--precision=2`) | **90,02%** — 12032 statements, 1201 nao cobertos |
| `uv run ruff check .` | verde |
| `uv run black --check .` | verde |
| `uv run mypy src tests` | verde |
| `npm run quality:migrations` | `upgrade head -> downgrade base -> upgrade head` contra PostgreSQL 16 real, verde |

A meta de 90% do IMP-063 esta batida **por medicao, nao por arredondamento**. O
relatorio padrao imprimia `90%` para 89,55% antes do IMP-350 — ver §5.

### 3.2 Documentacao

| Gate | Resultado |
|---|---|
| `npm run docs:validate` | **352 verificacoes OK, 32 avisos, 0 erros** |
| `npm run docs:test` | **173/173** |

Quem rodar depois deste commit vera **353** verificacoes, nao 352: este proprio
handoff e um documento validado e entrou na contagem. Os 32 avisos e os 0 erros
nao mudam.

### 3.3 Frontend

| Suite | Testes |
|---|---|
| `test:unit` | 72 |
| `test:component` | 69 |
| `test:contract` | 42 |
| `test:bff` | 135 |
| **subtotal** | **318** |

`api:check`, `lint`, `typecheck` e `build` verdes.

### 3.4 Navegador e stack real

`test:certification` verde, executado **antes** das capturas — a ordem importa e
esta explicada na §9.3 do backlog.

As dezesseis execucoes Playwright somam **138 testes verdes**: a11y, capturas
visuais, `e2e`, `session` e as onze suites por tela (`dashboard`, `devedores`,
`comercial`, `contratos`, `motor`, `cobranca`, `agenda`, `relatorios`,
`configuracoes`, `iam`, `automacao`), mais **`test:jornadas` 8/8** contra
Next.js, FastAPI e PostgreSQL 16 reais, e `test:infrastructure` verde.

`docs/audits/evidence/` voltou ao estado commitado ao fim da execucao — a arvore
nao ficou suja.

### 3.5 Migrations

23 migrations, head em `c47f1a2b8e30` (`alarga status do audit_log de 20 para
40`, entregue pelo IMP-350). O ciclo completo de ida e volta contra PostgreSQL
real prova a reversibilidade.

---

## 4. Caveats

### 4.1 O formato de envio do Evolution nao esta no contrato auditado

**O caveat mais importante deste handoff, e o unico que depende de mundo real.**

O `CRM_EVOLUTION_CONTRACT.md` define o nivel de autenticacao de `/send/*` e o
comportamento de tenant inativo, mas **nao documenta o payload de requisicao nem
o formato de resposta** de `POST /send/text`. O payload `{number, text, id}` e o
criterio de aceite `data.Info.ID` vieram de documentacao **externa** do Evolution
Go, nao da fonte auditada.

**Se o formato real divergir, todo envio bem-sucedido sera classificado como
`DESCONHECIDO`.**

Por que nao e perigoso, mas precisa ser fechado: `DESCONHECIDO` **nao dispara
retry** — `SolicitacaoNotificacao.preparar_retry` so aceita `FALHA_TEMPORARIA`.
Nao ha risco de mensagem duplicada para o devedor. O prejuizo e de escrituracao:
mensagens entregues ficariam registradas como resultado desconhecido, e o Credor
nao saberia o que saiu.

**Acao:** o primeiro envio real contra o Evolution deve conferir o formato e
ajustar o classificador. Depende da pergunta 3 do `contexto-externo.md`
(existe ambiente de teste do Evolution?), ainda aberta com o fundador.

### 4.2 O contrato publico declara politica de senha mais frouxa do que o sistema aceita

O IMP-342 pos o minimo de 10 caracteres em `_normalizar_segredo`, no dominio —
o funil unico por onde `definir` e `redefinir` passam, cobrindo API, CLI de
bootstrap e qualquer chamador futuro. **Os schemas Pydantic continuam com
`min_length=1`**, e a recusa chega como 422 de violacao de invariante.

Foi deliberado: mexer nos schemas obrigaria a regerar o snapshot e propagar SHA
pela governanca — o ponto exato que quebrou no IMP-330 e derrubou o `docs:test`
de 173 para 154 sem que ninguem visse. O preco e que um cliente do contrato le
um minimo que nao vale. **Divida declarada, nao esquecimento.**

### 4.3 O token de ativacao — CORRIGIDO em 2026-08-26, este caveat estava errado

**O que este caveat afirmava, e estava errado:** que a saida para um token de
ativacao perdido seria a CLI `bootstrap_plataforma`. **Ela nao serve.** A CLI
recusa quando a raiz administrativa ja existe (`PerfilConflitoError:
Administrador da Plataforma ja inicializado`) e quando o Tenant ja existe
(`TenantJaExisteError`). Ela roda **uma vez**, para criar a raiz — nunca para
recuperar.

O cenario real era pior do que o descrito: Tenant provisionado pela API, token
perdido, `credencial.redefinir` limitado ao `principal.tenant_id` e o
Administrador da Plataforma vivendo no tenant raiz. **Nao havia saida nenhuma**
— o Tenant ficaria provisionado e inacessivel para sempre.

**Por que isso deixou de importar:** decisao do fundador em 2026-08-26 — o
Administrador da Plataforma e o unico Tenant, e nao havera outros. Com isso o
`TenantProvisioningService`, unico chamador de `TokenAtivacao.emitir`, descreve
um fluxo que o produto nao percorre.

O IMP-349 foi **fechado como nao-aplicavel**, e o fluxo de ativacao e o
provisionamento por API foram removidos em vez de mantidos como codigo que
ninguem exerce. Ver o backlog do PLAN-032, item IMP-351.

**A licao, que vale mais que o caveat:** eu afirmei uma saida operacional sem
abrir o codigo que a implementaria. A CLI *parecia* servir pelo nome. Caveat que
descreve caminho de recuperacao precisa ser lido no codigo, nao inferido — quem
confiasse nele so descobriria o erro no dia do incidente.

### 4.4 `scheduler_worker.py` em 69,91%, e o grosso do resto e o `main()`

A cobertura total bateu a meta, mas este modulo continua abaixo. As linhas
311-390 sao a funcao `main()` de bootstrap — monta canais, servicos e handlers
a partir de variaveis de ambiente. Testa-la exigiria injetar o ambiente inteiro
para provar fiacao que o `docker compose up` ja exercita.

**Declarado em vez de perseguido:** cobrir `main()` inflaria o numero sem cobrir
comportamento. Se um dia a fiacao ficar condicional demais para ser lida de
relance, ai vale extrair a montagem para uma funcao testavel.

### 4.5 A tabela de heartbeat e global e sem `tenant_id`

`scheduler_worker_heartbeat` nao tem `tenant_id` — e correto, o worker e do
processo, nao do Tenant. Mas isso significa que **qualquer teste que escreva ali
afeta o `/health` de todas as outras suites**. O IMP-350 fechou isso com fixture
que limpa antes e depois; antes, os testes so passavam pela ordem de coleta do
pytest. Quem for escrever teste novo que toque heartbeat precisa do mesmo
cuidado.

### 4.6 Baseline documental: 32 avisos, 0 erros

`docs:validate` fecha com **352 verificacoes OK, 32 avisos, 0 erros**. Os avisos
sao referencias cruzadas para IDs de planejamento futuro e dois namespaces
legados (`DECISION`, `FEATURES`). Nenhum e regressao deste ciclo — a contagem foi
conferida contra o `master` antes e depois das mudancas, e e identica.

### 4.7 `DATABASE_URL` continua necessario para a suite local

O IMP-340 corrigiu metade do caveat 4.1 do handoff anterior:
`DEFAULT_DATABASE_URL` passou de `localhost` para `127.0.0.1`, com a razao em
comentario no codigo para ninguem "consertar" de volta. Isso elimina a espera de
timeout IPv6 que fazia a suite **parecer travada**.

A outra metade continua: a senha padrao e `emprestimo` e o container sobe com a
do `.env`. Comando que funciona:

```bash
export DATABASE_URL="postgresql+psycopg://emprestimo:$(grep -m1 '^POSTGRES_PASSWORD=' .env | cut -d= -f2-)@127.0.0.1:5432/emprestimo"
```

**Eu mesmo esqueci isso nesta sessao**, mesmo tendo lido o caveat no comeco dela,
e o `quality:migrations` falhou com `password authentication failed`. O caveat
esta certo; o que falta e o comando estar onde a pessoa ja esta olhando.

---

## 5. Armadilhas de verificacao aprendidas neste ciclo

Registradas porque custaram tempo real e nao sao obvias.

### `| tail` esconde o exit code

`uv run pytest -q 2>&1 | tail -25` reporta o status do **`tail`**, nao do
`pytest`. Li `exited with code 0` com tres `FAILED` impressos acima. Nao afeta CI
nem hook, que chamam os gates direto — afeta quem verifica na mao. Forma correta:

```bash
uv run pytest -q > /tmp/pytest.log 2>&1; echo "EXIT=$?"; tail -6 /tmp/pytest.log
```

### O relatorio de cobertura arredonda

`--cov-report=term-missing` imprime `90%` para **89,55%**. Num criterio de
conclusao, a diferenca importa. Use:

```bash
uv run coverage report --precision=2
```

### `/health` tem consumidores fora do `src/`

Somar um check ao `/health` parecia mudanca de uma linha. E a sonda de prontidao
de **duas stacks de teste** (`jornadas-e2e/real-stack.mjs` e
`infrastructure/real-stack-smoke.mjs`), e um contrato de governanca fixava o
literal `health.status, "healthy"`. Antes de mexer, varra `frontend/tests`
inteiro e separe quem *responde* de quem *consome* — dos dezesseis hits, treze
eram fixtures inofensivos.

### Suite interrompida deixa servidor vivo

A tentativa seguinte falha com "porta ja em uso", que parece defeito de
configuracao e nao e. Listar quem escuta em 3101-3112 e 3201-3212 e encerrar.

---

## 6. Regras que o ciclo confirmou

- **Erro silenciado vira sintoma distante da causa.** `handler_ausente`,
  `2>/dev/null || true` e `except Exception: return "unhealthy"` sao a mesma
  doenca em tres roupas. Barulho no lugar certo custa menos que silencio.
- **Corrigir na causa, nao no call site.** O `VARCHAR(20)` tinha um contorno no
  `comprovante.py` que o `notifications.py` nao copiou. Remendo por chamador e
  armadilha armada para o proximo.
- **Cobertura arredondada esconde caminho nao exercitado.** Os 0,45 ponto entre
  89,55% e 90% custaram dois testes que acharam um defeito de producao e um
  acoplamento entre suites. Fechar o numero pelos arquivos faceis nao teria
  achado nenhum dos dois.
- **Um gate que nao roda o que o CI roda nao e gate.** A lista local cobria 10
  dos 28 comandos do CI, e os 18 ausentes eram justamente as suites de
  navegador — onde os defeitos estavam.
- **Guardrail que fixa literal envelhece; guardrail que verifica intencao, nao.**
  Dois contratos de governanca precisaram mudar neste ciclo sem afrouxar.

---

## 7. Proximo Ciclo Recomendado

O MVP esta fechado e recertificado. O que fica na mesa, em ordem de urgencia
real:

1. **Validar o formato do Evolution contra o servidor real** (caveat 4.1). E o
   unico item que depende de mundo externo e o unico que pode fazer entrega
   correta parecer entrega desconhecida.
2. **Responder as perguntas abertas do `contexto-externo.md`** — onde guardar
   `evolution_tenant_id` e `evolution_api_key`, e se existe ambiente de teste do
   Evolution.
3. **IMP-349** antes do primeiro cliente novo, nao depois.
4. **IMP-347** (notificacoes diarias) — a visao do fundador ja tem o transporte
   pronto e o IMP-331 foi desenhado para alimenta-lo sem recalculo.

---

## 8. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.1.0 | 2026-08-26 | Caveat 4.3 corrigido: a CLI de bootstrap **nao** era saida para token perdido, e nao havia saida nenhuma. Com a decisao de Tenant unico, o IMP-349 fecha como nao-aplicavel e o fluxo de ativacao sai do produto (IMP-351). |
| 1.0.0 | 2026-08-25 | Fechamento do PLAN-032 e recertificacao do MVP, com caveats e pendencias declaradas. |
