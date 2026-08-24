# Contexto Externo

**Versao:** 1.1.0

**Status:** Vivo — mantido manualmente

---

# 1. Para que serve

Este documento registra o que existe **fora do repositorio** e que decisoes
tecnicas dependem: servicos contratados, integracoes de outros projetos,
infraestrutura, e decisoes tomadas em conversa que nunca viraram codigo.

Nenhuma analise de codigo descobre o que esta aqui. Sem este registro, uma
sessao nova conclui corretamente "isto nao existe no repositorio" e propoe
construir algo que a operacao ja tem.

**Regra de leitura:** antes de propor construir qualquer integracao, servico ou
infraestrutura, leia este documento. Se o assunto nao estiver aqui, pergunte
antes de assumir que nao existe.

**Regra de escrita:** quando algo for contratado, integrado ou decidido fora do
codigo, registre aqui na mesma hora. Um item errado e pior que um item ausente.

---

# 2. Integracoes disponiveis

## 2.1 API de WhatsApp — Evolution Go

**Contrato oficial:** `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md`. Fonte da verdade,
auditada contra o codigo em producao. Leia antes de integrar qualquer coisa.

| Campo | Valor |
|---|---|
| Situacao | **Pronta e em uso em outros projetos do time** |
| Provedor | Evolution Go auto-hospedado, `https://diamondgreen.com.br` |
| Modelo | um tenant Evolution por Tenant da TiaNet |
| Autenticacao | tres niveis: Global (`/tenant/*`), Tenant (`/instance/*` de gestao), Instancia (envio e conexao) |
| Retry de webhook | 5 tentativas, 30s de intervalo, depois descarta — **nao existe replay** |
| Tamanho de payload | midia vem em base64; `HistorySync` ja foi observado com 5,6MB |
| Ambiente de teste | *a preencher* |

### Recorte para a TiaNet

O contrato descreve um CRM com clientes e corretores. Na TiaNet, `cliente` mapeia
para **Tenant**; **corretor nao existe** — o Credor opera sozinho
(`FOUNDATION-001 §3`). Portanto os Eventos 3 e 5 do contrato ficam fora de
escopo, e o Evento 6 corresponde a inativacao de Tenant ja existente.

### Achados que condicionam o desenho

- **O webhook nao tem autenticacao**: a URL e o unico segredo. Por isso o
  recebimento so pode criar um pre-cadastro pendente, nunca lancar financeiro —
  quem descobrisse a URL emitiria divida no sistema.
- **`consultar_status` da porta `NotificationChannel` nao tem endpoint
  correspondente**: o status chega por webhook (`Receipt`), nao por consulta. O
  adapter precisara ler recibos armazenados, ou a porta muda.
- **Conexao e pre-requisito das duas direcoes**: nao se envia nada sem instancia
  conectada, o que exige criar tenant, criar instancia e escanear o QR.
- **O contrato nao descreve o formato de `POST /send/text`** (adicionado em
  2026-08-22, no IMP-346): ele fixa o nivel de autenticacao da rota e o
  comportamento de tenant inativo, mas nao traz exemplo de requisicao nem de
  resposta. O adapter foi escrito com payload `{number, text, id}` e aceite por
  `data.Info.ID`, extrapolados da documentacao publica do Evolution Go. **Nao
  esta validado contra o servidor.** Se divergir, envios bem-sucedidos viram
  `DESCONHECIDO` — sem risco de duplicata, porque esse resultado nao dispara
  retry, mas com prejuizo de escrituracao. Conferir no primeiro envio real e
  atualizar o contrato com o formato observado.

Consequencias ja incorporadas ao desenho:

- o envio de comprovante **nao** usa link `wa.me`; vai pela API;
- o adapter entra como implementacao de `NotificationChannel`
  (`src/emprestimo/domain/credit/automacao_ports.py`), ao lado do Resend;
- as conversas com o cliente serao registradas em `RegistroComunicacao`, que ja
  possui `ator_tipo`, `ator_identificador` e `provider_message_id`;
- `CanalComunicacao` **ja possui** o valor `whatsapp`, formalizado pela migration
  `0018` em 2026-08-20.

## 2.2 Agente de IA "TiaNet"

Atende pedidos que chegam pelo WhatsApp, registra o pre-cadastro e submete ao
Credor para aprovacao. E o segundo operador do sistema, conforme
`FOUNDATION-001 §3.1`.

| Campo | Valor |
|---|---|
| Situacao | planejado |
| Entra antes ou depois do wizard de emprestimo | *a preencher* |

## 2.3 Resend (e-mail)

`ResendNotificationChannel` existe no codigo e exige `RESEND_API_KEY` e
`RESEND_FROM`. **Nao se sabe se ha conta contratada.** Em `APP_ENV=production` o
worker recusa iniciar sem essas variaveis.

| Campo | Valor |
|---|---|
| Conta contratada | *a preencher* |
| Dominio remetente verificado | *a preencher* |

---

# 3. Infraestrutura

## 3.1 Ambiente local

Documentado em `docs/operations/ambiente-local-docker.md`. Stack completa em
Docker, validada ponta a ponta.

## 3.2 Servidor de producao

| Campo | Valor |
|---|---|
| Situacao | **nao provisionado** |
| Tipo (VPS, cloud gerenciada, PaaS) | *a preencher* |
| Dominio | *a preencher* |
| TLS | *a preencher* |
| Backup do PostgreSQL | *a preencher* |

Nao existe pipeline de CD no repositorio: `.github/workflows/quality.yml` e o
unico workflow e cobre apenas gates de qualidade.

---

# 4. Clientes e tenants

| Nome | Situacao |
|---|---|
| Ivonet | primeiro Tenant previsto; recebera a integracao de WhatsApp |

---

# 5. Ferramentas de apoio

## 5.1 Grafo de conhecimento (graphify)

`graphify-out/` e ignorado pelo git e vive apenas no disco de quem o gera.
Regerado em 2026-08-16 sobre o codigo: **8.267 nos, 24.614 arestas**, cobrindo
backend, frontend e testes. Diretorios gerados (`playwright-report`,
`test-results`, `.next`) sao excluidos — sem isso, cerca de 1.200 nos de bundle
minificado poluem o grafo.

Consultar antes de afirmar que algo nao existe. O grafo responde por relacao
entre simbolos do codigo; **nao cobre documentos** (extracao semantica nao foi
executada) nem nada listado neste arquivo.

O manifesto incremental nao foi salvo — a API mudou nesta versao do graphify —
entao um `--update` fara reconstrucao completa.

---

# 6. Perguntas em aberto

Itens que bloqueiam ou distorcem decisoes enquanto nao forem respondidos:

1. **Onde o agente recebe a mensagem?** Duas topologias possiveis, e elas mudam
   o escopo por inteiro:
   - (a) Evolution → webhook da TiaNet → registra conversa → agente le e cria o
     pre-cadastro;
   - (b) Evolution → agente → agente chama um endpoint autenticado da TiaNet.
   Em (b) a TiaNet **nao precisa de webhook publico**, o que e mais simples e
   mais seguro.
2. Onde ficam `evolution_tenant_id` e `evolution_api_key`? A entidade
   `Configuracao` (chave/valor por Tenant) existe, mas `api_key` e segredo e
   tabela generica de configuracao nao e lugar de segredo.
3. Ha ambiente de teste do Evolution, ou a integracao sera exercitada direto em
   producao?
4. Ha conta Resend ativa, ou o e-mail deve sair do escopo?
5. Qual servidor recebera o deploy, e existe dominio disponivel?

---

# 7. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.1.0 | 2026-08-16 | WhatsApp preenchido a partir do contrato Evolution Go versionado em `docs/whatsapp/`: modelo de tenant, tres niveis de autenticacao, limites de retry e payload, recorte para a TiaNet e achados que condicionam o desenho. |
| 1.0.0 | 2026-08-16 | Criado apos a sessao identificar que decisoes de desenho foram tomadas sem conhecer integracoes existentes fora do repositorio. |
