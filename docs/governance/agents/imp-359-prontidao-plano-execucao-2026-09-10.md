# Plano — Prontidão de produção do IMP-359 (GATE-E1b)

**Última revisão:** 2026-09-10 (rev. 2, pós-revisão especializada)
**Status:** Aguardando aprovação
**Slice atual:** não iniciado
**Bloqueado por:** valores dos segredos em `/root/tianet/.env.prod` (Slice 1b, pendente do proprietário); acesso SSH à VPS. O PLAN-034 saiu do caminho crítico — concluído em 2026-09-08 — e o commit que os slices esperavam é o PR #64
**Risco:** Alto
**Impacto agentic:** PRESENT — produção, segredos, rede e futuro runtime agentic. Parecer `ai_architect` será reconciliado antes da porta G5.
**Autorização:** pendente. G5 exigirá aceite explícito do proprietário com escopo e limites.
**Plano/IMP/GATE-E do produto:** [PLAN-033](../../implementation/plans/PLAN-033-copilot-tianet.md), [backlog](../../implementation/backlogs/PLAN-033-execution-backlog.md) IMP-359; GATE-E1b. Não renumera IMPs nem fecha gates por edição.

## Objetivo

Transformar "VPS provisionada, sem deploy" em produção demonstrada: TLS, proxy reverso, deploy com rollback, backup/restore ensaiado, segredos fora do git, observabilidade mínima e a decisão de origem do webhook (prova ou fail-closed) — tudo com evidência observada, conforme o critério de pronto do IMP-359.

## Contexto e achados do repositório

- VPS provisionada em 2026-08-31; domínio `tianet.com.br` ativo; TLS, backup, CD e endurecimento pendentes ([contexto-externo](../../operations/contexto-externo.md) §3.2).
- Único workflow é `quality.yml` (gates de qualidade); não existe pipeline de CD.
- Compose publica tudo em loopback; API e banco sem exposição pública por desenho — o proxy reverso de produção ainda não existe.
- Rota A registrada (DR-005 §7): `LLM_BASE_URL`, `LLM_MODEL=gpt-4o-mini` candidato, chave validada; segredos pelo canal `docs/credenciais/`.
- Webhook do Evolution sem autenticação (URL é o único segredo); decisão vigente: Operadora em fail-closed até prova de origem compatível.
- Ordem obrigatória herdada: medir `logout` repetido **antes** de apagar `adm_tianet`; apagar é irreversível.
- `AGENT_WEBHOOK_MAX_BYTES` ainda sem medição (backlog exige valor acima do maior HistorySync observado, teto de engenharia 8 MiB).

## Escopo e não objetivos

Inclui provisão, proxy/TLS, deploy/CD, backup/restore, segredos, observabilidade, medição de envelope/logout e relatório de evidência do GATE-E1b.

Ficam fora: IMP-353/354 (Fase A, vêm depois), IMP-356/357 (Fases C/D), inferência e tools, dados reais de clientes no agente, segundo Tenant, e qualquer envio real pelo canal.

## Invariantes arquiteturais

1. API e PostgreSQL jamais expostos publicamente; só o ingress do agente é público, atrás do proxy.
2. Nenhum segredo em git, imagem, log ou banco genérico; rotação documentada.
3. Allowlist de número não autentica webhook; sem prova de origem, Operadora desabilitada.
4. Rollback preserva banco e intenções; downgrade destrutivo nunca é o primeiro rollback.
5. Limites e parâmetros operacionais registrados antes de habilitar qualquer capacidade.
6. Um processo opera uma única instância/Tenant (limite da §6.1 do contexto-externo); segundo Tenant exige processo isolado, nunca ajuste de configuração.

## Opções e recomendação

Proxy reverso dedicado (Caddy/Nginx) com TLS automático vs. túnel gerenciado: recomenda-se proxy na VPS (controle da prova de origem por rede + logs locais), com renovação automática de certificado. CD mínimo por script versionado + tag de imagem imutável (sem plataforma nova por ora); reavaliar se o segundo deploy doer.

## Arquitetura alvo

Cloudflare na borda (proxy laranja ligado, decisão 2026-09-10) → proxy de origem na VPS (443, TLS com certificado válido) → listener de ingress do serviço `agent` em rede de provedor dedicada; `api`/frontend em rede interna, `postgres` sem porta pública. O canal API↔agent continua por socket Unix; o Evolution **não** fala com a API. Reconciliação com o §2.2 do contexto-externo: "sem webhook público" vale para a API TiaNet, nunca para o ingress do agente. Firewall da origem aceita 80/443 **somente** das faixas IP públicas da Cloudflare; a prova de origem do webhook lê `CF-Connecting-IP` e só confia nele após validar o peer contra essas faixas. Volumes de backup cifrados fora da máquina (chave de cifra sob custódia do Slice 1); segredos via ambiente + canal `docs/credenciais/`; métricas e logs centrais mínimos com alerta de expiração de certificado e de falha de backup.

## Slices de implementação

### Slice 1 — Segredos e prontidão administrativa
- **Propósito:** nascer com todos os segredos fora do git. (Política de dados do projeto OpenAI é follow-up da Fase C, não deste slice.)
- **Arquivos prováveis:** `.env.example`, `docs/operations/` (runbook de segredos), canal `docs/credenciais/` (fora do git).
- **Dependências:** acesso SSH; chave `LLM_API_KEY` já validada.
- **Aceite (lista nominal, verificável item a item):** `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `FRONTEND_SESSION_KEY_ID`, `FRONTEND_SESSION_KEY`, `WHATSAPP_TOKEN_ENCRYPTION_KEY` (gerada aqui), `EVOLUTION_TENANT_ID`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE_TOKEN`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, credencial do usuário copilot, refresh token, `COPILOT_OPERATOR_ALLOWLIST` (só número da Tia), segredo interno do agent e chave de cifra dos backups; rotação documentada por segredo.
- **Testes/verificação:** `git diff --check`, varredura com `gitleaks` (ou equivalente aprovado) em repo e imagens, checklist assinado. **Rollback:** revogar e regenerar o segredo afetado; nunca "desver" vazamento — se vazar, rotaciona.

### Slice 2 — Proxy reverso, DNS e TLS
- **Propósito:** tianet.com.br com HTTPS válido de ponta a ponta (borda Cloudflare + origem) e superfície mínima.
- **Arquivos prováveis:** composição/proxy, `docs/operations/` (topologia e runbook).
- **Dependências:** Slice 1; DNS apontado (laranja ligado, decisão 2026-09-10).
- **Aceite:** certificado válido com renovação automática e alerta de expiração (30 e 7 dias, no log e no canal do operador definido no runbook); firewall da origem só aceita 80/443 das faixas Cloudflare; só ingress do agente responde publicamente; API/banco inacessíveis de fora (prova negativa); headers e logs de acesso no proxy, com `CF-Connecting-IP` registrado.
- **Testes/verificação:** TLS Labs-equivalente local (`openssl s_client`), varredura de portas, teste de renovação a seco. **Rollback:** voltar DNS/apontamento anterior; site estático de manutenção se preciso.

### Slice 3 — Deploy, CD mínimo e endurecimento
- **Propósito:** subir a stack com rollback conhecido. REGRA: nenhum deploy direto no servidor; tudo passa pelo workflow `.github/workflows/deploy.yml` com aprovação manual do ambiente `production`.
- **Arquivos prováveis:** `docker-compose.prod.yml`, `.github/workflows/deploy.yml`, `scripts/deploy-gate.sh`, `Dockerfile*` sem mudança de comportamento, runbooks.
- **Dependências:** Slices 1–2; PLAN-034 concluído e commitado; ambiente `production` no GitHub com revisor obrigatório; chave de deploy restrita (`command=/opt/tianet/bin/deploy`, sem forward) autorizada na VPS; segredo `VPS_*` só no GitHub.
- **Aceite:** imagens imutáveis no GHCR (`prod-vX.Y.Z` + sha); tag descendente de master com workflow Quality verde (verificação `precondicoes` no próprio deploy, sem duplicar a suite); deploy só via workflow aprovado; gate na VPS valida tag, pull, migrate, up, health da API em 120s e faz rollback para `.last-good-tag` com RTO proposto de 15 min; usuário não-root, sem porta além do proxy; atualizações de SO agendadas.
- **Testes/verificação:** ensaio de deploy, kill de container, rollback cronometrado. **Rollback:** tag anterior (o próprio objeto do slice).

### Slice 4 — Backup e restore do PostgreSQL
- **Propósito:** perda da máquina não vira perda de dados.
- **Arquivos prováveis:** rotina de backup, runbook de restore, evidência sanitizada.
- **Dependências:** Slice 3.
- **Aceite:** backup automático com retenção de 30 dias (proposta; 7 diários + 4 semanais); restore ensaiado em banco descartável com dados sintéticos; RPO proposto de 24h e tempo de restore medido contra ele; alertas de falha de backup.
- **Testes/verificação:** restore completo + checagem de integridade; simulação de falha de backup dispara alerta. **Rollback:** manter rotina anterior até a nova provar 2 ciclos.

### Slice 5 — Observabilidade e medição de envelope
- **Propósito:** operar às cegas nunca mais; registrar a amostra de envelope (a decisão do limite fica na Entrega 356-B).
- **Arquivos prováveis:** configuração de logs/métricas/alertas, `docs/operations/observability-runbook.md`.
- **Dependências:** Slice 3.
- **Aceite:** logs sem PII/segredo/corpo; métricas de latência/erro/quota; alerta de certificado, backup e 5xx; amostra do maior HistorySync registrada com piso conhecido de 5,6 MB e limite proposto (múltiplo de 64 KiB acima, teto 8 MiB) — sem fixar `AGENT_WEBHOOK_MAX_BYTES` aqui; verificação de expurgo de 90 dias (contagem a seco) com dono no runbook.
- **Testes/verificação:** injeção de falha sintética observa alerta; canário confirma ausência de segredo em log. **Rollback:** configuração anterior versionada.

### Slice 6 — Origem do webhook e relatório GATE-E1b
- **Propósito:** fechar o critério de pronto: controle de origem ou fail-closed provado + medições Evolution.
- **Arquivos prováveis:** regra de proxy/allowlist, evidência sanitizada, relatório de gate.
- **Dependências:** Slices 2–5; janela com a `adm_tianet` ainda viva.
- **Aceite:** spoof de `Info.Sender` recusado/bloqueado **ou** Operadora desabilitada com PreCadastro operando — sem IP de egress estável do Evolution registrado em fonte, fail-closed é o resultado esperado, não exceção; `logout` repetido medido **antes** de apagar `adm_tianet`, nessa ordem; relatório ALP-001 com IMPs, testes, riscos e autorização de seguir.
- **Testes/verificação:** spoofing controlado, replay, relatório revisado. **Rollback:** reabilitar bloqueio total do ingress (fail-closed) a qualquer dúvida.

## Matriz de testes

| Risco | Evidência bloqueadora |
|---|---|
| Exposição indevida | Varredura de portas + prova negativa de API/banco de fora |
| Segredo vazado | `gitleaks` em repo/imagens/logs + checklist nominal; vazamento = rotação, não rollback |
| Deploy sem volta | Rollback cronometrado contra RTO de 15 min |
| Backup fictício | Restore real em banco descartável contra RPO de 24h + alerta de falha simulada |
| Certificado expirado | Renovação a seco + alerta a 30/7 dias |
| Spoof de webhook | Envelope forjado nunca abre Operadora; ou fail-closed demonstrado |
| Ordem Evolution | Logout medido antes de apagar instância; inversão reprova o slice |
| Tenancy | Processo ligado a 1 instância/Tenant demonstrado; segundo Tenant sem processo isolado reprova |

## Rollout e rollback

Sequência 1→6; cada slice termina em revisão. Produção sem tráfego real de cliente até GATE-E1b evidenciado. Rollback global: derrubar ingress, restaurar tag e banco do último backup íntegro, preservar intenções; credencial exposta revoga e regenera.

## Riscos

VPS sem acesso documentado; provedor Evolution sem ambiente de teste (janela única de medição); renovação TLS silenciosa; backup que nunca foi restaurado; pressão para "abrir" a Operadora sem prova (fail-closed é o padrão, não punição).

## Registro de decisões

- 2026-09-10: proprietário mandou seguir pela rota A e preparar este plano; G5 pendente.
- Sequência pós-PLAN-034 mantida; Operadora fail-closed até prova (backlog v1.9.1).
- Revisão especializada reconciliada em 2026-09-10 (ver Registro de revisão): topologia do ingress explicitada, tenancy no aceite, inventário nominal de segredos, envelope como proposta (decisão em 356-B), registry/tag nomeados, RTO/RPO e retenção propostos, fail-closed como resultado esperado.
- Backlog ainda cita "direção OpenRouter aprovada" nos segredos do IMP-359: leitura vigente é DR-005 §7 (rota A); anotado para reconciliação formal no slice 1.
- Política de dados do projeto OpenAI rebaixada de bloqueador para follow-up: só condiciona a Fase C, nada do GATE-E1b depende dela.
- 2026-09-10: proprietário aprovou manter o proxy Cloudflare laranja (rota 1): Origin/edge TLS, firewall só faixas CF, prova de origem via `CF-Connecting-IP`.

## Registro de revisão

Triagem `PRESENT`. Revisão `ai_architect` via Claude Code CLI (somente leitura, sem segredos/dados) em 2026-09-10: **CHANGES_REQUESTED** com 3 blockers (ingress do agente vs. rede interna; tenancy ausente; inventário de segredos incompleto) e 2 concerns (envelope em fase errada; tag sem registry), além de lacunas de aceite e 3 contradições. Todos incorporados acima; nenhuma correção foi adiada para execução. O parecer não fecha gates nem autoriza implementação.

## Progresso

| Slice | Estado | Evidência |
|---|---|---|
| 1a | concluído (local) | `.env.example` nominal, runbook, varredura limpa, review Claude incorporado |
| 1b | parcial | Docker 29.8.0+compose, `/root/tianet/.env.prod` gerado (600); faltam valores do proprietário |
| 2 | concluído | Caddy 2.6.2 (Ubuntu, auto-update) + UFW só-CF; `https://tianet.com.br/healthz` 200 de ponta a ponta; `/` 503 stub |
| 3 | **executado em 2026-09-12 (tag prod-v1.1.3)** | deploy verde após vps-install (artefatos convergiam); causa da falha anterior: compose sem `DATABASE_URL` no `migrate`. Health: api+db+worker ok; fiação frontend na borda (`/`→3000, prefixos→8000). Kill test em 2026-09-13: api derrubada de propósito, volta manual em 12s (borda <60s); sem restart automático — melhoria registrada para a próxima tag |
| 4 | **executado em 2026-09-13** | backup cifrado diário 03:00 (AES 256 CBC com PBKDF2, chave do `.env.prod`, retenção 7+28); primeiro backup 1,5 MB; restore ensaiado em banco descartável com integridade (45 tabelas, tenant:1) em ~10s; falha gera log + STATUS (alerta dedicado no Slice 5). Tropeços: flag `-o` inválida no openssl e `-q` inexistente no pg_restore — corrigidos |
| 5 | parcial | checks de cert/backup/5xx + cron ok; envelope como proposta (356-B); expurgo sem o que purgar |
| 6 | parcial | logout repetido medido 200 + `adm_tianet` apagada e confirmada (401) em 2026-09-13; falta: evidência fail-closed + relatório GATE-E1b |

## Notas de conclusão

—

## Follow-ups

- IMP-353/354 após GATE-E1b; IMP-356 só com dependências comprovadas.
- Certificação do `gpt-4o-mini` (Entrega 356-D) antes de dado verdadeiro.
- Confirmação da política de dados do projeto OpenAI (retenção/ZDR) antes da Fase C.

## Porta de aprovação

G5 exige aprovação explícita do proprietário com escopo e limites. Não autoriza commit, push, deploy em produção, dados reais, exclusão de instância ou remoção de volume. Autorizações de slices anteriores valem só se reconstituídas aqui.
