# 2026-09-01 - Handoff: WhatsApp no ar, PLAN-034 com a infraestrutura pronta

**Versao:** 1.0.0

**Status:** O WhatsApp da TiaNet **esta conectado e enviando**. O PLAN-034 tem
**3 dos 7 itens** entregues — as tres camadas abaixo da API: cifra, persistencia
e cliente do provedor. Restam casos de uso, endpoints, tela e a migracao do
worker.

**Periodo coberto:** 2026-08-31 a 2026-09-01

**Base:** `origin/master` em `42e079b`, arvore limpa. **Onze PRs mergeados**
(#39 a #49).

**Substitui:** `2026-08-31-handoff-plan-033-fase-b-fechada.md`.

---

## 1. Estado Executivo

Duas coisas mudaram de natureza neste periodo.

**O canal saiu do papel.** O WhatsApp deixou de ser integracao com formato
suposto e passou a ser instancia pareada, enviando, com o formato conferido
contra o servidor real. O caveat de maior risco do sistema fechou.

**A decisao de escopo subiu de degrau.** "Um Credor, um Tenant, um usuario"
vivia num handoff — registro de sessao, o degrau mais baixo — enquanto o
`FOUNDATION-006`, aprovado, dizia o contrario. Agora e ADR, com guardrail que
reprova quem reintroduzir a afirmacao.

O fio condutor do periodo: **verificacao que nao exercita o caminho da mudanca
nao e verificacao.** Declarei "provado" tres vezes antes de um gate discordar, e
nas tres o gate estava certo. Detalhes na §7.

---

## 2. O que foi entregue

### Governanca e decisao

| PR | Entrega |
|---|---|
| #39 | **ADR-003** — escopo single-tenant do v1, com guardrail em `docs:test` |
| #41 | **DR-006 resolvida** — tela de QR na plataforma, token cifrado, webhook para o agente |
| #44 | **PLAN-034** — sete itens para a conexao do WhatsApp |

### Correcoes estruturais

| PR | Entrega |
|---|---|
| #42 | `.gitignore` protege `docs/credenciais/` e `.bak`; **IMP-352 fechado** |
| #43 | **Banco de teste separado do de desenvolvimento** — caveat 8.5 |
| #40, #45 | Corridas nos testes de a11y: locator ambiguo e titulo do Next |

### PLAN-034 — infraestrutura

| PR | Item |
|---|---|
| #46 | **IMP-364** — cifra Fernet, sem modo degradado |
| #47 | **IMP-365** — migration, Entity, porta e repositorio |
| #48, #49 | **IMP-366** — cliente de gestao do Evolution, apos seis rodadas de review |

---

## 3. O WhatsApp esta no ar

Feito manualmente em 2026-08-31, e e isto que a tela vai automatizar:

| | |
|---|---|
| Tenant `tianet` | criado pela equipe que administra o Evolution |
| Instancia `adm_tianet` | `8a8c901f-16f9-4431-b19d-ed69cccc46c0` |
| Numero pareado | `556284290661` |
| Envio validado | pela classe de producao, resultado `ACEITA` |

**Tres fatos verificados contra o servidor**, e nao contra documentacao:

1. **`data.Info.ID` e eco** do `id` que enviamos. O Evolution nao emite
   identificador proprio — entao nao existe id do provedor para consultar
   depois, e entrega so se confirma por `Receipt`. Isso ja era o que
   `consultar_status` declarava; agora esta verificado.
2. **`webhookUrl` vazia e aceita** (`200` com `""`). Sustenta a decisao da
   DR-006 de apontar para o agente, que ainda nao existe.
3. **`Connected` e `LoggedIn` sao estados distintos.** So o segundo significa
   WhatsApp ligado. A instancia recem-criada responde `Connected: true` com
   `LoggedIn: false`.

As credenciais do tenant estao em `docs/credenciais/` — **fora do git**, e agora
protegidas por regra ampla no `.gitignore`.

---

## 4. As seis rodadas de review do IMP-366

O item passou por seis revisoes do Codex antes de ser aprovado. **Onze defeitos
reais**, dos quais tres mereciam ter sido pegos por mim:

| Defeito | O que teria acontecido |
|---|---|
| **`bool("false")` e `True`** | reportar pareado quando o provedor disse o contrario |
| **token com espacos** | criacao bem-sucedida e 401 em tudo depois, para sempre |
| **redirect aceito como logout** | marcar desconectado com a instancia ainda pareada |
| falha de transporte crua | indisponibilidade sem tratamento no handler |
| `DecodingError` escapando | idem, por heranca que `TransportError` nao cobre |
| QR gerando vs. provedor fora | tela sem como distinguir "aguarde" de "chame alguem" |
| `token=""` gerava UUID | credencial que o chamador nao pediu |
| PNG truncado, prefixo frouxo | imagem que nao renderiza |
| **fixture nao era PNG** | o teste afirmava que um nao-PNG passa |

**O primeiro e o mais instrutivo.** Passei o item distinguindo `Connected` de
`LoggedIn` no dominio, no cliente e nos testes — e escrevi a conversao que
permitiria exatamente o erro que estava evitando. Cuidado no desenho nao
substitui revisao.

### Uma discordancia registrada

Na quinta rodada o Codex pediu validar a estrutura inteira de chunks PNG, ou usar
parser de imagem. **Nao foi atendido**, e o motivo esta no commit: exigiria
Pillow para validar uma imagem que apenas repassamos, e a consequencia nao e
comparavel — PNG corrompido e imagem quebrada visivel na hora, nao estado
invertido silencioso. A substancia (truncamento) foi atendida com assinatura mais
chunk IEND, duas linhas, sem dependencia.

**Discordar de um achado e legitimo; discordar sem registrar o motivo nao e.**

---

## 5. Onde o PLAN-034 esta

| Item | Estado |
|---|---|
| IMP-364 — cifra | ✅ |
| IMP-365 — persistencia | ✅ |
| IMP-366 — cliente do Evolution | ✅ |
| **IMP-367 — casos de uso e permissoes** | **proximo** |
| IMP-368 — endpoints e contrato | depende do 367 |
| IMP-369 — tela | depende do 368 |
| IMP-370 — worker le do repositorio | depende do 365 |

As tres camadas abaixo da API estao prontas: **saber cifrar**, **ter onde
guardar**, **saber falar com o provedor**. O IMP-367 e onde elas se encontram.

**Contrato publico ainda em 107 operacoes e 135 schemas** — nenhum endpoint novo
foi exposto. O PLAN-034 §6 declara a chegada a 110/138 no IMP-368.

---

## 6. Fluxo de trabalho acordado

Vale mais que as entregas, porque a ordem errada custou dois merges ruins:

```
commit local  →  review do Codex ate aprovar  →  abre PR  →  Claude merga  →  CI  →  proximo
```

**O review vem ANTES do PR.** Duas vezes neste periodo um PR foi mergeado antes
das correcoes chegarem (#35 e #48), e nas duas o `master` ficou com a versao
reprovada. No #48 foram seis rodadas perdidas, recuperadas por cherry-pick no
#49.

O fundador nao merga mais; quem merga e o Claude, depois da aprovacao.

---

## 7. As tres verificacoes que nao verificavam

Padrao que se repetiu, e o mais util a carregar:

**Separacao de bancos (#43).** Rodei `test_devedor_application.py`, que usa a
sessao da fixture direto, e declarei provado. O gate achou **401 em toda a suite
de API**: a aplicacao resolvia a propria sessao por `DATABASE_URL` e continuava
no banco antigo. O arquivo que escolhi nao passava por HTTP — justamente o
caminho que a mudanca quebrava.

**Corrida da trilha (#36 do periodo anterior).** Duas tentativas de contrafactual
falharam, e foi a **falha em reproduzir** que mostrou que a hipotese estava
errada. O `error-context.md` do artefato do CI deu a resposta real.

**`git add -A` depois de suite Playwright (#45).** Varreu quatro PNGs de
evidencia regeradas para dentro do commit; o `docs:test` reprovou por SHA —
sintoma a milhas da causa. Use caminho explicito.

---

## 8. Caveats vigentes

### 8.1 Producao nao existe — **e o proximo marco**

Servidor **liberado** (VPS provisionada, dominio `tianet.com.br`), mas sem
deploy, TLS, backup ou CD. E o **IMP-359**, e bloqueia o GATE-E1b.

**O `EVOLUTION_INSTANCE_TOKEN` deixou de ser bloqueio**: o token existe. Com
`APP_ENV=production` e sem ele, o worker recusa subir (`scheduler_worker.py:342`)
— continua verdadeiro, mas agora e configuravel.

### 8.2 Contrato declara politica de senha mais frouxa que o sistema aceita

Herdado. Dominio exige 10 caracteres; schemas mantem `min_length=1`. Divida
declarada.

### 8.3 `scheduler_worker.py` em 69,91%

Herdado. O grosso e o `main()` de bootstrap.

### 8.4 CPFs historicos em `audit_log`

O vazamento novo foi fechado no IMP-361, mas os registros anteriores continuam —
um por cadastro duplicado. Limpar e mudanca destrutiva de banco, decisao
separada.

### 8.5 `CLAUDE.md` da raiz e gitignored

`.gitignore:43`. Edicoes vivem so na maquina que as fez. `frontend/CLAUDE.md` e
`frontend/AGENTS.md` **sao** versionados — assimetria que merece decisao.

### 8.6 `DecodingError` nao tratado em `resend.py` e `whatsapp.py` — NOVO

Mesma lacuna corrigida no cliente do Evolution existe nos dois adapters antigos
(tres ocorrencias). La a excecao cai no `except Exception` do worker e vira falha
temporaria — classificacao imprecisa, nao crash. Item proprio, pequeno.

### 8.7 Suite Playwright deixa servidor orfao — NOVO

Push interrompido deixa `backend-fixture.mjs` vivo na porta, e a suite seguinte
falha **sem imprimir nada**. Aconteceu tres vezes neste periodo. O hook restaura
evidencias sozinho, mas nao mata processo — candidato a melhoria.

---

## 9. Ambiente local

Stack Docker parada ao fim do periodo, com **apenas o Postgres de pe** — foi
derrubada para reduzir contencao no gate. Para voltar:

```
docker compose up -d
docker compose run --rm migrate
```

| | |
|---|---|
| Frontend | `http://localhost:3000` |
| API | `http://localhost:8010` — **nao** 8000 |
| Tenant | `tianet-local` |
| Admin | `admin@tianet.local` |

O campo do login e `identificador_institucional`, nao `tenant_identificador`.

**O banco de teste agora e `emprestimo_test`**, criado sozinho. Rodar a suite
nao apaga mais o banco de desenvolvimento.

---

## 10. Proximo ciclo

1. **IMP-367** — casos de uso e permissoes. Primeiro item que consome as tres
   camadas prontas.
2. **IMP-368** — endpoints e contrato. O guardrail cobra plano, contadores e
   snapshot OpenAPI juntos.
3. **IMP-369** — a tela.
4. **IMP-370** — worker le o token do repositorio, com o ambiente mantendo
   precedencia.
5. **IMP-359 — deploy.** Acordado como **ponto de parada**: a tela e o resto
   ficam prontos antes de configurar a VPS.

Itens menores acumulados: o `DecodingError` dos adapters antigos (§8.6), a
limpeza de portas no pre-push (§8.7), a decisao sobre CPFs historicos (§8.4) e
sobre versionar o `CLAUDE.md` (§8.5).

---

## 11. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-09-01 | WhatsApp conectado e validado contra o servidor real; ADR-003 fixa o escopo single-tenant com guardrail; DR-006 resolvida; PLAN-034 com tres de sete itens; banco de teste separado do de desenvolvimento; e o fluxo de review antes do PR, acordado depois de dois merges de versao reprovada. |
