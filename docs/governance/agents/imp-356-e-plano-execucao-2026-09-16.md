# Plano — IMP-356-E: saída durável (egress WhatsApp)

**Última revisão:** 2026-09-16
**Status:** Aprovado
**Slice atual:** Slice 1
**Bloqueado por:** aprovação explícita do fundador (G5) + decisão de rota de rede ANTES do slice 1 + parecer incorporado (ver Registro de revisão)
**Risco:** Alto
**Impacto agentic:** PRESENT
**Justificativa e gatilhos:** egress transmite para o mundo real (efeito externo irreversível); triagem com parecer especializado somente-leitura anexado antes do execute. Parecer não aprova gates.
**Autorização:** aprovada pelo fundador em 2026-09-16 com rota (c); escopo restrito aos 5 slices, sem envio real, sem wiring produtivo
**Plano/IMP/GATE-E do produto:** PLAN-033, IMP-356-E, GATE-E3 (aberto)

## Objetivo

Dar ao executor uma saída que não duplica, não inventa e não vaza:
intenção + payload persistidos antes do envio, chave idempotente por
entrada+índice, estados com desconhecido terminal, crash sem reenvio —
reutilizando o adapter Evolution e o formato IMP-352, sem segundo
adapter e sem tocar no transporte.

## Contexto e achados do repositório

- Adapter `EvolutionWhatsAppNotificationChannel` pronto com allowlist
  ADR-009 (só ConnectTimeout/ConnectError/PoolTimeout retentam; resto é
  desconhecido/permanente) e formato IMP-352 validado ao vivo.
- Falta tudo do lado conversacional: resolvedor de token escopado por
  (tenant, instância) — o atual itera tenants e vaza cross-tenant —,
  tabela própria de egress, derivação de chave, hook no executor,
  normalizador de destino, suite de crash/replay.
- **Bloqueio:** o proxy do agente só permite hosts OpenAI; o Evolution
  (`diamondgreen.com.br`) é inalcançável do confinamento. Opções na
  seção dedicada — nenhuma implementada.
- Executor termina hoje em `str` em memória (`executor.py:273-276`); o
  hook do egress entra ali, com recheck de permissão pré-envio.

## Escopo e não objetivos

Inclui: resolvedor escopado; tabela `egress_conversa` + migration;
chave entrada+índice + payload canônico; runner de envio plugado no
executor (persistir-antes, recheck, enviar, persistir-depois); política
desconhecido/indisponibilidade em texto fixo; links só nas 3 rotas;
suite 356-E com canal falso contador; docs; PR.

Não inclui: segundo adapter; mudança no transporte/classificação;
envio real (canal falso); wiring produtivo; `pre_cadastro.criar`;
TemplateNotificacao; replay histórico; restore automático; decisão de
habilitação (fail-closed, certificação, gates) — essas continuam
porteiras, não slices.

## Invariantes arquiteturais

1. Um único adapter; formato IMP-352 byte a byte; `id` correlaciona
   (eco do enviado, nunca ID do provedor), nunca deduplica.
2. Chave = `notification/sha256` de serialização canônica versionada
   (sort_keys, encoding fixo, vetores em teste) sobre vínculo completo:
   tenant, carteira quando aplicável, instância, classe, principal,
   destinatário normalizado, entrada do provedor, índice de saída,
   versão de ferramentas e call-id; credenciais fora do material.
   Persistir intenção+payload antes de enviar; mesma chave com conteúdo
   ou contexto divergente = conflito terminal, sem envio.
3. Estados `preparado/em envio/aceito/falha/desconhecido`; aceito e
   desconhecido nunca reenviam sozinhos. Só falha com prova de
   não-aceite retenta (1x, dentro de deadline e quota): erros pré-bytes
   (ConnectTimeout/ConnectError/PoolTimeout), 429 com `Retry-After` e
   409 de mesma chave concorrente; 5xx, timeouts de leitura/escrita e
   2xx malformado são desconhecido terminal. Lease nunca reautoriza
   envio incerto.
4. Aceito ≠ entregue (só Receipt confirma; `consultar_status` é
   receipt-only declarado). Conciliação de desconhecido é manual,
   permissionada e auditada — nunca retry, nunca promessa de entrega.
5. Single-tenant por processo (v1): token resolvido para O tenant e
   instância configurados, com precedência env e Fernet via
   `WHATSAPP_TOKEN_ENCRYPTION_KEY` (nunca claro, recusa nomeada sem
   degradado); qualquer divergência = conflito, sem envio. Segundo
   tenant exige processo isolado (reabertura de governança).
6. Recheck de identidade/permissão imediatamente antes de transmitir;
   revogada após consulta cancela o ainda não transmitido. Destino só
   do servidor: nunca LID→fone, grupo/`IsFromMe`/não-resolvido; sem
   prova de origem, Operadora sem egress (fail-closed).
7. Desconhecido recebe só texto fixo, zero fato de carteira; links só
   `/app/relatorios`, `/app/devedores`, `/app/motor`, sem query, origem
   fixa do servidor, sem token/CPF/dinheiro/comando; href do modelo
   nunca vira link.
8. Resposta financeira nunca é prosa livre: só apresentadores; 1
   mensagem ≤3.000 chars (maior encaminha à plataforma sem fracionar);
   prosa do modelo só quando nenhuma ferramenta foi usada.
9. Correlação ponta a ponta (inbox→sessão→tool→egress) com
   X-Correlation-ID preservado/gerado/devolvido; logs estruturados sem
   conteúdo/PII/segredo/DSN/senha/stack; 500 sem stack; métricas sem
   PII (payload canônico persistido nunca vai a log).
10. Retenção 90d em lotes de 1.000 alcança egress+refs; nunca
    `audit_log`; sem replay histórico; restore bloqueia incertos e
    pós-backup até conciliação; downgrade preserva intenções.
11. Egress consome deadline/quota do turno; 1 aviso/60s por remetente
    no máximo; recusa não gera tempestade: só `concluida` com texto
    gera envio; `incompleta/recusada` geram no máximo o aviso de quota
    já orçado.

## Opções e recomendação

Rota de rede do agente até o Evolution (bloqueio atual):
- (a) Estender allowlist do proxy — aumenta superfície do confinamento;
  exige reavaliação de segurança dedicada.
- (b) Egress via chamada interna/API TiaNet (fora do confinamento) —
  exige definir quais rotas e credencial.
- (c) Runner de egress fora da rede `agent-egress` (no serviço api/
  worker) — separa privilégio por processo.
- **Recomendação:** (c), com decisão final do fundador ANTES do slice 1
  (a interface do resolvedor e a topologia mudam por rota); slices
  seguintes não começam sem ela. Slice de documentação da rota some —
  a decisão entra no G5.
- **Decisão 2026-09-16 (fundador, após análise de viabilidade): rota (c).**
  Runner no worker sobre `JobAgendado` (claim/lease/retry/backoff
  prontos, poll 1s); agente só persiste a intenção; sem mudança de
  rede, sem endpoint novo, separação por processo mantida.

Token: resolvedor escopado novo (não reutilizar o iterador do worker).

## Arquitetura alvo

Executor produz texto → runner monta intenção (destinatário normalizado
do servidor, payload canônico+hash, chave entrada+índice) → persiste
`preparado` → recheck permissão → adapter (via rota decidida) →
persiste `aceito/falha/desconhecido` + `provider_message_id` →
métricas/logs sem PII. Desconhecido/indisponibilidade viram texto fixo
em código. Restore futuro bloqueia incertos (gancho, sem automação).

## Slices de implementação

### Slice 1 — resolvedor escopado + chave + payload
Propósito: identidade e idempotência antes de qualquer envio.
Arquivos: `agent/egress.py` (novo: normalizador de destino — nunca
LID→fone —, derivação de chave com vínculo completo + vetores,
payload canônico), resolvedor single-tenant (valida token contra
tenant/instância configurados, precedência env, Fernet), testes.
Aceite: token de A nunca resolve para B (teste cross-tenant); mesma
entrada+índice = mesma chave; divergência = conflito sem envio;
`assunto` exigido e ignorado como na porta. Testes: vetores de chave,
cross-tenant, normalização (grupo/própria/LID recusados). Rollback:
revert.

### Slice 2 — tabela `egress_conversa` + migration
Propósito: intenção durável com estados.
Arquivos: ORM + migration aditiva/reversível, repositório, UoW/ports,
testes (mock op + PG real).
DDL: `egress_conversa` (id, inbox FK, sessao FK, indice, chave
idempotente uq, payload_canonico+hash+versao, vínculo: tenant,
carteira, instancia, classe, principal, destinatario, ferramenta,
call-id; estado com `em envio`; provider id (eco); codigo;
timestamps; conciliacao_chave) + uq (inbox, indice) + uq (chave).
Aceite: crash entre persistir e enviar recupera sem duplicar;
`em envio` distingue pré de pós-POST; restore/conciliação manual
permissionada; expurgo 90d alcança egress sem tocar `audit_log`;
downgrade preserva intenções e remove só a tabela; head movido com
revisão. Rollback: revert.

### Slice 3 — runner plugado no executor
Propósito: o envio como código, não como efeito lateral.
Arquivos: `agent/egress.py` (runner), hook SÓ em resultado
`concluida` com texto (executor: após validação 3.000 chars, antes de
`_salvar_turno`) + aviso de quota 1/60s; `incompleta/recusada` não
geram envio. Deadline restante e quota do turno acoplados; correlação
inbox/sessão/correlation_id atravessa.
Arquivos: testes com canal falso contador.
Aceite: persistir-antes → recheck → enviar → persistir-depois; 1 retry
só pré-bytes/429-com-Retry-After/409-mesma-chave; desconhecido
terminal; links validados contra allowlist nominal; desconhecido =
texto fixo. Testes: 5 estados, replay zero chamadas, 2 workers, troca
contexto/destinatário, 401/revogação mid-egress, ferramenta negada.
Rollback: revert.

### Slice 4 — suite 356-E + contenção + observabilidade
Propósito: prova de não-duplicação e cobertura obrigatória.
Arquivos: testes (crash pré/pós-`enviar`, replay Info.ID, mudança de
contexto, token cross-tenant, restore/expurgo de egress, injection e
exfiltração via egress, payload grande e mídia → regra 3000 sem
fracionar financeiro, 1-aviso/60s, faults contra adapter real +
transporte falso, JWT/revogação, correlação ponta a ponta, scan
negativo DSN/senha/stack/PII, sem-teste-de-teto declarado por
DR-005 §3), teste de carga contida (rajada → teto segura), docs.
Aceite: matriz do aceite 356-E + itens obrigatórios verdes; nenhuma
ferramenta desabilitada sem decisão. Rollback: n/a (só testes+docs).

### Slice 5 — docs + PR
Propósito: verdade documental e fechamento.
Arquivos: backlog/DR/relatório de evidência, config (nomes, sem
segredo), PR.
Aceite: `docs:validate` limpo; nenhum envio real; habilitação segue
condicionada. Rollback: revert.

## Matriz de testes

| Risco | Prova |
|---|---|
| Duplo envio | crash pré/pós-enviar + replay + 2 workers, contador de chamadas |
| Token cross-tenant | resolvedor escopado, teste A→B negativo |
| Retry indevido | só 3 erros pré-rede retentam; 5xx/timeout leitura = desconhecido |
| Prosa como fato | só apresentadores; desconhecido = texto fixo |
| Vazamento | scan negativo (doc/tel/token) em payload, logs, métricas |
| Regressão | suites 356-A–F verdes |

## Rollout e rollback

Sem rollout: canal falso, sem wiring, sem envio real. Revert por slice.

## Riscos

- Rota de rede sem decisão trava utilidade do slice 3+ (mitigado: canal
  falso; decisão vai ao slice 5).
- Divergência Evolution real vs. falso (comportamento de borda) —
  mitigado por reuso integral do adapter real com transporte falso.
- Escopo escorrega para habilitação (fail-closed/prova de origem) —
  explicitamente fora; são porteiras, não slices.

## Registro de decisões

- Ordem 356-F antes de 356-E (executor precede saída).
- Reuso total do adapter; zero mudança em transporte/classificação.
- Impacto PRESENT; parecer somente-leitura antes do execute.

## Registro de revisão

- Parecer consultivo somente-leitura (política agentic, PRESENT):
  INAPTO na forma inicial, 8 bloqueantes — todas incorporadas
  (chave/DDL com vínculo + `em envio`; single-tenant + Fernet;
  retry com 429/409/Retry-After; hook delimitado a `concluida` +
  deadline/quota/correlação; ADR-009/016 completa + links nominais;
  expurgo/restore/conciliação; suite obrigatória completa;
  rota decidida antes do slice 1). Parecer não aprova gates nem
  autoriza execução.

## Progresso

- Slice 1 implementado e verificado localmente em 2026-09-16 (13 testes:
  vetores de chave, conflito terminal, cross-tenant negativo,
  normalização; ruff/black/mypy limpos). Pendente: push + PR.

## Notas de conclusão

- (após execução)

## Follow-ups

- Habilitações (fail-closed/prova de origem, certificação, política de
  dados, GATE-E1b/E3); wiring produtivo só após gates.

## Porta de aprovação

Não iniciar implementação relevante até registrar aprovação explícita.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-09-16 | Plano inicial do 356-E para parecer + aprovação; sem código. |

---

**O que tornaria este plano errado:** mudança de provedor de mensageria,
ou decisão de não usar o adapter Evolution (exigiria novo desenho).
**O que forçaria redesign:** Evolution passar a deduplicar por `id`
(mudaria a semântica de replay); exigência de confirmação de entrega
(impossível — só Receipt, sem consulta).
**Fora do plano:** ver "Não inclui".
**Evolução facilitada:** habilitar envio real troca o transporte falso
pelo real sem tocar runner/tabela. **Dificultada:** segundo canal
(e-mail/SMS) exigiria nova certificação de formato.
