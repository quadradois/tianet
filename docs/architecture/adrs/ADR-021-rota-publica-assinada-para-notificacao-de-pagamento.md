# ADR-021: Rota pública assinada no serviço agent para notificação de pagamento

> **Status:** Aceito
> **Data:** 2026-09-22
> **Autor(es):** Engenharia
> **Revisor(es):** —
> **Aprovação:** Proprietário / 2026-09-21 (desenho do PLAN-045, seção 2)
> **Substitui:** —
> **Substituído por:** —

---

## Contexto

O `docs/operations/contexto-externo.md` §2.2 registra, desde 2026-08-25, que **a
TiaNet não terá webhook público**: o agente recebe do Evolution e chama um
endpoint autenticado, e o checklist do IMP-359 manda expor publicamente apenas o
ingress do agente — API e banco sem exposição.

O PLAN-045 decidiu receber o acerto por **Pix dinâmico do Mercado Pago**
(decisão do proprietário em 2026-09-21). O provedor confirma pagamento por
notificação HTTP para uma URL pública. Não há como cumprir as duas coisas sem
escolher: ou a §2.2 abre para um segundo caso, ou o recebimento vira polling da
API do provedor.

O próprio contexto externo §2.4 já antecipava a colisão e exigia decisão
explícita antes do desenho — é o que esta ADR faz.

**O argumento que fechou a §2.2 não se transporta inteiro.** Ele dizia que uma
rota pública exigiria "validação de assinatura do Evolution" — peça que não
existe, porque **o webhook do Evolution não tem autenticação nenhuma**: a URL é
o único segredo (contexto externo §2.1). O Mercado Pago é diferente: **assina
cada notificação** com HMAC-SHA256 sobre um manifesto que inclui o id do
recurso, o `x-request-id` e o timestamp, com segredo do próprio painel. A
origem é provável sem confiar no sigilo da URL.

## Decisão

**Uma segunda rota pública, `POST /mercadopago/webhook`, passa a existir no
serviço `agent`** — nunca na API nem no banco —, pelo mesmo caminho já
provado: Cloudflare → Caddy → socat (`tianet-agent-bridge`) → socket Unix.

Condições que a decisão carrega, e sem as quais ela não vale:

1. **Assinatura antes do corpo.** A rota valida `x-signature`
   (`ts=<ts>,v1=<hmac>`) contra o manifesto
   `id:[data.id];request-id:[x-request-id];ts:[ts];`, onde `data.id` vem da
   query string, em comparação de tempo constante, com janela de ±5 min para o
   `ts`. Assinatura inválida ou ausente → `401`, sem log de conteúdo. Nada do
   corpo é lido antes disso.
2. **A notificação não é a verdade.** O corpo diz apenas *qual* recurso mudou.
   O estado vem de `GET /v1/payments/{data.id}` na API do provedor, com a
   credencial da conta. Nenhum lançamento nasce do payload recebido.
3. **Dois identificadores distintos.** `mp_notification_id` (o `id` do corpo)
   deduplica entregas; `mp_payment_id` (`data.id`) identifica o pagamento. Uma
   notificação nova sobre o mesmo pagamento é aceita e reprocessada de forma
   idempotente.
4. **Correlação por identificador nosso.** A cobrança local gera
   `external_reference`, que viaja até o provedor e volta; é ele que localiza a
   `CobrancaPix` e serve de `Idempotency-Key` do lançamento no Motor.
5. **Rollback documentado.** Um job consulta os Pix `pendente` a cada 5 minutos.
   Se o webhook falhar, o polling cobre — a integração degrada em latência, não
   em correção.
6. **A rota só faz isto.** Não recebe comando, não aceita outro tipo de evento,
   não responde dado.

## Consequências

**Positivas**
- Confirmação em segundos, enquanto o devedor ainda está na conversa.
- Conciliação automática: o pagamento entra no Motor com a mesma separação de
  juro e amortização do lançamento manual.
- Reaproveita a topologia que já custou quatro PRs de correção (imagem, bind,
  socket, rede) — nenhuma peça nova de infraestrutura.

**Negativas, aceitas**
- A superfície pública do sistema passa de uma rota para duas. Mitigação: a
  segunda é assinada, o que a primeira não é.
- Mais um segredo em produção (`MP_WEBHOOK_SECRET`), com o custo de rotação que
  todo segredo tem.
- A §2.2 deixa de ser uma regra absoluta e passa a ser uma regra com exceção
  nomeada. Quem ler só a §2.2 terá uma leitura incompleta — por isso aquele
  documento foi reconciliado na v1.13.0, e esta ADR é citada de lá.

**Neutras**
- A decisão não abre precedente para webhook na API TiaNet: a exceção é do
  serviço `agent`, e exige assinatura verificável. Provedor que não assine cai
  no caminho de polling.

## Alternativas consideradas

**Polling puro, sem rota nova.** Consultar a API do provedor a cada N minutos.
Mantém a §2.2 intacta e é o caminho de rollback escolhido — mas como regime
permanente entrega a confirmação minutos depois, o que quebra a conversa
("paguei" → silêncio), e faz uma consulta por Pix pendente a cada ciclo.
Descartada como regime normal, preservada como degradação.

**Webhook na API TiaNet.** Descartada: a API não tem rota pública por decisão, e
expô-la colocaria o banco a um salto da internet.

**Link de checkout do provedor em vez de Pix dinâmico.** Descartada no desenho:
traz cartão e boleto para um produto de juro sobre saldo, com taxas e prazos
diferentes, sem resolver a notificação.

## Referências

- `docs/implementation/plans/PLAN-045-atendimento-ao-devedor-e-recebimento-pix.md` §3.5, §4.2
- `docs/operations/contexto-externo.md` §2.1, §2.2, §2.4 (v1.13.0)
- `docs/governance/handoffs/2026-09-19-handoff-agent-no-ar-inbox-e-tela.md` (topologia Caddy/socat)
- Mercado Pago — Webhooks: formato de `x-signature`, manifesto e política de reentrega

## Histórico de Versões

| Versão | Data | Alteração |
|---|---|---|
| 1.0.0 | 2026-09-22 | Emissão. Abre a §2.2 para um segundo caso, condicionado a assinatura verificável, reconsulta do recurso e rollback por polling. |
