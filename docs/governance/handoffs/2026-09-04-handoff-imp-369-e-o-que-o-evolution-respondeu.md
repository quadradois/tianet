# 2026-09-04 — Handoff: IMP-369 entregue, e o que perguntar ao provedor valeu mais que medir

**Versao:** 1.0.0

**Status:** PLAN-034 com **6 dos 7 itens**. Falta o IMP-370, depois o deploy.

**Periodo coberto:** 2026-09-03 (noite) e 2026-09-04.

**Base:** `origin/master` em `588747a` (merge do PR #58). O IMP-369 vive no branch
`feat/imp-369-tela-conexao-whatsapp`, com PR aberto.

**Substitui:** `2026-09-03-handoff-imp-368-fechado-spec-003-e-o-gate-que-o-review-nao-substitui.md`.

---

# 1. O que fechou

| Item | O quê |
|---|---|
| **IMP-369** | Selo na barra lateral + tela de conexão. Review do Codex feito, 4 achados corrigidos |
| **ADR-019 v1.1.0** | A premissa da convergência do `logout` foi **medida — e é falsa** |
| **Caveat da deduplicação** | Aberto desde 02/09, **fechado**: o Evolution não deduplica |

---

# 2. A decisão que mais rendeu no dia: perguntar em vez de medir

O IMP-369 travou numa dúvida técnica — o QR renova sozinho? dá para pedir de
novo sem estragar nada? Eu estava a caminho de sondar a instância de produção.

**O fundador propôs outra coisa: escrever para o time que mantém o Evolution Go.**
Escrevemos `docs/whatsapp/2026-09-04-solicitacao-esclarecimento-evolution.md` com
cinco blocos de pergunta, cada uma dizendo *o que faríamos com a resposta*.

Eles responderam **por leitura do código-fonte, com citação `arquivo:linha`**, em
`docs/whatsapp/2026-09-04-resposta-esclarecimento-evolution.md`. Nenhuma pergunta
exigiu teste em produção. Nenhum número de fundador gasto.

**Duas perguntas abertas havia semanas fecharam de uma vez**, e uma delas com o
resultado **contrário** ao que tínhamos assumido.

**A lição para o próximo ciclo:** antes de sondar sistema de terceiro, verificar
se o terceiro é alcançável. Neste caso o provedor é do próprio time — e eu tinha
transformado *"não existe ambiente de teste separado"* em *"não dá para
verificar"*, o que travou a conversa sem motivo. O fundador desfez o nó.

---

# 3. O que a resposta do Evolution muda

## 3.1 — A premissa da ADR-019 é FALSA *(defeito em produção, ainda não corrigido)*

`POST /instance/logout` numa instância já desconectada **sempre retorna `400`**.
Nunca `2xx`. O fluxo passa por `ensureClientConnected`, que devolve
`"no active session found"` ou `"client disconnected"`.

**Nosso adapter recusa qualquer não-2xx**, então a segunda desconexão **falha
hoje**. Não é risco teórico — é defeito esperando a primeira repetição.

**Conserto pendente, e é pequeno:** tratar **qualquer `400`** de
`/instance/logout` como sucesso "já desconectado", igual ao que já fazemos com
`record not found` na exclusão. **Não filtrar pelo texto da mensagem** —
recomendação deles: a mensagem exata depende do timing da autocura interna.

A decisão da ADR não muda; o adapter muda. ADR-019 §"A premissa foi medida"
carrega o detalhe.

## 3.2 — Não existe deduplicação em `/send/text` *(caveat fechado)*

O `id` que enviamos é só o stanza ID repassado ao whatsmeow: sem checagem, sem
unicidade, sem cache. **Reenviar entrega duas mensagens.**

A postura atual — resultado incerto vira conciliação manual — **deixa de ser
cautela e passa a ser medição**. Está certa e permanece.

## 3.3 — O QR: repetir o `connect` é seguro *(desbloqueia a renovação automática)*

- `GET /instance/qr` **acompanha a rotação** — relê a instância a cada chamada
- **20s por código**, fixo na lib, **sem rate limit**
- Ao fim do 5º, a instância **cai** (`DisconnectReason="QR code limit reached"`),
  mas `GET /instance/qr` **se autocura** e reinicia o ciclo
- **`POST /instance/connect` repetido é seguro**: não reinicia o ciclo, não
  duplica handler, só re-aponta webhook. Palavras deles: *"resolve a renovação
  sem rota nova do lado de vocês"*
- `QRTimeout` dispara **uma vez por ciclo**, não por código — não serve para
  empurrar o próximo QR

**Consequência:** a rota nova que eu ia propor **não é necessária**. Descartei a
opção barata por medo, e a resposta estava a uma pergunta de distância.

## 3.4 — Dois achados que ninguém pediu

**Race condition no provedor.** Os mapas de client (`clientPointer`,
`myClientPointer`, `killChannel`) **não têm lock**, e são acessados por handlers
HTTP concorrentes. Recomendação deles: **não disparar `connect`/`logout`/`qr` em
paralelo** para a mesma instância. Precisamos de debounce no botão.

**O campo `connected` significa coisas diferentes por endpoint.** Em
`/instance/status` é socket aberto; em `/instance/all` e `/instance/get` é
**autenticado**. Falta auditar se o nosso adapter mistura os dois.

---

# 4. O IMP-369, e o que o review ensinou

## 4.1 — O que foi entregue

**Selo na barra lateral**, fora do menu, dois estados só. Lê o **contexto
operacional** — que já é buscado nas 35 páginas — e não o provedor. O `GET` de
estado vai ao Evolution toda vez; um selo lendo ele daria uma chamada externa por
página aberta.

**Tela** com botão explícito de conectar, quatro estados, polling, a11y sem
violação séria e 18 testes de jornada.

## 4.2 — Quatro achados do review, todos meus

**Polling sem fim.** Seguia o *estado* da conexão, então ligava ao abrir a tela
sem clicar, e voltava a ligar depois de "Desconectar". Agora segue **o QR na
tela**, com prazo.

**QR velho ressuscitando.** O resultado do conectar sobrevivia ao `refresh` e
reaparecia depois do logout. Consertado pela **estrutura**: uma ação só para as
duas operações, escolhida por `intent` — desconectar substitui o resultado.

**Mensagem prometendo QR inexistente** e **selo contraditório** (`pareada: true`
com `numero: null`).

## 4.3 — O padrão que se repetiu três vezes

**Comentário que promete o que o código não faz.** No IMP-368 foi o rollback que
dizia cobrir "cifra ausente" e não cobria. Depois foi o "usuário somente-leitura"
que não existe. Agora o polling que "só roda quando há o que esperar" e rodava
sempre.

Nas três, o comentário passou no review humano — o meu — porque **eu lia a
intenção, não o código**. O que pegou foi o revisor externo, toda vez.

## 4.4 — A regra de governança que fez trabalho de verdade

O guardrail que fixa a lista de Client Components reprovou **dois** componentes
novos. Olhando com o critério dele, o polling não precisava de arquivo próprio —
virou hook de dez linhas dentro da tela. A lista subiu por **um**, deliberadamente.

E o lint do React recusou `setState` síncrono em efeito, o que me obrigou a
**derivar** estado em vez de espelhar. O desenho final é melhor por causa da
recusa.

---

# 5. Caveats vigentes

| # | Caveat | Estado |
|---|---|---|
| — | **`logout` repetido falha** (§3.1) | **NOVO e ativo.** Defeito em produção, conserto pendente no adapter |
| — | Renovação automática do QR | Desbloqueada (§3.3), **não implementada** |
| — | Debounce em `connect`/`logout`/`qr` | **NOVO** (§3.4). Race no provedor |
| — | Auditar `connected` por endpoint | **NOVO** (§3.4) |
| 3.5 | `/CLAUDE.md` gitignored | Mitigado pela SPEC-004; falta decidir se versiona |
| 3.7 | Playwright deixa servidor órfão | **Confirmado de novo**: derrubou 3 pushes |
| — | Deduplicação no envio | **FECHADO** — medido, não existe (§3.2) |

Seguem abertos: 3.2 (política de senha), 3.3 (`scheduler_worker` 69,91%), 3.4
(CPFs em `audit_log`), 3.6 (guardrail da ADR-003), 3.8 e 3.9.

---

# 6. Fluxo de trabalho vigente

```
commit local → review do Codex até aprovar → PR → merge → CI → próximo
```

**O review vem ANTES do PR.** **Verificar o commit de MERGE, não os checks do
PR.** E rodar o **gate de pre-push** é parte de verificar: ele achou o que três
rodadas de review não acharam.

**Acrescentar:** liberar as portas 3107/3109/3207/3209 antes de todo push. A
suíte Playwright deixa servidor órfão, e o gate reprova por porta presa — não por
código.

---

# 7. Próximo ciclo, em ordem

1. **Consertar o `logout`** (§3.1). Defeito em produção, conserto pequeno;
2. **Renovação automática do QR** (§3.3), com debounce (§3.4). Repetir o `POST`
   é seguro — sem rota nova;
3. **Rodada 2 do Codex** no IMP-369, com os consertos acima;
4. **IMP-370** — worker lê o token e grava o estado; o aviso de queda nasce aqui;
5. **IMP-359 — deploy.** Sem insumo externo pendente. Inclui medir e apagar a
   `adm_tianet`, nessa ordem;
6. **Mercado Pago**, depois do deploy.

---

# 8. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-09-04 | IMP-369 entregue e revisado. O dia foi decidido por uma proposta do fundador: em vez de sondar a instância de produção, perguntar ao time que mantém o Evolution Go — que respondeu por leitura de código-fonte, fechou duas perguntas abertas havia semanas e ainda trouxe dois achados de arquitetura. Uma das respostas **refutou** uma premissa da ADR-019 e revelou defeito ativo em produção no `logout` repetido. A outra confirmou, por medição, que a postura conservadora no reenvio estava certa. |
