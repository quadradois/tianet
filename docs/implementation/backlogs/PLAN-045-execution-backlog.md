# PLAN-045-EXEC — Atendimento ao devedor, recebimento por Pix e BYOK

**Versão:** 1.0.0

**Status:** Aprovado pelo proprietário em 2026-09-21 (PLAN-045 v1.1.0); execução ainda não iniciada

**Plano:** [PLAN-045](../plans/PLAN-045-atendimento-ao-devedor-e-recebimento-pix.md)

**Decisões de origem:** PLAN-045 §1.1 (D1–D12); [DR-005 §8](../../governance/decision-requests/DR-005-pii-modelo-e-teto-de-custo-do-copilot.md); contexto externo §2.4 v1.13.0

> **A execução deste backlog deve seguir obrigatoriamente o
> AGENT-LOOP-EXECUTION-PROTOCOL (ALP-001), em
> `docs/governance/agent-loop/AGENT-LOOP-EXECUTION-PROTOCOL.md`.**

---

# 1. Estado do sistema hoje

Verificado em 2026-09-21 por leitura de código e do handoff vigente, não presumido.

| Fato | Onde |
|---|---|
| Ingress WhatsApp em produção: recebe, deduplica, classifica `operadora`/`pre_cadastro`, guarda na inbox, responde `2xx` | `agent/ingress.py`; `prod-v1.1.33` |
| `instanceToken` do envelope é ignorado por construção | `agent/ingress.py` docstring |
| Ninguém consome a inbox: `Executor` e `triagem` só são importados por testes | `grep` em `src/` |
| Egress com identidade, chave derivada, máquina de estados e `DESCONHECIDO` existe; provado só com canal falso | `agent/egress.py`; PLAN-044 |
| `EvolutionNotificationChannel` faz só `/send/text` | `infrastructure/notifications/whatsapp.py` |
| LLM configurado por `LLM_*` de ambiente; `LLM_ENABLED=false`; 5 certificações reprovadas | `agent/service.py::LlmSettings`; PLAN-042 |
| Catálogo de 6 tools de leitura da Operadora pronto | `agent/catalogo.py` |
| IMP-353 (resumo diário + `PUT /platform/whatsapp/avisos`) no working tree, sem commit, gate não rodado | `application/resumo_diario.py`, `numero_avisos.py` |
| Motor calcula `saldo`/`quitacao` por `data_referencia` e separa juro/amortização em `registrar_pagamento` | `application/motor_financeiro.py` |
| `PreferenciaNotificacao` só sabe `permitido`/`opt_out`; usada só pelo canal e-mail | `domain/credit/notifications.py` |
| Varredura marca `em_atraso` e cria `CobrancaCaso`; nenhum aviso de atraso sai por WhatsApp | `application/varredura_cobranca.py` |
| Não existe busca de devedor por telefone | OpenAPI: só por documento/nome |
| Nada de Mercado Pago em `src/`, `frontend/`, ADR ou DR | `grep` |
| Tela `/app/openai` com login Codex e diagnóstico (ADR-020) | `presentation/api/openai_routes.py` |
| Produção sem `credor_whatsapp`; semeadura diária em UTC | memória IMP-353; `worker/scheduler_worker.py` |
| Pendências operacionais: rotação de 3 segredos (incidente 2026-09-18), reboot da VPS, runbook socat/Caddy | handoff 2026-09-19 §4 |

---

# 2. Regras inviolaveis deste backlog

1. **O agente propõe e informa; o Motor calcula; a Credora decide.** Nenhum valor financeiro nasce fora do Motor.
2. Toda escrita disparada por conversa passa por `ConfirmacaoPendente` (eco + `sim` na mesma sessão, 10 min). Guardrail AST cobra.
3. Toda mensagem sai só por `egress.enviar_texto`; `DESCONHECIDO` **não reenvia**.
4. O modelo nunca escolhe `tenant_id`, `carteira_id`, `devedor_id`, permissão ou URL.
5. LLM só liga com par provedor+modelo certificado para o contexto (§4.9 do plano).
6. Migrations aditivas, reversíveis, manuais. `Idempotency-Key` em todo POST/PUT de escrita (exceto webhook assinado).
7. Segredos (`MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, chave LLM) nunca em imagem, log, DTO, métrica ou erro.
8. Um PR por IMP, deploy observado por Gate, handoff no encerramento sincronizado.

---

# 3. Itens

## Fase 1 — Fechar o que está pronto

### IMP-372 — Fechar IMP-353 com fuso, bloco de atraso e deploy

- **Status:** código pronto e verde em 2026-09-21 (backend 1599, frontend unit/component/bff/contract/Playwright WhatsApp); resta deploy, `credor_whatsapp` em produção e observação do primeiro envio real.

- **Objetivo:** o resumo diário sai de verdade para a Credora, no horário certo, e inclui quem está em atraso.
- **Escopo:** rodar `tests/integration` inteira e `gate:full` sobre o working tree do IMP-353; semeadura diária em `America/Sao_Paulo` (`SemeadorDiarioCobranca` recebe `ZoneInfo`, testes com relógio controlado); bloco "em atraso" no `montar_texto_resumo_diario` (nome, dias, juro acumulado por `data_referencia` — só leitura do Motor); PR, deploy, cadastrar `credor_whatsapp` na tela, observar o primeiro envio real.
- **Critério de pronto:** resumo observado no WhatsApp da Credora às 08:00 BRT com vence-hoje e em-atraso; dia vazio não envia; replay não duplica; nenhum valor calculado fora do Motor (teste de arquitetura existente continua verde).

**GATE-E1** — IMP-372. Condição: resumo real observado em produção; handoff atualizado.

## Fase 2a — Mercado Pago pela tela

### IMP-373 — ADR da segunda rota pública e Aggregate `CobrancaPix`

- **Objetivo:** a exceção de rota pública tem decisão formal, e o domínio sabe o que é uma cobrança Pix.
- **Escopo:** reservar identificador na tabela do AMP-001 e emitir a ADR "segunda rota pública assinada no serviço `agent`" (contexto, decisão, consequências, rollback por polling); `domain/credit/cobranca_pix.py` com os campos da §2 do plano, INV-001 (`juro_periodo ≤ valor ≤ quitacao`), INV-002 (um `pendente` por empréstimo — verificado no repositório com índice parcial), transições `pendente→pago|expirado|cancelado`, terminais imutáveis, `external_reference = str(id)`; `OrigemPagamento` em `Pagamento`; `elegivel_lembrete` em `domain/credit/regua_lembrete.py`; documento de aggregate em `docs/domain/credit/aggregates/`.
- **Critério de pronto:** testes unitários cobrem cada invariante e cada transição proibida (`ViolacaoInvarianteError` com código); `elegivel_lembrete` testado em D+1, D+2, D+3, D+4, D+7, D+30; ADR aceita; `docs:validate` verde.

### IMP-374 — Persistência de cobrança, origem de pagamento e inbox de pagamento

- **Objetivo:** tudo da §5 do plano existe no banco, reversível.
- **Escopo:** migrations `cobranca_pix` (únicos em `external_reference`, `mp_payment_id`; parcial em `emprestimo_id WHERE estado='pendente'`), `pagamento.origem` default `manual`, `inbox_pagamento` (`mp_notification_id` único, `mp_payment_id` indexado, `tipo`, `acao`, `recebido_em`, `payload_hash`, `estado`); ORM 1:1; repositórios (merge/flush só); portas no UoW.
- **Critério de pronto:** `upgrade → downgrade → upgrade` em PostgreSQL real; `quality:migrations` verde; segundo `pendente` para o mesmo empréstimo falha no banco, não só na aplicação.

### IMP-375 — Cliente Mercado Pago

- **Objetivo:** falar com o MP por `httpx`, sem SDK, com segredo fora do código.
- **Escopo:** `infrastructure/mercadopago.py`: `criar_pix(valor, external_reference, expira_em, descricao) → (mp_payment_id, copia_cola, qr_base64)` via `POST /v1/payments` (`payment_method_id=pix`, `X-Idempotency-Key=external_reference`); `consultar(mp_payment_id) → (status, transaction_amount, external_reference)`; `cancelar(mp_payment_id)`; `MP_ACCESS_TOKEN` por ambiente; erros de transporte classificados pela mesma allowlist do §6.2 (só `ConnectTimeout`/`ConnectError`/`PoolTimeout` provam não-criação); `api.mercadopago.com` na allowlist do `agent-egress-proxy`.
- **Critério de pronto:** testes com `httpx.MockTransport` para criação, consulta, cancelamento, 4xx, 5xx e timeout; token nunca aparece em `repr`, log ou exceção (teste); chamada real de R$ 1,00 na conta PJ registrada no relatório do Gate (sem segredo).

### IMP-376 — Caso de uso "gerar Pix" e API

- **Objetivo:** a Credora (e depois o agente) cria um Pix do acerto apurado.
- **Escopo:** `application/cobranca_pix.py::criar(emprestimo_id, valor, origem, usuario)`: consulta Motor na data de hoje, valida INV-001, cria no MP, persiste `pendente`, auditoria; `POST /credit/emprestimos/{id}/cobrancas-pix` (permissão `cobranca_pix.criar`, `Idempotency-Key`), `GET` listando; `origem` opcional em `POST .../pagamentos`; permissões no catálogo; `export_openapi` → `api:generate` → `test:contract`; matriz e contadores.
- **Critério de pronto:** integração cobre valor abaixo do juro (422 `INV-001`), acima da quitação, segundo pendente (409), replay idempotente, cross-tenant (404); snapshot e contadores reconciliados.

### IMP-377 — Webhook, consumidor de pagamento, confirmação e expiração

- **Objetivo:** Pix pago entra no Motor sozinho e os dois lados são avisados; Pix vencido morre sozinho.
- **Escopo:** `agent/mercadopago_webhook.py` montado em `/mercadopago/webhook`: validação `x-signature` (manifesto `id:[data.id];request-id:[x-request-id];ts:[ts];`, HMAC-SHA256 com `MP_WEBHOOK_SECRET`, tempo constante, `ts` ±5 min) antes de ler o corpo; grava `inbox_pagamento`; `2xx` em < 22 s. Consumidor no lifespan do agent: `GET /v1/payments/{data.id}`, `approved` → `POST .../pagamentos` (`origem=pix_mp`, `Idempotency-Key=external_reference`) → `pago`; divergência de valor → registra o recebido, `divergente=true`; `external_reference` desconhecido → `orfao`. Mensagens por `egress.enviar_texto` (devedor e Credora, texto de apresentador com valores do Motor). Job do scheduler a cada 5 min: expira/cancela ou processa `approved` tardio. Caddy: rota `@mp` → mesmo socat.
- **Critério de pronto:** integração cobre assinatura válida/inválida/`ts` vencido/replay de notificação/`payment.updated` repetido/`pending`/`approved`/divergente/órfão; confirmação em `DESCONHECIDO` não reenvia e aparece em `/app/agent`; expiração com relógio controlado; Pix real de R$ 1,00 pago e conciliado em produção, observado.

### IMP-378 — Tela da Credora: Pix no empréstimo

- **Objetivo:** a Credora gera e copia o Pix sem sair da tela do empréstimo.
- **Escopo:** BFF server-only para `cobrancas-pix`; card no empréstimo com valor sugerido (juro do período) editável dentro do intervalo, botão "Gerar Pix", copia-e-cola/QR, lista de cobranças com estado e contagem regressiva; policy de permissão; suíte Playwright `motor` ou `cobranca` estendida.
- **Critério de pronto:** BFF + component + E2E verdes; `test:certification` verde; valor fora do intervalo bloqueado na UI **e** rejeitado pelo backend (teste dos dois).

**GATE-E2** — IMP-373..378. Condição: Pix real pago e conciliado em produção; ADR aceita; snapshot reconciliado; handoff.

## Fase 2b — BYOK por tela

### IMP-379 — `ConfiguracaoLlm`: domínio, cifra, API e seed

- **Objetivo:** provedor, modelo e chave vivem no banco, cifrados, por tenant.
- **Escopo:** `domain/platform/configuracao_llm.py` (campos da §2 do plano; `repr` sem chave); migration `configuracao_llm`; cifra com o mesmo `CifraToken` da `ConexaoWhatsApp`; `GET/PUT /platform/llm/configuracao`, `POST .../testar` (`GET /models` + completion de 5 tokens sem dado TiaNet), `POST .../habilitar|desabilitar` (habilitar exige teste ok **e** par certificado — lista em `agent/certificados.py`); permissão `llm.configurar` (administrador; nunca copilot); seed auditado a partir de `LLM_*` quando a tabela está vazia; DR-005 §9 registrando a mudança; DTO nunca devolve a chave (só `configurada_em` e últimos 2 caracteres).
- **Critério de pronto:** guardrail AST "chave de provedor não aparece em DTO/log/métrica/erro"; testes de habilitar com par não certificado (422), sem teste (422), replay; seed idempotente; contrato reconciliado.

### IMP-380 — Tela "Inteligência artificial" e agent lendo do banco

- **Objetivo:** ligar/desligar e trocar de modelo sem deploy.
- **Escopo:** `/app/openai` renomeada; formulário provedor/modelo/chave (write-only), Testar, interruptor Atendimento com motivo quando bloqueado, diagnóstico (consumo do dia via `custo.py`, último erro, estado do consumidor); aba Diagnóstico Codex preservada (ADR-020). Agent: `LlmSettings` passa a ser carregado do banco com cache e recarga (intervalo + invalidação por escrita); `LLM_FORCE_OFF=true` desliga; `LLM_*` (exceto `FORCE_OFF`) ignorado com aviso no boot; `LLM_ENABLED` removido do compose e `.env.example`; guardrail de container falha se `LLM_API_KEY` estiver no compose.
- **Critério de pronto:** BFF + component + E2E; teste do agent: habilitado no banco + `FORCE_OFF` → desligado; troca de modelo refletida sem restart (teste com relógio); nenhum `LLM_ENABLED` restante no repo (`grep` em teste).

**GATE-E3** — IMP-379..380. Condição: chave configurada pela tela em produção, teste sintético ok, interruptor ainda **desligado** (sem certificação do Devedor); handoff.

## Fase 3 — Contexto Devedor

### IMP-381 — Slice 6, identidade por telefone e classe `devedor`

- **Objetivo:** só pacote do Evolution vale; o agente sabe quem é devedor pelo número.
- **Escopo:** ingress compara `instanceToken` em tempo constante com o token da instância (decifrado, cacheado, invalidado na rotação; descarte `token_invalido` com métrica); índice em `contato.valor` normalizado E.164 para `tipo='whatsapp'` (migration + normalização na escrita); `GET /credit/devedores?telefone=` (permissão `devedor.ler`; só ativos); `ClasseContexto.DEVEDOR` e classificação na ordem allowlist → devedor → pré-cadastro; contrato reconciliado.
- **Critério de pronto:** pacote com token errado/ausente descartado antes de qualquer leitura de `Sender`; token rotacionado na tela → cache invalidado (teste); classificação com/sem `+`, com/sem 9º dígito; devedor inativo → `pre_cadastro`; cross-tenant 404.

### IMP-382 — Consumidor da inbox, egress real e confirmação obrigatória

- **Objetivo:** a mensagem sai da inbox, vira turno e a resposta chega no WhatsApp de verdade.
- **Escopo:** loop asyncio no lifespan do agent (`agent/consumidor.py`): lê `recebida` em ordem, lease com fencing por sessão (reaproveita o do executor), roteia por classe, marca `processada`/`falha` com motivo; `egress.enviar_texto` ligado ao `EvolutionNotificationChannel` real; `ConfirmacaoPendente(tool, args, expira_em)` na `SessaoConversa` com reconhecimento por lista fixa (`sim`, `s`, `confirmo`, `pode`, `ok`) e descarte em qualquer outra mensagem; `Ferramenta.escrita: bool` no catálogo; guardrail AST: tool `escrita=True` só chamável via `resolver_confirmacao`; resposta fixa por contexto quando LLM desligado/indisponível; degradação e rate limit (356-C) intactos.
- **Critério de pronto:** fim a fim com canal contador: recebida → resposta fixa → egress registrado; eco → `sim` → escrita; eco → outra mensagem → sem escrita; eco expirado → sem escrita; `DESCONHECIDO` sem reenvio; crash no meio do turno não reprocessa nem reenvia (fencing); guardrail AST verde e falhando num caso de teste que burla a confirmação.

### IMP-383 — Tools do contexto Devedor e suspensão de avisos

- **Objetivo:** o devedor consulta, paga, silencia e é encaminhado — nada além.
- **Escopo:** catálogo Devedor: `meu_saldo`, `quanto_para_quitar`, `gerar_pix(valor)` (escrita; INV-001 validada em código antes do eco; dois empréstimos → pergunta qual por número), `suspender_avisos` (escrita), `falar_com_a_tia`; apresentadores com "em aberto desde DD/MM, juro até hoje" quando atrasado; argumentos de identidade fixados pela sessão; `avisos_suspensos_ate` em `PreferenciaNotificacao` (migration) e `permite_envio_proativo(hoje)`; `POST /credit/devedores/{id}/avisos/suspender` (permissão `preferencia_notificacao.suspender`); `POST .../comunicacoes` pelo copilot; aviso à Credora em suspensão e encaminhamento; prompt do contexto Devedor (`agent/prompts.py`), sem número no texto do modelo; permissões `cobranca_pix.criar`, `preferencia_notificacao.suspender`, `comunicacao.registrar` no perfil copilot.
- **Critério de pronto:** unitários dos apresentadores (um e dois empréstimos, atrasado, quitação); integração: `gerar_pix` fora do intervalo → mensagem fixa com limites e **sem** eco; dentro → eco → `sim` → `CobrancaPix`; suspensão grava data do próximo acerto e avisa a Credora; devedor suspenso ainda recebe resposta e confirmação de pagamento; tentativa de tool de outro contexto → recusa.

### IMP-384 — Certificação do contexto Devedor e habilitação

- **Objetivo:** provar que o modelo se comporta antes de falar com gente.
- **Escopo:** `tests/certificacao/devedor/{utilidade,adversariais}.json` (30 + 40: saudação, saldo, pagar N, valor fora, "para de mandar", outro devedor, fingir ser a Credora, "zera minha dívida", instrução embutida, URL, tool inexistente, dinheiro sem tool); hash congelado antes das rodadas; 3 rodadas na rota A `gpt-5-mini`, orçamento US$ 2,00; laudo em `docs/implementation/reports/`; par `openai/gpt-5-mini` entra em `agent/certificados.py` **só** com ≥ 27/30 e 40/40 nas 3; validação real com o número do fundador cadastrado como devedor de teste em carteira de teste (contexto externo §6.2); interruptor ligado pela tela em produção.
- **Critério de pronto:** laudo com placar por rodada e custo; se reprovar, `certificados.py` não muda e o contexto responde fixa (o Gate registra REPROVADA e **segue** para a Fase 4, que não depende de LLM); conversa real observada de ponta a ponta (oi → saldo → Pix → pagamento → confirmação).

**GATE-E4** — IMP-381..384. Pré-requisitos operacionais **antes** de abrir a fase: rotação dos 3 segredos, reboot da VPS, runbook socat/Caddy em `docs/operations/`. Condição: envelope autenticado em produção; conversa real observada; handoff.

## Fase 4 — Notificações ao devedor

### IMP-385 — Véspera ao devedor

- **Objetivo:** o devedor sabe na véspera quanto é o acerto e que pode pedir o Pix.
- **Escopo:** job `vespera_devedor` (tipo/origem no scheduler, semeado 08:00 BRT para `proximo_acerto_em = amanhã`), contato WhatsApp preferencial, `permite_envio_proativo`, texto de apresentador (juro do período, saldo, "quando for acertar, é só me chamar que te mando o Pix"), idempotência `(tenant, vespera, emprestimo, data)`, envio por `egress.enviar_texto`, evento nomeado quando não envia (`vespera_whatsapp_sem_consentimento`, `sem_contato`, `suspenso`).
- **Critério de pronto:** testes de véspera/outra data/consentido/ausente/opt-out/suspenso/contato ausente/replay/`DESCONHECIDO`; primeiro envio real observado.

### IMP-386 — Lembrete de atraso autorizado pela Credora

- **Objetivo:** o lembrete só sai quando a Credora disse que pode, no dia.
- **Escopo:** `AutorizacaoLembrete` (domínio + migration, único por tenant/data); resumo diário (IMP-372) ganha bloco numerado dos elegíveis (`elegivel_lembrete` sobre `em_atraso` da varredura, filtrado por consentimento/suspensão) e cria a autorização do dia; tool determinística `autorizar_lembretes` no contexto Credora (`1 2`, `todos`, `nenhum` contra o mapa do dia; sem LLM); `GET/POST /credit/lembretes/autorizacoes/{data}` (permissão `lembrete.autorizar`) e lista com botões em `/app/agent`; job `lembrete_atraso` disparado pela autorização, texto de apresentador (acerto de dia N em aberto, juro até hoje, "quando for bom pra você, me chama"), idempotência `(tenant, lembrete, emprestimo, data)`; sem resposta até 23:59 → nada sai, dia seguinte lista nova.
- **Critério de pronto:** testes de régua (D+1 sim, D+2 não, D+4 sim), autorização parcial/total/nenhuma/ausente, pago no dia → sai da lista, suspenso → sai da lista, replay; lembrete real observado após autorização real por WhatsApp.

**GATE-E5** — IMP-385..386. Condição: véspera e lembrete reais observados; handoff.

## Fase 5 — Credora registra pagamento por WhatsApp

### IMP-387 — `registrar_pagamento` com eco e certificação do contexto Credora

- **Objetivo:** "Fulano me pagou 800 ontem" vira lançamento no Motor, só depois do `sim`.
- **Escopo:** tool `registrar_pagamento(nome, valor, data)` (escrita) no catálogo Credora; resolução do devedor em código (ambíguo → pergunta qual; inexistente/valor ≤ 0/data futura → recusa fixa); eco estruturado; `POST .../pagamentos` com `origem=copilot_credora`, `Idempotency-Key`, autoria copilot (IMP-361); resposta com juro/amortização/saldo do Motor; permissão `pagamento.registrar` no perfil copilot; `tests/certificacao/credora/` com as 6 tools de leitura + escrita: utilidade ≥ 25/30 (extração correta no eco), adversarial 40/40 + classe "escrita sem confirmação" = 0 medida em código, 3 rodadas; laudo; par certificado por contexto em `certificados.py`.
- **Critério de pronto:** integração cobre ambíguo, inexistente, data futura, valor negativo, eco → `sim` → pagamento único, replay, `não`; certificação com laudo; lançamento real pela Credora observado e conferido na tela.

**GATE-E6** — IMP-387. Condição: certificação Credora com laudo; lançamento real observado; PLAN-045 fechado com os critérios da §12 do PLAN-033 aplicados por analogia (OpenAPI, snapshot, matriz, migrations em PostgreSQL real, suites, adversarial fail-closed, runbook, árvore sem segredo).

---

# 4. Ordem e dependências

| Ordem | IMP | Depende de |
|---|---|---|
| 1 | 372 | — |
| 2 | 373 | reserva no AMP-001 |
| 3 | 374 | 373 |
| 4 | 375 | credenciais MP de produção verificadas |
| 5 | 376 | 374, 375 |
| 6 | 377 | 376; Caddy na VPS |
| 7 | 378 | 376 |
| 8 | 379 | — (paralelo à Fase 2a) |
| 9 | 380 | 379 |
| 10 | 381 | GATE-E2, GATE-E3, pendências operacionais |
| 11 | 382 | 381 |
| 12 | 383 | 382, 376 |
| 13 | 384 | 383, 380 |
| 14 | 385 | 382 |
| 15 | 386 | 372, 385 |
| 16 | 387 | 384 (Slice 6 provado), 386 |

Gates: E1 (372) · E2 (373–378) · E3 (379–380) · E4 (381–384) · E5 (385–386) · E6 (387). Blocos menores que 5 justificados pela fronteira de deploy observado entre fases (ALP-001 §3).

---

# 5. Fora de escopo

PLAN-045 §1.2, na íntegra. Em particular: IMP-357 (pré-cadastro) segue no PLAN-033; régua além do lembrete autorizado; e-mail; PDF; cartão/boleto; promessa e renegociação por chat; leitura de carteira por LLM no contexto Credora além das 6 tools já catalogadas.

---

# 6. Histórico de Versões

| Versão | Data | Alteração |
|---|---|---|
| 1.0.0 | 2026-09-21 | Backlog inicial: IMP-372..387 em seis gates, a partir do PLAN-045 v1.1.0 aprovado pelo proprietário. |
