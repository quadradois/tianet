# Contrato de Integração — CRM ↔ Evolution Go

**Status:** fonte da verdade. Toda integração nova (ou revisão de integração existente) deve seguir este documento.
**Modelo:** Option A — Um tenant Evolution Go por cliente do CRM
**Premissa:** O CRM é o único intermediário. Clientes do CRM nunca acessam o Evolution Go diretamente.

Este documento foi auditado linha a linha contra o código-fonte real (`/opt/evolution-go`, branch em produção neste servidor) em 2026-07-16, e reauditado em 2026-08-16. Onde o comportamento observado diverge do que seria "ideal", isso está marcado explicitamente na seção 9 (Bugs e comportamentos não-óbvios) — não escondemos atrás de uma descrição idealizada.

**Reauditoria de 2026-08-16:** a reauditoria encontrou dois bugs de exposição cross-tenant que contradiziam este documento — a `GLOBAL_API_KEY` conseguia listar/deletar/ler logs de instâncias de **qualquer** tenant via `/instance/*` (contradizendo a Seção 1, que já dizia que isso não deveria acontecer), e `GET /instance/logs/:id` não filtrava por tenant (qualquer tenant podia ler logs de outro sabendo o `instanceId`). Ambos foram corrigidos no código e no deploy em produção nesta mesma data — o comportamento descrito nas Seções 1 e 8 agora reflete exatamente o que o código faz. A Seção 5.2 também foi corrigida (nomes de evento de `CALL` e categorias que faltavam).

---

## 0. Segurança — leia antes de copiar qualquer coisa daqui

**Nunca coloque a `GLOBAL_API_KEY` real neste documento ou em qualquer material compartilhado entre equipes de CRM diferentes.** Uma versão anterior deste contrato continha a chave global em texto puro na Seção 3 — isso já causou pelo menos um incidente real (uma integração usou a chave global onde deveria usar a chave do próprio tenant, e falhou silenciosamente — ver Seção 9.3). A Global Key dá acesso administrativo a **todos os tenants**, não só ao seu. Se você recebeu uma cópia antiga deste documento com uma chave real dentro, avise a equipe que administra o servidor para rotacionar a chave.

Neste documento, todo valor de chave/token é um placeholder (`{...}`). Nunca real.

---

## 1. Hierarquia de autenticação — a parte que mais gera bug

```
Evolution Go
  └── GLOBAL_API_KEY   → só funciona em rotas /tenant/*.
        │                 NÃO cria nem gerencia instâncias.
        │                 Nunca deve sair do backend do CRM (nunca vai pro corretor).
        │
        └── Tenant por cliente do CRM
              ├── evolution_tenant_id
              └── evolution_api_key (gerada automaticamente pelo Evolution Go)
                    │        → usada com header X-Tenant-ID para criar/listar/deletar instâncias
                    │
                    ├── Instância ADM      → evolution_instance_token
                    ├── Instância Corretor 1 → evolution_instance_token
                    └── Instância Corretor N → evolution_instance_token
                             → o token de CADA instância é usado sozinho (sem X-Tenant-ID)
                               para conectar, enviar mensagem, pegar QR, etc.
```

Existem **três** níveis de autenticação, cada um só serve pra um grupo de rotas — misturar um nível no lugar de outro produz erros que não deixam óbvio o motivo:

| Nível | Header(s) | Onde funciona | Onde NÃO funciona |
|---|---|---|---|
| **Global** (`GLOBAL_API_KEY`) | `apikey: {global_key}` | `/tenant/create`, `/tenant/all`, `/tenant/info/:id`, `/tenant/update/:id`, `/tenant/delete/:id`, `/tenant/apikey/:id` | **Nenhuma** rota `/instance/*` (create, all, info, delete, proxy, forcereconnect, logs, etc.) — desde a correção de 2026-08-16 (`AuthTenant`, `pkg/middleware/auth_middleware.go`), a chave global é rejeitada uniformemente em todas elas: **401** "not authorized" se você mandar `X-Tenant-ID` (a chave global nunca bate com a `apiKey` de nenhum tenant), ou **401** "X-Tenant-ID header is required" se não mandar o header. **Use sempre a chave do tenant + `X-Tenant-ID`.** |
| **Tenant** (`evolution_api_key` + `X-Tenant-ID`) | `apikey: {tenant_key}` + `X-Tenant-ID: {tenant_id}` | `/instance/create`, `/instance/all`, `/instance/info/:id`, `/instance/delete/:id`, `/instance/proxy/:id`, `/instance/forcereconnect/:id`, `/instance/logs/:id` | Nenhuma rota de `/tenant/*` (essas exigem a global) |
| **Instância** (`evolution_instance_token`) | `apikey: {instance_token}` (sozinho, sem `X-Tenant-ID`) | `/instance/connect`, `/instance/status`, `/instance/qr`, `/instance/pair`, `/instance/disconnect`, `/instance/reconnect`, `/instance/logout`, `/instance/:id/advanced-settings`, tudo em `/send/*`, `/user/*`, `/message/*`, `/chat/*`, `/group/*`, `/call/*`, `/community/*`, `/label/*`, `/unlabel/*`, `/newsletter/*`, `/polls/*` | `/instance/create`, `/tenant/*` |

---

## 2. Alterações necessárias no banco do CRM

### Tabela de clientes (já existe)
```sql
ALTER TABLE clientes ADD COLUMN evolution_tenant_id   VARCHAR(36);
ALTER TABLE clientes ADD COLUMN evolution_api_key     VARCHAR(36);
```

### Tabela de instâncias WhatsApp (criar se não existir)
```sql
CREATE TABLE whatsapp_instancias (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id              UUID NOT NULL REFERENCES clientes(id),
  tipo                    VARCHAR(20) NOT NULL,  -- 'adm' ou 'corretor'
  corretor_id             UUID REFERENCES corretores(id),  -- NULL se tipo = 'adm'
  evolution_instance_id   VARCHAR(36) NOT NULL,
  evolution_instance_name VARCHAR(100) NOT NULL,
  evolution_instance_token VARCHAR(100) NOT NULL,
  status                  VARCHAR(20) DEFAULT 'desconectado',  -- 'conectado' | 'desconectado' | 'aguardando_qr'
  numero_whatsapp         VARCHAR(30),
  webhook_configurado     BOOLEAN DEFAULT false,
  criado_em               TIMESTAMP DEFAULT NOW(),
  atualizado_em           TIMESTAMP DEFAULT NOW()
);
```

---

## 3. Variáveis de ambiente no CRM

```env
EVOLUTION_HOST=https://diamondgreen.com.br
EVOLUTION_GLOBAL_KEY={pedir à equipe que administra o servidor — nunca hardcode, nunca compartilhe entre CRMs}
EVOLUTION_WEBHOOK_URL=https://crm.suaempresa.com/webhooks/whatsapp
```

`EVOLUTION_GLOBAL_KEY` só deve existir no backend responsável por criar/gerenciar **tenants** (evento 1 e evento 6 abaixo). Se o seu backend só cria/gerencia instâncias dentro de um tenant já existente, você não precisa dessa chave — use só `evolution_api_key` do tenant, armazenada no banco.

---

## 4. Contratos por evento do CRM

### EVENTO 1 — Novo cliente criado no CRM

**Quando:** cadastro de novo cliente é salvo
**Ação:** criar tenant no Evolution Go e salvar credenciais
**Auth:** Global

**Request:**
```http
POST {EVOLUTION_HOST}/tenant/create
apikey: {EVOLUTION_GLOBAL_KEY}
Content-Type: application/json

{
  "name": "crm_cliente_{cliente_id}"
}
```

**Response `201`:**
```json
{
  "id":        "aaa-bbb-ccc",
  "name":      "crm_cliente_123",
  "apiKey":    "xxx-yyy-zzz",
  "active":    true,
  "createdAt": "2026-07-16T12:00:00Z"
}
```

**Ação no CRM após resposta:**
```sql
UPDATE clientes
SET evolution_tenant_id = 'aaa-bbb-ccc',
    evolution_api_key   = 'xxx-yyy-zzz'
WHERE id = {cliente_id};
```

**Tratamento de erro:** se falhar, registrar erro e re-tentar em background. Não bloquear o cadastro do cliente.

---

### EVENTO 2 — Cliente solicita instância ADM

**Quando:** cliente ativa o módulo WhatsApp ADM no CRM
**Ação:** criar instância ADM no tenant do cliente
**Auth:** Tenant (⚠️ nunca a Global — ver Seção 1)

**Buscar credenciais do cliente:**
```sql
SELECT evolution_tenant_id, evolution_api_key FROM clientes WHERE id = {cliente_id};
```

**Request:**
```http
POST {EVOLUTION_HOST}/instance/create
apikey: {evolution_api_key}
X-Tenant-ID: {evolution_tenant_id}
Content-Type: application/json

{
  "name":  "adm_{cliente_id}",
  "token": "{uuid_gerado_pelo_crm}"
}
```

> `token`: gerar um UUID (ou qualquer string única) no CRM e armazenar. Este token será usado sozinho (sem `X-Tenant-ID`) em todas as operações desta instância.

**Response `200`:**
```json
{
  "message": "success",
  "data": {
    "id":                  "035eaa43-...",
    "tenant_id":           "aaa-bbb-ccc",
    "name":                "adm_123",
    "token":               "uuid-gerado-pelo-crm",
    "webhook":             "",
    "connected":           false,
    "events":              "",
    "createdAt":           "2026-07-16T12:00:00Z",
    "...":                 "objeto completo tem mais campos (advancedSettings, proxy, etc.) — use só o que precisar"
  }
}
```

**Salvar no CRM:**
```sql
INSERT INTO whatsapp_instancias
  (cliente_id, tipo, evolution_instance_id, evolution_instance_name, evolution_instance_token)
VALUES
  ({cliente_id}, 'adm', '035eaa43-...', 'adm_123', 'uuid-gerado-pelo-crm');
```

**Erro comum:** `401 "not authorized"` (ou `401 "X-Tenant-ID header is required"` se você não mandou o header) — normalmente significa que a `apikey` enviada é a Global Key, não a do tenant. Confira qual chave o seu código está usando.

---

### EVENTO 3 — Novo corretor adicionado ao cliente

Idêntico ao Evento 2, trocando o `name` (ex.: `corretor_{corretor_id}_{cliente_id}`).

---

### EVENTO 4 — Conectar instância (fluxo QR code)

**Quando:** usuário clica em "Conectar WhatsApp" no CRM
**Ação:** conectar instância, obter QR, aguardar scan
**Auth:** Instância (token da própria instância, sozinho)

**Passo 4.1 — Registrar webhook e ativar conexão:**
```http
POST {EVOLUTION_HOST}/instance/connect
apikey: {evolution_instance_token}
Content-Type: application/json

{
  "webhookUrl": "{EVOLUTION_WEBHOOK_URL}",
  "subscribe":  ["MESSAGE", "CONNECTION", "QRCODE"]
}
```

**Valores válidos de `subscribe`** — só estes existem. Qualquer outro valor é **descartado silenciosamente** (não gera erro, só um log de aviso no servidor que você não vê):

```
ALL, MESSAGE, SEND_MESSAGE, READ_RECEIPT, PRESENCE, HISTORY_SYNC,
CHAT_PRESENCE, CALL, CONNECTION, LABEL, CONTACT, GROUP, NEWSLETTER,
QRCODE, BUTTON_CLICK
```

`["ALL"]` assina todos de uma vez. Se você não mandar `subscribe`, o padrão é só `["MESSAGE"]`.

⚠️ **Nomes que NÃO existem e são de outra versão do Evolution API** (não usar): `MESSAGES_UPSERT`, `CONNECTION_UPDATE`, `QRCODE_UPDATED`. Ver Seção 5 para os nomes reais de evento que chegam no seu webhook.

Opcional, novo campo (2026-07): `"webhookIncludeMedia": "false"` — desliga o embutimento de mídia em base64 no webhook **só para esta instância** (ver Seção 6.4). Se omitido, herda o padrão do servidor.

**Atualizar status no CRM:**
```sql
UPDATE whatsapp_instancias
SET status = 'aguardando_qr', webhook_configurado = true
WHERE evolution_instance_id = '...';
```

**Passo 4.2 — Buscar QR code para exibir ao usuário:**
```http
GET {EVOLUTION_HOST}/instance/qr
apikey: {evolution_instance_token}
```

**Response `200`:**
```json
{
  "message": "success",
  "data": {
    "Qrcode": "data:image/png;base64,iVBORw0KGgo...",
    "Code":   "2@ABC123..."
  }
}
```

⚠️ Note o `Q` e o `C` maiúsculos — não é `qrcode`/`code`. Confirmado em teste ao vivo nesta auditoria.

> Exibir `data.Qrcode` como `<img src="data:image/png;base64,...">` no CRM.
> Se der erro `"no QR code available. Please wait a moment and try again"`: aguardar 3 segundos e tentar de novo (máximo 5x). O QR expira sozinho em ~20s e o servidor gera até 5 antes de reiniciar o ciclo — se demorar demais entre gerar e escanear, vai dar erro no celular ("não foi possível conectar o dispositivo"); é só pedir um novo.

**Passo 4.3 — Aguardar confirmação via webhook** *(ver Seção 5)*

---

### EVENTO 5 — Corretor removido do cliente

**Auth:** Tenant

```http
DELETE {EVOLUTION_HOST}/instance/delete/{evolution_instance_id}
apikey: {evolution_api_key}
X-Tenant-ID: {evolution_tenant_id}
```

**Response `200`:** `{"message": "success"}`

⚠️ Se `evolution_instance_id` **não existir** (já foi deletado, ID errado, etc.), o servidor retorna **`500`**, não `404` — é um bug conhecido (ver Seção 9.1). Trate `500` nessa rota especificamente como "provavelmente já não existe", não como erro de infraestrutura.

---

### EVENTO 6 — Cliente cancelado ou inativado no CRM

**Auth:** Global

```http
PUT {EVOLUTION_HOST}/tenant/update/{evolution_tenant_id}
apikey: {EVOLUTION_GLOBAL_KEY}
Content-Type: application/json

{
  "name":   "crm_cliente_{cliente_id}",
  "active": false
}
```

**Response `200`:** o objeto tenant atualizado (mesmo formato do Evento 1).

> Quando `active: false`: chamadas autenticadas com **token de instância** (`Auth` middleware — `/instance/connect`, `/send/*`, etc.) retornam **`403`**. Chamadas autenticadas com **tenant key + X-Tenant-ID** (`AuthTenant` — `/instance/create`, `/instance/all`, etc.) retornam **`401`**, não 403. São dois middlewares diferentes com respostas diferentes pro mesmo estado — trate ambos como "tenant inativo".
> Para reativar: mesmo endpoint com `"active": true`.

---

## 5. Webhook — eventos recebidos pelo CRM

O Evolution Go envia `POST` para a `webhookUrl` configurada no Evento 4, a cada evento assinado em `subscribe`.

### 5.1 — Envelope (sempre presente, sempre estas chaves, sempre minúsculas)

```json
{
  "event":         "Message",
  "instanceId":    "035eaa43-...",
  "instanceToken": "uuid-da-instancia",
  "instanceName":  "adm_123",
  "data":          { "...": "formato depende do evento, ver abaixo" }
}
```

### 5.2 — Nomes reais de `event` (não são os nomes que você assina em `subscribe`)

O que você assina em `subscribe` (Seção 4) é uma **categoria**. O que chega no campo `event` do webhook é o **nome específico** dentro dessa categoria — vem do código interno do WhatsApp (whatsmeow), não do valor que você assinou:

| Você assinou (`subscribe`) | `event` que chega |
|---|---|
| `MESSAGE` | `"Message"` |
| `SEND_MESSAGE` | `"SendMessage"` |
| `READ_RECEIPT` | `"Receipt"` (com `data.state`: `"Read"`, `"ReadSelf"` ou `"Delivered"`) |
| `CONNECTION` | `"Connected"`, `"LoggedOut"`, `"Disconnected"`, `"ConnectFailure"`, `"PairSuccess"`, `"TemporaryBan"` |
| `QRCODE` | `"QRCode"`, `"QRTimeout"` |
| `PRESENCE` | `"Presence"` |
| `CALL` | `"CallOffer"`, `"CallAccept"`, `"CallTerminate"`, `"CallOfferNotice"`, `"CallRelayLatency"` — **não existe** `"CallReject"` como evento de webhook; rejeição automática de chamada é só uma configuração da instância (`advanced-settings`), nunca chega no webhook |
| `GROUP` | `"GroupInfo"`, `"JoinedGroup"` |
| `HISTORY_SYNC` | `"HistorySync"` — pode vir com payload de vários MB, ver Seção 6.5 |
| `CHAT_PRESENCE` | `"ChatPresence"`, `"Archive"` |
| `LABEL` | `"LabelEdit"`, `"LabelAssociationChat"`, `"LabelAssociationMessage"` |
| `CONTACT` | `"Contact"`, `"PushName"` |
| `NEWSLETTER` | `"NewsletterJoin"`, `"NewsletterLeave"` |
| `BUTTON_CLICK` | `"ButtonClick"` |

Se o seu código faz `if (event === "MESSAGES_UPSERT")` ou `if (event === "CONNECTION_UPDATE")`, ele nunca vai casar com nada — foi exatamente esse bug que travou o fluxo de OTP de um dos nossos tenants (comparação de nome de evento incompatível com esta versão do servidor).

### 5.3 — Mensagem recebida (`event: "Message"`)

```json
{
  "event": "Message",
  "instanceId": "035eaa43-...",
  "instanceToken": "...",
  "instanceName": "adm_123",
  "data": {
    "Info": {
      "Chat":           "5511999999999@s.whatsapp.net",
      "Sender":         "5511999999999@s.whatsapp.net",
      "SenderAlt":      "184xxxxxxxxxxx@lid",
      "AddressingMode": "pn",
      "IsFromMe":       false,
      "IsGroup":        false,
      "ID":             "3EB0XXXXXXXXXXXXXXXX",
      "PushName":       "Nome do Contato",
      "Type":           "text",
      "Timestamp":      "2026-07-16T12:00:00-03:00"
    },
    "Message": {
      "conversation": "Olá, tenho interesse no imóvel!"
    }
  }
}
```

Pontos de atenção:

- `data.Info.*` é **PascalCase** (struct Go interna, sem tradução) — `Chat`, não `remoteJid`; `ID`, não `id`; `IsFromMe`, não `fromMe`. Não existe objeto `key`.
- `data.Message.*` (o conteúdo da mensagem em si) tende a vir em **camelCase** (`conversation`, `imageMessage`, etc. — gerado a partir do protobuf do WhatsApp). Ou seja: **o mesmo payload mistura duas convenções de caixa** — `Info` maiúsculo, `Message` minúsculo. Não é inconsistência sua, é assim que o servidor gera.
- **`@lid` (identificador oculto):** quando o remetente tem privacidade de número ativada, o WhatsApp entrega um JID `@lid` em vez de `@s.whatsapp.net`. O servidor já tenta normalizar isso: se detectar `Sender` como `@lid` e `SenderAlt` como `@s.whatsapp.net`, ele **inverte os dois** antes de montar o payload — então, quando existe um número real disponível, `Info.Sender`/`Info.Chat` já vêm como `@s.whatsapp.net`, e o LID puro fica em `Info.SenderAlt`. Se não houver correspondência (privacidade total), `Info.Sender` permanece `@lid` e não existe outro campo com o número real — o WhatsApp simplesmente não entrega esse dado nesse caso. **Sempre leia `Info.Chat`/`Info.Sender` para o identificador principal, nunca assuma que é sempre um número de telefone.**
- **Deduplicação:** o servidor não deduplica `Message`, mas deduplica `Receipt` (leitura) por 30 minutos — não espere reenvio do mesmo evento de leitura em sequência rápida.

**Identificar a instância no CRM:**
```sql
SELECT cliente_id, corretor_id, tipo
FROM whatsapp_instancias
WHERE evolution_instance_id = '{data valor de instanceId, não instanceName}';
```
> Preferir `instanceId` a `instanceName` para o `WHERE` — é a chave primária real, imutável.

### 5.4 — Instância conectada/desconectada (`event: "Connected"` / `"LoggedOut"` / `"Disconnected"` / `"ConnectFailure"`)

Não existe um único evento `CONNECTION_UPDATE` com um campo `state`. São eventos distintos:

```json
{ "event": "Connected", "instanceId": "...", "data": { "...": "detalhes da conexão" } }
```
```json
{ "event": "LoggedOut", "instanceId": "...", "data": { "reason": "...", "...": "..." } }
```

**Ação no CRM:** `"LoggedOut"`/`"Disconnected"`/`"ConnectFailure"` significam desconectado. Acione a reconexão do Evento 4 **somente se a desconexão não foi pedida por você**.

⚠️ Um `logout` deliberado — por exemplo o `DELETE /platform/whatsapp/conexao` do PLAN-034 §6 — também emite `LoggedOut`. Reconectar nesse caso desfaz, em segundos, a ação que o operador acabou de tomar. Guarde a intenção antes de chamar o `logout` e ignore o evento correspondente.

⚠️ **`Connected` NÃO é o mesmo que "número pareado".** Verificado ao vivo em 2026-08-31: uma instância recém-criada responde `Connected: true` com `LoggedIn: false` — o socket está de pé e nenhum WhatsApp está vinculado. Tratar `Connected` como estado operacional faz o CRM anunciar WhatsApp funcionando sem ninguém do outro lado.

Use `"PairSuccess"`, ou `LoggedIn` em `GET /instance/status`, para o estado operacional. Reserve `Connected` para "transporte ativo".

### 5.5 — Reconexão automática

Em desconexão **não solicitada**, chamar `POST /instance/reconnect` (auth: instância) com backoff, e se continuar falhando, tratar como sessão expirada e reiniciar o fluxo de QR (Evento 4).

⚠️ A ressalva da §5.4 vale aqui também: se o `logout` foi pedido pelo operador, reconectar desfaz a ação dele. Verifique a intenção registrada antes de reconectar.

---

## 6. Payload de webhook — tamanho, mídia e retry

### 6.1 — Mídia embutida (base64)

Por padrão (`WEBHOOK_FILES=true`, que é o default do servidor mesmo sem configurar nada), **toda mensagem com mídia — foto, áudio, vídeo, documento, sticker, inclusive mídia de uma mensagem citada numa resposta de texto — carrega o arquivo inteiro em base64 dentro de `data.Message.base64`.** Isso pode inflar o payload de poucos KB pra vários MB.

**Se o seu backend não precisa do arquivo em si**, valide o corpo aceitando pelo menos alguns MB de margem (nunca assuma "mensagem = payload pequeno"), ou peça pra equipe da plataforma desligar isso pra sua instância especificamente (`webhookIncludeMedia: "false"` no Evento 4 — ver 6.4).

### 6.2 — Buscar mídia sob demanda

Independente de `webhookIncludeMedia`, dá pra buscar o arquivo de uma mensagem específica quando precisar:

```http
POST {EVOLUTION_HOST}/message/downloadmedia
apikey: {evolution_instance_token}
Content-Type: application/json

{ "...": "referência da mensagem — confirmar payload exato com a equipe da plataforma antes de integrar" }
```
**Response:** `{"message": "success", "data": {"base64": "...", "timestamp": ...}}`

### 6.3 — Política de retry

Evento que falha no seu endpoint (qualquer resposta fora de `2xx`, incluindo timeout) é reenviado **até 5 vezes, com 30 segundos de intervalo entre tentativas (~150s no total)**. Depois disso, é descartado permanentemente — não existe fila de retry persistente nem endpoint pra reprocessar eventos perdidos.

⚠️ **O servidor não distingue erro `4xx` de `5xx`.** Um `413` (corpo grande demais) é reenviado exatamente como um `500` seria — as 5 tentativas acontecem mesmo sabendo que o corpo nunca vai caber. Recomendação: seu endpoint deve **sempre responder `2xx` rapidamente** (mesmo que descarte o conteúdo depois, de forma assíncrona) para não desperdiçar tentativas de retry nem fazer o servidor achar que precisa reenviar.

### 6.4 — Controle de mídia por instância (`webhookIncludeMedia`)

Campo opcional em `POST /instance/connect` (ver Evento 4): `"webhookIncludeMedia": "true"` ou `"false"`. Se omitido, herda o padrão do servidor (hoje: incluir mídia). Uma vez definido, o valor fica salvo pra instância — não precisa reenviar em toda chamada de `connect`, a não ser que queira mudar.

### 6.5 — HistorySync (achado recente, ainda não totalmente medido)

Ao reconectar uma instância, o servidor pode disparar eventos `HistorySync` com payloads de vários MB (chegamos a observar 5,6MB num único evento). Isso não depende de `webhookIncludeMedia`. Se seu endpoint tem limite de corpo agressivo, garanta que ele tolera esse tipo de evento também, ou trate erro de tamanho nesse evento especificamente sem quebrar o resto do fluxo.

---

## 7. Monitoramento — healthcheck periódico

⚠️ **Atualizado em 2026-09-01:** o algoritmo abaixo reagia apenas a
`connected = false`. Com a distinção entre `Connected` e `LoggedIn` verificada ao
vivo (§5.4), isso deixava o CRM marcado como conectado no estado
`Connected: true, LoggedIn: false` — socket de pé, **nenhum número vinculado**.
É exatamente o cenário de uma sessão expirada, que é o que o monitoramento
existe para detectar.

```http
GET {EVOLUTION_HOST}/instance/all
apikey: {evolution_api_key}
X-Tenant-ID: {evolution_tenant_id}
```

```
Para cada instância retornada:
  # `/instance/all` traz `connected`; o pareamento vem de `/instance/status`,
  # que e a unica resposta verificada ao vivo contendo `LoggedIn`.
  se connected = false:
    operacional = false
  senao:
    operacional = GET /instance/status (auth: instancia) → LoggedIn

  se operacional = false e status no CRM = 'conectado':
    → atualizar status para 'desconectado'
    → se a desconexao foi PEDIDA pelo operador (ver §5.4): parar aqui
    → senao: tentar reconectar (POST /instance/reconnect)
    → se 3 falhas: notificar cliente via CRM
```

---

## 8. Referência de endpoints por operação do CRM

| Operação CRM | Método | Endpoint | Auth |
|---|---|---|---|
| Criar cliente | POST | `/tenant/create` | Global |
| Desativar/reativar cliente | PUT | `/tenant/update/:tenantId` | Global |
| Deletar cliente | DELETE | `/tenant/delete/:tenantId` | Global |
| Criar instância (ADM ou corretor) | POST | `/instance/create` | Tenant |
| Listar instâncias do cliente | GET | `/instance/all` | Tenant |
| Info de uma instância | GET | `/instance/info/:instanceId` | Tenant |
| Deletar instância | DELETE | `/instance/delete/:instanceId` | Tenant |
| Conectar / definir webhook | POST | `/instance/connect` | Instância |
| Obter QR code | GET | `/instance/qr` | Instância |
| Status da instância | GET | `/instance/status` | Instância |
| Reconectar | POST | `/instance/reconnect` | Instância |
| Desconectar (logout) | DELETE | `/instance/logout` | Instância |
| Buscar mídia de uma mensagem | POST | `/message/downloadmedia` | Instância |
| Enviar mensagem texto | POST | `/send/text` | Instância |
| Enviar mídia | POST | `/send/media` | Instância |
| Enviar localização | POST | `/send/location` | Instância |


### 8.1 — `POST /send/text`: corpo e resposta observados

Observado contra o servidor real em **2026-08-31** (TiaNet, instância
`adm_tianet`). Até essa data este contrato listava a rota na tabela acima mas não
fixava corpo nem resposta — e o adapter da TiaNet usava um formato extrapolado da
documentação pública, nunca conferido. Era o caveat de maior risco da integração.

**Request** — auth de Instância (token sozinho, sem `X-Tenant-ID`):

```http
POST {EVOLUTION_HOST}/send/text
apikey: {evolution_instance_token}
Content-Type: application/json

{
  "number": "556299999999",
  "text":   "conteudo da mensagem",
  "id":     "{identificador escolhido pelo CRM}"
}
```

**Response `200`:**

```json
{
  "data": {
    "Info": {
      "ID":        "{o mesmo id enviado no request}",
      "Chat":      "556299999999@s.whatsapp.net",
      "Sender":    "556288888888:74@s.whatsapp.net",
      "IsFromMe":  true,
      "IsGroup":   false,
      "Type":      "ExtendedTextMessage",
      "Timestamp": "2026-08-31T15:42:51-03:00"
    }
  }
}
```

**O achado que importa:** `data.Info.ID` **é eco do `id` que você enviou**, não um
identificador gerado pelo servidor. Duas consequências para quem integra:

1. O critério de aceite `data.Info.ID` está correto — mas confirma apenas que o
   Evolution recebeu e aceitou, não que o WhatsApp entregou.
2. Como o identificador é seu, ele **correlaciona** requisição e resposta — e é
   o que permite ligar um reenvio à tentativa original. Mas correlacionar não é
   deduplicar: **não foi verificado** se o Evolution ou o WhatsApp suprimem uma
   segunda mensagem com o mesmo `id`.

   ⚠️ **Esse cenário está vivo hoje, e são dois defeitos conhecidos.**
   `EvolutionWhatsAppNotificationChannel` classifica **todo timeout** e
   **toda resposta 5xx** como `FALHA_TEMPORARIA`, e o Scheduler reenvia — o que
   **viola a ADR-009**, cuja tabela põe `5xx` e "timeout/reset após transmitir
   bytes" em `resultado_desconhecido`, que bloqueia retry. Se o Evolution
   aceitou antes de o cliente desistir, o devedor recebe duas vezes. Só
   `ConnectTimeout`, `ConnectError` e `PoolTimeout` são comprovadamente
   anteriores ao envio de bytes. Ver `contexto-externo.md` §6.2.
3. **Não existe identificador do provedor** para consultar depois: entrega só se
   confirma pelo webhook de `Receipt` (§5).

O `Sender` traz o sufixo de dispositivo (`:74`), o `Chat` não. Compare sempre
pelo número, não pela string inteira.

---

## 9. Bugs e comportamentos não-óbvios (ler antes de debugar em produção)

Conhecidos, confirmados no código, ainda não corrigidos. Desenhe sua integração levando em conta que eles existem hoje:

1. **`DELETE /instance/delete/:id` num ID inexistente retorna `500`, não `404`.** Trate como "não existe" na prática, não como erro de infraestrutura.
2. **Tenant inativo (`active: false`) retorna `403` em rotas autenticadas por token de instância, mas `401` em rotas autenticadas por tenant key** (`/instance/create`, `/instance/all`, etc.). Trate ambos como "tenant inativo".
3. **`GLOBAL_API_KEY` em qualquer rota `/instance/*` sempre falha com `401`** ("not authorized" com `X-Tenant-ID`, ou "X-Tenant-ID header is required" sem ele). Use sempre a chave do próprio tenant + `X-Tenant-ID` — a global só serve pra `/tenant/*`. Até 2026-08-16 esse erro só existia em `/instance/create` (e vinha como `400`, não `401`) e a chave global efetivamente gerenciava instâncias de qualquer tenant nas outras rotas de `/instance/*` — isso foi o bug real de exposição cross-tenant corrigido nesta data (ver nota de reauditoria no topo do documento). O comportamento atual (rejeição uniforme) não é mais um bug, é o desenhado.
4. **Valores inválidos em `subscribe` são descartados silenciosamente**, sem erro na resposta — só um log no servidor que você não vê. Valide contra a lista da Seção 4 antes de enviar.
5. **`POST /instance/connect` numa instância já conectada é idempotente** — só atualiza `webhookUrl`/`subscribe`/configurações, não força QR novo nem derruba a sessão. Seguro de chamar repetidamente pra rotacionar o segredo do webhook.
6. **QR code expira em ~20s, até 5 por ciclo**, depois reinicia sozinho um novo ciclo. Buscar um QR e não escanear na hora dá erro no app ("não foi possível conectar o dispositivo") — não é bug, é o código já ter rotacionado.
7. **Sessão sobrevive a restart do servidor** (fica persistida no Postgres) — reconectar depois de um restart normalmente não pede QR novo, só uma chamada de `/instance/connect`. Exceção observada: pareamentos muito recentes (poucas horas) podem não ter sido gravados a tempo antes de um restart — nesse caso específico, vai pedir QR novo mesmo.
8. **O adapter da TiaNet reenvia em timeout e em 5xx**, violando a ADR-009 — é defeito nosso, não do Evolution, mas condiciona a integração: enquanto não for corrigido, uma resposta 5xx ou um `ReadTimeout` pode gerar cobrança duplicada, porque não foi verificado se o provedor deduplica pelo `id` (§8, item 2).
9. **Nenhum endpoint existe pra inspecionar ou drenar webhooks que falharam** — depois das 5 tentativas de retry (Seção 6.3), o evento simplesmente some.

---

## 10. Checklist de implementação no CRM

### Banco de dados
- [ ] Adicionar `evolution_tenant_id` e `evolution_api_key` na tabela de clientes
- [ ] Criar tabela `whatsapp_instancias`

### Variáveis de ambiente
- [ ] Configurar `EVOLUTION_HOST`, `EVOLUTION_GLOBAL_KEY` (só se for criar tenants), `EVOLUTION_WEBHOOK_URL`
- [ ] Confirmar que `EVOLUTION_GLOBAL_KEY` não é usada em nenhuma chamada de `/instance/*`

### Eventos a implementar
- [ ] Criar cliente → `POST /tenant/create` (Global) → salvar credenciais
- [ ] Ativar ADM / adicionar corretor → `POST /instance/create` (**Tenant**, nunca Global) → salvar instância
- [ ] Conectar instância → connect (com `subscribe` validado contra a Seção 4) + polling QR → exibir QR ao usuário
- [ ] Remover corretor → `DELETE /instance/delete/:id`, tratando `500` como "já não existe"
- [ ] Desativar cliente → `PUT /tenant/update` com `active: false`

### Webhook
- [ ] Endpoint aceita corpo grande (vários MB) OU pediu `webhookIncludeMedia: "false"` explicitamente
- [ ] Sempre responde `2xx` rápido, mesmo que processe de forma assíncrona depois
- [ ] Compara `event` contra os nomes reais da Seção 5.2 (`"Message"`, não `"MESSAGES_UPSERT"`)
- [ ] Lê `data.Info.Chat`/`data.Info.Sender` (não `data.key.remoteJid`)
- [ ] Trata o caso de `Sender` vir como `@lid` sem `SenderAlt` correspondente (sem número real disponível)
- [ ] Identifica a instância por `instanceId`, não por `instanceName`

### Monitoramento
- [ ] Job periódico a cada 5 minutos → `GET /instance/all` por cliente ativo
- [ ] Lógica de reconexão automática com limite de tentativas
- [ ] Alerta para o cliente quando instância fica offline por mais de X minutos
