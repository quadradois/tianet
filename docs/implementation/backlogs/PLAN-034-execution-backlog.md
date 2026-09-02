# PLAN-034 — Backlog de execução: conexão do WhatsApp na plataforma

**Versão:** 1.0.0

**Plano:** [PLAN-034](../plans/PLAN-034-conexao-do-whatsapp-na-plataforma.md)

**Decisão de origem:** [DR-006](../../governance/decision-requests/DR-006-conexao-do-whatsapp-dentro-da-plataforma.md)

---

# 1. Estado do sistema hoje

Verificado em 2026-08-31, não presumido.

| Fato | Onde |
|---|---|
| Tenant `tianet` existe no Evolution | criado pela equipe que administra o servidor |
| Instância `adm_tianet` criada e pareada | manualmente, no fechamento do IMP-352 |
| `POST /instance/create` ecoa o token que o chamador envia | contrato §8.1 |
| `POST /instance/connect` aceita `webhookUrl` vazia | resposta `200` com `"webhookUrl": ""` |
| `Connected` e `LoggedIn` são estados distintos | `/instance/status` |
| Adapter de envio faz **só** `/send/text` | `infrastructure/notifications/whatsapp.py` |
| Nada de Evolution é persistido | o ORM não tem tabela nem coluna |
| `cryptography` **não** está instalado | `pyproject.toml` |

---

# 2. API

Idêntica à seção 6 do plano. O `contract-check` exige igualdade, não continência.

- `GET /platform/whatsapp/conexao` — estado da conexão. Permissão
  `whatsapp.conexao.ler`. `404` quando nenhuma instância existe.
- `POST /platform/whatsapp/conexao` — cria a instância se necessário e inicia o
  pareamento. Permissão `whatsapp.conexao.gerir`. Idempotente por
  `Idempotency-Key`.
- `DELETE /platform/whatsapp/conexao` — encerra o pareamento. Permissão
  `whatsapp.conexao.gerir`.

Inventário: **107 → 110 operações**, **135 → 138 schemas**.

---

# 3. Itens

### IMP-364 — Cifra do token de instância

- **Objetivo:** poder guardar o token sem guardá-lo em texto claro.
- **Escopo:** dependência `cryptography`; `CifraToken` sobre `Fernet`, com chave
  em `WHATSAPP_TOKEN_ENCRYPTION_KEY`; recusa nomeada no start quando
  `APP_ENV=production` e a variável falta.
- **Critério de pronto:** ida e volta preserva o token; chave ausente recusa em
  vez de degradar; o cifrado difere do claro em teste que falharia se alguém
  trocasse a cifra por identidade.

### IMP-365 — Persistência da conexão

- **Objetivo:** a conexão sobreviver a restart sem edição manual de `.env`.
- **Escopo:** migration aditiva `conexao_whatsapp`; ORM; repositório;
  `UNIQUE (tenant_id)`.
- **Limite:** migration aditiva; downgrade é `DROP TABLE`. Nenhuma tabela
  existente é tocada.
- **Critério de pronto:** ciclo `upgrade → downgrade → upgrade` verde; token
  gravado como `BYTEA` cifrado; leitura devolve o valor original.

### IMP-366 — Cliente de gestão do Evolution

- **Objetivo:** falar com `/instance/*` sem contaminar o adapter de envio.
- **Escopo:** `EvolutionInstanceClient` com `criar`, `conectar`, `qr`, `status` e
  `logout`. Auth de Tenant só no `criar`; as demais com token de instância.
- **Por que classe separada:** o contrato §0 registra incidente real por confundir
  chave de tenant com token de instância. Tipos distintos tornam a troca impossível
  por construção.
- **Critério de pronto:** as cinco rotas cobertas por fixtures com as respostas
  reais capturadas em 2026-08-31, incluindo `webhookUrl` vazia aceita e
  `Connected` sem `LoggedIn`. Nenhum teste toca a rede.

### IMP-367 — Casos de uso e permissões

- **Objetivo:** orquestrar consulta, conexão e desconexão sob RBAC.
- **Escopo:** `ConsultarConexaoWhatsApp`, `ConectarWhatsApp`,
  `DesconectarWhatsApp`; permissões `whatsapp.conexao.ler` e
  `whatsapp.conexao.gerir` no catálogo; `CATALOGO_PERMISSOES_VERSAO` sobe.
- **Critério de pronto:** instância inexistente, pendente e pareada distinguidas;
  `Connected` sem `LoggedIn` **não** conta como conectado; auditoria registra
  autoria conforme o IMP-361, sem o QR nos detalhes.

### IMP-368 — Endpoints e contrato

- **Objetivo:** expor as três operações da seção 2.
- **Escopo:** rotas, schemas, snapshot OpenAPI, contadores de superfície.
- **Critério de pronto:** `api:check` verde; inventário em 110/138; RBAC coberto
  com 401, 403 e 404.

### IMP-369 — Tela de conexão

- **Objetivo:** conectar o WhatsApp sem sair da plataforma.
- **Escopo:** tela com QR, polling de status, estados de erro e de QR expirado,
  e o número visível quando pareado.
- **Critério de pronto:** jornada Playwright cobre não conectado → QR → pareado;
  a11y sem violação crítica ou séria; **o QR não aparece em log, trilha nem
  métrica** — guardrail de teste, não convenção.

### IMP-370 — Worker lê o token do repositório

- **Objetivo:** encerrar a dependência de `EVOLUTION_INSTANCE_TOKEN` no ambiente.
- **Escopo:** leitura pelo repositório, com o ambiente mantendo precedência
  enquanto existir.
- **Por que fase própria:** trocar origem do token junto com a criação da tela
  arriscaria deixar o worker sem canal, e worker sem canal é operação sem aviso.
- **Critério de pronto:** worker sobe com o token vindo do banco; com a variável
  presente, ela prevalece e o comportamento atual não muda.

---

# 4. Ordem e dependências

| Ordem | Item | Depende de |
|---|---|---|
| 1 | IMP-364 | — |
| 2 | IMP-365 | IMP-364 |
| 3 | IMP-366 | — |
| 4 | IMP-367 | IMP-365, IMP-366 |
| 5 | IMP-368 | IMP-367 |
| 6 | IMP-369 | IMP-368 |
| 7 | IMP-370 | IMP-365 |

O IMP-366 não depende de nada e pode andar em paralelo com 364/365.

---

# 5. Fora de escopo

- **Receber mensagens.** É a Fase C do PLAN-033 (IMP-356), e depende do agente,
  que não existe.
- **Webhook apontando para a TiaNet.** A DR-006 decidiu apontar para o agente,
  preservando o `contexto-externo.md` §2.2.
- **Múltiplas instâncias por Tenant.** A ADR-003 fixou o escopo single-tenant;
  `UNIQUE (tenant_id)` expressa isso no banco.
- **Rotação da chave de cifra.** Vira item próprio quando houver segundo segredo
  cifrado. **Reconectar nao regenera o token**: o reconnect preserva o valor da instancia, entao recuperar de chave perdida exige criar instancia nova e reparear.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-31 | Sete itens materializando o PLAN-034, com o estado do sistema verificado contra o servidor real em vez de presumido. |
