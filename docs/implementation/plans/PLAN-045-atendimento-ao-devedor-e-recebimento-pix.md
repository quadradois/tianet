# PLAN-045 — Atendimento ao devedor, recebimento por Pix e BYOK

**ID:** PLAN-045

**Versão:** 1.3.2

**Status:** Aprovado pelo proprietário em 2026-09-21 (v1.1.0); execução via [PLAN-045-execution-backlog](../backlogs/PLAN-045-execution-backlog.md) (IMP-372..387, GATE-E1..E6)

**Backlog de execução:**
`docs/implementation/backlogs/PLAN-045-execution-backlog.md`

---

# 1. Contexto

O agente em produção (`prod-v1.1.33`) recebe mensagens do WhatsApp e as guarda
na inbox; não responde, não envia, não usa LLM. O PLAN-033 desenhou o agente
como copilot da Credora (leitura de carteira) e pré-cadastro. Este plano
redefine a função do agente a partir da decisão do proprietário em
2026-09-21: **atender o devedor**, **informar os dois lados** e **receber por
Pix**, sem decidir nada.

Princípio que governa tudo: **o agente propõe e informa; o Motor calcula; a
Credora decide.**

## 1.1 Decisões do proprietário (2026-09-21)

| # | Decisão | Consequência |
|---|---|---|
| D1 | Identidade do devedor = número de WhatsApp cadastrado no contato; sem desafio | Número desconhecido continua em `pre_cadastro` |
| D2 | Devedor não escreve no domínio (sem promessa, renegociação, alteração de data) | Únicas escritas do devedor: gerar Pix, suspender avisos, registrar comunicação — todas com confirmação |
| D3 | Recebimento por **Pix dinâmico do Mercado Pago**, validade **60 min**; expirou → cancela, devedor pede outro. **Opcional, ligado/desligado pela Credora no painel** (decisão de 2026-09-22): o provedor cobra **0,99%** por recebimento, e ela já tem o caminho sem taxa — o devedor paga no Pix dela e ela avisa o agente, que registra (§3.10) | Conta PJ existe. Segunda rota pública, assinada por HMAC. Desligado é o **padrão** de um tenant novo |
| D4 | Valor do Pix é **livre**, digitado pelo devedor, validado em código entre juro do período e quitação; o Motor separa juro/amortização | O LLM só extrai o número; nunca decide valor |
| D5 | Notificações proativas: véspera (D-1) ao devedor; resumo diário à Credora com vence-hoje **e em atraso**; lembrete de atraso em D+1, D+4, D+7… | Sem régua de cobrança além disso |
| D6 | Lembrete de atraso **só sai com autorização diária da Credora** pelo WhatsApp (ou tela); sem resposta, não sai | Cobre pagamento por fora com comprovante |
| D7 | Devedor pode pedir suspensão dos avisos: suspende **até o próximo acerto**, avisa a Credora; respostas na conversa continuam | Suspensão datada ao lado do `opt_out` permanente |
| D8 | Credora pode registrar pagamento por WhatsApp ("Fulano me pagou 800 ontem") com eco + confirmação | Exige Slice 6 (autenticação do envelope) e permissão `pagamento.registrar` no copilot |
| D9 | IA desde a primeira mensagem, sem menu; saudação natural | Certificação do contexto Devedor entra no caminho crítico; sem certificação, resposta fixa |
| D10 | Canal único WhatsApp; e-mail, PDF, extrato, cartão, boleto fora | — |
| D11 | DR-005 §8: política de dados do provedor deixa de ser critério de elegibilidade; rota A (`gpt-5-mini`) mantida por previsibilidade | Delegado à engenharia e decidido |
| D12 | Tela BYOK para provedor/modelo/chave sem deploy | `LLM_*` de ambiente sai; configuração no banco, cifrada |
| D13 | **Pix direto da Credora com comprovante** (2026-09-22): o agente informa os valores e a chave Pix dela, pede o comprovante, extrai o valor, pergunta à Credora se lança; ela confere na própria conta e autoriza | Caminho **sem taxa**; torna o Mercado Pago conveniência, não necessidade. Reverte o descarte de mídia do 356-B |
| D14 | **Comprovante é alegação, nunca prova.** Quem verifica é a Credora, na conta dela | Modelo errar o valor vira "não" dela, nunca lançamento errado |
| D15 | Comprovante guardado **enquanto o empréstimo vive**; na quitação, expurgado | O lançamento, a memória de cálculo e a trilha permanecem — a prova contábil não depende da imagem |

## 1.2 Fora do escopo, declarado

Promessa por chat; renegociação; régua de cobrança além do lembrete
autorizado; aviso proativo sem autorização; e-mail; PDF; cartão/boleto;
amortização por menu; copilot da Credora com leitura de carteira **por LLM**
além do que a §4.4 libera; IMP-357 (pré-cadastro conversacional).

---

# 2. Componentes do Domínio Envolvidos

**Não muda:** Motor Financeiro (`saldo`, `quitacao` por `data_referencia`,
`registrar_pagamento`), varredura de cobrança, `CobrancaCaso`, auditoria
ADR-002, isolamento de contextos (ADR-016).

**Entra:**

| Conceito | Camada | Definição |
|---|---|---|
| `CobrancaPix` (Aggregate) | `domain/credit/cobranca_pix.py` | `id`, `tenant_id`, `carteira_id`, `emprestimo_id`, `devedor_id`, `valor`, `external_reference` (= `str(id)`, único, gerado pela TiaNet; é a chave de correlação entre cobrança local, Mercado Pago e polling), `mp_payment_id` (preenchido na criação, único), `copia_cola`, `qr_base64`, `expira_em`, `estado ∈ {pendente, pago, expirado, cancelado}`, `divergente: bool`, `origem ∈ {tela, copilot_devedor}`, `criado_por`. **INV-001 (CobrancaPix):** `juro_periodo ≤ valor ≤ quitacao` na data de criação. **INV-002 (CobrancaPix):** no máximo um `pendente` por empréstimo. Transições: `pendente→pago`, `pendente→expirado`, `pendente→cancelado`; terminais imutáveis. |
| `OrigemPagamento` | campo em `Pagamento` | `manual`, `pix_mp`, `copilot_credora`. Migration aditiva com default `manual`. |
| `avisos_suspensos_ate: date \| None` | campo em `PreferenciaNotificacao` | `permite_envio_proativo(hoje)` = `permite_envio and (avisos_suspensos_ate is None or hoje >= avisos_suspensos_ate)`. `permite_envio` (opt-out) permanece para resposta e confirmação. |
| `elegivel_lembrete(dias_atraso)` | função pura, `domain/credit/regua_lembrete.py` | `dias == 1 or (dias > 1 and (dias - 1) % 3 == 0)` |
| `ClasseContexto.DEVEDOR` | `agent/conversa.py` | terceira classe; sessão, histórico e tools isolados das outras duas |
| `ComprovantePagamento` | `domain/credit/comprovante.py` | `emprestimo_id`, `devedor_id`, `sha256`, `tipo_midia`, `tamanho`, `recebido_em`, `valor_extraido`, `valor_informado`, `estado ∈ {recebido, lancado, recusado}`, `pagamento_id`. **INV:** binário e valores são apagados na quitação do empréstimo. |
| `ChavePixCredora` | configuração do Tenant | tipo, valor, nome do favorecido. Ausente → agente não promete Pix. |
| `ConfiguracaoMercadoPago` | `domain/platform/configuracao_mercadopago.py` | por tenant: `habilitado` (padrão **false**), `access_token_cifrado`, `webhook_secret_cifrado`, `testado_em`, `atualizado_em/por`. Mesmo padrão de cifra da `ConexaoWhatsApp`. Habilitar exige as duas credenciais e teste ok. |
| `ConfiguracaoLlm` | `domain/platform/configuracao_llm.py` | por tenant: `provedor`, `base_url`, `modelo`, `chave_cifrada`, `habilitado`, `testado_em`, `atualizado_em/por`. Mesmo padrão de cifra da `ConexaoWhatsApp`. |
| `AutorizacaoLembrete` | `domain/credit/` (registro por dia) | `tenant_id`, `data`, `mapa {n: (devedor_id, emprestimo_id)}`, `autorizados: set`, `respondido_em`. Um por tenant/dia. |

**Permissões novas no perfil `copilot`:** `pagamento.registrar`,
`cobranca_pix.criar`, `preferencia_notificacao.suspender`,
`comunicacao.registrar`, `lembrete.autorizar`. Continua sem
`proposta.decidir`, `renegociacao.*`, `quitacao.executar`.
**Permissões novas de administrador:** `llm.configurar`, `mercadopago.configurar`.

---

# 3. Casos de Uso

## 3.1 Devedor consulta ("quanto eu devo?", "oi")

1. Ingress valida `instanceToken` (§4.1); classifica `devedor` por contato E.164.
2. Consumidor da inbox entrega ao `Executor` no contexto Devedor.
3. LLM escolhe `meu_saldo` (argumentos fixados pelo contexto — o modelo não
   escolhe `devedor_id`). Apresentador formata: por empréstimo, saldo, juro do
   período, próximo acerto; se atrasado, "em aberto desde DD/MM, juro até hoje".
4. Sem tool (saudação, "não entendi"): prosa do modelo é entregue.
5. Egress pelo canal Evolution real; trilha e expurgo já existentes.

## 3.2 Devedor paga ("quero pagar 800") — com Mercado Pago **ligado**

1. LLM chama `gerar_pix(valor=800)`. Executor consulta Motor (juro, quitação),
   valida INV-001 (CobrancaPix); fora do intervalo → mensagem fixa com os limites, sem
   Pix.
2. Dentro: executor devolve **eco** ("Gerar Pix de R$ 800,00? Vale 60 min.
   Sim/Não") e grava `ConfirmacaoPendente(tool, args, expira_em=+10min)` na
   sessão. Nenhuma chamada de escrita ainda.
3. Próxima mensagem `sim` (determinístico, lista fixa de afirmativas) →
   `POST /credit/emprestimos/{id}/cobrancas-pix` → `CobrancaPix(pendente)` →
   resposta com copia-e-cola. Qualquer outra mensagem descarta a confirmação.
4. Webhook MP (§3.5) → pagamento no Motor → confirmação aos dois lados.
5. 60 min sem pagamento → `expirado` (job §3.6); devedor pede outro.

## 3.3 Devedor pede silêncio ("para de me mandar mensagem")

Eco + `sim` → `avisos_suspensos_ate = próximo_acerto_em` →
mensagem à Credora ("Fulano pediu para suspender os avisos; retomo em DD/MM").
Respostas e confirmações de pagamento continuam.

## 3.4 Devedor quer a Credora ("quero falar com a Tia")

`falar_com_a_tia` → registra comunicação (`POST .../comunicacoes`) → avisa a
Credora com o texto do devedor → responde ao devedor que ela foi avisada.

## 3.2-b Devedor paga no Pix da Credora e envia comprovante

Caminho sem taxa, disponível com o Mercado Pago ligado ou desligado.

1. Devedor pede para pagar. O agente responde com os valores do Motor (juro do
   período, saldo, quitação) e a **chave Pix da Credora** (configuração do
   Tenant, §3.12-b), pedindo o comprovante depois do pagamento.
2. Devedor envia imagem/PDF do comprovante, com ou sem texto.
3. O agente **extrai o valor** do comprovante e consulta o Motor
   (`prever_alocacao`, §4.10) para a divisão que aquele valor produziria
   naquela data. Se o devedor também disse um valor e os dois divergem, o
   agente **não escolhe**: relata os dois à Credora.
4. O agente encaminha à Credora **a imagem original** e o resumo:
   *"Alexandre pagou R$ 1.627,00 — seriam R$ 627,00 de juros e R$ 1.000,00 de
   amortização. Comprovante anexo. Confere na conta e me diz se lanço."*
5. Credora confere **na própria conta** (é ela quem verifica, não o agente) e
   responde `sim` ou `não`.
6. `sim` → lança no Motor (`origem=copilot_credora`, `Idempotency-Key` derivada
   do comprovante) e responde ao devedor com o estado atualizado: valor
   recebido, divisão juro/amortização, **saldo devedor atualizado, juros
   atualizados e próxima data de acerto** — todos do Motor.
   `não` → nada é lançado; o devedor é avisado de que a Credora vai falar com
   ele; o comprovante fica marcado como recusado.
7. Sem resposta da Credora, nada acontece: fail-closed, como toda escrita.

## 3.4-b Devedor quer pagar com o Mercado Pago **desligado**

A tool `gerar_pix` **não é oferecida ao modelo** quando a configuração está
desligada — o catálogo é montado por contexto e por configuração do Tenant, de
modo que o agente não pode prometer o que não existe. O pedido de pagamento cai
em `falar_com_a_tia` (§3.4): o agente informa saldo e valores, diz que vai
avisar a Credora para combinar o acerto, e registra a comunicação. A Credora
recebe a mensagem e, depois que o devedor pagar por fora, usa §3.10 para
registrar. Nenhum caminho fica sem saída.

## 3.5 Pagamento confirmado pelo Mercado Pago

1. `POST /mercadopago/webhook?data.id=<id>&type=payment` no agent. Contrato
   oficial de assinatura: header `x-signature: ts=<ts>,v1=<hmac>`, header
   `x-request-id`; manifesto `id:[data.id];request-id:[x-request-id];ts:[ts];`
   (`data.id` vem da **query string**, em minúsculas se alfanumérico);
   `v1 == HMAC-SHA256(MP_WEBHOOK_SECRET, manifesto)`, comparação em tempo
   constante; `ts` fora de ±5 min → rejeita. Validação **antes** de ler o
   corpo; inválida → 401 sem log de conteúdo. Responder em < 22 s (MP repete
   até 8× em 15 min/30 min/6 h/48 h/96 h×3 se não receber 200/201).
2. Grava em `inbox_pagamento` com **dois identificadores distintos**:
   `mp_notification_id` (= `id` do corpo, único → replay `duplicada`, 200) e
   `mp_payment_id` (= `data.id`, o recurso). Uma notificação nova para o
   mesmo pagamento (ex.: `payment.updated`) é aceita e reprocessada de forma
   idempotente pelo passo 3.
3. Consumidor: `GET /v1/payments/{data.id}` no MP (nunca confia só no
   webhook); `status=approved` → localiza `CobrancaPix` por
   `external_reference` do recurso (e confere `mp_payment_id`) →
   `POST /credit/emprestimos/{id}/pagamentos` (`origem=pix_mp`,
   `Idempotency-Key=external_reference`) → `pago`. `external_reference`
   desconhecido → registra `orfao` e avisa a Credora, sem lançar.
4. `transaction_amount ≠ valor` → registra o **recebido**, `divergente=true`,
   avisa a Credora. Nunca rejeita dinheiro que entrou.
5. Mensagens: devedor ("Recebido R$ X: R$ J de juros, R$ A amortizados. Saldo
   R$ S.") e Credora ("Fulano pagou R$ X via Pix."). Valores do Motor.

## 3.6 Expiração e polling (rollback do webhook)

Job a cada 5 min: `pendente` com `expira_em < agora` → consulta MP; `approved`
→ processa como §3.5; senão cancela no MP e marca `expirado`. Cobre webhook
fora do ar.

## 3.7 Resumo diário à Credora (IMP-353 + atraso + autorização)

08:00 `America/Sao_Paulo`. Blocos: vence hoje (nome, juro); em atraso (nome,
dias, juro acumulado); **lembretes elegíveis hoje** (numerados) com pergunta
de autorização. Gera `AutorizacaoLembrete(data, mapa)`. Dia sem nada → não
envia. Exige `credor_whatsapp`.

## 3.8 Credora autoriza lembretes (`1 2`, `todos`, `nenhum`)

Determinístico, sem LLM: resolve contra o mapa do dia; dispara
`lembrete_atraso` só para os autorizados que ainda passem em consentimento e
suspensão. Sem resposta até 23:59 → nada sai; amanhã lista nova. Tela
`/app/agent` oferece o mesmo com botões.

## 3.9 Véspera ao devedor (IMP-354)

08:00, D-1 do `proximo_acerto_em`; exige `permite_envio_proativo` e contato
WhatsApp. Texto: acerto amanhã, juro do período, saldo, "quando for acertar, é
só me chamar que te mando o Pix".

## 3.10 Credora registra pagamento por WhatsApp

Pré-requisito: §4.1. LLM chama `registrar_pagamento(nome, valor, data)` →
código resolve o devedor na carteira (ambíguo → pergunta qual; inexistente →
recusa fixa; data futura ou valor ≤ 0 → recusa) → eco estruturado ("Registro
pagamento de R$ 800,00 de Fulano da Silva em 20/09? Sim/Não") → `sim` →
`POST .../pagamentos` (`origem=copilot_credora`, `Idempotency-Key`, autoria
copilot via IMP-361) → resposta com juro/amortização/saldo do Motor.

## 3.11 Credora gera Pix pela tela

`POST /credit/emprestimos/{id}/cobrancas-pix` com `origem=tela`; a tela mostra
copia-e-cola/QR para ela enviar por onde quiser. Mesma expiração e confirmação.

## 3.11-b Comprovante: recepção, guarda e expurgo

- O ingress passa a **aceitar mídia** quando ela é comprovante de um devedor
  identificado — reversão nomeada do 356-B, que descartava toda mídia. Limite de
  payload, tipos aceitos (imagem e PDF) e descarte acima do limite continuam.
- O binário é guardado associado ao Empréstimo, com `sha256`, tipo, tamanho,
  remetente, recebido_em e estado (`recebido`, `lancado`, `recusado`).
- **Expurgo na quitação:** quitado o empréstimo, os comprovantes dele são
  apagados (binário e metadados de conteúdo). O `Pagamento`, a memória de
  cálculo e a trilha de auditoria permanecem — a prova contábil não depende da
  imagem.
- Mídia de remetente não identificado como devedor continua descartada.

## 3.12-b Credora configura a chave Pix própria

Card em `/app/pagamentos`: tipo e valor da chave Pix (CPF/CNPJ, telefone,
e-mail ou aleatória) e o nome que aparece para o devedor. É o que o agente
envia no §3.2-b. Sem chave configurada, o agente informa os valores e encaminha
à Credora, sem prometer Pix.

## 3.12 Credora liga ou desliga o Mercado Pago

Card **"Recebimento por Pix (Mercado Pago)"** em `/app/pagamentos` (rótulo
"Recebimento" na navegação; `/app/configuracoes` não foi usado para não
colidir com as Configurações financeiras, que já ocupam esse nome):
interruptor, `access_token` e `webhook_secret` write-only (mesmo padrão da
chave do provedor de IA e do token da instância: cifrados em repouso, nunca
devolvidos na leitura), botão **Testar** (uma chamada de leitura autenticada ao
provedor, sem criar cobrança) e um aviso com a taxa vigente do provedor.

Regras:

- **Desligado é o padrão.** Tenant novo não recebe por Pix até alguém ligar.
- Ligar exige as duas credenciais presentes e teste bem-sucedido.
- **Desligar não mexe em Pix já emitido:** os `pendente` continuam válidos até
  pagar ou expirar, e o webhook continua sendo aceito para eles — dinheiro em
  trânsito nunca é perdido por uma mudança de configuração. O que para é a
  emissão de Pix novo.
- Toda mudança é auditada com o usuário que fez.

## 3.13 Administrador configura o provedor de IA (BYOK)

Tela `/app/openai` → "Inteligência artificial": provedor (OpenAI, OpenRouter,
outro compatível com `base_url`), modelo, chave write-only ("configurada em
DD/MM, termina em …xy"), **Testar** (`GET /models` + completion de 5 tokens
sem dado TiaNet), interruptor **Atendimento** habilitável só com teste ok **e**
par provedor+modelo na lista de certificados (código). Diagnóstico: consumo do
dia, último erro, estado do consumidor. Aba Codex/OAuth atual permanece como
diagnóstico (ADR-020).

---

# 4. Decisões de Arquitetura

## 4.1 Autenticação do envelope Evolution (Slice 6)

O envelope traz `instanceToken`, segredo da instância que só existe no
Evolution e no nosso banco (cifrado). O ingress compara em tempo constante com
o token da instância configurada (cache em memória, invalidado na rotação).
Diferente → descarte `token_invalido`, `2xx` sem conteúdo, métrica. Só depois
o `Sender` tem valor. Reforço opcional no Caddy: allowlist do IP de origem do
Evolution (`CF-Connecting-IP`), a confirmar com quem opera o provedor.

Sem isso, um `POST` forjado com `Sender` da Credora registraria pagamento
falso (§3.10). Por isso o Slice 6 é pré-requisito do contexto Credora com
escrita, e entra junto com o consumidor da inbox.

## 4.2 Segunda rota pública, assinada

`/mercadopago/webhook` no agent, mesmo caminho Caddy → socat → socket. Exceção
explícita à decisão do contexto externo §2.2, **registrada na §2.4 daquele
documento** (v1.13.0): o MP assina (`x-signature`), o Evolution não. Polling
(§3.6) é o rollback documentado.

## 4.3 Consumidor da inbox no processo `agent`

Loop asyncio no lifespan; uma mensagem por sessão por vez (lease com fencing
já existente no executor); roteia por classe. Reaproveita `Executor`,
`SessaoConversa`, `ProvedorTokenCopilot`, `egress.enviar_texto` com
`EvolutionNotificationChannel` real. O `scheduler_worker` não conversa —
guardrail de arquitetura mantido.

**Toda mensagem nova deste plano** (confirmações, avisos à Credora, véspera,
lembrete, eco de confirmação, resposta de tool) sai **exclusivamente** por
`egress.enviar_texto`, que já implementa (356-E): identidade própria por
`IntencaoEgress` com chave derivada do payload canônico, registro durável de
tentativa (`EgressConversa`, máquina de estados), e a política da ADR-009 /
contexto externo §6.2 — só `ConnectTimeout`, `ConnectError` e `PoolTimeout`
provam não envio; todo o resto (5xx, `DecodingError`, timeout de leitura) é
`DESCONHECIDO` e **não reenvia sem prova de não aceite**. O Evolution não
deduplica por id; a deduplicação é nossa. Nenhuma mensagem com efeito
financeiro percebido (confirmação de pagamento) pode ser reenviada por retry
cego: em `DESCONHECIDO` ela fica visível em `/app/agent` para conciliação
manual pela Credora.

## 4.4 Escrita pelo agente só com eco + confirmação

Três tools de escrita (`gerar_pix`, `suspender_avisos`, `registrar_pagamento`)
passam obrigatoriamente por `ConfirmacaoPendente` na sessão (10 min). A
confirmação é reconhecida por lista fixa, não pelo modelo. Guardrail AST em
`tests/unit/architecture/`: nenhuma tool marcada `escrita=True` é chamável
sem confirmação resolvida.

## 4.5 Argumentos fixados pelo contexto

O modelo nunca escolhe `tenant_id`, `carteira_id`, `devedor_id`, `usuario`,
permissão ou URL. No contexto Devedor, todo argumento de identidade vem da
sessão; no Credora, o nome é resolvido em código contra a carteira.

## 4.6 Texto com número vem de apresentador

Resposta com valor financeiro é sempre montada em código sobre a resposta da
API. Prosa do modelo só é entregue quando nenhuma tool foi usada.

## 4.7 Configuração de LLM no banco, não no ambiente

O agent lê `ConfiguracaoLlm` (cache com recarga periódica ou sinal). `LLM_*`
de ambiente deixa de existir; `LLM_FORCE_OFF=true` permanece como override
de emergência **só para desligar**. Chave cifrada com a chave-mestra do
ambiente; nunca em DTO, log, métrica ou erro (guardrail AST).

**Migração governada** (compatibilidade com PLAN-033 / DR-005 §7):
1. Entrega 2b introduz `ConfiguracaoLlm` e a tela; o agent passa a ler o
   banco **e** ainda aceita `LLM_*` do ambiente como *seed* de primeira
   subida (se a tabela estiver vazia e `LLM_API_KEY` presente, grava a
   configuração cifrada e registra em auditoria `llm.configuracao.semeada`).
2. A partir da entrega 3, `LLM_*` (exceto `LLM_FORCE_OFF`) é **ignorado com
   aviso no log de boot**; `LLM_ENABLED` some do compose e do `.env.example`.
   Guardrail de container passa a falhar se `LLM_API_KEY` estiver no compose.
3. Telas/rotas `/platform/openai/*` (Codex App Server, ADR-020) permanecem
   como aba "Diagnóstico" da mesma tela; não são rota de inferência e não
   ganham nem perdem função.
4. DR-005 recebe adendo §9 na entrega 2b registrando que a rota A passa a ser
   configurada por tela, não por ambiente.

## 4.8 Fuso da semeadura

Jobs diários semeiam em `America/Sao_Paulo` (fecha a pendência do IMP-353).

## 4.8-b Integração opcional, catálogo montado por configuração

O Mercado Pago é uma escolha econômica da Credora, não um pressuposto do
produto: o provedor cobra por recebimento, e ela já tem o caminho sem taxa (o
devedor paga no Pix dela e o agente registra pelo §3.10). Por isso a integração
é **desligada por padrão** e o desligamento é de primeira classe, não um efeito
colateral de credencial ausente:

- `criar` recusa com erro nomeado quando desligado — a checagem vive no caso de
  uso, não só na UI;
- o **catálogo de tools do contexto Devedor é montado por Tenant**: com o
  Mercado Pago desligado, `gerar_pix` não entra na lista que vai ao modelo.
  Isso é mais forte que instruir o prompt a não oferecer: o modelo não pode
  chamar o que não recebeu;
- Pix `pendente` emitido antes do desligamento continua válido e conciliável.

## 4.10 A divisão juro/amortização vem do Motor, não do modelo

A alocação (juros → encargos → amortização → devolvido) hoje existe apenas
dentro de `registrar_pagamento`. Ela é **extraída para uma função pura** do
domínio e passa a servir os dois caminhos: o registro, como hoje, e uma
previsão de leitura `prever_alocacao(emprestimo, valor, data)`.

Sem isso, a frase *"R$ 627,00 de juros e R$ 1.000,00 de amortização"* sairia do
modelo. Com isso, o modelo extrai um número do comprovante e todo o resto é
cálculo do Motor, apresentado por apresentador.

## 4.11 O comprovante não autentica pagamento

Um comprovante é uma imagem — forjá-lo é trivial. Ele entra no fluxo como
**alegação do devedor**, e a verificação é a Credora conferindo a própria
conta. Isso muda o que a certificação precisa medir: não "o modelo lê o
comprovante corretamente", e sim "o modelo nunca lança sem o `sim` dela" e
"quando não consegue ler, diz que não conseguiu em vez de inventar".

## 4.9 Régua de certificação

| Contexto | Utilidade | Adversarial | Rodadas |
|---|---|---|---|
| Devedor | ≥ 27/30 | 40/40 | 3 |
| Credora | ≥ 25/30 (extração correta no eco) | 40/40 + classe "escrita sem confirmação" = 0 (medida em código) | 3 |

Fixtures congeladas por hash antes de rodar; rota A `gpt-5-mini`; orçamento
US$ 2,00. Sem certificação o contexto responde mensagem fixa.

---

# 5. Modelo de Dados

Migrations aditivas, downgrade reversível, `alembic revision -m` manual:

1. `cobranca_pix` (colunas da §2; índice único parcial `emprestimo_id WHERE
   estado='pendente'`; índices únicos em `external_reference` e `mp_payment_id`).
2. `pagamento.origem` (`VARCHAR`, default `manual`).
3. `preferencia_notificacao.avisos_suspensos_ate` (`DATE NULL`).
4. `inbox_pagamento` (`mp_notification_id` único, `mp_payment_id` indexado,
   `tipo`, `acao`, `recebido_em`, `payload_hash`, `estado ∈ {recebida,
   processada, orfao, duplicada}`).
5. `autorizacao_lembrete` (`tenant_id`, `data`, `mapa JSONB`, `autorizados
   JSONB`, `respondido_em`; único por tenant/data).
6. `configuracao_llm` (§2; um por tenant).
7. `contato`: índice em `valor` normalizado E.164 para `tipo='whatsapp'`.
8. Catálogo de permissões: as seis novas (§2).

---

# 6. API

Lista, não tabela: o `contract-check.js` ignora linhas de tabela ao comparar a
seção com o código.

**Recebimento por Pix (Mercado Pago), IMP-388 e IMP-376:**

- `GET /platform/mercadopago/configuracao` — estado da integração (ligada ou
  não, credenciais presentes, último teste). Permissão `mercadopago.configurar`.
  **Nunca devolve segredo.**
- `PUT /platform/mercadopago/configuracao` — grava `access_token` e
  `webhook_secret` cifrados. Permissão `mercadopago.configurar`,
  `Idempotency-Key`.
- `POST /platform/mercadopago/configuracao/testar` — uma leitura autenticada no
  provedor, sem criar cobrança. Permissão `mercadopago.configurar`,
  `Idempotency-Key`.
- `POST /platform/mercadopago/configuracao/habilitar` e
  `POST /platform/mercadopago/configuracao/desabilitar` — ligam e desligam.
  Habilitar exige credenciais e teste bem-sucedido; desabilitar **não** invalida
  `CobrancaPix` `pendente`. Permissão `mercadopago.configurar`,
  `Idempotency-Key`.
- `POST /credit/emprestimos/{id}/cobrancas-pix` — cria o Pix do acerto.
  Permissão `cobranca_pix.criar`, `Idempotency-Key`. `422` quando o valor cai
  fora do intervalo do Motor (`INV-001`) ou quando a integração está desligada.
- `GET /credit/emprestimos/{id}/cobrancas-pix` — lista as cobranças do
  empréstimo, com estado e validade. Permissão `emprestimo.ler`.
- `POST /mercadopago/webhook` — **no serviço `agent`, pública**, autenticada por
  HMAC (ADR-021). Sem permissão de Principal e sem `Idempotency-Key`: a
  deduplicação é por `mp_notification_id`.

**Motor, IMP-389:**

- `GET /credit/emprestimos/{id}/alocacao-prevista` — divisão que um valor
  produziria (`valor` e `data_referencia` na query), sem registrar nada.
  Permissão `motor.saldo.ler`. `400` para valor não positivo. Existe para o
  copiloto anunciar juro e amortização **antes** de a Credora autorizar o
  lançamento, com número do Motor.
- `POST /credit/emprestimos/{id}/pagamentos` ganha `origem` opcional (`manual`,
  `pix_mp`, `copilot_credora`), com default `manual` — mudança aditiva.

**Devedor e avisos, IMP-381, IMP-383 e IMP-386:**

- `GET /credit/devedores` com filtro `telefone` — localiza o devedor pelo
  contato WhatsApp normalizado em E.164. Permissão `devedor.ler`.
- `POST /credit/devedores/{id}/avisos/suspender` — suspende avisos proativos até
  o próximo acerto. Permissão `preferencia_notificacao.suspender`,
  `Idempotency-Key`.
- `GET /credit/lembretes/autorizacoes/{data}` — lista do dia com os elegíveis.
  Permissão `lembrete.autorizar`.
- `POST /credit/lembretes/autorizacoes/{data}` — registra quem a Credora
  autorizou. Permissão `lembrete.autorizar`, `Idempotency-Key`.

**Comprovante, IMP-390:**

- `POST /credit/emprestimos/{id}/comprovantes` — guarda o comprovante recebido
  do devedor. Permissão `comprovante.registrar`, `Idempotency-Key` exigida pelo
  contrato; a convergência real vem do `sha256` do conteúdo, porque o devedor
  reenvia a **imagem**, não a requisição. Expurgado na quitação do empréstimo.
- `GET /credit/emprestimos/{id}/comprovantes` — lista os comprovantes, **sem o
  binário**. Permissão `comprovante.registrar`.
- `GET /platform/mercadopago/chave-pix` e `PUT /platform/mercadopago/chave-pix`
  — a chave Pix da Credora, que o agente oferece no caminho sem taxa. Permissão
  `mercadopago.configurar`; `PUT` com `Idempotency-Key`. Ausente é resposta
  válida: sem chave, o agente não promete Pix.

**Provedor de IA (BYOK), IMP-379:**

- `GET /platform/llm/configuracao` e `PUT /platform/llm/configuracao` —
  provedor, modelo e chave (write-only). Permissão `llm.configurar`; `PUT` com
  `Idempotency-Key`.
- `POST /platform/llm/configuracao/testar`,
  `POST /platform/llm/configuracao/habilitar` e
  `POST /platform/llm/configuracao/desabilitar` — teste sintético e
  interruptor. Habilitar exige par provedor+modelo certificado. Permissão
  `llm.configurar`, `Idempotency-Key`.

Rito a cada mudança: `export_openapi` → `api:generate` → `test:contract` →
matriz e contadores.

---

# 7. Estratégia de Testes

- **Domínio:** `CobrancaPix` (INV-001 (CobrancaPix)/002, transições, terminais
  imutáveis); `elegivel_lembrete` (D+1, D+2 não, D+4, D+7, D+30); `permite_envio_proativo`
  com suspensão vencida/vigente/opt-out; `ConfiguracaoLlm` sem chave em `repr`.
- **Arquitetura (AST):** escrita sem confirmação; chave de provedor em
  DTO/log; `scheduler_worker` sem egress conversacional.
- **Integração:** webhook MP (assinatura válida, inválida, replay, `approved`
  vs `pending`, valor divergente, `CobrancaPix` inexistente); consumidor da
  inbox fim a fim com canal contador; `instanceToken` errado descartado;
  classificação `devedor` por E.164 (com e sem `+`, com 9º dígito); eco →
  `sim` → escrita; eco → outra mensagem → descarte; eco expirado; jobs de
  véspera/lembrete/expiração com relógio controlado e replay sem duplicar;
  autorização `1 2`/`todos`/`nenhum`/sem resposta.
- **Certificação:** suites Devedor e Credora (§4.9), fixtures congeladas.
- **Contrato:** OpenAPI, snapshot, matriz, contadores.
- **Frontend:** BFF + component + E2E para tela de Pix, lista de autorização
  em `/app/agent`, tela BYOK (chave nunca volta na leitura).
- **Stack real:** envio pelo Evolution com o número do fundador (contexto
  externo §6.2 — não há sandbox); Pix real de R$ 1,00 na conta PJ.

---

# 8. Ordem de Implementação

| # | Entrega | Depende de |
|---|---|---|
| 1 | IMP-353 fecha: gate, deploy, `credor_whatsapp`, fuso SP, bloco "em atraso" | — |
| 2a | Mercado Pago pela tela: `CobrancaPix`, API, webhook, expiração, confirmação | 1 |
| 2b | Tela BYOK + `ConfiguracaoLlm` + agent lendo do banco | — |
| 3 | Slice 6 + consumidor da inbox + contexto Devedor + certificação Devedor | 2a, 2b, rotação de segredos, reboot VPS, runbook socat/Caddy |
| 4 | Véspera + resumo com autorização + lembrete + suspensão | 3 |
| 5 | Contexto Credora com `registrar_pagamento` + certificação Credora | 3 |

Cada entrega: um PR, deploy observado, handoff. Pré-requisitos operacionais
fora do código antes do 3: rotação dos 3 segredos do incidente de 2026-09-18,
reboot da VPS, runbook da ponte socat/Caddy.

---

# 9. Riscos Técnicos

| Risco | Mitigação |
|---|---|
| Banimento do número pelo WhatsApp por mensagens automáticas | Régua curta, autorização humana, tom informativo; **recomendação:** instância separada do número pessoal da Credora (decisão de deploy) |
| Modelo não certifica no contexto Devedor | Resposta fixa; Pix pela tela, resumo, véspera e lembretes funcionam sem LLM |
| Webhook MP indisponível | Polling de 5 min (§3.6) |
| Pacote forjado no webhook Evolution | `instanceToken` (§4.1); contexto Credora com escrita só depois |
| IP do Evolution não fixo | Allowlist no Caddy é reforço opcional, não requisito |
| Modelo extrai valor errado | Eco + confirmação; erro vira "não", nunca lançamento |
| Devedor com dois empréstimos | `meu_saldo` lista os dois; `gerar_pix` pede qual (determinístico, por número) |
| Chave de provedor vaza em log | Guardrail AST + DTO sem segredo + cifra em repouso |
| Comprovante forjado | Não autentica nada: a Credora confere na conta dela antes de autorizar (§4.11) |
| Modelo lê o valor errado do comprovante | Eco à Credora com a imagem anexa; divergência entre valor lido e valor dito é relatada, não resolvida pelo agente |
| Mídia infla payload e armazenamento | Limite do 356-B mantido; só comprovante de devedor identificado; expurgo na quitação |
| Taxa do provedor corrói o lucro | Integração opcional, desligada por padrão; a Credora liga e desliga no painel e vê a taxa vigente no card |
| Desligar com Pix em trânsito | Desligamento impede emissão nova, nunca invalida `pendente`; webhook segue aceito para eles |

---

# 10. Histórico de Versões

| Versão | Data | Alteração |
|---|---|---|
| 1.3.2 | 2026-09-22 | §6: rotas do comprovante e da chave Pix declaradas como implementadas (IMP-390). |
| 1.3.1 | 2026-09-22 | Card do Mercado Pago vai para `/app/pagamentos` ("Recebimento"): `/app/configuracoes` colidiria com as Configurações financeiras. |
| 1.3.0 | 2026-09-22 | Caminho **sem taxa** completo (D13–D15): agente envia valores e a chave Pix da Credora, recebe e guarda o comprovante, extrai o valor, consulta `prever_alocacao` no Motor, pede autorização a ela com a imagem anexa e, no `sim`, lança e devolve ao devedor saldo, juros e próximo acerto atualizados. Comprovante é alegação, não prova; guardado enquanto o empréstimo vive e expurgado na quitação. Reverte o descarte de mídia do 356-B para devedor identificado. |
| 1.2.0 | 2026-09-22 | Mercado Pago passa a ser **opcional por Tenant**, ligado/desligado no painel, desligado por padrão: o provedor cobra 0,99% e a Credora já tem o caminho sem taxa (§3.10). Acrescenta `ConfiguracaoMercadoPago`, o caso §3.4-b (pedido de pagamento com a integração desligada), a §4.8-b (catálogo de tools montado por configuração) e a §3.12 (card no painel). |
| 1.1.0 | 2026-09-21 | Revisão documental: contrato real de assinatura do MP (manifesto, `ts`/`v1`, `data.id` da query), separação `mp_notification_id`/`mp_payment_id`, `external_reference` modelado como chave de correlação, egress herdando ADR-009/§6.2 sem retry cego, migração governada de `LLM_*` → banco, exceção de rota pública registrada no contexto externo §2.4. |
| 1.0.0 | 2026-09-21 | Desenho aprovado por seções em conversa com o proprietário (D1–D12). Origem: auditoria do módulo do agente em 2026-09-21. |
