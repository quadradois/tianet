# Deploy de Producao

**Versao:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

Levar uma tag `prod-vX.Y.Z` do GitHub para a VPS, com rollback conhecido.

Este runbook cobre o Slice 3 do IMP-359. O ambiente local equivalente esta em
[ambiente-local-docker](ambiente-local-docker.md); os segredos, em
[runbook-segredos](runbook-segredos.md).

**Regra:** nenhum deploy direto no servidor. Todo deploy passa pelo workflow
`.github/workflows/deploy.yml`. Merge em `master` publica sozinho: o workflow
cria a proxima tag `prod-vX.Y.(Z+1)` e segue sem aprovacao manual.

**Decisao (2026-09-11):** o reviewer do environment `production` foi removido —
mantenedor solo, sem dado real de cliente, a aprovacao so adicionava latencia.
Recolocar quando entrar dado real ou quando o Slice 4 (backup/restore) fechar,
o que vier primeiro.

---

# 2. As portas do fluxo

| Porta | Onde | O que barra |
|---|---|---|
| pre-commit | `hooks/pre-commit` | docs invalidos, lint e tipos do frontend |
| pre-push | `hooks/pre-push` | a suite inteira, na ordem do CI |
| branch protection | GitHub, `master` | merge sem PR ou com qualquer dos 4 checks vermelho |
| `precondicoes` | `deploy.yml` | tag fora do padrao, que nao descende de master, ou com Quality nao-verde |
| environment | GitHub, `production` | ref que nao seja `master` nem tag `prod-v*` |
| gate da VPS | `/opt/tianet/bin/deploy` | artefato divergente da tag, migrate/up com erro, health que nao fecha |

Nenhuma delas substitui as outras. O gate da VPS e a ultima, nao a unica.

---

# 3. Pre-requisitos, uma vez

1. Segredos em `/root/tianet/.env.prod`, modo 600 (ver
   [runbook-segredos](runbook-segredos.md)). Sem valores reais o gate falha no
   `pull`.
2. Chave de deploy restrita em `~/.ssh/authorized_keys` da VPS. A linha esta no
   cabecalho de `scripts/deploy-gate.sh`:

   ```
   command="/opt/tianet/bin/deploy",no-agent-forwarding,no-port-forwarding,\
   no-pty,no-user-rc,no-X11-forwarding ssh-ed25519 AAAA... deploy@github
   ```

   Com `command=` o sshd ignora o comando do cliente e entrega o original em
   `$SSH_ORIGINAL_COMMAND` — e por isso que o gate le as duas formas.
3. Segredos `VPS_HOST`, `VPS_USER` e `VPS_DEPLOY_KEY` no GitHub.
4. Artefatos instalados (secao 4).

---

# 4. Sincronizar os artefatos da VPS

`docker-compose.prod.yml` e o gate vivem na VPS como copias. O gate confere o
SHA-256 dos dois contra `/app/deploy` na imagem da tag e recusa com **exit 3**
se divergirem — antes de tocar em producao.

Na VPS, como root:

```bash
# primeira vez (repositorio publico)
curl -fsSLO https://raw.githubusercontent.com/quadradois/tianet/master/scripts/vps-install.sh
chmod +x vps-install.sh

./vps-install.sh prod-vX.Y.Z
```

O instalador puxa a imagem, extrai os dois arquivos **da propria imagem** (nao
do git, para nao instalar um arquivo de commit diferente do que gerou a
imagem), guarda a versao anterior em `*.anterior` e confere os digests pela
mesma regra do gate. Termina em `INSTALL-OK`.

Repita a cada tag que altere `docker-compose.prod.yml` ou `deploy-gate.sh`.

---

# 5. Deploy

1. Merge do PR em `master`, com os 4 checks verdes. O push dispara o
   workflow, que cria a proxima tag `prod-vX.Y.(Z+1)` no commit do merge.
2. Bump de minor ou major e manual, sobre um commit de `master` ja publicado
   — o push da tag dispara o mesmo workflow, e os merges seguintes continuam
   a contar a partir dela:

   ```bash
   git tag prod-v1.2.0 <sha-de-master>
   git push origin prod-v1.2.0
   ```

3. O workflow roda `precondicoes` (tag valida, descende de master, Quality
   verde no commit — espera ate 30 min pelo `quality.yml` do mesmo push),
   constroi e publica as 4 imagens no GHCR e chama o gate na VPS, sem parar
   para aprovacao.

O gate executa, nesta ordem: `pull` → conferencia de artefatos → `up -d`
(inclui o migrate) → health de api e frontend → estado `running` dos cinco
servicos → grava `.last-good-tag` → `DEPLOY-OK`.

Ate a conferencia de artefatos nada de producao foi tocado, e uma falha ali
sai limpa, sem rollback.

---

# 6. Rollback

Automatico: qualquer falha depois do `up` reverte para `.last-good-tag`. O log
distingue tres desfechos, e eles pedem acoes diferentes:

| Linha | Significado | Acao |
|---|---|---|
| `ROLLBACK-OK: <tag>` | a stack anterior voltou a subir | investigar a tag nova sem pressa |
| `ROLLBACK-FALHOU: <tag>` | a reversao tentou e nao subiu | producao indefinida, intervir agora |
| `ROLLBACK-IMPOSSIVEL` | nao havia `.last-good-tag` (primeiro deploy) | subir manualmente a partir de uma tag conhecida |

Manual, na VPS:

```bash
/opt/tianet/bin/deploy prod-v<anterior>
```

**Limite conhecido:** o rollback volta as imagens, nao o schema. Um deploy que
migrou o banco deixa o schema a frente do codigo antigo. Isso e seguro porque
migrations sao aditivas com downgrade reversivel (SPEC-004, regra 8) — quebrar
essa regra quebra o rollback. Backup e restore ensaiados sao o Slice 4 do
IMP-359 e ainda nao existem: ate la, o rollback depende dessa regra e de mais
nada.

---

# 7. Quando o gate recusa

| Saida | Causa | Correcao |
|---|---|---|
| `TAG fora do padrao` | tag nao e `prod-vX.Y.Z` | publicar tag no padrao |
| `falta /root/tianet/.env.prod` | segredos ausentes | secao 3, item 1 |
| `<arquivo> diverge da versao publicada` (exit 3) | artefato da VPS de outra tag | rodar `vps-install.sh` (secao 4) |
| `nao carrega /app/deploy/...` | imagem anterior aos artefatos de deploy | publicar uma tag nova |
| `api sem health` / `frontend sem resposta` | servico nao subiu | ver `docker compose logs`; o rollback ja tentou reverter |
| `servico X em estado 'exited'` | container morreu apos subir | logs do servico; o rollback ja tentou reverter |

No workflow, `aguardando Quality` seguido de reprovacao significa que um dos 4
checks nao fechou verde no commit da tag — a correcao e no codigo, nao no gate.

---

# 8. O que ainda nao existe

- Backup e restore do PostgreSQL (Slice 4).
- Observabilidade e alertas de certificado/backup (Slice 5).
- Prova de origem do webhook do Evolution (Slice 6); ate la, Operadora em
  fail-closed.
