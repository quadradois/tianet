# 2026-09-04 — Handoff: IMP-371 fechado, e os testes que não provavam nada

**Versao:** 1.1.0

**Status:** PLAN-034 com **7 dos 8 itens**. Falta o IMP-370, depois o deploy.

**Periodo coberto:** 2026-09-04 (tarde).

**Base:** `origin/master` em `cc54ced` (merge do PR #60), CI verde nos quatro
jobs **no commit de merge**.

**Substitui:** `2026-09-04-handoff-imp-369-e-o-que-o-evolution-respondeu.md`.

---

# 1. O que fechou

| Item | O quê |
|---|---|
| **IMP-371** | Os três consertos que a resposta do Evolution mandou fazer: `logout` repetido, renovação automática do QR, debounce |
| **Defeito ativo em produção** | O `logout` repetido falhava. Não falha mais |
| **Sonda do Postgres nas jornadas** | Media o servidor errado. Reprovou dois pushes antes de eu olhar direito |
| **Caveat da serialização** | **Aberto e aceito** pelo fundador, com o conserto futuro escrito |

O IMP-371 não existia quando o PLAN-034 foi escrito. Ele nasceu inteiro da
resposta que o time do Evolution Go mandou em 2026-09-04 — três achados que
**quatro rodadas de review no IMP-369 não produziram**.

---

# 2. A lição do dia: um teste verde que não prova nada é pior que teste nenhum

Escrevi um teste para provar o debounce. Ele passava. O Codex disse que ele
passava **pelo motivo errado**, e eu fiz a mutação para conferir: removi o
`!pendente` do laço, e o teste continuou verde.

Ele prendia o **clique** — e no clique o estado ainda é `idle`, então o laço nem
existia. A condição que eu achava estar testando nunca era exercitada.

Investigar isso rendeu mais que o conserto. Descobri que o `!pendente` faz uma
coisa que eu não sabia: **a alternância dele é o que faz o efeito rearmar**. As
dependências são `[renovacaoAtiva, qrcode, formAction]`; se o provedor devolver o
mesmo QR duas vezes — legítimo, o código vive 20s —, `qrcode` não muda, e sem
essa alternância nenhum temporizador novo é armado. O laço morreria calado na
primeira repetição.

**Passei a verificar cada guarda quebrando o código de propósito.** Sete
mutações: `startTransition`, `!pendente` do laço, `!pendente` do polling,
`!renovacaoAtiva`, `setVencido`, a guarda do polling e o `!conectada`. Três
delas revelaram testes que passavam sem provar nada — todas apontadas pelo
Codex, nenhuma por mim.

**Consequência prática para o próximo ciclo:** quando um teste guarda uma
condição booleana, remover a condição e ver o teste falhar é barato e é a única
evidência de que ele guarda alguma coisa. Fazer isso ANTES de declarar pronto.

---

# 3. As duas reversões, que valeram mais que os consertos

## 3.1 — Desliguei o polling durante o laço, e o Playwright me parou

A rodada 2 apontou, com razão, que suspender o polling por `!pendente` não
cancela um `refresh` **já em voo**. Desarmei o intervalo durante todo o laço de
renovação — mais seguro no papel.

**Duas jornadas Playwright reprovaram na hora**, e estavam certas: sem polling, a
tela leva até 20s para dizer "Conectado" depois do escaneamento, porque a única
leitura de estado passa a ser o `revalidatePath` de cada renovação. O preço era
do operador.

Voltei à resposta do provedor e li de novo. A recomendação da §7.1 é **literal e
estreita**: *"evitem disparar `connect`/`logout`/`qr` em paralelo"*. O `status`
aparece na lista de handlers que tocam os mapas sem lock, mas **fora da
recomendação** — ele lê o ponteiro, os outros três mexem nele.

Segui a recomendação ao pé da letra e deixei a sobra documentada como teto
conhecido, com marcador `ponytail:` no código.

**A lição:** o teste de jornada defendeu o operador contra uma decisão de
engenharia que parecia mais segura. Ele não estava medindo código, estava
medindo experiência.

## 3.2 — Recusei dois achados, e o Codex derrubou as duas recusas

Na rodada 2 recusei o achado da janela do QR (o laço termina pelo orçamento, não
pela janela) e o do caminho sem QR (parar de perguntar é o defeito que o IMP-369
fechou). **As duas recusas estavam certas na letra e erradas no efeito:**

- a janela era **rearmada a cada QR novo**, então o último código do ciclo ficava
  de pé por mais 120s — cerca de 100s exibindo um QR morto, com polling. A vida
  real de um código é 20s. Virou 30s: 20 de vida e 10 de folga;
- se as cinco tentativas voltarem sem QR, o laço acaba, o polling nunca liga e o
  aviso continuava dizendo "ele aparece assim que ficar pronto". Parar de
  perguntar está certo; **parar calado prometendo continuidade, não**.

---

# 4. O que o IMP-371 entregou

## 4.1 — O `logout` (defeito ativo, agora fechado)

Qualquer `400` de `/instance/logout` é sucesso "já desconectado", casado **pelo
status e não pela frase**: a mensagem depende do timing da autocura interna
deles. O teste é parametrizado com três corpos, dois que ninguém enumerou e um
**corpo HTTP vazio de verdade** (`content=b""`, e não `{}`, que ainda é um JSON
de dois bytes).

**Atenção ao método:** a resposta do provedor escreveu `POST`. O contrato
registra e o adapter usa **`DELETE`**. A rota é a mesma; a ADR-019 v1.2.0 tem a
ressalva.

## 4.2 — A renovação automática

20s de intervalo, teto de **quatro renovações** — cinco tentativas com a do
clique, o tamanho de um ciclo do provedor. Tentativas, e não códigos garantidos:
uma delas pode voltar sem QR.

**O laço segue a tentativa de pareamento, não o QR na tela.** Essa foi a correção
mais importante da rodada 1: o provedor responde `200` com `qrcode_base64: null`
enquanto ainda gera — caminho normal, não falha — e amarrado ao QR o laço **nunca
começava** justamente aí.

Para o laço não renascer depois do logout, o estado da ação passou a dizer
**qual** operação o produziu (`operacao: "conectar" | "desconectar"`). Antes, a
única pista era a AUSÊNCIA da chave `qrcode`, e distinguir "ausente" de "nulo" é
sutileza demais para sustentar uma garantia.

## 4.3 — A rota nova que não foi necessária

O IMP-369 ia propor uma rota para renovar o QR, e desistiu por medo de repetir o
`connect`. O provedor confirmou que repetir é seguro. **Nenhuma rota nova.**

---

# 5. Caveats vigentes

| # | Caveat | Estado |
|---|---|---|
| — | **Serialização é da ABA, não da instância** | **NOVO e aceito pelo fundador.** Duas abas podem disparar `connect` no mesmo segundo. Conserto futuro: `pg_try_advisory_lock` por tenant, que **muda o contrato** |
| — | Auditar `connected` por endpoint | **FECHADO em 2026-09-04.** Nao ha mistura, e o motivo e mais forte que "nao chamamos esses endpoints": nos **chamamos os dois** — `buscar_instancia` usa `/instance/all` e `jid_da_instancia` usa `/instance/info/:id` — e deles lemos apenas `name`, `id`, `token` e `jid`. O campo ambiguo nunca e lido. O estado vem so de `/instance/status`, que traz `Connected` e `LoggedIn` separados |
| — | Evidências visuais desatualizadas pelo selo | **NOVO.** O selo do IMP-369 mudou as 35 páginas, e só as 6 evidências do WhatsApp foram refeitas. As outras 44 mostram a barra lateral sem o selo |
| — | `gate:full` tem armadilha de ordem | **NOVO.** Ele termina em `test:harness`, que termina em `test:certification` — depois das capturas. O `hooks/pre-push` **não** usa `test:harness`, e explica por quê. A autoridade de pre-push é o hook |
| 3.5 | `/CLAUDE.md` gitignored | Mitigado pela SPEC-004; falta decidir se versiona |
| 3.7 | Playwright deixa servidor órfão | **Confirmado de novo.** Desta vez a causa fui eu: gate interrompido deixa servidor vivo e porta presa |
| — | `logout` repetido | **FECHADO** (§4.1) |
| — | Renovação automática do QR | **FECHADA** (§4.2) |

Seguem abertos: 3.2 (política de senha), 3.3 (`scheduler_worker` 69,91%), 3.4
(CPFs em `audit_log`), 3.6 (guardrail da ADR-003), 3.8 e 3.9.

---

# 6. Armadilhas de ambiente que custaram tempo hoje

**O `| tail -N` engole o código de saída.** Rodei o gate duas vezes achando que
tinha passado; o exit 0 era do `tail`. Log vai para arquivo, e o `EXIT=` é o do
comando.

**O pre-push leva ~12 minutos**, mais que o limite padrão de comando. Matar o
push no meio deixa servidor órfão E evidências regeradas na árvore.

**A suíte de jornadas morre por falta de memória** quando roda depois das outras
14, mesmo passando 8/8 isolada. Com ~3 GB livres o servidor Next cai
(`ERR_CONNECTION_RESET`, depois `REFUSED`). Fechar abas antes do push é
solução real.

**A sonda do Postgres nas jornadas estava errada, e agora não está.** O
`pg_isready` rodava sem `-h`, falando pelo socket Unix — e durante o `initdb` a
imagem sobe um servidor **temporário** com `listen_addresses=''` que atende ali e
responde "pronto". O seed conecta por TCP e caía no intervalo entre o temporário
morrer e o real subir. Com `-h 127.0.0.1` a pergunta passa a ser a mesma que o
seed faz.

---

# 7. Fluxo de trabalho vigente

```
commit local → review do Codex ATÉ APROVAR → PR → merge → CI do MERGE → próximo
```

**Três rodadas foram necessárias neste ciclo**, e a terceira ainda achou coisa
que valia. Uma rodada só teria mergeado um laço que não começava no caminho mais
comum, com um teste de debounce que não testava o debounce.

**O gate roda DEPOIS do review, e achou três vezes o que o review não achou:** o
SHA da evidência, a sonda do Postgres e a fragilidade de memória.

**Liberar as portas antes do push** continua valendo — 3101 a 3109 e 3201 a 3209.

---

# 8. Próximo ciclo, em ordem

1. **IMP-370** — worker lê o token do repositório e grava o estado da conexão; o
   aviso de queda nasce aqui;
2. **IMP-359 — deploy.** Sem insumo externo pendente. Inclui medir e apagar a
   `adm_tianet`, nessa ordem;
3. **Mercado Pago**, depois do deploy.

Itens pequenos que podem entrar em qualquer janela: auditar o campo `connected`,
refazer as 44 evidências que o selo desatualizou, e decidir se `gate:full`
deveria parar de terminar em `test:harness`.

## 8.1 — Âncoras do IMP-370, levantadas em 2026-09-04

Levantadas ao fechar o IMP-371, para a sessão que executar não gastar a primeira
hora procurando. **Nenhuma decisão foi tomada aqui** — só a leitura do terreno.

**Onde o ambiente ganha hoje:** `src/emprestimo/worker/scheduler_worker.py:336`
lê `EVOLUTION_INSTANCE_TOKEN` e, na falta dele, exige ambiente que não seja
produção. É esse ponto que a precedência do PLAN-034 §4.5 preserva.

**A leitura pelo repositório já existe:** `find_token(tenant_id)` está no
contrato (`src/emprestimo/domain/platform/ports.py:128`) e é usado pelo
`_garantir_instancia`. Não precisa nascer nada novo para ler.

**A dobra que vai aparecer, e é de desenho:** o
`EvolutionWhatsAppNotificationChannel` recebe o `instance_token` **no
construtor** (`infrastructure/notifications/whatsapp.py:16`), e o worker monta
**um canal só, na subida**. O token do repositório é dado por Tenant, e só
existe dentro de uma UoW — então lê-lo de lá exige resolver o token **por envio**
(ou construir o canal preguiçosamente), e não mais uma vez no bootstrap. Essa é
a decisão de desenho do item, e ela não estava escrita em lugar nenhum.

**Para gravar o estado:** `_sincronizar`
(`src/emprestimo/application/conexao_whatsapp.py:173`) é o que o `GET` de estado
usa hoje, e ele **vai ao provedor toda vez** — o pareamento vem de leitura, nunca
de inferência local. É exatamente aqui que o caveat do campo `connected` morde:
`/instance/status` diz socket aberto, `/instance/all` e `/instance/get` dizem
autenticado. Reaproveitar `_sincronizar` herda a semântica certa; escrever uma
leitura nova é onde alguém erra.

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.1.0 | 2026-09-04 | Acrescenta a §8.1 com as ancoras do IMP-370, levantadas a pedido do fundador antes de abrir a sessao nova. A que valeu a checagem: o canal do WhatsApp recebe o token NO CONSTRUTOR e o worker monta um canal so na subida — ler o token do repositorio, que e dado por Tenant dentro de uma UoW, exige resolve-lo por envio. E decisao de desenho do item, e nao estava escrita em lugar nenhum. |
| 1.0.0 | 2026-09-04 | IMP-371 entregue e mergeado em `cc54ced`, com CI verde no commit de merge. Tres rodadas adversariais do Codex, todas REFUTADO, treze achados acatados. O dia foi decidido por uma mutacao: removi uma guarda de proposito e o teste que deveria protege-la continuou verde — o que revelou que o `!pendente` faz uma coisa que eu nao sabia. Duas jornadas Playwright derrubaram uma decisao de engenharia que parecia mais segura e custava 20s ao operador. E o gate achou tres defeitos que nenhuma rodada de review achou. |
