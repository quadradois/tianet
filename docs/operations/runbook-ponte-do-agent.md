# Runbook — Ponte do agent (Caddy → socat → socket)

**Versao:** 1.1.0

**Status:** Vivo — descreve o estado de producao desde `prod-v1.1.33`

---

# 1. Objetivo

O webhook do WhatsApp entra por `https://tianet.com.br/whatsapp/webhook` e
precisa chegar ao servico `agent`, que **nao publica porta nenhuma**. Entre os
dois existem duas pecas que vivem **fora do repositorio**, no host da VPS: uma
rota no Caddy e uma unidade systemd rodando `socat`.

Ate 2026-09-22 esse arranjo existia so no handoff do dia em que nasceu. Quem
precisasse reinstalar a VPS, entender um `502` ou auditar a superficie publica
teria de reconstruir o raciocinio a partir de quatro PRs de correcao. Este
documento e a fonte.

---

# 2. O caminho completo

```
Internet
  → Cloudflare (TLS, proxy)
  → Caddy no host          :443  — rota @agent
  → socat no host          127.0.0.1:8010
  → socket Unix            /var/lib/docker/volumes/tianet_agent-runtime/_data/agent.sock
  → container agent        uvicorn --fd (modo socket)
  → Postgres               rede agent-egress
```

A API TiaNet e o banco **nao** aparecem neste caminho: a unica coisa publica
e o ingress do agent, e agora tambem `/mercadopago/webhook` (ADR-021).

---

# 3. Por que socat, e nao publish

Quatro PRs corrigiram tentativas anteriores; cada uma falhou por um motivo
diferente, e o motivo importa para nao serem refeitas:

| Tentativa | Por que falhou |
|---|---|
| Bind TCP em `127.0.0.1` dentro do container | o publish do compose entrega no IP do container (DNAT); um socket de loopback recusa. PR #93 |
| Bind `0.0.0.0` + `ports:` no compose | o servico vive **somente** na rede interna `agent-egress`; o daemon descarta publish sem NAT. PR #94 |
| Socket Unix + Caddy apontando direto | o Caddy roda no host e o socket vive num volume Docker; funciona, mas exige o Caddy conhecer o caminho interno do volume, que muda com o nome da stack |

A ponte `socat` resolve o ultimo ponto: ela traduz `127.0.0.1:8010` para o
socket, e o Caddy fala TCP com algo estavel. Ha **guardrail de teste** para
cada uma das tres regressoes (`tests/unit/agent/test_agent_container_contract.py`).

---

# 4. As pecas no host

## 4.1 Unidade systemd

`/etc/systemd/system/tianet-agent-bridge.service`:

```ini
[Unit]
Description=Ponte TCP->socket Unix do agent TiaNet
After=docker.service
Requires=docker.service

[Service]
ExecStart=/usr/bin/socat TCP-LISTEN:8010,bind=127.0.0.1,fork,reuseaddr \
  UNIX-CONNECT:/var/lib/docker/volumes/tianet_agent-runtime/_data/agent.sock
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

`bind=127.0.0.1` **nao e detalhe**: sem ele a porta 8010 fica aberta na
internet, e quem a alcancar fala com o agent sem passar pelo Caddy nem pelo
Cloudflare.

```bash
systemctl daemon-reload
systemctl enable --now tianet-agent-bridge
systemctl status tianet-agent-bridge
```

## 4.2 Rota no Caddy

Em `/etc/caddy/Caddyfile`, dentro do bloco do dominio:

```caddyfile
@agent path /whatsapp/webhook /mercadopago/webhook
handle @agent {
  reverse_proxy 127.0.0.1:8010
}
```

`path` e uma **allowlist**: so estes dois caminhos chegam ao agent. Qualquer
outro segue para a API/frontend, como antes.

```bash
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
```

Guarde backup datado antes de editar (`Caddyfile.AAAAMMDD-descricao`).

## 4.3 Dependencia de pacote

`socat` vem do apt. Ele foi instalado em 2026-09-18 e **o apt sinalizou reboot
pendente** (provavelmente kernel) — ver §6.

---

# 5. Diagnostico

Do host, em ordem — cada passo isola uma camada:

```bash
# 1. O container esta de pe e o socket existe?
docker compose -f /opt/tianet/docker-compose.prod.yml ps agent
ls -l /var/lib/docker/volumes/tianet_agent-runtime/_data/agent.sock

# 2. A ponte responde?
systemctl is-active tianet-agent-bridge
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8010/health

# 3. O Caddy roteia?
curl -sS -o /dev/null -w '%{http_code}\n' https://tianet.com.br/whatsapp/webhook \
  -X POST -H 'Content-Type: application/json' -d '{}'
```

| Sintoma | Causa provavel | Acao |
|---|---|---|
| `curl 000` em 8010 | ponte parada ou socket ausente | `systemctl restart tianet-agent-bridge`; se persistir, o container nao subiu |
| `502` do Caddy | ponte parada | idem acima |
| `404` em `/whatsapp/webhook` | rota `@agent` ausente do Caddyfile | §4.2 |
| Socket ausente apos deploy | o volume foi recriado; a ponte segura o caminho antigo | `systemctl restart tianet-agent-bridge` |
| `200` mas nada na inbox | problema **dentro** do agent, nao na ponte | `docker compose logs agent`; ver `/app/agent` |

**Depois de todo deploy que recria o volume, reinicie a ponte.** O `socat`
resolve o caminho na conexao, mas um volume recriado troca o inode do socket.

---

# 6. Reboot e pendencias

**Todos os servicos de longa duracao tem `restart: unless-stopped`** desde
`prod-v1.1.41` (PR #105). Antes disso nenhum tinha politica, e um reboot do
host deixava a TiaNet fora do ar ate alguem rodar `up -d` a mao. A ponte e o
Caddy voltam por conta propria (`enable --now`, `Restart=always`).

Provado em 2026-09-22: reboot do kernel `6.8.0-136` para `6.8.0-139`, SSH de
volta em ~45 s, os seis containers de pe sem intervencao, `health` e a ponte
respondendo.

Depois de um reboot, confira em ordem:

```bash
uname -r
docker ps --format "{{.Names}} {{.Status}}" | grep tianet-prod
curl -s https://tianet.com.br/health
systemctl is-active tianet-agent-bridge caddy
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8010/health
```

**Recriar so o `api` derruba o `frontend`.** O frontend usa `network_mode:
"service:api"`: recriado o api, o frontend fica preso na rede do container
antigo e para de responder, com o Caddy devolvendo 502. Sempre recrie os dois
juntos (`up -d --force-recreate frontend` depois do api), ou rode `up -d` sem
nomear servicos.

Pendente: `MP_WEBHOOK_SECRET` entra no `.env.prod` quando o IMP-377 subir; a
rota `/mercadopago/webhook` ja esta na allowlist do Caddy acima.

---

# 7. Historico de Versoes

| Versao | Data | Alteracao |
|---|---|---|
| 1.1.0 | 2026-09-22 | §6 reescrita: politica de reinicio em producao (PR #105), reboot provado, checklist pos-reboot e a armadilha do `network_mode: service:api`. |
| 1.0.0 | 2026-09-22 | Primeira versao. Tira do handoff de 2026-09-19 o arranjo Caddy/socat/socket e o registra como runbook, com diagnostico por camada e as tres regressoes que os PRs #92-#95 corrigiram. |
