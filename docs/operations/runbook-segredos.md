# Runbook — Segredos do IMP-359

**Dono:** operação TiaNet. **Revisão:** 2026-09-10 (Slice 1a, parte local).

## Inventário nominal

| Segredo | Onde nasce | Onde vive | Rotação |
|---|---|---|---|
| `POSTGRES_PASSWORD` | provisão (1b) | ambiente VPS | a cada incidente ou 12 meses |
| `JWT_SECRET_KEY` | provisão (1b) | ambiente VPS | invalida sessões; janela de manutenção |
| `FRONTEND_SESSION_KEY_ID` / `FRONTEND_SESSION_KEY` | provisão (1b) | ambiente VPS | por ID, sem derrubar a outra |
| `WHATSAPP_TOKEN_ENCRYPTION_KEY` | provisão (1b) | ambiente VPS + canal `docs/credenciais/` | aceita re-pareamento via provedor |
| `EVOLUTION_TENANT_ID` / `EVOLUTION_API_KEY` | provedor Evolution | ambiente VPS + canal | no painel do provedor |
| `EVOLUTION_INSTANCE_TOKEN` | pareamento | banco cifrado | reconectar a instância |
| `LLM_BASE_URL` / `LLM_MODEL` | DR-005 §7 (configuração, não segredo) | ambiente VPS | só por decisão registrada |
| `LLM_BASE_URL` / `LLM_MODEL` | DR-005 §7 (configuração, não segredo) | ambiente VPS | só por decisão registrada |
| `EVOLUTION_HOST` | contrato Evolution (configuração, não segredo) | ambiente VPS | acompanha o provedor |
| `LLM_API_KEY` | painel OpenAI do cliente | ambiente VPS + canal | no painel; sem fallback automático |
| Credencial do usuário copilot + refresh token | seed Fase C | login normal, sem token eterno | revogação imediata no desligamento |
| `COPILOT_OPERATOR_ALLOWLIST` | IMP-359 (só número da Tia) | ambiente VPS | a cada mudança de operador |
| `TIANET_AGENT_INTERNAL_SECRET` | provisão (1b), mín. 32 aleatórios | ambiente VPS + agent | distinto de sessão humana/Codex |
| `BACKUP_ENCRYPTION_KEY` | provisão (Slice 4) | canal, separada do backup | nunca junto do backup |

## Regras do canal

- Segredo real só em `.env` local (ignorado) ou `docs/credenciais/` (ignorado, linha 55 do `.gitignore`). Nada disso é versionado — verificado no aceite.
- `.env.example` carrega nomes e instruções, jamais valores.
- Proibido: chat, screenshot, log, métrica, trace, prompt ou evidência com valor.

## Varredura (aceite do Slice 1)

Escopo reduzido nesta parte 1a: working tree versionado. Histórico e camadas
de imagem só com `gitleaks` na parte 1b — o Slice 1 não fecha sem isso.

```powershell
# Equivalente aprovado para o working tree (usar até o gitleaks entrar no 1b):
# 1) segredos versionados por engano:
git ls-files | Select-String -Pattern "\.env$|credenciais|pem$|key$"
# 2) padrões em arquivos versionados (ignora .env local, docs/credenciais/,
#    lockfiles — hashes `integrity` do npm são checksums públicos, não segredos
#    — e fixtures sintéticas):
git grep -nE "sk-[A-Za-z0-9_-]{20,}|[A-Za-z0-9_-]{43}=|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|xox[bap]-" -- . ":!.env" ":!docs/credenciais/" ":!frontend/package-lock.json" ":!package-lock.json" ":!*fixture*"
```

`LLM_*` passam ao `agent` pelo compose desde o IMP-356-D lote 2 slice 5
(valores via ambiente; `LLM_API_KEY` vazia por padrão). Na VPS, os nomes
precisam existir em `/root/tianet/.env.prod` — provisionamento via SSH,
pendente do proprietário. Até lá, vivem só no `.env` local e no canal.

## Vazamento

1. Revogar na origem imediatamente. 2. Regenerar e reprovisionar. 3. Registrar data, escopo e causa no handoff — sem colar o valor antigo nem o novo.

## Pendente da parte 1b (VPS, exige SSH)

Geração de todas as chaves acima no provisionamento, `gitleaks` instalado na rotina, e checklist nominal assinado item a item.
