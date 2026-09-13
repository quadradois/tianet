# PLAN-035 - Relatório GATE-E1b: prontidão de produção do Copilot TiaNet

**Data:** 2026-09-13
**Veredito:** **APROVADO COM RESSALVAS** — prontidão demonstrada; ressalvas não bloqueiam Fase A, bloqueiam dados reais de cliente até o Slice 4 estar ciclado (está) e a revisão do ciclo fechar.
**Autor:** coordenação (evidências observadas, não declaradas).

## Cobertura por item do IMP-359

| Item do checklist | Evidência | Estado |
|---|---|---|
| Servidor endurecido | Ubuntu 24.04, UFW ativo (22 + 80/443 só Cloudflare), unattended-upgrades ligado | ✅ |
| Domínio + DNS | `tianet.com.br` + `www` resolvendo para a borda, proxy laranja ligado (decisão 2026-09-10) | ✅ |
| TLS | Let's Encrypt via Caddy, expira em 86 dias, renovação automática; alerta 30/7 dias configurado | ✅ |
| Reverse proxy | Caddy 2.6.2, `/`→3000, prefixos de API→8000, `/healthz`→health; `CF-Connecting-IP` registrado | ✅ |
| Rota pública só ingress do agente | API/banco sem porta pública; prova negativa por varredura de portas pendente de registro formal | ⚠️ parcial |
| API e banco sem exposição | Compose sem publish além de loopback; UFW nega o resto | ✅ |
| Backup + restore | Diário 03:00 cifrado, retenção 7+28; restore ensaiado com integridade (45 tabelas) em ~10s; RPO 24h medido | ✅ |
| CD com rollback | Pipeline tag→Quality→build→gate; rollback para `.last-good-tag` no gate; kill test: volta manual em 12s | ✅ |
| Healthcheck/restart | Healthchecks ativos; **sem restart automático** — melhoria registrada para a próxima tag | ⚠️ ressalva |
| Rotação de segredos | Runbook + inventário nominal; rotação documentada, nunca exercitada | ⚠️ não exercitada |
| Logs/métricas/alertas/runbooks | `ops-check.sh` (cert/backup/5xx); alerta dedicado de backup no Slice 5; runbooks versionados | ✅ parcial |
| Segredos provisionados | 17 vars em `/root/tianet/.env.prod` (600); `EVOLUTION_INSTANCE_TOKEN` via fluxo QR (correto); bootstrap ligado→usado→desligado em 2026-09-13 | ✅ |
| Tenancy (1 instância/Tenant) | Processo único; segundo Tenant exige processo isolado (documentado, não testado — sem segundo Tenant) | ✅ por desenho |
| Origem do webhook | Fail-closed vigente (sem ingress, Operadora desabilitada por construção); prova com tráfego real pendente do IMP-356-A | ⚠️ parcial |
| `logout` + `adm_tianet` | Logout repetido 200 (premissa ADR-019 confirmada); instância apagada com 200 e confirmada 401 | ✅ |
| Envelope `AGENT_WEBHOOK_MAX_BYTES` | Amostra 5,6 MB registrada; valor como proposta (decisão na 356-B) | ➡️ 356-B |

## Divergências e tropeços honestos

- Deploy v1.1.3 falhou por compose sem `DATABASE_URL` no `migrate` (localhost) — corrigido, rerun verde.
- Falso "bloqueio do provedor": faltava `EVOLUTION_HOST` no `.env.prod` — culpa nossa, provedor inocentado com evidência.
- Time-bombs de data nos testes (e2e imp-261, seed jornadas) — corrigidos para datas relativas.
- `up -d api` isolado orfana a netns do frontend — registrado no runbook; recriar sempre em par.

## Decisão

GATE-E1b **cumprido para avançar à Fase A** (IMP-353/354). Produção com dado real de cliente continua condicionada a: (1) revisão deste relatório pelo proprietário, (2) rotação das credenciais expostas em chat, (3) política de dados do projeto OpenAI confirmada antes da Fase C.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-09-13 | Emissão inicial: veredito APROVADO COM RESSALVAS com evidências dos Slices 1–4 e 6 parcial. |
