# Discovery — Agentic de atendimento e relatorios

**Data:** 2026-09-09  
**Objetivo:** identificar a documentacao de planejamento do atendimento agentic
por WhatsApp e verificar como os relatorios operacionais entram no desenho.  
**Workflow / classificacao:** `discover` / `ARCHITECTURAL`  
**Impacto agentic:** `PRESENT`  
**Estado:** discovery concluido; a Fase C permanece bloqueada pelo GATE-E1b e
por uma lacuna no catalogo nominal de ferramentas.  
**Parecer especializado:** OpenCode Harness, tarefa
`8b1a8ce0-c1cf-4580-a9ef-ab24d87d4d0f`, `ai_architect`, `READ_ONLY`.

---

## 1. Resposta executiva

Existe planejamento formal e detalhado para o Agentic. A fonte principal e o
[PLAN-033](../../implementation/plans/PLAN-033-copilot-tianet.md), com execucao
detalhada no
[backlog do PLAN-033](../../implementation/backlogs/PLAN-033-execution-backlog.md)
e decisoes de IA na
[DR-005](../../governance/decision-requests/DR-005-pii-modelo-e-teto-de-custo-do-copilot.md).

O repositorio ja possui o canal WhatsApp e os relatorios operacionais, mas ainda
nao possui o servico conversacional. O `docker-compose.yml` publica `postgres`,
`migrate`, `worker`, `api` e `frontend`; nao ha processo `agent`. Tambem nao ha,
no codigo de producao, cliente LLM, inbox conversacional, sessao do agente,
registro de tool-call ou Aggregate `PreCadastro`.

Os quatro endpoints de relatorio estao implementados e protegidos por
`relatorios.operacionais.ler`. Entretanto, a Entrega 356-D ainda nao os nomeia
como ferramentas. Ela exige uma allowlist nominal de GETs e cita apenas o saldo
agregado do IMP-362. Antes de implementar a Fase C, o plano precisa decidir,
endpoint por endpoint, quais relatorios o agente pode consultar, com permissao,
parametros, schema filtrado e campos que nao podem chegar ao modelo.

---

## 2. Fontes governantes

| Fonte | Papel |
|---|---|
| [PLAN-033](../../implementation/plans/PLAN-033-copilot-tianet.md) | Objetivo, fases, API, fora de escopo e gates |
| [Backlog PLAN-033](../../implementation/backlogs/PLAN-033-execution-backlog.md) | Regras inviolaveis, IMPs, dependencias e criterios de pronto |
| [DR-005](../../governance/decision-requests/DR-005-pii-modelo-e-teto-de-custo-do-copilot.md) | BYOK, PII no prompt, custo e retencao |
| [Contexto externo](../../operations/contexto-externo.md) | Evolution, topologia, VPS, provedor e insumos operacionais |
| [PLAN-014](../../implementation/plans/PLAN-014-epic-007-operacao-diaria.md) | Implementacao dos relatorios operacionais |
| [PRODUCT-008](../../product/credit/capabilities/PRODUCT-008-administrar-relatorios.md) e [FEATURE-031](../../product/credit/features/FEATURE-031-consultar-relatorios-operacionais.md) | Fronteiras de produto dos relatorios |

---

## 3. Estado observado

### 3.1 Fundacao ja entregue

| Item | Estado observado |
|---|---|
| IMP-352 — validar Evolution | Concluido em 2026-08-31; o conector voltou a ser observado localmente em 2026-09-09 |
| IMP-358 — governanca | Concluido; GATE-E1a cumprido em 2026-08-27 |
| IMP-355 — usuario/perfil copilot | Rota de criacao concluida; seed do perfil `copilot` ficou para a abertura da Fase C |
| IMP-360 — separar submeter de decidir | Concluido em 2026-08-27 |
| IMP-361 — autoria | Declarado concluido no handoff de 2026-08-31; falta carimbo equivalente no backlog |
| IMP-362 — saldo agregado por Devedor | Concluido em 2026-08-27; GET protegido por `motor.saldo.ler` |

### 3.2 Trabalho ainda pendente

| Item | Estado e dependencia |
|---|---|
| IMP-359 — producao e tenancy | Pendente. VPS e dominio existem; faltam deploy, TLS, backup/restore, CD/rollback, endurecimento, segredos, prova de origem do webhook, runbooks e higiene da instancia Evolution |
| IMP-353 — resumo diario ao Credor | Pendente e deterministico; exige GATE-E1b |
| IMP-354 — aviso de vespera ao Devedor | Pendente e deterministico; exige consentimento e GATE-E1b |
| IMP-356 A–F — servico conversacional | Nao iniciado; depende de IMP-359 e das fundacoes anteriores |
| IMP-357 — PreCadastro com aprovacao humana | Nao iniciado; depende do IMP-356 |

O WhatsApp conectado comprova o canal, mas nao fecha o IMP-359 nem cria o
atendimento agentic.

### 3.3 Relatorios disponiveis para um futuro catalogo de ferramentas

| Endpoint GET | Parametros de negocio | Permissao |
|---|---|---|
| `/credit/carteiras/{carteira_id}/relatorios/resumo` | `data_referencia` | `relatorios.operacionais.ler` |
| `/credit/carteiras/{carteira_id}/relatorios/vencimentos` | `data_referencia` | `relatorios.operacionais.ler` |
| `/credit/carteiras/{carteira_id}/relatorios/pagamentos` | `inicio`, `fim` | `relatorios.operacionais.ler` |
| `/credit/carteiras/{carteira_id}/relatorios/fluxo` | `inicio`, `fim` | `relatorios.operacionais.ler` |
| `/credit/devedores/{devedor_id}/saldo` | referencia temporal do contrato | `motor.saldo.ler` |

Os quatro primeiros vivem em
`src/emprestimo/presentation/api/operacao_diaria_routes.py` e usam
`RelatoriosOperacionaisService`. O saldo agregado vive em
`src/emprestimo/presentation/api/motor_routes.py` e ja foi criado para impedir
que o LLM some saldos.

---

## 4. To-be ja planejado

O PLAN-033 divide o produto em quatro fases:

1. **Fase A, sem LLM:** o sistema envia resumo diario ao Credor e aviso de
   vespera ao Devedor com texto deterministico.
2. **Fase B, sem LLM:** identidade propria, RBAC segregado e autoria das escritas.
3. **Fase C, com LLM:** atendimento de leitura por WhatsApp, tool-use restrito a
   GETs, inbox duravel, deduplicacao, limites, egress idempotente, JWT, auditoria
   propria e retencao.
4. **Fase D, com LLM:** coleta conversacional de pre-cadastro; somente o Credor
   aprova e cria o Devedor.

O IMP-356 foi decomposto em seis entregas:

- `356-A`: ingress duravel, classificacao e deduplicacao;
- `356-B`: limite de payload e descarte de midia;
- `356-C`: rate limit, concorrencia e medicao de consumo;
- `356-D`: cliente LLM BYOK e tool-use restrito;
- `356-E`: egress pelo adapter Evolution existente;
- `356-F`: sessao, JWT, auditoria, metricas e expurgo aos 90 dias.

---

## 5. Lacuna material: relatorios ainda nao sao ferramentas governadas

O backlog determina que a Operadora recebe uma allowlist **nominal** de GETs,
incluindo o saldo do IMP-362. Nenhum trecho do PLAN-033 ou de seu backlog lista
nominalmente `resumo`, `vencimentos`, `pagamentos` e `fluxo` nessa allowlist.

Isso impede certificar a Fase C, pois ainda nao esta definido:

- quais endpoints entram no perfil `copilot`;
- quais parametros a aplicacao monta a partir do contexto autenticado;
- quais campos de resposta podem chegar ao LLM;
- como cada resposta sera apresentada sem calculo local;
- quais consultas exigem desambiguacao de Devedor, data ou periodo;
- se campos de projecao, em especial `projecao_juros`, ficam fora do canal
  conversacional para evitar que uma estimativa seja apresentada como promessa.

**Achado B1 — `BLOCKER`, estado `OPEN`:** o catalogo nominal e seus schemas devem
ser decididos no workflow Architect/Plan antes de executar o IMP-356-D. O parecer
especializado nao fecha o gate e o discovery nao escolhe silenciosamente esse
escopo.

---

## 6. Regras que o agente deve preservar

1. O agente nunca calcula dinheiro; copia valores tipados da API e do Motor.
2. Pagamento, estorno, renegociacao, contrato, emprestimo, proposta e decisao
   comercial nao sao ferramentas do v1.
3. Somente o contexto Operadora pode consultar carteira.
4. Remetente desconhecido entra em `PreCadastro`, com zero ferramentas de leitura.
5. Operadora e PreCadastro nunca compartilham sessao, historico, cache,
   tool-call ou resposta.
6. A allowlist do numero nao autentica o webhook. A origem precisa ser provada no
   reverse proxy; sem isso, a Operadora permanece desabilitada em fail-closed.
7. O modelo nao escolhe Tenant, Carteira, Usuario, permissao, URL ou ferramenta.
8. Nao existe fallback automatico de modelo ou provedor.
9. Falha, timeout, rate limit ou resposta invalida produzem mensagem fixa.
10. Tool-calls tem trilha propria sem prompt, corpo integral, segredo ou PII
    desnecessaria em logs.

---

## 7. Divergencias documentais encontradas

| Divergencia | Evidencia | Consequencia |
|---|---|---|
| Provedor BYOK | PLAN-033 e backlog ainda dizem que a escolha esta pendente; `contexto-externo.md` diz que foi escolhido e a chave existe, mas nome e modelo ainda nao foram registrados | O IMP-359 deve reconciliar `LLM_BASE_URL` e `LLM_MODEL` antes do deploy |
| Status dos relatorios | PRODUCT-008 e FEATURE-031 permanecem `Proposto`; PLAN-014 e seu backlog estao `Implementado`, e o codigo possui os quatro endpoints | A verdade documental do produto esta defasada |
| Fluxo “previsto e realizado” | Documentos e nome do endpoint prometem previsto/realizado; o codigo removeu o valor `previsto` apos a DR-004 e devolve `realizado`, quantidade de acertos e IDs de pagamentos | Contrato e linguagem do agente precisam refletir o que o backend realmente afirma |
| IMP-361 | Handoff declara concluido, backlog nao possui o mesmo carimbo | Estado deve ser reconciliado sem reexecutar trabalho concluido |

---

## 8. Sequencia recomendada

1. Executar Architect/Plan para reconciliar o PLAN-033 e declarar o catalogo
   nominal de ferramentas de relatorio, suas permissoes e schemas filtrados.
2. Concluir o IMP-359 e demonstrar o GATE-E1b em VPS, incluindo a prova de origem
   do webhook ou o bloqueio fail-closed da Operadora.
3. Executar IMP-353 e IMP-354 conforme a ordem vigente do plano; ambos entregam
   valor sem LLM.
4. Implementar IMP-356 em slices A–F, com cada controle deterministico testado.
5. Certificar a Fase C com a suite adversarial completa. Um transcript feliz nao
   certifica o agente.
6. Somente depois abrir o IMP-357 e a Fase D.

Essa ordem respeita as dependencias do backlog. A alternativa de implementar os
IMPs 353/354 antes do IMP-359 foi rejeitada nesta reconciliacao porque ambos
dependem explicitamente do GATE-E1b.

---

## 9. Review do coordenador

**Completude:** o parecer cobriu AS-IS, to-be, alternativas, invariantes,
contrato de avaliacao, matriz dos IMPs e lista de endpoints.  
**Fontes revalidadas:** rotas, servico de relatorios, catalogo IAM, compose,
PLAN-033, backlog, DR-005 e contexto externo.  
**Correcao aplicada:** descartada a sequencia `IMP-353 -> IMP-354 -> IMP-359`,
pois contradiz as dependencias do backlog.  
**Resultado:** `BLOQUEADA` para iniciar a Fase C enquanto B1 estiver aberto;
discovery aceito como evidencia.  
**Gate afetado:** GATE-E3, sem alterar o bloqueio operacional anterior do
GATE-E1b.

## 10. Contrato de avaliacao futuro

| Requisito | Evidencia esperada | Bloqueador |
|---|---|---|
| Catalogo de tools | Lista nominal, permissao, schema de entrada e schema filtrado de saida | sim |
| Isolamento | Testes com Operadora, desconhecido, dois Tenants e dois Devedores | sim |
| Autorizacao | Origem do webhook provada; Tenant/Carteira/Usuario fora do controle do LLM | sim |
| Prompt injection | Tentativas de exfiltracao, URL arbitraria, tool inexistente e escrita financeira falham fechadas | sim |
| Dinheiro | Toda resposta monetaria aponta para campo oficial de uma tool-call; nenhuma soma ou inferencia local | sim |
| Durabilidade | Replay, concorrencia e crash antes/depois do tool-call nao duplicam efeito ou resposta | sim |
| Degradacao | Timeout, rate limit, 401 e resposta invalida usam mensagem fixa, sem fallback | sim |
| Privacidade | Logs e metricas sem prompt integral, segredo, token ou PII desnecessaria; expurgo em 90 dias | sim |

