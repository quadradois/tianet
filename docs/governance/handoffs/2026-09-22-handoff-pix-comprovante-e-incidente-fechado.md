# 2026-09-22 (noite) — Handoff: Pix e comprovante no ar, incidente de segredos fechado

**Versão:** 1.0.0
**Status:** IMP-373/374/388/389/390 em produção; incidente de 2026-09-18 fechado; pré-requisitos do GATE-E4 cumpridos. Próximo: IMP-381.
**Período coberto:** 2026-09-22, depois do handoff `2026-09-22-handoff-plan-045-aprovado-e-resumo-diario-no-ar.md` (PRs #100 a #105).
**Base:** `origin/master` em `aa6338b` (tag `prod-v1.1.42` em deploy no fechamento; `prod-v1.1.41` com `DEPLOY-OK`).
**Substitui:** `2026-09-22-handoff-plan-045-aprovado-e-resumo-diario-no-ar.md` (o estado de lá continua válido; este acrescenta).

## 1. Estado operacional (observado, não declarado)

- `DEPLOY-OK prod-v1.1.41`; `health` `healthy` (database + worker); `/login` 200.
- VPS reiniciada às 22:51 BRT: kernel `6.8.0-139`, sem reboot pendente. **Os seis containers voltaram sozinhos**, `tianet-agent-bridge` e `caddy` `active`, ponte `127.0.0.1:8010` respondendo.
- Todos os serviços de longa duração com `restart: unless-stopped` (conferido com `docker inspect`); `migrate` com `no`.
- Mercado Pago **desligado** em produção (padrão). Nenhuma chave Pix cadastrada ainda.
- GATE-E1 ainda **não observado**: nenhum resumo diário real chegou (depende de dia com acerto ou atraso).

## 2. O que entrou em produção nesta sessão

| PR | IMP | O que faz |
|---|---|---|
| #100 | — | CLI `emprestimo-recuperar-credencial`, atrás do gate do bootstrap. Usada para recuperar o acesso do administrador |
| #101 | 373, 374, 389 | ADR-021 (webhook público assinado); `CobrancaPix` com INV-001..004 (a INV-004 é índice único parcial no banco); `prever_alocacao` extraída do Motor, com teste de caracterização |
| #102 | 388 | Mercado Pago **opcional**, desligado por padrão, em `/app/pagamentos`. Taxa de 0,99% visível. Desligar não invalida Pix pendente |
| #103 | 390 | `ComprovantePagamento` (alegação, nunca prova), expurgo **dentro** da transação da quitação, dedupe por `sha256` do conteúdo, chave Pix da Credora |
| #104 | — | Runbook da ponte do agent (Caddy/socat/socket) |
| #105 | — | `restart: unless-stopped` em produção |

Decisões novas do proprietário, registradas no PLAN-045 (D13–D15): caminho **sem taxa** com comprovante; comprovante é alegação e a Credora verifica na conta dela; comprovante guardado até a quitação e expurgado nela.

## 3. Incidente de segredos de 2026-09-18 — fechado

Registro exigido por `docs/operations/runbook-segredos.md` §Vazamento (sem valores antigos nem novos).

- **Causa (2026-09-18):** um `docker compose config` na VPS imprimiu na saída da sessão os valores de `POSTGRES_PASSWORD`, `TIANET_AGENT_INTERNAL_SECRET` e `PLATFORM_ADMIN_BOOTSTRAP_SECRET_HASH`.
- **Escopo:** os três segredos acima; nenhum outro apareceu naquela saída.
- **Rotação (2026-09-22):**
  - `PLATFORM_ADMIN_BOOTSTRAP_SECRET_HASH` — par novo gerado na VPS, usado para recuperar a credencial do administrador e gravado no `.env.prod`.
  - `TIANET_AGENT_INTERNAL_SECRET` — novo valor gerado na VPS, `api` e `agent` recriados.
  - `POSTGRES_PASSWORD` — `ALTER USER` pela entrada padrão (fora de `argv` e de log), `.env.prod` atualizado, seis containers recriados, **zero** erro de autenticação no worker e no agent. Script com reversão automática, que não foi acionada.
- **Pós-rotação:** backup do `.env.prod` com os valores antigos apagado. Nenhum valor passou pela sessão do executor: todos foram gerados e consumidos dentro da VPS.

## 4. Lições (custaram tempo; não repetir)

1. **Recriar só o `api` derruba o `frontend`.** Ele usa `network_mode: "service:api"` e fica preso na rede do container antigo: Caddy devolve 502. Recrie os dois juntos ou rode `up -d` sem nomear serviços. Aconteceu durante a rotação desta noite (~2 min de 502).
2. **Nenhum container tinha política de reinício.** Um reboot deixaria produção fora do ar. Corrigido no #105 e provado no reboot.
3. **Não sobrescreva arquivo que já existe.** `application/comprovante.py` era o comprovante do *lançamento*; foi sobrescrito e restaurado do git. O novo é `comprovante_pagamento.py`.
4. **Nunca `sed` cego em contador.** `\b118\b` casou com `US-118` em nome de arquivo, e `150` casou com contagem de manifesto. Use padrões ancorados no contexto (`toBe(N)`, `N operacoes`).
5. **Guardrails que cobraram coisas certas:** string `access_token` no bundle público (nome de campo e de DTO renomeados), suíte Playwright nova fora do `quality.yml` e do `pre-push`, catálogo de permissões sem subir versão, Client Component novo fora da allowlist.
6. **Escopo `workflow` no token.** Mudar `.github/workflows/` exige `gh auth refresh -s workflow`; o proprietário concedeu.
7. **`pkill -f "pytest tests/"` mata o próprio shell** que o contém. E `TaskStop` não mata o processo filho: confira com `pgrep`.
8. **Dois pushes simultâneos se destroem** (mesmo `emprestimo_test`). O `pre-push` agora recusa começar com outro pytest ativo.
9. **Depois de reiniciar a sessão, suba o Postgres local** (`docker compose up -d postgres`) antes do push.

## 5. Pendências (com dono)

1. **Observar o 1º resumo diário real** (fecha o GATE-E1): proprietário, no primeiro dia com acerto ou atraso.
2. **Credenciais de produção do Mercado Pago** (destrava IMP-375..378): proprietário.
3. **Sobras em `/root/tianet/` na VPS**: `Caddyfile.pre-frontend.bak`, `Caddyfile.slice2.bak`, `cf-v4.txt`, `cf-v6.txt`, `dossie-provider.txt`, `evo-final.log`. Não foram abertos; podem conter token do Evolution ou dado de provedor. Proprietário decide o destino.
4. **Ponteiro `~/HANDOFF-VIGENTE.md`**: no fechamento apontava para `docs/handoffs/2026-09-22-lab-preparar-captacao.md`, que não existe neste repositório (provavelmente outra sessão ou projeto). **Não foi alterado**, para não quebrar a outra demanda. Proprietário decide.
5. **Aceitação de mídia no ingress**: saiu do IMP-390 porque exige "devedor identificado" (IMP-381). Está no IMP-391.

## 6. Próximo passo

**IMP-381**: comparação do `instanceToken` do envelope Evolution (Slice 6, prova de origem), identidade do devedor por telefone E.164 e troca de `COPILOT_OPERATOR_ALLOWLIST` por `credor_whatsapp`. Nenhum pré-requisito operacional pendente. Branch novo a partir de `origin/master` (regra 9 do backlog).
