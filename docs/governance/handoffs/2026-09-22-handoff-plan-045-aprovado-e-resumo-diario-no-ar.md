# 2026-09-22 — Handoff: PLAN-045 aprovado, resumo diário no ar (GATE-E1 parcial)

**Versão:** 1.0.0
**Status:** IMP-353 + IMP-372 em produção (`prod-v1.1.35`, `DEPLOY-OK`); envio real do resumo **ainda não observado**; PLAN-045 aprovado com backlog IMP-372..387.
**Período coberto:** 2026-09-21 (auditoria do agente) → 2026-09-22 (PRs #97 e #98 mergeadas).
**Base:** `origin/master` em `a8693e4` (tag `prod-v1.1.35`).
**Substitui:** `2026-09-19-handoff-agent-no-ar-inbox-e-tela.md` (o estado de lá continua válido; este acrescenta).

## 1. Estado operacional (observado, não declarado)

- `DEPLOY-OK prod-v1.1.35` no log do workflow (2026-09-22T10:14Z); `GET /health` público → `healthy`, `database` e `worker` `healthy`.
- Código em produção: resumo diário ao `credor_whatsapp` com blocos **vence hoje** e **em atraso**; semeadura diária em `America/Sao_Paulo`; `GET/PUT /platform/whatsapp/avisos` + card "Avisos do sistema" em `/app/whatsapp`.
- **Não observado:** nenhum resumo saiu ainda. Falta `credor_whatsapp` cadastrado no tenant de produção (proprietário) e um dia com acerto ou atraso na carteira.
- Agent, ingress, inbox e tela `/app/agent` como no handoff de 19/09 — nada mudou ali.

## 2. O que esta sessão decidiu (PLAN-045, aprovado pelo proprietário)

Função do agente **redefinida**: atender o devedor, informar os dois lados, receber por Pix — nunca decidir. Doze decisões em `PLAN-045 §1.1` (D1–D12); as que custaram discussão e **não devem ser reabertas sem o proprietário**:

| Decisão | Rejeitou |
|---|---|
| Identidade do devedor = número cadastrado, sem desafio | desafio por CPF |
| Devedor não escreve no domínio | promessa por chat ("não elimina juros") |
| Pix dinâmico MP, **valor livre** digitado pelo devedor, guarda `juro ≤ valor ≤ quitação` em código, 60 min | "só juro ou quitação" |
| IA desde a primeira mensagem | menu determinístico |
| Lembrete de atraso D+1, D+4, D+7…, **só com autorização diária da Credora** (clientes pagam por fora) | régua automática |
| Suspensão a pedido do devedor **até o próximo acerto** | opt-out permanente |
| Credora registra pagamento por WhatsApp com eco + `sim` → exige Slice 6 (`instanceToken`) | — |
| DR-005 §8: política de dados do provedor deixa de ser critério; rota A `gpt-5-mini` mantida (decisão delegada: previsibilidade > gratuidade) | reabrir `:free` |
| BYOK por tela; `LLM_*` de ambiente sai (migração governada) | — |
| Identidade da Credora = `credor_whatsapp` da tela, não `COPILOT_OPERATOR_ALLOWLIST` | env |

Backlog: `docs/implementation/backlogs/PLAN-045-execution-backlog.md` — IMP-372..387, GATE-E1..E6, ordem 1 → 2a/2b → 3 → 4 → 5.

## 3. Lições do push (custaram ~1h; não repetir)

1. **PRs entram por squash.** Branch que já contém conteúdo mergeado conflita em tudo que o próximo IMP tocar (#97). Regra 9 do backlog: **branch novo por IMP a partir de `origin/master`**.
2. **`test:whatsapp` regenera `docs/audits/evidence/*.png`.** A certificação fixa o SHA de cada captura; `git add -A docs` leva os PNGs junto e reprova o push. O hook `pre-push` restaura sozinho, mas só se você ainda não commitou. Commit por caminho explícito.
3. **`.env` vindo do Windows tem CRLF.** O hook derivava `DATABASE_URL` em shell (sem `quote()`, com `\r`) → `password authentication failed`. Removido: `database_url()` em `session.py` é a fonte única, e `scripts/validate_migrations.py` agora a usa. Converta o `.env` local para LF (`sed -i 's/\r$//' .env`).
4. Ambiente Linux novo: `docker compose up -d postgres`, `npm --prefix frontend run build` e `npx playwright install chromium chromium-headless-shell` antes do primeiro `test:harness`.
5. **Mergear enquanto o pre-push roda** deixa o último commit órfão (aconteceu com a regra 9 → #98). Espere o `-> branch` no terminal.

## 4. Pendências (não resolvidas, com dono)

1. **`credor_whatsapp` em produção (proprietário):** `/app/whatsapp` → "Avisos do sistema" → número com DDI. Sem isso o resumo audita `enfileirar.ignorado: credor_whatsapp_nao_configurado` e não envia.
2. **Observar o primeiro resumo real** (fecha o GATE-E1): 08:00 BRT do primeiro dia com acerto ou atraso. Auditoria em `/app/automacao`.
3. **Rotação dos 3 segredos** do incidente de 2026-09-18 — continua aberta; pré-requisito do GATE-E4.
4. **Reboot da VPS** (kernel) — aberto.
5. **Runbook socat/Caddy** em `docs/operations/` — aberto; ganha a rota `@mp` no IMP-377.
6. **ADR da segunda rota pública** — reserva no AMP-001 antes de emitir (IMP-373 começa por isso).
7. **Credenciais de produção do Mercado Pago** — conta PJ existe; verificar antes do IMP-375.
8. **Número do agente separado do pessoal da Ivonete** — recomendação do PLAN-045 §9; decisão de deploy do proprietário.

## 5. Próximo passo

`git checkout -b feat/imp-373-cobranca-pix origin/master` → reservar ADR no AMP-001 → `domain/credit/cobranca_pix.py` com INV-001/002 + `regua_lembrete.py` + doc de aggregate. Plano de execução por IMP em `docs/governance/agents/imp-373-plano-execucao-2026-09-22.md` antes de código.
