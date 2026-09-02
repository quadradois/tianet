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
defeitos de codigo** que ninguem tinha visto, e que podem mandar a mesma
mensagem duas vezes ao destinatario.

---

# 2. O que a auditoria corrigiu

As cinco de gravidade alta:

| Onde | O que dizia | Por que importava |
|---|---|---|
| `FOUNDATION-008` | "Multi-Tenant Nivel 1" como capacidade do MVP | Mesma decisao que a ADR-003 revogou, em outras palavras — e por isso o guardrail nao alcancou |
| `FOUNDATION-008` | IA e integracoes de terceiros fora do MVP | Permitia rejeitar o PLAN-033 e o PLAN-034, ambos aprovados |
| `ADR-009` | token "nunca em log ou banco" | A DR-006 decidiu o oposto e o IMP-365 ja implementou |
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
levam ao mesmo lugar: **o destinatario recebe a mesma mensagem duas vezes**.

**Que mensagem, exatamente.** O adapter do WhatsApp esta ligado a
`enviar_comprovante` e `enviar_aviso_sobra` (`scheduler_worker.py:346-354`);
`enviar_lembrete` usa o canal de e-mail. Entao o que duplica hoje e **comprovante
de pagamento e aviso de sobra**, nao cobranca. Menos grave, e nao inocuo: dois
comprovantes do mesmo pagamento, ou dois avisos de sobra, sao ambiguos sobre
dinheiro para quem recebe. Quando o lembrete migrar para o WhatsApp, o mesmo
defeito passa a duplicar cobranca.

**3.1 — Resposta 5xx** (`whatsapp.py:87`). A ADR nomeia `5xx` como o primeiro
item de `resultado_desconhecido`; o adapter devolve `FALHA_TEMPORARIA` com
codigo `provider_5xx`, e o Scheduler reenvia. Um 502 ou 504 de gateway chega
depois de o upstream ter aceitado a mensagem — e nao ha como distinguir isso de
um 500 que nao aceitou nada.

**3.2 — Transporte indistinto** (`whatsapp.py:52-53`). O `except` unico devolve
`FALHA_TEMPORARIA` para todo `TimeoutException` **e** todo `TransportError`. A
ADR so autoriza retry para falha **comprovadamente anterior** ao envio de bytes,
e esses dois ramos misturam os dois lados: `ConnectTimeout` e `ConnectError` sao
anteriores, mas `ReadError`, `WriteError` e `RemoteProtocolError` sao resets
**depois** de transmitir — exatamente o caso que a ADR nomeia ao lado do timeout.

**3.3 — `DecodingError` escapa** (`whatsapp.py:52`, `resend.py:52`). Ela e
`RequestError`, **nao** `TransportError` — irma dele na hierarquia, fora do
`except`. Sobe do adapter, e `SchedulerWorker._execute` converte **qualquer**
excecao do handler em `FALHA_TEMPORARIA` (`scheduler_worker.py:191-201`), que
reenvia. O decoding falha lendo o **corpo da resposta**: a requisicao ja foi
enviada e pode ter sido aceita.

Estava listado como caveat de higiene (§4.6). Nao e: e o mesmo defeito.

**Uma ocorrencia dela e outra coisa.** Em `resend.py:59`, dentro de
`consultar_status`, o unico chamador e `NotificationService.conciliar`
(`notifications.py:637`) — fluxo administrativo, disparado por gente, com motivo
e IAM. Ali a excecao nao vira retry: vira erro nao tratado no meio da
conciliacao. Defeito tambem, consequencia diferente; nao confundir os dois ao
corrigir.

A correcao e separar o que a ADR separa:

- **Anterior ao envio** — `ConnectTimeout`, `ConnectError` e **`PoolTimeout`**:
  temporarias, podem reenviar. O `PoolTimeout` estoura **esperando uma conexao do
  pool**, antes de existir requisicao; trata-lo como desconhecido bloquearia
  retry legitimo sob contencao;
- **Depois de transmitir** — `ReadTimeout`, `WriteTimeout`, `ReadError`,
  `WriteError`, `RemoteProtocolError` e `DecodingError`: sem prova de nao aceite,
  `resultado_desconhecido`;
- **`provider_5xx`** — `RESULTADO_DESCONHECIDO`, como a tabela manda.

O proprio adapter ja classifica **2xx malformado** como `DESCONHECIDO`, que e a
linha vizinha da mesma tabela. E o **adapter do Resend**, mais antigo e escrito
sob a mesma ADR, mapeia `5xx` e toda falha de transporte para `DESCONHECIDO`
(`resend.py:52-64`) — conservador ate demais, tratando como desconhecido tambem o
que a ADR permitiria reenviar. No 5xx e no transporte, o do WhatsApp diverge da
ADR e do irmao ao mesmo tempo; no `DecodingError` os dois erram junto. Sao
omissoes, nao desenho.

Agrava: **nao foi medido** se o Evolution ou o WhatsApp suprimem uma segunda
mensagem com o mesmo `id`. O eco do `id` correlaciona requisicao e resposta, mas
correlacionar nao e deduplicar.

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
| 4.8 | **NOVO** — as tres violacoes da ADR-009 descritas na §3 (5xx, transporte indistinto e `DecodingError`), que hoje duplicam comprovante e aviso de sobra, e duplicariam cobranca quando o lembrete migrar para o WhatsApp |
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
| 1.0.0 | 2026-09-02 | Auditoria de consistencia documental com 38 correcoes em onze arquivos; as tres violacoes da ADR-009 nos adapters de notificacao (5xx, transporte indistinto e `DecodingError` escapando para o retry do Scheduler), que hoje duplicam comprovante e aviso de sobra; dois caveats novos; e o que nove rodadas de review ensinaram sobre editar documentacao cruzada ponto a ponto. |
