# PLAN-034 — Conexão do WhatsApp na plataforma

**ID:** PLAN-034

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Contexto

Hoje conectar um número de WhatsApp exige acesso ao servidor Evolution Go em
`diamondgreen.com.br`. Quem opera a TiaNet não tem conta lá — então cada número
novo, e **cada reconexão**, depende de alguém com acesso administrativo ao
servidor. Se o WhatsApp cair num sábado, a operação para até essa pessoa aparecer.

A [DR-006](../../governance/decision-requests/DR-006-conexao-do-whatsapp-dentro-da-plataforma.md),
resolvida em 2026-08-31, decidiu construir a tela de QR dentro da plataforma. Este
plano materializa aquela decisão.

**O que já está pronto e não se repete aqui.** O tenant `tianet` existe no
Evolution, criado pela equipe que administra o servidor; a instância `adm_tianet`
foi criada e pareada manualmente em 2026-08-31, o que fechou o IMP-352 e validou
o formato de envio contra o provedor real. Este plano automatiza o que foi feito
à mão, e passa a ser o único caminho para reconexões.

**Fluxo do Evolution, verificado e não suposto** (contrato §8.1 e Eventos 2 e 4):

1. `POST /instance/create` — auth de Tenant. O **chamador gera** o token da
   instância e o envia; o Evolution ecoa de volta.
2. `POST /instance/connect` — auth de Instância. Aceita `webhookUrl` **vazia**,
   verificado em 2026-08-31.
3. `GET /instance/qr` — devolve `Qrcode` como data URI PNG e `Code` como string
   de pareamento.
4. `GET /instance/status` — `Connected` (socket) e `LoggedIn` (número pareado)
   são coisas diferentes; só o segundo significa conectado de verdade.

---

# 2. Componentes do Domínio Envolvidos

Nenhum agregado de crédito é tocado. A conexão é configuração de plataforma.

| Componente | Papel |
|---|---|
| `ConexaoWhatsApp` (novo) | Entidade de plataforma: identidade da instância no Evolution e o token, cifrado |
| `Tenant` | Escopo. Mantido como invariante estrutural conforme a [ADR-003](../../architecture/adrs/ADR-003-escopo-single-tenant-do-v1.md), mesmo com um único Tenant |
| `Principal` / catálogo IAM | Duas permissões novas |

**Uma instância por Tenant.** O v1 é single-tenant (ADR-003), então na prática
uma instância. O `tenant_id` continua na tabela e nas queries — não porque haverá
um segundo, mas porque escopo explícito é o que impede um bug de vazar dado entre
fronteiras se um dia houver.

---

# 3. Casos de Uso

| Caso de uso | Responsabilidade |
|---|---|
| `ConsultarConexaoWhatsApp` | Estado atual: existe instância, está pareada, qual número, há QR pendente |
| `ConectarWhatsApp` | Cria a instância se ainda não existe, conecta, devolve o QR |
| `DesconectarWhatsApp` | `logout` no Evolution; a instância permanece, o pareamento cai |

O QR **não é persistido**. Ele vive segundos, é buscado no Evolution a cada
consulta enquanto o pareamento estiver pendente, e some quando `LoggedIn` vira
verdadeiro.

---

# 4. Decisões de Arquitetura

## 4.1 Cliente de gestão separado do adapter de envio

`EvolutionWhatsAppNotificationChannel` continua fazendo **só** `/send/text`. A
gestão de instância (`create`, `connect`, `qr`, `status`, `logout`) vive em um
cliente novo, `EvolutionInstanceClient`.

São dois níveis de autenticação diferentes — o envio usa o token da instância, o
`create` usa a chave do tenant com `X-Tenant-ID` — e o contrato §0 registra um
incidente real causado por confundir chaves. Separar as classes torna a confusão
impossível por construção, em vez de depender de quem escreve lembrar.

## 4.2 Token cifrado em repouso, com chave fora do banco

Decidido na DR-006. O token dá controle total da instância: enviar, ler,
desconectar. Quem o tiver fala pelo número do Credor.

**Isso exige a dependência `cryptography`**, que não está no projeto hoje. Não há
AES na stdlib, e criptografia à mão não é opção. `Fernet` (AES de 128 bits em modo CBC, com HMAC)
resolve o caso com uma API que é difícil de usar errado.

A chave vem de `WHATSAPP_TOKEN_ENCRYPTION_KEY`, variável de ambiente, **nunca do
banco** — chave guardada junto do dado cifrado não protege nada. Ausência da
variável em `APP_ENV=production` é recusa nomeada no start, no mesmo padrão que
`EVOLUTION_INSTANCE_TOKEN` já usa.

## 4.3 O que continua em variável de ambiente

`EVOLUTION_HOST`, `EVOLUTION_TENANT_ID` e `EVOLUTION_API_KEY` — as credenciais de
**gestão** do tenant. Elas não são geradas pela plataforma e não mudam por ação
de usuário; persistí-las não traria ergonomia nenhuma e ampliaria a superfície
cifrada sem ganho. O `contexto-externo.md` §6.1, reconciliado pela DR-006, já
registra essa divisão.

## 4.4 `webhookUrl` configurável, vazia hoje

Decidido na DR-006 pergunta 3: o webhook aponta para o **agente**, não para a
TiaNet, preservando a decisão do `contexto-externo.md` §2.2 de não expor webhook
público. `EVOLUTION_WEBHOOK_URL` ausente significa string vazia, que o Evolution
aceita — **verificado em 2026-08-31**, não inferido.

## 4.5 `EVOLUTION_INSTANCE_TOKEN` continua funcionando

O worker lê o token do ambiente. Este plano **não muda isso**. Quando a tela criar
a instância, o token passa a existir também no banco; a leitura pelo worker migra
para o repositório em fase própria, com o ambiente como precedência enquanto a
migração não fecha. Trocar as duas coisas ao mesmo tempo arriscaria deixar o
worker sem canal — e worker sem canal é operação sem aviso.

---

# 5. Modelo de Dados

Migration **aditiva**. Nenhuma tabela existente é alterada.

```
conexao_whatsapp
  id                     UUID     PK
  tenant_id              UUID     NOT NULL  -- escopo (ADR-003)
  evolution_instance_id  VARCHAR  NOT NULL
  evolution_instance_nome VARCHAR NOT NULL
  token_cifrado          BYTEA    NOT NULL  -- Fernet; nunca em texto claro
  numero_pareado         VARCHAR  NULL      -- preenchido quando LoggedIn
  criado_em              TIMESTAMPTZ NOT NULL
  atualizado_em          TIMESTAMPTZ NOT NULL

  UNIQUE (tenant_id)   -- uma instancia por Tenant no v1
```

`token_cifrado` é `BYTEA`, não `VARCHAR`: cifra é binário, e guardar binário como
texto convida a corrupção por encoding.

**Downgrade:** `DROP TABLE conexao_whatsapp`. Aditiva na ida, reversível na volta.

---

# 6. API

Três operações sobre um único recurso. Todas exigem Principal autenticado.

- `GET /platform/whatsapp/conexao` — estado da conexão. Permissão
  `whatsapp.conexao.ler`. Devolve estado, número pareado quando houver, e o QR
  enquanto o pareamento estiver pendente. `404` quando nenhuma instância existe.
- `POST /platform/whatsapp/conexao` — cria a instância se necessário e inicia o
  pareamento. Permissão `whatsapp.conexao.gerir`. Idempotente por
  `Idempotency-Key` (AD-002). Devolve o QR.
- `DELETE /platform/whatsapp/conexao` — encerra o pareamento (`logout` no
  Evolution). Permissão `whatsapp.conexao.gerir`. A instância permanece; apenas o
  número é desvinculado.

**Inventário:** de **107 operações e 135 schemas** para **110 e 138**.

**Permissões novas no catálogo:** `whatsapp.conexao.ler` e
`whatsapp.conexao.gerir` — de 55 para 57. O catálogo é fonte canônica versionada,
então `CATALOGO_PERMISSOES_VERSAO` sobe.

**O QR nunca vira log.** Ele é credencial de pareamento: quem o obtém vincula um
dispositivo ao WhatsApp do Credor. Trafega na resposta, não em log, não em trilha
de auditoria, não em métrica.

---

# 7. Estratégia de Testes

| Camada | O que cobre |
|---|---|
| Unitário — cifra | ida e volta do token; chave ausente recusa; texto cifrado difere do claro |
| Unitário — cliente Evolution | as cinco rotas com respostas reais capturadas em 2026-08-31, inclusive `webhookUrl` vazia aceita |
| Unitário — casos de uso | instância inexistente, pendente e pareada; `Connected` sem `LoggedIn` **não** é conectado |
| Contrato | as três operações no snapshot OpenAPI; contadores conferidos |
| Integração | RBAC das duas permissões; 401, 403 e 404 |
| Playwright | tela renderiza QR, faz polling e mostra o número ao parear |

**Nenhum teste chama o Evolution real.** As respostas capturadas viram fixture; a
suíte não pode depender de rede nem criar instância em servidor de verdade.

**Guardrail:** teste que reprova se o token aparecer em texto claro em qualquer
lugar que não seja o campo cifrado — resposta de API, log ou trilha.

---

# 8. Ordem de Implementação

| Fase | Entrega | Por que nesta ordem |
|---|---|---|
| 1 | Dependência `cryptography`, cifra e testes | Nada persiste antes de saber cifrar |
| 2 | Migration, ORM, repositório | Persistência antes de quem a usa |
| 3 | `EvolutionInstanceClient` com fixtures reais | Isola o servico externo antes dos casos de uso |
| 4 | Casos de uso + permissões no catálogo | RBAC junto com o comportamento |
| 5 | Endpoints + snapshot OpenAPI + contadores | O guardrail cobra os três juntos |
| 6 | Tela e jornada Playwright | Interface por último, sobre contrato estável |

---

# 9. Riscos Técnicos

| Risco | Mitigação |
|---|---|
| Confundir chave de tenant com token de instância — o incidente do contrato §0 | Classes separadas (§4.1); o tipo impede a troca |
| QR vazar em log e permitir pareamento indevido | Guardrail de teste (§7); QR nunca entra em trilha |
| Perder a chave de cifra e tornar o token irrecuperável | Recusa nomeada no start sem a variável; reconectar pela tela regenera o token |
| Worker ficar sem canal durante a migração de leitura | §4.5: ambiente tem precedência até a fase própria fechar |
| Rede do Evolution instável durante o pareamento | Estado vem sempre do provedor, nunca de cache local; `Connected` ≠ `LoggedIn` |

---

# 10. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-31 | Materializa a DR-006: três operações sobre `/platform/whatsapp/conexao`, token cifrado com `cryptography`, cliente de gestão separado do adapter de envio, e o fluxo do Evolution documentado a partir do que foi verificado contra o servidor real. |
