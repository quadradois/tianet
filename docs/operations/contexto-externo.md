# Contexto Externo

**Versao:** 1.3.1

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
| Ambiente de teste | **Nao existe** — respondido em 2026-08-25. Validacoes controladas usam producao com o numero do fundador; ver §6.2 |

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
- **O formato de `POST /send/text` foi VALIDADO em 2026-08-31** (IMP-352). O
  contrato nao o descrevia, e o adapter usava `{number, text, id}` com aceite por
  `data.Info.ID` extrapolados da documentacao publica. **Nao divergia.** Corpo e
  resposta observados foram incorporados a secao 8.1 de
  `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md`.

  O que a resposta real ensinou, e nao estava em lugar nenhum: **`data.Info.ID` e
  eco** do `id` que enviamos, nao identificador gerado pelo servidor.

  Isso **correlaciona** requisicao e resposta, e nao mais que isso: nao foi
  medido se o provedor suprime uma segunda mensagem com o mesmo `id`, entao um
  retry apos timeout, reset ou 5xx pode entregar duas vezes (§6.2). E **nao
  existe id do provedor**
  para consultar depois — entrega so se confirma por `Receipt`, que e o que
  `consultar_status` ja declarava.

Consequencias ja incorporadas ao desenho:

- o envio de comprovante **nao** usa link `wa.me`; vai pela API;
- o adapter entra como implementacao de `NotificationChannel`
  (`src/emprestimo/domain/credit/automacao_ports.py`), ao lado do Resend;
- as conversas conduzidas pelo agente **nao** usam `RegistroComunicacao`
  (corrigido em 2026-08-27 pelo PLAN-033/IMP-358): `devedor_id` e obrigatorio
  naquela tabela, e uma conversa de pre-cadastro ainda nao tem Devedor. O agente
  tera modelo proprio de sessao e mensagem, com `devedor_id` opcional.
  `RegistroComunicacao` continua registrando comunicacoes ligadas a um Devedor
  existente, como o comprovante e o aviso de sobra ja fazem;
- `CanalComunicacao` **ja possui** o valor `whatsapp`, formalizado pela migration
  `0018` em 2026-08-20.

## 2.2 Agente de IA "TiaNet"

Atende pedidos que chegam pelo WhatsApp, registra o pre-cadastro e submete ao
Credor para aprovacao. E o segundo operador do sistema, conforme
`FOUNDATION-001 §3.1`.

| Campo | Valor |
|---|---|
| Situacao | desenhado — PLAN-033 v1.1.0 |
| Entra antes ou depois do wizard de emprestimo | *a preencher* |
| Topologia de recepcao | **Evolution -> agente -> endpoint autenticado da TiaNet** (decidido em 2026-08-25) |
| Contextos de conversa | **dois, isolados** (registrado em 2026-08-27): Operadora (allowlist de numeros, comeca so com o da Tia, unico com leitura de carteira) e Pre-cadastro (remetente desconhecido, zero acesso a dados). Nunca compartilham sessao, historico ou ferramenta. |
| Autenticacao do remetente | allowlist de numero **nao e autenticacao**: `Info.Sender` e forjavel por quem tiver a URL do webhook. O contexto Operadora so liga com prova de origem no reverse proxy; sem prova, fica desabilitado fail-closed (PLAN-033/IMP-359). |

**A TiaNet nao tera webhook publico.** A decisao foi pela topologia (b): o
agente recebe do Evolution e chama um endpoint autenticado da TiaNet, no mesmo
padrao de autenticacao que o resto do sistema ja usa.

O que isso evita, e por isso importa: a alternativa (a) exigiria uma rota **nao
autenticada aberta para a internet**, mais validacao de assinatura do Evolution,
mais uma peca para manter e mais superficie exposta. Nada disso e necessario
quando o agente ja e um cliente autenticado.

## 2.3 Resend (e-mail)

**E-mail esta fora do escopo do MVP.** Decisao do fundador em 2026-08-25: nao ha
conta Resend contratada, e o canal real da operacao e o WhatsApp.

| Campo | Valor |
|---|---|
| Conta contratada | **nao** |
| Dominio remetente verificado | nao se aplica |

`ResendNotificationChannel` continua no codigo, atras da porta
`NotificationChannel`. Se `RESEND_API_KEY` e `RESEND_FROM` existirem, ele e
usado; nada foi removido.

**O que mudou:** `APP_ENV=production` sem essas variaveis derrubava o worker na
subida. Isso bloqueava o deploy inteiro por causa de um canal que a operacao nao
usa. Agora o worker sobe.

**O que nao mudou, de proposito:** o canal ausente **nao** vira
`FakeNotificationChannel`. Aquele fake devolve `ACEITA` com um
`provider_message_id` sintetico — em teste e util, em producao seria mentira: a
trilha registraria como entregue um e-mail que nunca saiu. Em vez disso entra o
`CanalNaoConfiguradoNotificationChannel`, que recusa com
`FALHA_PERMANENTE` e codigo `canal_nao_configurado:email`. Terminal, porque
retry nao configura credencial, e **nomeado**, porque o operador precisa ver o
motivo na trilha.

---

# 3. Infraestrutura

## 3.1 Ambiente local

Documentado em `docs/operations/ambiente-local-docker.md`. Stack completa em
Docker, validada ponta a ponta.

## 3.2 Servidor de producao

| Campo | Valor |
|---|---|
| Situacao | **VPS provisionada em 2026-08-31.** Sem deploy ainda |
| Tipo | VPS |
| Dominio | `tianet.com.br` — ativo |
| TLS | *pendente* |
| Backup do PostgreSQL | *pendente* |
| CD e endurecimento | *pendentes* |

O insumo de **servidor** que bloqueava o **IMP-359** deixou de existir: a maquina
e o dominio estao disponiveis. Falta trabalho nosso — deploy, TLS, backup, CD e
endurecimento —, e a sequencia acordada com o fundador poe isso **depois** do
PLAN-034.

**Um insumo externo permanece:** a escolha do provedor de IA com o cliente. Sem
ela, `LLM_BASE_URL`, `LLM_API_KEY` e `LLM_MODEL` nao tem valor para provisionar,
e o IMP-359 nao fecha. Ver DR-005 e §2.2.

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

# 6. Perguntas respondidas em 2026-08-25

As cinco perguntas que estavam abertas foram respondidas pelo fundador. Ficam
registradas com a resposta, para que ninguem as reabra como se fossem duvida.

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Onde o agente recebe a mensagem? | **(b)** Evolution -> agente -> endpoint autenticado da TiaNet. Sem webhook publico. Ver §2.2. |
| 2 | Onde ficam `evolution_tenant_id` e `evolution_api_key`? | **Variavel de ambiente**, como ja e hoje (`EVOLUTION_INSTANCE_TOKEN`). Ver abaixo. |
| 3 | Ha ambiente de teste do Evolution? | **Nao.** A validacao sera em producao, com o numero do proprio fundador. Ver abaixo. |
| 4 | Ha conta Resend ativa? | **Nao.** E-mail fora do escopo do MVP. Ver §2.3. |
| 5 | Qual servidor recebe o deploy? | **VPS provisionada e dominio `tianet.com.br` ativo** desde 2026-08-31. Faltam deploy, TLS, backup, CD e endurecimento. Ver §3.2. |

## 6.1 Segredo do Evolution: variavel de ambiente

> **Superado em parte pela [DR-006](../governance/decision-requests/DR-006-conexao-do-whatsapp-dentro-da-plataforma.md)
> (2026-08-31).** O fundador decidiu que a conexao do WhatsApp passa a ter **tela
> de QR na plataforma**, porque quem opera nao tem conta no `diamondgreen.com.br`.
> Com isso o **token da instancia** passa a ser persistido **cifrado em repouso**
> no banco — sem isso a conexao nao sobrevive a um restart sem edicao manual do
> `.env`, que e o atrito que a tela elimina.
>
> O que **permanece** desta secao: `EVOLUTION_HOST` e as credenciais de **gestao**
> do tenant Evolution continuam em variavel de ambiente; a recusa de usar a
> entidade `Configuracao` continua valida, e pelo mesmo motivo — a DR-006 escolheu
> armazenamento cifrado justamente para nao repetir esse erro.
>
> O "limite declarado" abaixo previa que isso viraria tabela de segredos com
> criptografia quando cada Tenant tivesse instancia propria. A
> [ADR-003](../architecture/adrs/ADR-003-escopo-single-tenant-do-v1.md) decidiu que
> **nao havera segundo Tenant no v1** — a tabela chegou por outro caminho, o da
> ergonomia da conexao, e guarda um unico token.


O adapter ja recebe host e token por injecao, e `main()` os le de
`EVOLUTION_HOST` e `EVOLUTION_INSTANCE_TOKEN`. **Nada muda no codigo.**

Por que nao a entidade `Configuracao`: e tabela generica chave/valor, sem
criptografia em repouso, e exposta por endpoints de configuracao — o segredo
vazaria por leitura legitima, que e o pior tipo de vazamento porque nao parece
incidente.

**Limite declarado:** variavel de ambiente e uma instancia por processo. Serve
enquanto ha um credor e um Tenant. **No dia em que cada Tenant tiver instancia
propria do Evolution**, isso vira tabela de segredos com criptografia e
rotacao — escopo real, nao ajuste. Registrar agora evita descobrir no meio da
migracao.

## 6.2 Validacao do formato de envio: producao, com o numero do fundador

> **VALIDADO em 2026-08-31.** Envio real executado pela propria classe de
> producao (`EvolutionWhatsAppNotificationChannel`), para o numero do fundador,
> na instancia `adm_tianet`. Resultado: `ACEITA` / `accepted`.
>
> **O formato nao divergia.** `data.Info.ID` e o criterio correto — e a resposta
> revelou que ele e **eco do `id` enviado**, nao identificador gerado pelo
> servidor. O corpo e a resposta observados foram incorporados ao contrato, na
> secao 8.1 de `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md`, que ate entao listava
> a rota sem fixar seu formato.
>
> Consequencia registrada: como o identificador e nosso, ele **correlaciona**
> requisicao e resposta. Nao foi medido se o provedor suprime uma segunda
> mensagem com o mesmo `id`, entao correlacionar nao e deduplicar. E **nao ha
> identificador do provedor** para consultar depois — entrega so se confirma por
> `Receipt`, o que o adapter ja declarava em `consultar_status`.

Nao ha ambiente de teste do Evolution — a validacao acima foi feita em producao,
para o numero do proprio fundador, sem que nenhum devedor real recebesse
mensagem. Esse continua sendo o unico caminho para conferencias futuras.

**O que ficou aberto — e nao e uma decisao, sao defeitos.** A validacao
respondeu o formato, nao a deduplicacao. Mas a politica para esse caso **ja esta
decidida** na ADR-009: timeout ou reset *depois de transmitir bytes* e
`resultado_desconhecido`, que **bloqueia retry e concilia** — porque nao ha prova
de que a requisicao nao foi aceita.

Sao **tres pontos** no adapter, e os tres levam a mesma consequencia concreta:
o Scheduler reenvia sem prova de que o primeiro envio nao foi aceito. Se o
provedor nao deduplicar pelo `id` — nao medido —, o destinatario recebe duas
vezes. Hoje o adapter do WhatsApp esta ligado ao **comprovante do lancamento** do
emprestimo e ao **aviso de sobra de pagamento** (`enviar_lembrete` usa o canal de
e-mail), entao sao esses dois — dois comprovantes do mesmo emprestimo sugerem
dois emprestimos. Quando o lembrete migrar para o WhatsApp, alcanca cobranca.

- **Resposta 5xx** (`_classificar_resposta`, codigo `provider_5xx`) — a tabela da ADR nomeia `5xx` como o
  primeiro item de `resultado_desconhecido`; o adapter devolve
  `FALHA_TEMPORARIA` com codigo `provider_5xx`. Um 502 ou 504 de gateway chega
  depois de o upstream ter aceitado, e nao ha como distinguir isso de um 500 que
  nao aceitou nada;
- **Transporte indistinto** (o `except` de `enviar`) — o `except` unico devolve
  `FALHA_TEMPORARIA` para todo `TimeoutException` e todo `TransportError`,
  misturando `ConnectTimeout`/`ConnectError` (anteriores ao envio) com
  `ReadError`, `WriteError`, `CloseError` e `RemoteProtocolError` (resets **depois** de
  transmitir, que a ADR nomeia ao lado do timeout);
- **`DecodingError` escapa** (o mesmo `except`, nos dois adapters) — ela e
  `RequestError`, nao `TransportError`, entao o `except` nao a captura; sobe do
  adapter, e o `SchedulerWorker` converte qualquer excecao do handler em
  `FALHA_TEMPORARIA`. Como o decoding falha lendo o **corpo da resposta**, a
  requisicao ja foi enviada. Em `consultar_status` a mesma
  excecao nao vira retry: vira erro nao tratado na conciliacao administrativa.

A correcao e separar o que a ADR separa: `ConnectTimeout`, `ConnectError` e
`PoolTimeout` sao falhas *comprovadamente anteriores* ao envio de bytes —
temporarias, podem reenviar (o `PoolTimeout` estoura esperando uma conexao do
pool, antes de existir requisicao); `ReadTimeout`, `WriteTimeout`, `ReadError`,
`WriteError`, `CloseError`, `RemoteProtocolError`, `DecodingError` e o `5xx` nao tem prova de
nao aceite, e viram `resultado_desconhecido`.

O proprio adapter ja classifica **2xx malformado** como desconhecido, que e a
linha vizinha da mesma tabela — os tres pontos acima sao omissao, nao desenho.
Corrigir isso e item de codigo, nao de documentacao.

---

# 7. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.3.1 | 2026-09-02 | A §6.2 registrava so um terco do problema. Alem do timeout indistinto: **resposta 5xx** vira `FALHA_TEMPORARIA` e a tabela da ADR-009 poe `5xx` em `resultado_desconhecido`; e **`DecodingError` escapa** do `except` (e `RequestError`, nao `TransportError`) direto para o retry do Scheduler. Sao tres pontos, nao um; e o `except` de transporte ainda mistura falhas anteriores ao envio com resets posteriores (`ReadError`, `WriteError`, `RemoteProtocolError`). Registrado tambem o que de fato duplica hoje: comprovante e aviso de sobra, nao cobranca — o lembrete usa o canal de e-mail. E o `PoolTimeout` entra na lista de falhas anteriores ao envio de bytes — estoura esperando conexao do pool, antes de existir requisicao. |
| 1.3.0 | 2026-08-27 | Reconciliacoes do PLAN-033/IMP-358: conversas do agente saem de `RegistroComunicacao` (devedor_id obrigatorio impede) e ganham modelo proprio; contextos Operadora/Pre-cadastro e o limite da allowlist registrados na §2.2. |
| 1.2.0 | 2026-08-25 | As cinco perguntas em aberto foram respondidas pelo fundador e a secao §6 deixou de ser duvida para virar registro. E-mail saiu do escopo do MVP e o worker deixou de ser derrubado por falta de conta Resend — com recusa nomeada no lugar do fake que fingia entrega. Topologia do agente decidida sem webhook publico. Segredo do Evolution fica em variavel de ambiente, com o limite de uma instancia por processo declarado. |
| 1.1.0 | 2026-08-16 | WhatsApp preenchido a partir do contrato Evolution Go versionado em `docs/whatsapp/`: modelo de tenant, tres niveis de autenticacao, limites de retry e payload, recorte para a TiaNet e achados que condicionam o desenho. |
| 1.0.0 | 2026-08-16 | Criado apos a sessao identificar que decisoes de desenho foram tomadas sem conhecer integracoes existentes fora do repositorio. |
