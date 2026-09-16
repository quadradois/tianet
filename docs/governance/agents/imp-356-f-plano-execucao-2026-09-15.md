# Plano — IMP-356-F: executor, sessão, auditoria própria e observabilidade

**Última revisão:** 2026-09-15
**Status:** Concluído
**Slice atual:** Slice 5 (lote concluído tecnicamente)
**Bloqueado por:** aprovação explícita do fundador (G5)
**Risco:** Alto
**Impacto agentic:** PRESENT
**Justificativa e gatilhos:** executor altera caminho produtivo (leases, escrita em tabelas novas, refresh de credencial, auditoria); triagem com parecer especializado somente-leitura anexado antes do execute, conforme política agentic. Parecer não aprova gates.
**Autorização:** aprovada pelo fundador em 2026-09-15; escopo restrito aos 5 slices, só dado sintético, sem egress real, sem wiring no ingress produtivo até slice 5; início pelo Slice 1
**Plano/IMP/GATE-E do produto:** PLAN-033, IMP-356-F, GATE-E3 (aberto)

## Objetivo

Fechar o loop do copiloto sem abrir a torneira: executor com deadline e
orçamento enforcement em código, sessão com refs opacas vinculadas,
credencial copilot com refresh proativo e 401 único, trilha própria sem
PII e métricas persistidas. Tudo verificável com relógio controlado,
PostgreSQL real e falhas injetadas — nenhum transcript feliz isolado.

## Contexto e achados do repositório

- Lote 1+2 entregues (catálogo, dispatcher, apresentadores, LlmClient,
  intenções, medição, triagem com modelo recusado). Falta só quem chama:
  executor, resolvedor de produção, provedor de token com refresh, log
  próprio. Assinaturas prontas para plugar (`LlmClient.chat`,
  `interpretar_chamada`, `executar_ferramenta`, `renderizar`).
- Base 356-A/B/C pronta: inbox com unicidade, admissão com slots
  (`SlotExecucaoORM` reutilizável como trava), métricas processo-local.
- `SessaoConversa` hoje é só chave (sem mensagens/refs/expiração); colunas
  `referencia_pendente/expira_em` existem e nascem vazias aguardando F.
- Auth: access 15min / refresh 7d, sem rotação de refresh; `refresh()` sob
  demanda, ninguém do agente chama. Sem secret store, sem perfil copilot.
- Auditoria: `audit_log` genérico + `auditar_escrita` (só IDs); sem tabela
  própria de execução; `RegistroComunicacao` proibido para o agente
  (`devedor_id` NOT NULL).
- Modelo segue não certificado (PLAN-037/038): executor roda contra
  LlmClient real só em ambiente de certificação; prova produtiva usa
  respostas enlatadas + falhas injetadas até certificação.

## Escopo e não objetivos

Inclui: modelos próprios (mensagem, tool-call) + resolvedor de refs por
sessão; credencial copilot (login, secret store, refresh proativo, 401
único); executor (deadline 45s, 2 LLM / 2 tools / 6 HTTP, lease 60s com
fencing, 1 vaga Operadora); trilha própria correlacionada (sem PII);
métricas persistidas + mascaramento; suite 356-F; docs; PR.

Não inclui: egress real (356-E), `pre_cadastro.criar`, proposta/escritas,
memória longa/RAG, segundo tenant, replay histórico, dado real no agente,
troca de modelo/provedor, wiring produtivo do loop (só após GATE-E3).

## Invariantes arquiteturais

1. Orçamento aprovado G5 vira código, não texto: 2 LLM / 2 tools / 6 HTTP,
   deadline `primeiro_claim+45s` imutável, reserva durável por HTTP
   registrada por entrada/índice ANTES de cada tentativa, esgotamento
   recusa incompleto sem reinício; reclaim nunca zera contador; consumo
   incerto é terminal, nunca retry automático.
2. Uma execução por sessão; lease 60s/renovação 10s com fencing; executor
   vencido não finaliza nem envia; reclaim nunca zera contador.
3. Refs opacas: 5min, só seleção pendente da sessão, invalidadas por
   expiração/troca de contexto/revogação/expurgo; cada uso reconfirma
   vínculo cadastral + sessão + classe + principal + permissão. Nomes
   nunca são chave de autorização. TTL 5min não herda retenção 90d.
4. Credencial: secret store definido na prontidão (IMP-359) com rotação,
   separação (agente/copilot/humano) e DB user restrito; renovação antes
   dos 15min; revalidação de Principal/RBAC a cada tool e antes de
   finalizar — divergência cancela e não envia; no máximo 1 refresh por
   401, sem loop; token nunca em mensagem/log/métrica.
5. GET nunca escreve `audit_log`; F faz zero writes em `audit_log`
   (invariante testada); trilha própria reconstrói ferramenta/schema/
   versões/contagens/motivos sem PII (ADR-016 intacta); expurgo nunca
   alcança `audit_log` (append-only).
6. Isolamento absoluto: sem promoção de classe, sem cruzar sessão/
   histórico/tool-call/resposta; desconhecido nunca lê carteira.
7. Budgets de tokens com fail-fast: entrada 8.000 / saída 1.000 por
   chamada (inclui instruções+schemas+histórico+refs); sem medidor
   confiável, inferência desabilitada. HTTP LLM 15s / API 5s sempre
   limitados pelo deadline restante.
8. Habilitação condicionada (flag não substitui): IMP-359/GATE-E1b com
   Operadora fail-closed até prova de origem, certificação de modelo +
   política de dados da rota A, e GATE-E3. Sem isso, capacidade existe
   mas não opera.

## Opções e recomendação

- (a) Executor como módulo `agent/executor.py` sobre peças existentes,
  tabelas novas `mensagem_conversa`/`tool_call_exec` + colunas de sessão
  **(recomendado)**: menor blast radius, reutiliza trava de slots.
- (b) Reaproveitar `RegistroComunicacao` — recusado: `devedor_id` NOT NULL
  e semântica de negócio incompatível (backlog proíbe).
- (c) Secret store em tabela PG cifrada vs. arquivo 600 no volume —
  decisão de prontidão no slice 2 (recomendação: arquivo 600 + env,
  mesmo padrão do `.env.prod`; sem Vault neste recorte).

## Arquitetura alvo

`inbox aceita → claim slot (1/sessão, Operadora reservada) → sessão +
contexto (carteira 1x) → loop ≤2: LLM → interpretar → executar → renderizar`
tudo sob deadline, com reserva durável por HTTP e trilha própria por
tool-call → resposta via apresentador ou degradação fixa. Refresh proativo
da credencial; 401 → 1 refresh → encerra. Crash em qualquer ponto tem
estado terminal definido (nunca reenvio automático, nunca reinício de
orçamento).

## Slices de implementação

### Slice 1 — modelos próprios + resolvedor de refs
Propósito: sessão com memória mínima e refs vinculadas.
Arquivos: `src/emprestimo/agent/` (domínio sessão/mensagem/tool-call),
`infrastructure/db/orm.py` + migration aditiva/reversível,
`infrastructure/repositories/conversa.py`, testes.
DDL: `mensagem_conversa` (id, sessao_id→sessao_conversa, inbox_id,
índice, papel, texto, criado_em; único (sessao_id, índice));
`tool_call_exec` (id, sessao_id, inbox_id, call_id, ferramenta, schema
versão, parametros_canônicos sem PII, resultado_filtrado, latência,
completude, proveniência, correlation_id, criado_em); sessão ganha
`referencia_pendente/expira_em` no domínio. Chaves e índices únicos
declarados na migration; DB user do agente sem acesso às tabelas de
crédito.
Aceite: `referencia_pendente/expira_em` vivos no domínio; resolvedor
`ref→devedor_id` com escopo sessão + TTL 5min + invalidação (distinta
da retenção 90d); unicidade/invariantes preservados; downgrade testado.
Testes: ciclo de vida, expiração por relógio injetado, troca de classe
invalida, corrida. Rollback: revert (tabelas novas, sem leitor
produtivo).

### Slice 2 — credencial copilot
Propósito: login, secret store, refresh proativo, 401 único.
Arquivos: `agent/credencial.py` (novo), `service.py` (fiação),
testes. Secret store compatível com IMP-359 (rotação, separação
agente/copilot/humano, DB user restrito) — arquivo 600 só se a
governança reabrir a decisão; sem Vault neste recorte salvo decisão.
Aceite: login como copilot; access renovado antes de 15min;
refresh 7d respeitado; revalidação por uso; revogação/401 → no máximo
1 refresh e encerra sem loop, cancelando o ainda não transmitido;
token fora de mensagem/log/métrica (teste negativo com scan).
Testes: refresh, revogação, 401 único, 401 após refresh = encerra,
expiração iminente renova, revogação entre tools cancela.
Rollback: revert; nada consome ainda.

### Slice 3 — executor com deadline e orçamento
Propósito: o loop, com limites em código.
Arquivos: `agent/executor.py` (novo), testes com relógio controlado,
MockTransport + falhas injetadas.
Aceite: deadline 45s imutável; 2 LLM/2 tools/6 HTTP enforcement (3ª
chamada recusada em código, não em prompt); budgets de tokens com
fail-fast; timeouts HTTP limitados ao deadline restante; entrada com
idade >120s não consulta; contexto 10 msgs/30min; resposta API acima
de 256KiB/100 itens recusada (sem truncamento enganoso); resposta ao
canal em 1 msg ≤3.000 chars (financeiro nunca fracionado); lease+
fencing (executor vencido não finaliza); 1 vaga Operadora; reserva
durável; crash → consumo desconhecido + terminal sem reinício;
reconsulta ≤1 com reautorização. Qualificação de custo backend por
ferramenta (100 consultas sintéticas, p95≤2s, nenhuma >5s) ou
ferramenta desabilitada. Testes: cada limite isolado + combinado,
restart não duplica, relógio fake. Rollback: revert.

### Slice 4 — trilha própria + métricas + mascaramento
Propósito: reconstruir sem PII.
Arquivos: tabela/log próprio, extensão métricas (persistência),
testes de mascaramento/correlação/retenção.
Aceite: GET não cria `audit_log`; F faz zero writes (teste negativo);
trilha mostra ferramenta/schema/`tool_version`/`call_id`/`fetched_at`/
latência/correlação; documento/telefone/prompt/resposta/corpo/token/
segredo/DSN/senha/stack ausentes (scan negativo); fronteira explícita:
prompt Operadora pode ter PII liberada, log nunca; X-Correlation-ID
preservado/gerado e devolvido em 2xx/4xx/5xx; logs estruturados; 500
sem stack; resultado bruto da API filtrado antes de persistir;
métricas: latência/etapa, erro schema/API/IA, recusa autorização,
consumo conhecido×desconhecido, custo, quota, falha JWT, tool negada,
expurgo. Expurgo 90d em lotes de 1.000 (inbox/sessão/mensagem/
tool-call/egress+refs, nunca `audit_log`); restore bloqueia egress
incerto/pós-backup; expurgo não desligável em silêncio. Rollback:
revert.

### Slice 5 — suite 356-F + docs + PR
Propósito: prova de operação, não de modelo.
Suite completa obrigatória: remetente não autorizado, prompt injection,
exfiltração, 2 tenants/devedores, replay Info.ID, payload grande, mídia,
crash antes/depois de efeitos, rate limit, indisponibilidade provedor,
refresh/revogação JWT, tentativa de aprovar proposta, escrita financeira
recusada, auditoria própria sem PII. Sem teste de teto em moeda por
DR-005 §3 (observar/alertar, não bloquear).
Arquivos: testes em PG real, backlog, DR/relatório de evidência, PR.
Aceite: suite verde em PG real; plano continua válido; sem wiring
produtivo (flag). Rollback: revert.

## Matriz de testes

| Risco | Prova |
|---|---|
| Estouro de orçamento/loop | enforcement por código + restart + workers simultâneos |
| Executor zumbi finaliza | fencing: vencido não finaliza nem envia |
| Ref vazada/reusada | TTL, troca de classe, expurgo, reconfirmação |
| Loop de 401 / token em log | 401 único, scan negativo de segredo |
| Duplicação (replay/crash) | Info.ID, 2 instâncias, crash antes/depois |
| PII em trilha | scan negativo + correlação sem conteúdo |
| Regressão | suites 356-A–D verdes |

## Rollout e rollback

Sem rollout produtivo: tudo atrás de flag, sem fiação no ingress, sem
egress. Revert por slice. Produção não muda comportamento.

## Riscos

- Lease/fencing com bug congela sessões → mitigado por
  `liberar_expiradas` + teste de executor morto.
- Secret store caseiro mal guardado → seguir padrão `.env.prod` 600,
  nunca tabela; scan negativo em teste.
- Executor pronto antes do modelo certificado → verificação com
  respostas enlatadas; certificação continua porteira (PLAN-037/038).
- Escopo escorrega para egress/pré-cadastro → slices recusam (lista
  explícita de não inclui).

## Registro de decisões

- Ordem 356-F antes de 356-E (dependência: executor precede saída).
- Impacto PRESENT; parecer especializado somente-leitura antes do execute.
- Sem wiring produtivo até GATE-E3.

## Registro de revisão

- Parecer consultivo somente-leitura (política agentic, PRESENT):
  INAPTO na forma inicial, 9 ressalvas — todas incorporadas acima
  (suite completa + sem-teto declarado, expurgo com lote/cascata/
  restore, parâmetros como enforcement/fail-fast, custo backend ou
  desabilitação, secret store IMP-359, revalidação por uso, ADR-016
  completa + fronteira prompt/log, habilitação condicionada, DDL).
  Parecer não aprova gates nem autoriza execução.

## Progresso

- Slice 1 implementado e verificado localmente em 2026-09-15 (11 testes
  novos: domínio+resolvedor puros, repos em PG real, migration mockada;
  regressão agente+migrations 181 ok + 1 skip pré-existente;
  ruff/black/mypy limpos). Pendente: push + PR.
- Slice 2 implementado e verificado localmente em 2026-09-15 (15 testes
  novos: renovação proativa, 401 único, revogação, store cifrado real,
  migration mockada; regressão agente+migrations verde; ruff/black/mypy
  limpos). ARMADILHA REGISTRADA: `.gitignore:56` (`*credencial*`)
  ignora também código-fonte com "credencial" no nome — commitar esses
  arquivos sempre com `git add -f`. Pendente: push + PR.
- Slice 3 implementado e verificado localmente em 2026-09-15 (17 testes
  novos: idade/vaga/deadline/orçamentos/reconsulta/404/resposta
  excedida/negada/crash + 1–2 turnos; regressão agente 182 ok + 1 skip
  pré-existente; ruff/black/mypy limpos). Decisões: 2º turno só após
  localizar (única dependência entre tools); 401 mid-turn é terminal
  (token estava fresco → revogação); prosa descartada quando há
  apresentações. Qualificação de custo backend adiada ao slice 5
  (flag `ferramentas_habilitadas` pronta). Pendente: push + PR.
- Slice 4 implementado e verificado localmente em 2026-09-16 (11 testes
  novos: trilha com correlação, zero-writes em `audit_log`, logs com
  correlation sem PII/segredo, expurgo em lotes poupando auditoria;
  regressão agente+migrations verde; ruff/black/mypy limpos). Achado:
  traceback de banco ecoa parâmetros do INSERT — `_salvar_turno` loga
  sem `exc_info`. Métricas persistidas = linhas tool_call (latência
  real) + contadores; pipeline externo fica para operação. Pendente:
  push + PR.
- Slice 5 implementado e verificado localmente em 2026-09-16 (suite
  operacional com 8 casos em stack real + qualificação de custo 6/6 OK;
  regressões verdes; ruff/black/mypy/docs:validate limpos). Achado:
  resumo media p95 8,9s (N+1 + filtro O(L×P) na projeção) — corrigido
  sem mudar contrato (`find_by_emprestimo_ids` + agrupamento único);
  segunda medição estável, nenhuma ferramenta desabilitada. Habilitação
  produtiva segue condicionada (fail-closed, certificação, GATE-E3).

## Notas de conclusão

- (após execução)

## Follow-ups

- 356-E (egress), recertificação com novo candidato, GATE-E3.

## Porta de aprovação

Não iniciar implementação relevante até registrar aprovação explícita.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-09-15 | Plano inicial do 356-F para parecer + aprovação; sem código. |

---

**O que tornaria este plano errado:** modelo certificado antes (mudaria a
verificação, não o desenho); decisão por Vault gerenciado (troca slice 2);
exigência de replay histórico (fora do v1 por desenho).
**O que forçaria redesign:** necessidade de exatamente-uma-vez no provedor
(impossível — Evolution não deduplica); expurgo alcançando `audit_log`
(proibido — append-only).
**Fora do plano:** ver "Não inclui".
**Evolução facilitada:** 356-E pluga egress no ponto de resposta do
executor. **Dificultada:** transformar trilha própria em trilha de negócio
(violaria ADR-002).
