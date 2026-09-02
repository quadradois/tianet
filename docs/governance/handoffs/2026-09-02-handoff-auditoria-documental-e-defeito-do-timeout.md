# 2026-09-02 - Handoff: documentacao reconciliada, e um defeito de codigo que ela revelou

**Versao:** 1.0.0

**Status:** PLAN-034 com **3 dos 7 itens** (cifra, persistencia, cliente do
provedor). Documentacao reconciliada com as decisoes recentes. **Tres defeitos
operacionais abertos**, descritos na §3 — o item mais urgente deste handoff.

**Periodo coberto:** 2026-09-01 a 2026-09-02

**Base:** `origin/master` em `67bfb81`, arvore limpa. Treze PRs mergeados no
ciclo (#39 a #51).

**Substitui:** `2026-09-01-handoff-plan-034-infraestrutura-da-conexao.md`, que
continua valido como registro daquela data e detalha as entregas do PLAN-034.

---

# 1. O que aconteceu neste periodo

Uma auditoria de consistencia documental, pedida depois de doze PRs com decisoes
que atravessam varios documentos. Encontrou **11 inconsistencias**; corrigi-las
gerou outras, e foram **nove rodadas de review** ate os achados virarem de
precisao. **38 correcoes no total**, em onze arquivos.

O resultado que mais importa nao foi contar inconsistencias — foi **descobrir
defeitos de codigo** que ninguem tinha visto, e que reenviam mensagem sem prova
de que a primeira nao foi aceita.

---

# 2. O que a auditoria corrigiu

As cinco de gravidade alta:

| Onde | O que dizia | Por que importava |
|---|---|---|
| `FOUNDATION-008` | "Multi-Tenant Nivel 1" como capacidade do MVP | Mesma decisao que a ADR-003 revogou, em outras palavras — e por isso o guardrail nao alcancou |
| `FOUNDATION-008` | IA e integracoes de terceiros fora do MVP | Permitia rejeitar o PLAN-033 e o PLAN-034, ambos aprovados |
| `ADR-009` | token "nunca em log ou banco" | A DR-006 reverteu **so a clausula de banco** — persistido, mas cifrado (IMP-365). **Log continua proibido, sem excecao** |
| Contrato Evolution | tratar `Connected` como "conectado" | O defeito que o review pegou no codigo, vivo no documento que o originou |
| `contexto-externo.md` | servidor nao provisionado | Mantinha o deploy bloqueado por insumo que ja existe |

A ADR-009 foi resolvida por **adendo**, seguindo o precedente do IMP-358, e nao
por DR nova: a DR-006 ja tinha decidido, e abrir DR re-litigaria o decidido.

**Nao foi alterado:** registro historico (`docs/audits/`, handoffs antigos) deve
descrever o que se pensava na epoca. E `.specify/memory/constitution.md` — eu
propunha remover, o Codex discordou com argumento melhor (template com
placeholders inequivocos, sem referencia em gate ou documento, sem competir com
a governanca real), e aceitei.

---

# 3. Os defeitos abertos — leia antes de tocar em notificacao

**A ADR-009 ja decidiu**, na tabela de estados externos, quando um envio pode ser
reenviado:

| Estado | Evidencia | Acao |
|---|---|---|
| `falha_temporaria` | 429, conflito concorrente da mesma chave ou **falha comprovadamente anterior ao envio de bytes** | retry |
| `resultado_desconhecido` | **5xx**, 2xx malformado, **timeout/reset apos transmitir bytes** ou qualquer resposta sem prova de nao aceite | **bloquear retry** e conciliar |

`EvolutionWhatsAppNotificationChannel` viola isso em **tres pontos**, e os tres
levam ao mesmo lugar: **o Scheduler reenvia sem prova de que o primeiro envio nao
foi aceito**. Se o provedor nao deduplicar pelo `id` — e isso **nao foi medido**
—, o destinatario recebe a mesma mensagem duas vezes.

**Que mensagem, exatamente.** O adapter do WhatsApp esta ligado a
`enviar_comprovante_whatsapp` e `avisar_sobra_pagamento_whatsapp`
(`scheduler_worker.py`, mapa `handlers`); `enviar_lembrete` usa o canal de e-mail. E o
comprovante e o do **lancamento do emprestimo** — origem `comprovante_lancamento`,
corpo encabecado "Comprovante do lancamento" (`montar_texto_comprovante`) —, nao de
pagamento. Entao o que pode duplicar hoje e **o comprovante de contratacao e o
aviso de sobra de pagamento**, nao cobranca. Menos grave, e nao inocuo: dois
comprovantes do mesmo emprestimo sugerem dois emprestimos. Quando o lembrete
migrar para o WhatsApp, o mesmo defeito passa a alcancar cobranca.

**3.1 — Resposta 5xx** (`whatsapp.py`, `_classificar_resposta`, codigo `provider_5xx`). A ADR nomeia `5xx` como o primeiro
item de `resultado_desconhecido`; o adapter devolve `FALHA_TEMPORARIA` com
codigo `provider_5xx`, e o Scheduler reenvia. Nenhum 5xx prova que o upstream
recusou: um 502 pode ser o gateway sem conseguir falar com ele, mas tambem pode
chegar depois de o upstream ter aceitado; um 504 so diz que o gateway desistiu de
esperar. E prova de recusa que a ADR exige para reenviar.

**3.2 — Transporte indistinto** (`whatsapp.py`, o `except` de `enviar`). O
`except` unico devolve `FALHA_TEMPORARIA` para todo `TimeoutException` **e** todo
`TransportError`. A ADR so autoriza retry quando a nao-aceitacao e
**comprovada**, e esses dois ramos varrem junto o que prova (`ConnectTimeout`,
`ConnectError`) e o que nao prova nada (`ReadTimeout`, `ReadError`, `WriteError`,
`CloseError`, `RemoteProtocolError`).

**3.3 — `DecodingError` escapa** (o mesmo `except` em `whatsapp.py` e em
`resend.py`). Ela e `RequestError`, **nao** `TransportError` — irma dele na
hierarquia, fora do `except`. Sobe do adapter, e `SchedulerWorker._execute`
converte **qualquer** excecao do handler em `FALHA_TEMPORARIA`, que reenvia. Aqui
a requisicao comprovadamente foi enviada — ha uma resposta, so nao da para
decodifica-la.

Estava listado como caveat de higiene (§4.6). Nao e: e o mesmo defeito.

**Uma ocorrencia dela e outra coisa.** Em `resend.py`, dentro de
`consultar_status`, o unico chamador e `NotificationService.conciliar` — fluxo
administrativo, disparado por gente, com motivo e IAM. Ali a excecao nao vira
retry: vira erro nao tratado no meio da conciliacao. Defeito tambem, consequencia
diferente; nao confundir os dois ao corrigir.

**A correcao nao e uma lista maior, e inverter o padrao.** Tentei enumerar as
excecoes "de depois do envio" tres vezes e faltou uma em cada — `PoolTimeout`,
depois `ReadError`/`RemoteProtocolError`, depois `CloseError`. O erro nao era a
lista: era o criterio. "Depois de transmitir bytes" **nao e verificavel** a
partir da excecao. Um `WriteError` pode estourar na primeira escrita, sem nenhum
byte na rede; a biblioteca nao diz qual foi.

O criterio da ADR nao e o momento fisico, e a **prova**: "retry somente ocorre
quando ha prova de que o provedor nao aceitou o efeito", e "na duvida, prevalece
`resultado_desconhecido`". Entao a regra e uma allowlist curta, e o resto cai no
seguro por omissao:

- **Retry so aqui** — `ConnectTimeout`, `ConnectError` e `PoolTimeout`: a
  requisicao **nao chegou a existir na rede**, e isso e verificavel. O
  `PoolTimeout` estoura esperando uma conexao do pool, antes de haver requisicao;
  trata-lo como desconhecido bloquearia retry legitimo sob contencao;
- **Todo o resto** — `resultado_desconhecido`. Nao por serem posteriores ao
  envio, mas por **nao provarem nada**. Escrito assim, uma excecao nova do httpx
  cai no lado seguro sozinha, em vez de esperar a quarta rodada de review;
- **`provider_5xx`** — `RESULTADO_DESCONHECIDO`, como a tabela manda, e pela
  mesma razao: um 502 pode ser falha de conexao do gateway com o upstream, e um
  504 so diz que o gateway desistiu de esperar. Nenhum dos dois prova aceite —
  nem prova o contrario, que e o que faria falta.

O proprio adapter ja classifica **2xx malformado** como `DESCONHECIDO`, que e a
linha vizinha da mesma tabela. E o **adapter do Resend**, mais antigo e escrito
sob a mesma ADR, mapeia `5xx` e toda falha de transporte para `DESCONHECIDO` — conservador ate demais, tratando como desconhecido tambem o
que a ADR permitiria reenviar. No 5xx e no transporte, o do WhatsApp diverge da
ADR e do irmao ao mesmo tempo; no `DecodingError` os dois erram junto. Sao
omissoes, nao desenho.

O que separa "reenvio indevido" de "mensagem duplicada" e a deduplicacao pelo
`id`, e ela **nao foi medida**: o eco do `id` correlaciona requisicao e resposta,
mas correlacionar nao e deduplicar. Enquanto ninguem medir, a ADR manda assumir o
pior — e por isso o defeito nao depende dessa medicao para ser corrigido.

**Nao e decisao do fundador.** Eu cheguei a levar o item do timeout como
"decisao com troca", e estava errado: a ADR decidiu em agosto. Sao defeitos de
conformidade, e o item mais urgente que este handoff deixa.

---

# 4. Caveats vigentes

Os herdados continuam validos e estao detalhados no handoff de 2026-09-01 §8.
Em resumo:

| # | Caveat |
|---|---|
| 4.1 | **Producao nao existe.** VPS e dominio `tianet.com.br` disponiveis; faltam deploy, TLS, backup, CD e endurecimento. E o IMP-359. **Um insumo externo permanece:** a escolha do provedor de IA com o cliente, sem a qual `LLM_BASE_URL`, `LLM_API_KEY` e `LLM_MODEL` nao tem valor |
| 4.2 | Contrato declara politica de senha mais frouxa que o sistema aceita |
| 4.3 | `scheduler_worker.py` em 69,91% |
| 4.4 | CPFs historicos em `audit_log` — limpar e mudanca destrutiva, decisao separada |
| 4.5 | `CLAUDE.md` da raiz e gitignored; `frontend/CLAUDE.md` e versionado |
| 4.6 | `DecodingError` nao tratado em `resend.py` (2x) e `whatsapp.py` — **nao e higiene**: no envio e o terceiro caminho de retry inseguro (§3.3); no `consultar_status` e erro nao tratado na conciliacao |
| 4.7 | Suite Playwright deixa servidor orfao; a proxima falha **sem imprimir nada** |
| 4.8 | **NOVO** — as tres violacoes da ADR-009 descritas na §3 (5xx, transporte indistinto e `DecodingError`): reenvio sem prova de nao aceite, hoje no comprovante de lancamento e no aviso de sobra, e na cobranca quando o lembrete migrar para o WhatsApp |
| 4.9 | **NOVO** — o guardrail da ADR-003 casa por texto, nao por ideia. Pega a frase que o regex conhece; deixou passar "Multi-Tenant Nivel 1", que e a mesma decisao. Ha **quatro linhas** com essa forma em `ADR-001:25`, `AMP-001:141` e `PLAN-001:17,161` |

---

# 5. O que este periodo ensinou sobre editar documentacao

**Corrigir ponto a ponto uma documentacao densamente cruzada nao converge.** As
nove rodadas oscilaram entre dois e quatro achados, sem cair: cada correcao
criava divergencia com o arquivo que eu nao tinha aberto. **Onze dos achados**
foram literalmente isso — consertar um documento e deixar o vizinho
contradizendo.

**O que reduziu o problema foi um comando, nao atencao.** Varrer o repositorio
pela afirmacao depois de cada correcao. Na primeira vez que fiz, achou o **dobro**
do que o review apontava. Escrever sobre o habito em nove commits seguidos nao
mudou nada.

**Varredura com exclusao nao e varredura.** Rodei `grep -v "ADR-003"` e escondi
justamente o arquivo com o problema.

**Um motivo errado sobrevive mais que a decisao.** Escrevi na ADR-009 que a
persistencia resolve "conexao que nao sobrevive a restart" — nao sobrevive coisa
nenhuma: reconectar nao muda o token, e a variavel de ambiente sobrevive. O que
a persistencia resolve e o **nascimento** da instancia. Decisao correta, motivo
errado; a proxima pessoa herda o raciocinio.

**Enumerar e mais fragil que decidir o criterio.** A §3 listou tres vezes as
excecoes que nao podem ser reenviadas, e faltou uma em cada rodada. A lista nao
estava incompleta por descuido: o criterio que eu usava para monta-la — "depois
de transmitir bytes" — nao e observavel a partir da excecao. Trocado por
"prova de nao aceite", a regra virou allowlist curta com o resto seguro por
omissao, e parou de precisar de rodada. Quando uma lista erra toda vez, o defeito
costuma estar no criterio que a gera, nao nos itens.

**Cuidado no desenho nao substitui revisao.** No IMP-366 eu distingui `Connected`
de `LoggedIn` no dominio, no cliente e nos testes — e escrevi a conversao
`bool("false")`, que e `True`, permitindo exatamente o erro que eu evitava.

---

# 6. Fluxo de trabalho vigente

```
commit local  →  review do Codex ate aprovar  →  abre PR  →  Claude merga  →  CI  →  proximo
```

**O review vem ANTES do PR.** A ordem invertida custou dois merges de versao
reprovada (#35 e #48). O fundador nao merga; quem merga e o Claude, depois da
aprovacao.

**Verificar o commit de MERGE, nao os checks do PR.** Sao commits diferentes;
verde num nao implica verde no outro.

**Um review pode travar.** Um deles ficou 18h em `verifying` com o log parado —
o monitor precisa detectar log estagnado, nao so mudanca de status.

---

# 7. Proximo ciclo

1. **Corrigir as violacoes da ADR-009** (§3). Pequeno, delimitado, e o unico
   item com risco operacional real.
2. **IMP-367** — casos de uso e permissoes. Primeiro item que consome as tres
   camadas prontas do PLAN-034.
3. **IMP-368** — endpoints e contrato; o guardrail cobra plano, contadores e
   snapshot OpenAPI juntos.
4. **IMP-369** — a tela. **IMP-370** — worker le do repositorio.
5. **IMP-359 — deploy.** **Ponto de parada acordado:** tudo pronto antes de
   configurar a VPS.

Itens menores: o guardrail da ADR-003 reforcado (§4.9), o `DecodingError` dos
adapters antigos (§4.6), limpeza de portas no pre-push (§4.7), e as decisoes
sobre CPFs historicos (§4.4) e o `CLAUDE.md` (§4.5).

---

# 8. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-09-02 | Auditoria de consistencia documental com 38 correcoes em onze arquivos; as tres violacoes da ADR-009 nos adapters de notificacao (5xx, transporte indistinto e `DecodingError` escapando para o retry do Scheduler), que reenviam sem prova de nao aceite o comprovante de lancamento e o aviso de sobra; dois caveats novos; e o que nove rodadas de review ensinaram sobre editar documentacao cruzada ponto a ponto. |
