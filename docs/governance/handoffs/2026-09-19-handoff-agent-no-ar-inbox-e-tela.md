# 2026-09-19 — Handoff: agent no ar (inbox + tela read-only)

**Versão:** 1.0.0
**Status:** S0, S1, S2, S3 entregues e verificados em produção (`prod-v1.1.33`).
**Período coberto:** 2026-09-17 (PR 91) → 2026-09-19 (PR 96 + S2 real).
**Base:** `origin/master` em `97abf2b`+ (PR 96 mergeada; tag `prod-v1.1.33` com `DEPLOY-OK`).

## 1. Estado operacional (observado, não declarado)

- Stack `prod-v1.1.33`: 6 containers `running`, 4 `healthy` (postgres, api, agent, egress-proxy).
- Ingress WhatsApp montado e recebendo: `POST /whatsapp/webhook` → inbox (`recebida`), replay → `duplicada:true` sem reprocessar, zero LLM e zero envios por construção (andar A).
- Mensagem REAL do fundador recebida e classificada `operadora` (allowlist funciona); desconhecidos → `pre_cadastro`.
- Caminho público: `https://tianet.com.br/whatsapp/webhook` → Cloudflare → Caddy (`@agent` → `127.0.0.1:8010`) → socat `tianet-agent-bridge` → socket `agent.sock` → agent → Postgres.
- Webhook do Evolution apontado para a URL pública (sessão preservada: conectado+pareado antes/depois).
- Tela `/app/agent` no ar e confirmada visualmente pelo proprietário (resumo + recentes).
- `AGENT_TENANT_ID` + `AGENT_INSTANCIA_ID` presentes no `.env.prod` (600); instância `tianet_a3c1a973-...` pareada, sem queda.

## 2. O que cada PR destravou (cadeia)

| PR | Defeito real encontrado | Fix |
|---|---|---|
| #92 | Boot v1.1.28 morria (`httpx` via metricas, `sqlalchemy` via UoW; pacotes `infrastructure/` ausentes da imagem) | lock + `COPY` + `Uso` TYPE_CHECKING + guardrail de cobertura do lock |
| #93 | TCP `127.0.0.1` no container recusa o DNAT do publish (porta mapeada, `curl` 000) | bind `0.0.0.0` + perímetro no compose + guardrail |
| #94 | Publish 8010 em serviço só-em-rede-interna é descartado sem NAT pelo daemon | modo socket + Caddy→socket (ponte socat no host) + guardrail |
| #95 | Webhook 500 (`DATABASE_URL` ausente; postgres fora da `agent-egress`) | URL + postgres na `agent-egress`, agent fora da default + guardrail |
| #96 (S3) | Sem endpoint/tela de operação | `GET /platform/agent/inbox` + `/app/agent` + `agent.inbox.ler` (catálogo 1.3.0 + migration) + snapshot 116/148 |

Deploys falharam 2× em exit 3 (compose da VPS divergente da tag) — recuperados pelo runbook (`vps-install.sh` + repeat do gate). Rollbacks preservaram produção nos dois.

## 3. Arquivos/entregas fora do git (host VPS 86.48.0.157)

- `/etc/caddy/Caddyfile` + backup `Caddyfile.20260918-s1` (rota `@agent`).
- `/etc/systemd/system/tianet-agent-bridge.service` (socat root, só `127.0.0.1:8010` → socket; `enable --now`, ativo).
- `socat` instalado via apt (anotado: apt sugeriu reboot pendente — provavelmente kernel; **reboot NÃO executado**).
- `/opt/tianet/*.anterior` (backups do vps-install).
- `/tmp/set_webhook.py` residual DENTRO do container api (somente-leitura, sem segredos; some no próximo recreate).

## 4. Pendências (não resolvidas, com dono)

1. **Rotação de 3 segredos (INCIDENTE, proprietário):** em 2026-09-18 um `docker compose config` na VPS imprimiu valores de `POSTGRES_PASSWORD`, `TIANET_AGENT_INTERNAL_SECRET` e `PLATFORM_ADMIN_BOOTSTRAP_SECRET_HASH` na saída da sessão. Tratar como comprometidos: revogar, regenerar, registrar (runbook-segredos §Vazamento).
2. **Reboot da VPS (proprietário):** kernel pendente após apt. Agendar janela.
3. **F2/F3/F4 do parecer AI Architect (OPEN):** sem prova de origem (Slice 6) → Operadora segue sem leitura de carteira além da classificação; sem modelo certificado → `LLM_ENABLED=false`; sem fiação egress/Executor → sem envio. Andar B exige decisão do proprietário.
4. **Runbook:** documentar ponte socat + rota Caddy do agent em `docs/operations/` (estado atual vive só neste handoff + Caddyfile do host).

## 5. Adjudicação (revisão do coordenador)

- F1 (deploy travado): `RESOLVED` — `DEPLOY-OK` observado em 4 tags seguidas.
- Guardrails novos travam as 4 regressões em CI/pre-push (lock, bind, topologia socket, fiação postgres).
- Testes que enfraqueceriam o gate: nenhum adicionado; contadores de contrato atualizados com comentários de origem (padrão do repo).
- Limites: suite E2E nova para `/app/agent` não criada (BFF+policy+contrato cobrem); healthcheck do agent voltou a `healthy` com o modo socket (micro-fix previsto tornou-se desnecessário).
