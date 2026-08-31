# 2026-08-31 - Handoff: PLAN-033 Fase B fechada, higiene do codebase e DR-006 aberta

**Versao:** 1.0.0

**Status:** PLAN-033 com **Fase B completa** (IMP-355, IMP-360, IMP-361) e
IMP-362 adiantado da Fase C. Nenhum item tecnico restante esta desbloqueado:
tudo o que sobra depende de dois insumos externos.

**Periodo coberto:** 2026-08-30 a 2026-08-31

**Base:** `origin/master` em `2b195c8`, arvore limpa. Quatro PRs mergeados nesta
sessao (#34 a #37).

**Substitui:** `2026-08-27-handoff-plan-032-fechado-plan-033-fase-b.md`, que
continua valido como registro daquela data.

---

## 1. Estado Executivo

A sessao comecou como uma auditoria de higiene tecnica — escopo pequeno,
aparentemente autocontido — e terminou fechando a Fase B do PLAN-033.

O fio condutor desta vez foi outro: **verificacao que confirma a si mesma**. Em
quatro momentos distintos, algo estava verde por um motivo que nao era o motivo
declarado.

| O que parecia | O que era |
|---|---|
| Loading states sem import = codigo morto | contrato governado, verificado por `docs:test` |
| Teste afirmando a mensagem de erro na trilha | teste fixando um vazamento de CPF como correto |
| `gh pr checks` verde = merge seguro | checks do head do PR; o merge e outro commit |
| CI vermelho que fica verde ao re-rodar | corrida ganhando o sorteio, defeito intacto |

Nenhum desses foi encontrado por leitura de codigo. Todos foram encontrados por
um gate que fazia uma pergunta diferente da que o autor tinha em mente.

---

## 2. O que foi entregue

### PR #34 — auditoria de higiene tecnica

Auditoria sobre 479 arquivos (253 Python, 226 TS/JS), executada via Codex e
verificada independentemente. Diff estritamente removivel: **-163 linhas
liquidas**.

| Grupo | Removido |
|---|---|
| Backend | stub `health()` sem decorator; `uuid_do_resultado` nunca consumido; tres helpers do plano de parcelas que a DR-004 matou; serializadores do antigo `PeriodoFinanceiro` |
| Frontend | Server Actions sem consumidor; 12 aliases/reexports redundantes; 2 `as unknown as` e os tipos artificiais que os sustentavam |
| Dependencias | `factory-boy` (uso zero), duplicacao dev de `httpx`, `faker` fora do lock |

**31 das 32 remocoes estavam certas.** A que errou foram
`CobrancaLoadingState` e `ContratosLoadingState`: sem import estatico, mas
**contrato governado** verificado por `docs:test` (IMP-293, IMP-295). O
consumidor e a governanca de documentacao, nao o grafo de imports — analise
estatica nao alcanca esse tipo de consumidor. O gate de pre-push pegou antes do
push; restaurados no `e8b25a8`.

### PR #35 — IMP-361, autoria na trilha

Os sete eventos de `DevedorCadastroService.criar` — inicio, `aggregate_criado`,
`evento_cadastrado`, sucesso, falha, rollback e replay — passam a carregar o
`usuario_id` do Principal. Antes **nenhum** carregava, e `criar.rollback` nao
tinha `detalhes` nenhum: escrita do copilot ficaria indistinguivel de escrita
humana na trilha da ADR-002.

`_autoria()` monta a base num lugar so. O guardrail e `TestAutoriaNaTrilha`, que
percorre **todas** as chamadas de auditoria exigindo o Principal — verificado
por mutacao: removendo `**autoria` de um evento, o teste reprova nomeando a acao
culpada.

**O achado que nao estava no backlog** esta na §3.

### PR #36 — corrida na sincronizacao da trilha

Ver §4. Deixou o `master` vermelho por um intervalo e foi consertado.

### PR #37 — DR-006

`docs/governance/decision-requests/DR-006-conexao-do-whatsapp-dentro-da-plataforma.md`.
Ver §6.

---

## 3. O defeito que a tarefa expos: CPF na trilha append-only

`criar.falha` gravava `f"{type(exc).__name__}: {exc}"`. A mensagem de
`DevedorJaExisteError` interpola o documento:

```
f"Devedor com documento {documento!r} ja existente na Carteira {carteira_id}"
```

**Todo cadastro com CPF duplicado escrevia o CPF na trilha append-only.** Nao ha
UPDATE nem DELETE em `audit_log` por desenho — o que entrou ali nao sai.

**Pior: o teste existente afirmava essa string, CPF e tudo, como comportamento
correto.** Nao foi descuido de quem escreveu — o teste descrevia fielmente o que
o codigo fazia. Ninguem tinha perguntado se o que o codigo fazia devia ser feito.

A correcao grava `erro_tipo` com o nome do tipo. Nao e padrao inventado: e o
mesmo que `UsuarioCadastroService` (IMP-355) ja usava, num arquivo que comenta
literalmente *"IMP-361 antecipado aqui"*.

**Nao foi feito, deliberadamente:**

- O payload de `criar.evento_cadastrado` mantem documento, nome e contatos. Ali
  o PII e o registro do fato de negocio que a ADR-002 existe para guardar;
  remove-lo destruiria o proposito da trilha, e e decisao de governanca.
- **Linhas ja gravadas nao foram tocadas.** Ver caveat 8.6.

---

## 4. A corrida, e por que re-rodar teria escondido

O CI reprovou `test_sobra_real_worker_entrega_aviso_e_registra_comunicacao` com
`entregar.resultado` ausente, enquanto a suite passava local e no pre-push.

O worker roda em thread propria — `cycle()` submete ao executor e retorna. A
ordem dentro da thread e:

1. auditoria `entregar.inicio` — sessao independente, commita
2. `_processar`: envia, grava `RegistroComunicacao`, `job.concluir` -> **commit**
3. auditoria `entregar.resultado` — sessao independente, commita

`_aguardar_estado_job` retorna no passo 2. Em maquina lenta, a thread principal
le `audit_log` antes do passo 3.

**A trilha pousar depois nao e defeito.** A ADR-002 exige sessao independente
justamente para a auditoria sobreviver ao rollback da transacao de negocio. O
que estava errado era o teste concluir *"job CONCLUIDO logo trilha completa"*.

`_aguardar_acoes_auditoria` sincroniza no fato certo. O mesmo defeito latente
existia em `test_entrega_comprovante.py`, que o CI ainda nao tinha alcancado.

**Verificado por contrafactual**, nos dois sentidos: com a escrita da trilha
atrasada em 0,4 s para simular CI lento, o codigo anterior reprova nos dois
testes com a assinatura exata do CI, e o corrigido passa.

**O registro que importa:** o commit `83f1b86`, que **nao** contem o conserto,
ficou verde numa **re-execucao**. Sem mudanca de codigo. Se a resposta ao
vermelho tivesse sido "re-roda ate passar", o defeito continuaria la, voltando
quando o CI estivesse carregado. Corrida verde nao e corrida consertada.

---

## 5. Evidencias

Conjunto completo verde sobre `418ac51`, via `pre-push` (que roda o CI inteiro
local, mesma ordem — PLAN-032 §9.3):

| Gate | Resultado |
|---|---|
| `ruff` / `black` / `mypy src tests` | verdes — 285 arquivos formatados, 255 tipados |
| `pytest` (PostgreSQL 16 real) | verde |
| Vitest unit / component / contrato / bff | **59 arquivos, 318 testes** |
| `eslint` / `typecheck` / `build` | verdes, 25 rotas |
| `docs:validate` | 358 OK, 35 avisos, **0 erros** |
| `docs:test` | **173/173** |
| treze suites Playwright + `test:jornadas` | verdes |
| `quality:migrations` | ciclo completo |

Tempos de `pre-push` observados: 814 s, 430 s, 396 s — e **8 s** no PR de
documentacao, onde o hook dispensa os gates de codigo por escopo.

---

## 6. DR-006 — conexao do WhatsApp pela plataforma

**Aberta, aguardando o fundador.** Pedido: escanear o QR dentro da TiaNet,
porque quem opera nao tem conta no `diamondgreen.com.br`. A justificativa e
operacional e correta.

Virou DR porque atender **reverte decisao registrada**:

- `contexto-externo.md` §6.1 (2026-08-25) decidiu segredo em variavel de
  ambiente, com a condicao de saida declarada: *"no dia em que cada Tenant tiver
  instancia propria, isso vira tabela de segredos com criptografia"*. A condicao
  chegou.
- Backlog do PLAN-033, linha 68: multi-Tenant **fora deste ciclo**.
- `/instance/connect` exige `webhookUrl`, e §2.2 decidiu que a TiaNet **nao
  expoe webhook publico**.

Estado verificado no codigo, nao lembrado: o adapter so faz `/send/text`; nao
existe endpoint de gestao de instancia; o ORM nao guarda credencial de Evolution;
o frontend nao tem tela nem QR.

Quatro perguntas com opcoes e custo. Recomendacao registrada: tela restrita ao
Administrador da Plataforma, webhook apontando para o **agente** (preserva §2.2),
ciclo proprio em vez de emenda ao PLAN-033.

**O IMP-352 nao depende disto** e deve vir antes: risco de dado antes de atrito
operacional.

---

## 7. Ambiente local — como esta

Stack Docker no ar, `/health` **healthy** nos dois checks.

| | |
|---|---|
| Frontend | `http://localhost:3000` |
| API | `http://localhost:8010` — **nao** 8000; `.env` define `API_PORT=8010` |
| Tenant | `tianet-local` |
| Admin | `admin@tianet.local` |

Usuario criado via `emprestimo-bootstrap-plataforma` e **login validado**:
`POST /auth/login` retorna 200 com tokens.

O `PLATFORM_ADMIN_BOOTSTRAP_SECRET_HASH` do `.env` foi trocado nesta sessao — o
segredo anterior nao era conhecido por ninguem, so o hash. O campo do login e
`identificador_institucional`, nao `tenant_identificador`.

**O build Docker funcionou** — o caveat 7.4 do handoff anterior nao se
reproduziu nesta maquina. Considere-o fechado ate nova ocorrencia.

---

## 8. Caveats vigentes

### 8.1 O formato de envio do Evolution — RESOLVIDO em 2026-08-31

> **Fechado.** Tenant `tianet` criado pela equipe que administra o servidor,
> instancia `adm_tianet` criada pela TiaNet com token proprio, WhatsApp pareado,
> e envio real validado pela classe de producao: `ACEITA`/`accepted`. O formato
> **nao divergia**. Ver `contexto-externo.md` §6.2 e a secao 8.1 do contrato.

O texto abaixo fica como registro do risco enquanto ele existiu.

**Herdado, ainda aberto, e o de maior risco.** O payload `{number, text, id}` e
o criterio `data.Info.ID` vieram de documentacao externa. Se divergir, todo
envio bem-sucedido vira `DESCONHECIDO` — sem duplicata para o devedor, com
prejuizo de escrituracao. E o **IMP-352**, e espera o numero do fundador e o
`EVOLUTION_INSTANCE_TOKEN` no ambiente.

Esclarecido nesta sessao, pelo contrato: **o token da instancia e gerado por
quem chama** `/instance/create`, nao emitido pelo Evolution nem produzido pelo
QR. O que o Evolution gera automaticamente e a `evolution_api_key` **do tenant**,
na resposta do `/tenant/create`. Confundir os dois atrasa o IMP-352 sem motivo.

### 8.2 Contrato declara politica de senha mais frouxa do que o sistema aceita

Herdado. O dominio exige 10 caracteres; os schemas mantem `min_length=1` e a
recusa vem como 422. Deliberado, divida declarada.

### 8.3 Producao nao existe

Herdado. Servidor **nao provisionado**, sem dominio, TLS, backup ou CD. E o
**IMP-359**, e bloqueia o GATE-E1b.

### 8.4 `scheduler_worker.py` em 69,91%

Herdado. O grosso do que falta e o `main()` de bootstrap.

### 8.5 Dev e teste compartilham o mesmo banco — NOVO

`DATABASE_URL` aponta para o mesmo `emprestimo` em desenvolvimento e em teste, e
o `conftest` executa `DROP SCHEMA IF EXISTS public CASCADE`. **Rodar a suite
apaga o banco que a aplicacao esta usando** — aconteceu duas vezes nesta sessao:
API respondeu 503, login deu 500 e o worker morreu com `relation "audit_log"
does not exist`. Recuperacao: `docker compose run --rm migrate`.

O guard do `137e47a` (`exigir_host_descartavel`) **nao protege disso**, e esta
certo assim: `127.0.0.1` *e* legitimamente o banco de teste. O guard defende
contra apontar para producao, onde o banco do compose se chama `emprestimo` — o
mesmo nome de producao, de modo que **so o host distingue os dois ambientes**.

Separar os dois bancos e configuracao, nao codigo, e vale fazer antes de haver
dado que alguem queira manter.

### 8.6 CPFs historicos em `audit_log` — NOVO

O vazamento novo esta fechado (§3), mas os registros anteriores continuam la —
um por cadastro duplicado desde sempre. Limpar e **mudanca destrutiva de banco**
e precisa de decisao separada. Nao foi tocado.

### 8.7 `CLAUDE.md` da raiz e gitignored — NOVO

`.gitignore:43:/CLAUDE.md`. Consequencias observadas:

- O commit `4ed9938` lista na mensagem uma alteracao ao `CLAUDE.md` que **nao
  esta no diff** — o arquivo nao podia entrar. Corrigido por comentario no PR #34;
  historico mergeado nao foi reescrito.
- Edicoes ao `CLAUDE.md` (retirada da mencao a Factory Boy; ponteiro do handoff)
  existem **so na maquina que as fez** e vao divergir em qualquer clone novo.

`frontend/CLAUDE.md` e `frontend/AGENTS.md` **sao** versionados. A regra e
ancorada na raiz e atinge um arquivo so — assimetria que merece decisao.

---

## 9. Armadilhas de ambiente confirmadas

As tres do handoff anterior **reapareceram todas**, na mesma sessao, porque o
handoff nao foi lido na abertura: a tarefa parecia autocontida. O protocolo de
abertura existe exatamente para isso.

- **Servidor orfao nas portas de teste.** Um push interrompido deixou tres
  processos vivos (runner de contratos, fixture na 3205, `next start` na 3105).
  O push seguinte falhou com `port is already used`.
- **Evidencias sujas depois de suite de captura interrompida.** `docs:test`
  reprova por SHA de evidencia. Agravante observado: se as evidencias ja estao
  sujas quando o hook comeca, ele **nao restaura** — por desenho, para nao
  descartar trabalho seu.
- **`| tail` esconde o exit code.** Um push relatado como sucesso tinha falhado.

### Novas nesta sessao

- **Recriar o servico `api` orfana o `frontend`.** O compose usa
  `network_mode: "service:api"`; recriar a api destroi o netns que o frontend
  aponta. Recrie os dois.
- **CI do commit de merge nao e CI do PR.** `gh pr checks` reporta o head do PR.
  O merge produz outro commit, e e ele que roda contra `master`. Ver §10.
- **`Path.write_text` no Windows converte `\n` em `\r\n`.** Um `\r` invisivel
  entrou num segredo e o hash nao bateu. Para alimentar `getpass` por pipe, use
  `write_bytes`.

---

## 10. Regras que a sessao confirmou

- **Verde no PR nao implica verde no merge.** O PR #35 foi mergeado enquanto o
  push do conserto ainda rodava; o merge levou o IMP-361 sem ele, e `master`
  ficou vermelho. Verificar o commit de merge, sempre.
- **Corrida verde nao e corrida consertada.** Re-execucao sem mudanca de codigo
  deixou verde um commit defeituoso.
- **Analise estatica de imports nao enxerga consumidor governado por doc.**
  Antes de remover, perguntar quem consome — nao so quem importa.
- **Teste pode fixar um defeito como contrato.** Dois casos nesta sessao: o CPF
  na trilha e, no ciclo anterior, o deadlock de permissoes. Um teste descreve o
  que o codigo faz; ele nao pergunta se devia.
- **Contrafactual antes de declarar causa.** "Passa aqui, falha no CI" e
  hipotese. Reproduzir a falha e ve-la sumir com o conserto e evidencia.
- **Guardrail que nao sabe falhar e decoracao.** `TestAutoriaNaTrilha` so vale
  porque foi verificado por mutacao.

---

## 11. Proximo ciclo

Em ordem:

1. **Responder a DR-006.** Bloqueia qualquer codigo de conexao do WhatsApp.
2. **IMP-352** — um envio real ao Evolution fecha o caveat 8.1, o unico que pode
   fazer entrega correta parecer entrega desconhecida. **Nao depende da DR-006.**
   Precisa do numero do fundador e do token; o token e **gerado por quem cria a
   instancia** (§8.1).
3. **IMP-359** — servidor, quando contratado. Desbloqueia o GATE-E1b e, com ele,
   as Fases A e C do Copilot.
4. **Separar o banco de dev do de teste** (§8.5) — barato agora, caro depois que
   houver dado a preservar.
5. **Decidir sobre os CPFs historicos** (§8.6) e sobre versionar o `CLAUDE.md`
   da raiz (§8.7).

Fora estes, **nao ha item tecnico desbloqueado** no PLAN-033: IMP-353, IMP-354,
IMP-356 e IMP-357 dependem de IMP-352 e IMP-359.

---

## 12. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-31 | Fase B do PLAN-033 fechada, auditoria de higiene, IMP-361 com o CPF fora da trilha, corrida de sincronizacao consertada, DR-006 aberta, e tres caveats novos: banco compartilhado entre dev e teste, CPFs historicos e `CLAUDE.md` gitignored. |
