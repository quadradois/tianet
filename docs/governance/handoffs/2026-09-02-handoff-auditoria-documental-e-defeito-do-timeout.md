# 2026-09-02 - Handoff: documentacao reconciliada, e um defeito de codigo que ela revelou

**Versao:** 1.0.0

**Status:** PLAN-034 com **3 dos 7 itens** (cifra, persistencia, cliente do
provedor). Documentacao reconciliada com as decisoes recentes. **Um defeito
operacional aberto**, descrito na §3 — e o item mais urgente deste handoff.

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

O resultado que mais importa nao foi contar inconsistencias — foi **descobrir um
defeito de codigo** que ninguem tinha visto, e que pode mandar a mesma cobranca
duas vezes ao devedor.

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

# 3. O defeito aberto — leia antes de tocar em notificacao

**A ADR-009 §§53-80 ja decidiu** o tratamento de timeout:

> "Se nao for possivel provar que uma requisicao anterior nao foi aceita,
> **inclusive timeout** ou reset depois do envio de bytes, o estado e
> `resultado_desconhecido`"

E a tabela manda **bloquear retry e conciliar**.

**O codigo viola isso.** `EvolutionWhatsAppNotificationChannel` classifica todo
`httpx.TimeoutException` como `FALHA_TEMPORARIA`, e o Scheduler reenvia. Se o
Evolution aceitou a mensagem antes do timeout do cliente, **o devedor recebe a
cobranca duas vezes**.

Agrava: **nao foi medido** se o Evolution ou o WhatsApp suprimem uma segunda
mensagem com o mesmo `id`. O eco do `id` correlaciona requisicao e resposta, mas
correlacionar nao e deduplicar.

**A correcao e a distincao que a ADR exige e o codigo nao faz:**

- `ConnectTimeout` e `ConnectError` — falha comprovadamente **anterior** ao envio
  de bytes: temporaria, pode reenviar;
- `ReadTimeout` e demais — timeout **depois** de transmitir: sem prova de nao
  aceite, e `resultado_desconhecido`.

**Nao e decisao do fundador.** Eu cheguei a leva-la como "decisao com troca", e
estava errado: a ADR decidiu em agosto. E defeito de conformidade, e o item mais
urgente que este handoff deixa.

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
| 4.6 | `DecodingError` nao tratado em `resend.py` (2x) e `whatsapp.py` |
| 4.7 | Suite Playwright deixa servidor orfao; a proxima falha **sem imprimir nada** |
| 4.8 | **NOVO** — a violacao da ADR-009 descrita na §3 |
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

1. **Corrigir a violacao da ADR-009** (§3). Pequeno, delimitado, e o unico item
   com risco operacional real.
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
| 1.0.0 | 2026-09-02 | Auditoria de consistencia documental com 38 correcoes em onze arquivos; a violacao da ADR-009 no tratamento de timeout, que pode duplicar cobranca ao devedor; dois caveats novos; e o que nove rodadas de review ensinaram sobre editar documentacao cruzada ponto a ponto. |
