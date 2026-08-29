# 2026-08-27 - Handoff: PLAN-032 fechado, PLAN-033 desenhado e Fase B em execucao

**Versao:** 1.0.0

**Status:** PLAN-032 **concluido** (18/18). PLAN-033 desenhado, refutado por
revisao adversarial, corrigido e em execucao — quatro itens entregues, GATE-E1b
bloqueado por insumo externo.

**Periodo coberto:** de 2026-08-25 (auditoria de CI) a 2026-08-27

**Base:** `origin/master` em `89e4857`, mais dois PRs abertos e uma correcao nao
commitada ao fim da sessao — ver §6.

**Substitui:** `2026-08-25-handoff-plan-032-mvp-recertificado.md`, que continua
valido como registro daquela data.

---

## 1. Estado Executivo

A sessao comecou fechando o PLAN-032 e terminou com o PLAN-033 em execucao. O
fio condutor de tudo o que foi feito: **funcionalidade existente cujo caminho de
falha ninguem exercitava**.

Sete defeitos reais foram encontrados, e **nenhum deles era do codigo escrito
nesta sessao** — todos ja estavam no sistema, esperando alguem percorrer a
cadeia inteira:

| Defeito | Como apareceu |
|---|---|
| `audit_log.status` VARCHAR(20) derrubava a entrega do aviso de sobra | teste do caminho de erro (IMP-350) |
| Cobertura era 89,55%, nao 90% — o relatorio arredondava | `--precision=2` |
| Beco sem saida do token de ativacao, sem saida nenhuma | verificacao do caveat 4.3 |
| Quem submetia proposta podia aprova-la | revisao adversarial (IMP-360) |
| Nao existia rota para criar Usuario | revisao adversarial (IMP-355) |
| Somar saldo exigia faze-lo fora do Motor | revisao adversarial (IMP-362) |
| **O sistema subia e nao deixava fazer nada** | **teste em Docker** |

O ultimo e o mais instrutivo, e esta na §4.

---

## 2. O que foi entregue

### PLAN-032 — fechado

| Item | Entrega |
|---|---|
| IMP-341 | As tres vozes do token de ativacao alinhadas |
| IMP-342 | Politica minima de credencial no funil do dominio, nao nos schemas |
| IMP-343 | Heartbeat com consumidor no `/health`; worker parado **degrada**, nao derruba |
| IMP-350 | Caminho de entrega coberto; achou o `VARCHAR(20)` |
| IMP-345 | Recertificacao: 33 gates verdes sobre arvore limpa, cobertura **90,02%** |
| IMP-351 | Provisionamento por API e fluxo de ativacao removidos |

### PLAN-033 — desenhado e em execucao

O desenho v1.0.0 foi **REFUTADO** por revisao adversarial (Codex/fable-judge)
com 30 achados. Todos aceitos, organizados em 12 tarefas com direcao decidida, e
a correcao delegada ao mesmo revisor. A v1.1.0 substituiu premissas por trabalho
explicito; hoje esta em **v1.7.0**.

| Item | Entrega |
|---|---|
| IMP-358 | Governanca: adendos as ADR-002 e ADR-009, DR-005, reconciliacoes documentais |
| IMP-360 | `comercial.proposta.submeter` separada de `decidir` |
| IMP-355 | `POST /iam/usuarios` — o sistema nao permitia criar um segundo operador |
| IMP-362 | `GET /credit/devedores/{id}/saldo` — soma no Motor |

**Contrato publico:** 107 -> 105 (IMP-351) -> 106 (IMP-355) -> **107 operacoes**
e **135 schemas** (IMP-362). Snapshot vigente com SHA-256
`23d8d91f5f5890ef5ca010d1fc45a458458e5028042c80e7e15dbf82052af76a`.

---

## 3. Decisoes do fundador registradas

| Decisao | Onde |
|---|---|
| **BYOK** — o cliente nao usa Anthropic; API compativel com OpenAI, endpoint configuravel | DR-005, PLAN-033 v1.2.0 |
| **PII liberada no prompt**, inclusive CPF integral de terceiros | DR-005 §1 |
| **Sem teto de custo** em moeda; rate limiting e medicao permanecem | DR-005 §3 |
| **Retencao de 90 dias** para conversa, inbox e tool-call | DR-005 §4 |
| **E-mail fora do escopo** do MVP — destravou o deploy | `contexto-externo.md` §2.3 |
| **Sem webhook publico** na TiaNet; o agente recebe e chama endpoint autenticado | `contexto-externo.md` §2.2 |
| **Gate dividido** em E1a (governanca, cumprido) e E1b (canal e producao) | PLAN-033 §11 |
| **Uso pessoal: um Tenant, um usuario** | §4 deste handoff |

Sobre a PII: a Arquitetura recomendou minimizacao com mascara e apresentou,
antes da decisao, que nenhuma funcionalidade do v1 perderia nada, que em BYOK o
prompt pode transitar por agregador, e que os CPFs sao de **terceiros** com o
fundador como controlador sob LGPD. A decisao foi mantida ciente disso e esta
registrada com essa formulacao para valer daqui a um ano.

---

## 4. O defeito que so o Docker encontrou

**O sistema subia, autenticava, e o unico usuario tomava 403 em tudo.**

`POST /platform/tenants`, removido pelo IMP-351, era o **unico** lugar que
concedia `PERMISSOES_ADMIN_TENANT`. O `bootstrap_plataforma` dava apenas as
cinco permissoes `tenant.*` — e o endpoint que elas autorizavam tambem havia
sido removido.

Observado na stack real: login **200**, e depois **403** em criar usuario,
criar perfil e consultar saldo. Inclusive em `perfil.gerir`, entao **nao havia
como se autoconceder permissao**. Deadlock completo.

**Por que os 18 gates nao pegaram:** cada teste de integracao monta o RBAC de
que precisa, direto pelo repositorio. Nenhum pergunta *"quem, partindo de um
banco vazio, consegue operar o sistema?"*.

**Pior que isso: dois testes fixavam o deadlock como comportamento esperado.**
O unitario exigia que o perfil tivesse **exatamente** as cinco `tenant.*`, e o
de integracao afirmava `assert not carregado.permite("devedor.criar")` — ou
seja, **afirmava que o unico usuario nao podia operar**.

Os testes nao erraram sozinhos. Eles descreviam fielmente um sistema em que o
provisionamento por API concedia as permissoes operacionais. Quando o IMP-351
removeu esse endpoint, **os testes continuaram verdes descrevendo um mundo que
deixou de existir** — e nenhum deles fazia a pergunta que importava. E o mesmo
padrao que o IMP-311 encontrou nas jornadas em 2026-08-20: suite descrevendo um
produto que nao existia mais.

**A correcao (IMP-363):** o bootstrap concede o catalogo inteiro — 55
permissoes, contra 5. Alinhada com a decisao de uso pessoal: separar papel
administrativo de operacional so faria sentido com mais de uma pessoa, e aqui
produzia exatamente o deadlock.

**A licao operacional:** suite verde nao prova sistema operavel. O teste em
Docker levou cinco minutos e encontrou o que 1031 testes nao viam, porque era a
unica verificacao que partia de um banco vazio e perguntava se dava para
trabalhar.

---

## 5. Evidencias

Ultimo conjunto completo verde, sobre `b3f7915`:

| Gate | Resultado |
|---|---|
| `pytest` (PostgreSQL 16 real) | **1031 verdes** |
| `docs:validate` | 356 OK, 35 avisos, **0 erros** |
| `docs:test` | **173/173** |
| frontend unit / component / contrato / bff | verdes |
| treze suites Playwright | verdes |
| `test:jornadas` | **8/8** em stack real |
| `quality:migrations` | ciclo completo de ida e volta |

Seis PRs mergeados nesta sessao (#26 a #31), todos **verdes na primeira
tentativa** — resultado direto da auditoria de CI que abriu a sessao.

**Verificacao em stack real** (Docker, 2026-08-27), depois da correcao do
bootstrap: login 200; criar operadora 201 e ela **autentica**; segredo fraco
422; devedor inexistente 404; `enviar-para-analise` passa na permissao;
`/health` sem worker responde **200 com `degraded`**.

---

## 6. Estado ao fim da sessao — o que NAO esta no master

Tres coisas, e todas precisam de acao:

1. **PR #32** (IMP-355) — aberto, CI verde, `MERGEABLE`.
2. **PR #33** (IMP-362) — aberto, saiu da branch do #32. **Mergear o #32
   primeiro** deixa o historico linear.
3. **Correcao do bootstrap (IMP-363)** — commitada junto com este handoff, na
   branch `codex/imp-362-saldo-agregado`, com os dois testes corrigidos e os 18
   gates verdes (pytest **1031**). Vai ao master pelo **PR #33**. Sem ela, um
   deploy novo nasce inoperavel.

---

## 7. Caveats vigentes

### 7.1 O formato de envio do Evolution nao esta validado

Herdado e **ainda aberto**. O payload `{number, text, id}` e o criterio
`data.Info.ID` vieram de documentacao externa. Se divergir, todo envio
bem-sucedido vira `DESCONHECIDO` — sem duplicata para o devedor, com prejuizo de
escrituracao. Virou o **IMP-352**, e espera apenas o numero do fundador e o
`EVOLUTION_INSTANCE_TOKEN` no ambiente.

### 7.2 Contrato declara politica de senha mais frouxa do que o sistema aceita

O dominio exige 10 caracteres; os schemas mantem `min_length=1` e a recusa vem
como 422. Deliberado, para nao regerar snapshot — divida declarada.

### 7.3 Producao nao existe

Servidor **nao provisionado**, sem dominio, TLS, backup ou CD. O
`docker compose up` sobe a stack; o caminho automatizado nao existe. E o
**IMP-359**, e bloqueia o GATE-E1b.

### 7.4 Build do Docker falhou por TLS ao PyPI

Nesta maquina, `pip install` dentro do build falhou com `SSLEOFError`, enquanto
o host baixava do PyPI em 0,3 s e o Docker puxava imagens normalmente. Ambiente,
nao codigo — a verificacao foi feita rodando a API do host contra o Postgres do
container.

### 7.5 `scheduler_worker.py` em 69,91%

O grosso do que falta e o `main()` de bootstrap. Cobri-lo inflaria o numero sem
cobrir comportamento.

---

## 8. Armadilhas de ambiente confirmadas nesta sessao

Todas custaram tempo real e reaparecem.

- **Servidor orfao nas portas de teste.** Suite interrompida deixa o servidor
  vivo; a proxima falha **sem imprimir nada**, parecendo defeito de codigo. A
  faixa correta e **3100..3112 e 3201..3212** — a 3100 e do config padrao,
  usado por `e2e`, `a11y` e `visual`, e ficar em 3101+ deixa justamente ela de
  fora (erro que eu cometi).
- **Evidencias sujas depois de suite de captura interrompida.** O `docs:test`
  reprova por SHA de evidencia — sintoma a milhas da causa. Rodar
  `git checkout -- docs/audits/evidence/` antes do proximo push.
- **`| tail` esconde o exit code** do comando anterior.
- **O relatorio de cobertura arredonda**: use `coverage report --precision=2`.
- **`DATABASE_URL` e obrigatorio** para a suite local; o caveat esta certo e eu
  mesmo esqueci nesta sessao.
- **A API do compose escuta na porta do `.env`** (`API_PORT=8010`), nao 8000.

---

## 9. Proximo ciclo

Em ordem:

1. **Mergear #32 e #33**, nessa ordem, e **commitar o IMP-363** — sem ele, um
   deploy novo nasce inoperavel.
2. **IMP-352** — um envio real ao Evolution fecha o unico caveat que pode fazer
   entrega correta parecer entrega desconhecida. Precisa do numero e do token.
3. **IMP-359** — servidor, quando contratado. Desbloqueia o GATE-E1b e, com ele,
   as Fases A e C do Copilot.
4. **IMP-361** — autoria na trilha; ultimo item da Fase B, nao depende de nada
   externo.

---

## 10. Regras que a sessao confirmou

- **Suite verde nao prova sistema operavel.** Cinco minutos de Docker acharam o
  que 1031 testes nao viam.
- **Erro silenciado vira sintoma distante da causa.** `handler_ausente`,
  `2>/dev/null || true` e `except Exception: return "unhealthy"` sao a mesma
  doenca em tres roupas.
- **Corrigir na causa, nao no call site.** O `VARCHAR(20)` tinha contorno num
  arquivo que o seguinte nao copiou.
- **Cadeia de SHA tem tres categorias:** vigente substitui, cadeia acrescenta,
  registro datado se mantem com nota. Confundi-las falsifica historia.
- **Contador que cobra e guardrail funcionando.** Seis contadores por endpoint
  novo e a superficie publica sendo governada, nao burocracia.
- **Revisao adversarial vale o custo.** Refutou um desenho que parecia pronto e
  produziu tres itens que consertaram problemas ja existentes.

---

## 11. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-27 | Fechamento do PLAN-032, desenho e Fase B do PLAN-033, decisoes do fundador, o defeito achado em Docker e os tres pendentes ao fim da sessao. |
